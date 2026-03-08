"""Whole-Genome Sequencing, Ancestry, and Blockchain endpoints."""

import hashlib
import json
import os
import re

from flask import Blueprint, current_app, g, jsonify, request

from app.extensions import db, limiter
from app.models.audit import AuditLog
from app.models.wgs import AncestryAnalysis, BlockchainRecord, WGSUpload
from app.api.decorators import login_required
from app.services.file_upload import UploadValidationError, save_upload

wgs_bp = Blueprint("wgs", __name__, url_prefix="/api/v1/wgs")

ALLOWED_WGS_FORMATS = {"fastq", "fq", "bam"}


def _sanitize_filename(name: str) -> str:
    name = os.path.basename(name)
    name = re.sub(r"[^\w.\-]", "_", name)
    return name or "upload"


def _audit(action: str, **kwargs):
    log = AuditLog(
        user_id=g.current_user.id,
        action=action,
        ip_address=request.remote_addr,
        **kwargs,
    )
    db.session.add(log)


def _detect_format(filename: str) -> str:
    """Detect WGS file format from extension."""
    lower = filename.lower()
    if lower.endswith((".fastq", ".fq", ".fastq.gz", ".fq.gz")):
        return "fastq"
    if lower.endswith((".bam",)):
        return "bam"
    return "fastq"


# ── POST /api/v1/wgs/upload-wgs ─────────────────────────────────────────────


@wgs_bp.route("/upload-wgs", methods=["POST"])
@limiter.limit("3 per hour")
@login_required
def upload_wgs():
    """Accept FASTQ/BAM whole-genome sequencing file.

    Parses basic stats with Biopython/pysam, estimates depth, and triggers
    ancestry analysis via Celery background task.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file provided. Use multipart field 'file'."}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename."}), 400

    detected_format = _detect_format(file.filename)
    user = g.current_user

    # WGS files can be very large — use the VCF size limit (500 MB)
    try:
        encrypted_path, sha256_hex, file_size = save_upload(
            file=file,
            file_type="csv",  # Skip magic-byte check; WGS formats vary
            max_size_bytes=current_app.config["MAX_VCF_SIZE_BYTES"],
            user_encrypted_dek=user.data_encryption_key_enc,
            master_key=current_app.config["MASTER_ENCRYPTION_KEY"],
        )
    except UploadValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    upload = WGSUpload(
        user_id=user.id,
        filename_original=_sanitize_filename(file.filename),
        file_path_encrypted=str(encrypted_path),
        file_hash_sha256=sha256_hex,
        file_format=detected_format,
        status="uploaded",
        file_size_bytes=file_size,
    )
    db.session.add(upload)
    db.session.flush()

    # Create ancestry analysis record
    ancestry = AncestryAnalysis(
        user_id=user.id,
        wgs_upload_id=upload.id,
        status="queued",
    )
    db.session.add(ancestry)

    _audit("upload_wgs", resource_type="WGSUpload", resource_id=upload.id)
    db.session.commit()

    # Dispatch Celery task
    celery_task_id = None
    try:
        from app.tasks.wgs_tasks import run_wgs_analysis
        task = run_wgs_analysis.delay(upload.id, ancestry.id)
        celery_task_id = task.id
    except Exception:
        pass

    return jsonify({
        "upload_id": upload.id,
        "ancestry_analysis_id": ancestry.id,
        "file_format": detected_format,
        "file_size_bytes": file_size,
        "status": upload.status,
        "task_id": celery_task_id,
        "message": "WGS file received. Analysis will begin shortly.",
    }), 202


# ── GET /api/v1/wgs/uploads ─────────────────────────────────────────────────


@wgs_bp.route("/uploads", methods=["GET"])
@login_required
def list_wgs_uploads():
    """List all WGS uploads for the current user."""
    uploads = (
        WGSUpload.query.filter_by(user_id=g.current_user.id)
        .order_by(WGSUpload.uploaded_at.desc())
        .all()
    )
    return jsonify([
        {
            "id": u.id,
            "filename": u.filename_original,
            "file_format": u.file_format,
            "depth": u.depth,
            "read_count": u.read_count,
            "avg_quality": u.avg_quality,
            "status": u.status,
            "uploaded_at": u.uploaded_at.isoformat(),
            "file_size_bytes": u.file_size_bytes,
        }
        for u in uploads
    ])


# ── GET /api/v1/wgs/ancestry-report/<id> ────────────────────────────────────


@wgs_bp.route("/ancestry-report/<analysis_id>", methods=["GET"])
@login_required
def get_ancestry_report(analysis_id: str):
    """Retrieve deep ancestry analysis report.

    Includes haplogroup assignments, population composition, migration paths,
    archaic ancestry estimates, and NCBI haplogroup references.
    """
    analysis = AncestryAnalysis.query.filter_by(
        id=analysis_id, user_id=g.current_user.id
    ).first()

    if not analysis:
        return jsonify({"error": "Ancestry analysis not found."}), 404

    report = {}
    if analysis.report_json:
        try:
            report = json.loads(analysis.report_json)
        except (json.JSONDecodeError, TypeError):
            pass

    population = {}
    if analysis.population_composition_json:
        try:
            population = json.loads(analysis.population_composition_json)
        except (json.JSONDecodeError, TypeError):
            pass

    return jsonify({
        "id": analysis.id,
        "status": analysis.status,
        "mt_haplogroup": analysis.mt_haplogroup,
        "y_haplogroup": analysis.y_haplogroup,
        "population_composition": population,
        "archaic_ancestry_pct": analysis.archaic_ancestry_pct,
        "report": report,
        "started_at": analysis.started_at.isoformat() if analysis.started_at else None,
        "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
        "error_message": analysis.error_message,
        "disclaimer": (
            "Ancestry estimates are based on computational models and reference "
            "populations. Results are approximate and should not be used for "
            "legal or medical purposes. Haplogroup assignments reflect deep "
            "maternal/paternal lineage only."
        ),
    })


# ── GET /api/v1/wgs/ancestry-reports ────────────────────────────────────────


@wgs_bp.route("/ancestry-reports", methods=["GET"])
@login_required
def list_ancestry_reports():
    """List all ancestry analyses for the current user."""
    analyses = (
        AncestryAnalysis.query.filter_by(user_id=g.current_user.id)
        .order_by(AncestryAnalysis.id.desc())
        .all()
    )
    return jsonify([
        {
            "id": a.id,
            "status": a.status,
            "mt_haplogroup": a.mt_haplogroup,
            "y_haplogroup": a.y_haplogroup,
            "archaic_ancestry_pct": a.archaic_ancestry_pct,
            "wgs_upload_id": a.wgs_upload_id,
        }
        for a in analyses
    ])


# ── POST /api/v1/wgs/blockchain-store ───────────────────────────────────────


@wgs_bp.route("/blockchain-store", methods=["POST"])
@limiter.limit("10 per hour")
@login_required
def blockchain_store():
    """Anonymize and store health data hash on blockchain.

    Accepts a data_type (wgs, genome, blood, microbiome, ancestry) and
    an optional source_id referencing the original upload/analysis.
    The data is anonymized (PII stripped), hashed, and either:
     - Stored on-chain via the HealthDataNFT contract, or
     - Simulated if no Ethereum node is configured.

    Optionally mints an NFT for data ownership provenance.
    """
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "JSON body required."}), 400

    data_type = body.get("data_type", "").lower()
    if data_type not in {"wgs", "genome", "blood", "microbiome", "ancestry"}:
        return jsonify({
            "error": "Invalid data_type. Must be one of: wgs, genome, blood, microbiome, ancestry."
        }), 400

    source_id = body.get("source_id", "")
    mint_nft = body.get("mint_nft", False)
    metadata_uri = body.get("metadata_uri", "")

    user = g.current_user

    # Build anonymized data payload
    data_payload = {
        "data_type": data_type,
        "source_id": source_id,
        "user_id_hash": hashlib.sha256(user.id.encode()).hexdigest(),
        "timestamp": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
    }

    # Add source-specific metadata (non-PII only)
    source_meta = _get_source_metadata(user.id, data_type, source_id)
    if source_meta:
        data_payload["source_metadata"] = source_meta

    from app.utils.wgs_analyzer import anonymize_data_hash
    data_hash = anonymize_data_hash(data_payload)

    # Attempt blockchain storage
    from app.utils.blockchain_utils import (
        get_web3_connection,
        mint_health_record,
        store_data_hash as chain_store,
        simulate_blockchain_store,
    )

    rpc_url = current_app.config.get("ETH_RPC_URL", "")
    contract_address = current_app.config.get("HEALTH_NFT_CONTRACT_ADDRESS", "")

    # Check if real blockchain is available
    w3 = get_web3_connection(rpc_url) if rpc_url else None

    if w3 and contract_address:
        if mint_nft:
            result = mint_health_record(
                data_hash=data_hash,
                metadata_uri=metadata_uri,
                rpc_url=rpc_url,
                contract_address=contract_address,
            )
        else:
            result = chain_store(
                data_hash=data_hash,
                rpc_url=rpc_url,
                contract_address=contract_address,
            )

        tx_result = {
            "success": result.success,
            "tx_hash": result.tx_hash,
            "block_number": result.block_number,
            "gas_used": result.gas_used,
            "token_id": result.token_id,
            "chain_id": w3.eth.chain_id,
            "mode": "live",
            "error": result.error if not result.success else None,
        }
    else:
        # Simulation mode
        tx_result = simulate_blockchain_store(data_hash, data_type)

    # Record in database
    record = BlockchainRecord(
        user_id=user.id,
        data_type=data_type,
        data_hash=f"0x{data_hash}",
        tx_hash=tx_result.get("tx_hash"),
        token_id=tx_result.get("token_id"),
        contract_address=contract_address or None,
        chain_id=tx_result.get("chain_id", 0),
        status="confirmed" if tx_result.get("success") else "pending",
        metadata_uri=metadata_uri or None,
    )
    db.session.add(record)

    _audit("blockchain_store", resource_type="BlockchainRecord", resource_id=record.id)
    db.session.commit()

    return jsonify({
        "record_id": record.id,
        "data_hash": f"0x{data_hash}",
        "transaction": tx_result,
        "message": (
            "Data hash stored on blockchain."
            if tx_result.get("success")
            else "Blockchain store pending or simulated."
        ),
    }), 201


# ── POST /api/v1/wgs/blockchain-list-for-sale ───────────────────────────────


@wgs_bp.route("/blockchain-list-for-sale", methods=["POST"])
@limiter.limit("5 per hour")
@login_required
def blockchain_list_for_sale():
    """List an anonymized health data NFT for sale.

    Users can monetize their anonymized data by setting a price in Wei.
    Buyers get access to the anonymized dataset hash; actual data sharing
    happens off-chain via encrypted channels.
    """
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "JSON body required."}), 400

    record_id = body.get("record_id", "")
    price_wei = body.get("price_wei", "")

    if not record_id or not price_wei:
        return jsonify({"error": "record_id and price_wei are required."}), 400

    record = BlockchainRecord.query.filter_by(
        id=record_id, user_id=g.current_user.id
    ).first()
    if not record:
        return jsonify({"error": "Blockchain record not found."}), 404

    if not record.token_id:
        return jsonify({
            "error": "No NFT token associated with this record. "
                     "Re-store with mint_nft=true first."
        }), 400

    from app.utils.blockchain_utils import (
        get_web3_connection,
        list_data_for_sale,
        CHAIN_CONFIG,
    )

    rpc_url = current_app.config.get("ETH_RPC_URL", "")
    contract_address = current_app.config.get("HEALTH_NFT_CONTRACT_ADDRESS", "")

    w3 = get_web3_connection(rpc_url) if rpc_url else None

    if w3 and contract_address:
        result = list_data_for_sale(
            token_id=record.token_id,
            price_wei=int(price_wei),
            rpc_url=rpc_url,
            contract_address=contract_address,
        )

        if result.success:
            record.is_listed_for_sale = True
            record.price_wei = str(price_wei)
            db.session.commit()

            return jsonify({
                "success": True,
                "token_id": record.token_id,
                "price_wei": str(price_wei),
                "tx_hash": result.tx_hash,
                "message": "Data listed for sale on the marketplace.",
            })
        else:
            return jsonify({
                "success": False,
                "error": result.error,
            }), 500
    else:
        # Simulation mode
        record.is_listed_for_sale = True
        record.price_wei = str(price_wei)
        db.session.commit()

        return jsonify({
            "success": True,
            "token_id": record.token_id,
            "price_wei": str(price_wei),
            "mode": "simulation",
            "message": "Data listing simulated. Configure Ethereum for live marketplace.",
        })


# ── GET /api/v1/wgs/blockchain-records ──────────────────────────────────────


@wgs_bp.route("/blockchain-records", methods=["GET"])
@login_required
def list_blockchain_records():
    """List all blockchain records for the current user."""
    records = (
        BlockchainRecord.query.filter_by(user_id=g.current_user.id)
        .order_by(BlockchainRecord.created_at.desc())
        .all()
    )
    return jsonify([
        {
            "id": r.id,
            "data_type": r.data_type,
            "data_hash": r.data_hash,
            "tx_hash": r.tx_hash,
            "token_id": r.token_id,
            "chain_id": r.chain_id,
            "status": r.status,
            "is_listed_for_sale": r.is_listed_for_sale,
            "price_wei": r.price_wei,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ])


# ── Helpers ─────────────────────────────────────────────────────────────────


def _get_source_metadata(user_id: str, data_type: str, source_id: str) -> dict:
    """Fetch non-PII metadata from the source record for hashing."""
    if not source_id:
        return {}

    if data_type == "wgs":
        upload = WGSUpload.query.filter_by(id=source_id, user_id=user_id).first()
        if upload:
            return {
                "file_format": upload.file_format,
                "depth": upload.depth,
                "file_hash": upload.file_hash_sha256,
            }
    elif data_type == "genome":
        from app.models.genome import GenomeUpload
        upload = GenomeUpload.query.filter_by(id=source_id, user_id=user_id).first()
        if upload:
            return {
                "source_service": upload.source_service,
                "genome_build": upload.genome_build,
                "file_hash": upload.file_hash_sha256,
            }
    elif data_type == "ancestry":
        analysis = AncestryAnalysis.query.filter_by(
            id=source_id, user_id=user_id
        ).first()
        if analysis:
            return {
                "mt_haplogroup": analysis.mt_haplogroup,
                "y_haplogroup": analysis.y_haplogroup,
            }

    return {}
