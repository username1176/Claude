"""Celery tasks for genome analysis.

The main task, ``run_genome_analysis``, is dispatched after a VCF upload
and orchestrates the full pipeline:

    Decrypt file → Parse VCF → Query external APIs → Score risks →
    Generate recommendations → Generate AI report → Persist results
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import httpx
from celery import shared_task

from app.extensions import db
from app.models.genome import (
    GenomeAnalysis,
    GenomeUpload,
    HealthRecommendation,
    Variant,
    VariantAnnotation,
)
from app.services.encryption import decrypt_dek, decrypt_file
from app.services.genome_analyzer import (
    AnnotationResult,
    ParsedVariant,
    detect_genome_build,
    generate_recommendations,
    parse_vcf,
    query_clinvar,
    query_ensembl_vep,
    query_gwas_catalog,
    query_ncbi_gene,
    score_risks,
)
from app.services.report_generator import generate_report

logger = logging.getLogger(__name__)


def _update_analysis(analysis: GenomeAnalysis, **kwargs) -> None:
    """Update analysis fields and commit."""
    for key, value in kwargs.items():
        setattr(analysis, key, value)
    db.session.commit()


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def run_genome_analysis(self, analysis_id: str) -> dict:
    """Run the full genome analysis pipeline.

    Args:
        analysis_id: UUID of the GenomeAnalysis record.

    Returns:
        Summary dict with counts and status.
    """
    from flask import current_app

    analysis = db.session.get(GenomeAnalysis, analysis_id)
    if not analysis:
        logger.error("Analysis %s not found", analysis_id)
        return {"error": "Analysis not found"}

    upload = analysis.upload
    if not upload:
        _update_analysis(analysis, status="error", error_message="Upload record missing")
        return {"error": "Upload record missing"}

    _update_analysis(analysis, status="running", started_at=datetime.now(timezone.utc))

    try:
        # ── Step 1: Decrypt and parse VCF ────────────────────────────────
        logger.info("Step 1: Decrypting and parsing VCF for analysis %s", analysis_id)

        master_key = current_app.config["MASTER_ENCRYPTION_KEY"]
        user = upload.user
        dek = decrypt_dek(user.data_encryption_key_enc, master_key)

        encrypted_path = Path(upload.file_path_encrypted)
        vcf_bytes = decrypt_file(encrypted_path, dek)

        genome_build = detect_genome_build(vcf_bytes)
        upload.genome_build = genome_build
        db.session.commit()

        parsed_variants = parse_vcf(vcf_bytes)
        if not parsed_variants:
            _update_analysis(
                analysis,
                status="error",
                error_message="No variants found in VCF file. Check file format.",
            )
            return {"error": "No variants parsed"}

        analysis.variant_count = len(parsed_variants)
        db.session.commit()

        # ── Step 2: Persist parsed variants ──────────────────────────────
        logger.info("Step 2: Storing %d parsed variants", len(parsed_variants))

        variant_models: list[Variant] = []
        for pv in parsed_variants:
            vm = Variant(
                analysis_id=analysis_id,
                rsid=pv.rsid,
                chromosome=pv.chromosome,
                position=pv.position,
                ref_allele=pv.ref_allele,
                alt_allele=pv.alt_allele,
                genotype=pv.genotype,
                quality=pv.quality,
            )
            db.session.add(vm)
            variant_models.append(vm)
        db.session.commit()

        # ── Step 3: Query external APIs ──────────────────────────────────
        logger.info("Step 3: Querying external genome databases")

        # Collect rsIDs for batch queries
        rsids_with_id = [(pv.rsid, vm.id) for pv, vm in zip(parsed_variants, variant_models) if pv.rsid]
        rsid_list = list({rsid for rsid, _ in rsids_with_id})
        rsid_to_variant_id: dict[str, str] = {rsid: vid for rsid, vid in rsids_with_id}

        ncbi_api_key = current_app.config.get("NCBI_API_KEY", "")

        # All annotations keyed by rsID or "chrom:pos:ref:alt"
        all_annotations: dict[str, list[AnnotationResult]] = {}

        with httpx.Client(timeout=httpx.Timeout(connect=10, read=30, write=10, pool=10)) as client:
            # 3a. Ensembl VEP
            logger.info("  3a: Querying Ensembl VEP (%d variants)", len(parsed_variants))
            vep_annotations = query_ensembl_vep(parsed_variants, client, genome_build)
            for key, anns in vep_annotations.items():
                all_annotations.setdefault(key, []).extend(anns)

            # 3b. ClinVar
            logger.info("  3b: Querying ClinVar (%d rsIDs)", len(rsid_list))
            clinvar_annotations = query_clinvar(rsid_list, client, ncbi_api_key)
            for rsid, anns in clinvar_annotations.items():
                all_annotations.setdefault(rsid, []).extend(anns)

            # 3c. GWAS Catalog
            logger.info("  3c: Querying GWAS Catalog (%d rsIDs)", len(rsid_list))
            gwas_annotations = query_gwas_catalog(rsid_list, client)
            for rsid, anns in gwas_annotations.items():
                all_annotations.setdefault(rsid, []).extend(anns)

            # 3d. NCBI Gene summaries for unique gene symbols
            gene_symbols = set()
            for anns in all_annotations.values():
                for ann in anns:
                    if ann.gene_symbol:
                        gene_symbols.add(ann.gene_symbol)
            if gene_symbols:
                logger.info("  3d: Querying NCBI Gene (%d genes)", len(gene_symbols))
                query_ncbi_gene(list(gene_symbols), client, ncbi_api_key)

        # ── Step 4: Persist annotations ──────────────────────────────────
        logger.info("Step 4: Storing annotations")

        annotated_variant_ids: set[str] = set()
        for key, anns in all_annotations.items():
            # Resolve key to variant_id
            # key may be rsID or "chrom:pos:ref:alt"
            variant_id = rsid_to_variant_id.get(key)
            if not variant_id:
                # Try matching by chrom:pos:ref:alt
                for pv, vm in zip(parsed_variants, variant_models):
                    vkey = f"{pv.chromosome}:{pv.position}:{pv.ref_allele}:{pv.alt_allele}"
                    if vkey == key:
                        variant_id = vm.id
                        break
            if not variant_id:
                continue

            annotated_variant_ids.add(variant_id)
            for ann in anns:
                db.session.add(
                    VariantAnnotation(
                        variant_id=variant_id,
                        source=ann.source,
                        gene_symbol=ann.gene_symbol,
                        consequence=ann.consequence,
                        clinical_significance=ann.clinical_significance,
                        condition_name=ann.condition_name,
                        trait_association=ann.trait_association,
                        risk_allele=ann.risk_allele,
                        odds_ratio=ann.odds_ratio,
                        p_value=ann.p_value,
                        pubmed_ids=ann.pubmed_ids,
                        source_record_id=ann.source_record_id,
                    )
                )
        db.session.commit()

        analysis.annotated_variant_count = len(annotated_variant_ids)
        db.session.commit()

        # ── Step 5: Score risks ──────────────────────────────────────────
        logger.info("Step 5: Scoring risk categories")

        risk_categories = score_risks(parsed_variants, all_annotations)
        risk_summary = {
            rc.category: {
                "label": rc.label,
                "score": rc.score,
                "level": rc.level,
                "key_variants": rc.key_variants,
            }
            for rc in risk_categories
        }
        analysis.risk_summary_json = json.dumps(risk_summary)
        db.session.commit()

        # ── Step 6: Generate recommendations ─────────────────────────────
        logger.info("Step 6: Generating recommendations")

        recommendations = generate_recommendations(parsed_variants)
        for rec in recommendations:
            db.session.add(
                HealthRecommendation(
                    analysis_id=analysis_id,
                    category=rec.category,
                    title=rec.title,
                    body=rec.body,
                    evidence_rsids=rec.evidence_rsids,
                    evidence_sources=rec.evidence_sources,
                    confidence=rec.confidence,
                    priority=rec.priority,
                )
            )
        db.session.commit()

        # ── Step 7: Generate AI report ───────────────────────────────────
        logger.info("Step 7: Generating natural language report")

        openai_key = current_app.config.get("OPENAI_API_KEY", "")
        report_text = generate_report(
            risk_categories=risk_categories,
            recommendations=recommendations,
            variant_count=len(parsed_variants),
            annotated_count=len(annotated_variant_ids),
            openai_api_key=openai_key,
        )

        # ── Step 8: Finalize ─────────────────────────────────────────────
        now = datetime.now(timezone.utc)
        _update_analysis(
            analysis,
            status="complete",
            ai_report_text=report_text,
            ai_report_generated_at=now,
            completed_at=now,
        )

        logger.info(
            "Analysis %s complete: %d variants, %d annotated, %d recommendations",
            analysis_id, len(parsed_variants), len(annotated_variant_ids), len(recommendations),
        )
        return {
            "analysis_id": analysis_id,
            "status": "complete",
            "variant_count": len(parsed_variants),
            "annotated_variant_count": len(annotated_variant_ids),
            "recommendation_count": len(recommendations),
        }

    except Exception as exc:
        logger.exception("Analysis %s failed: %s", analysis_id, exc)
        _update_analysis(
            analysis,
            status="error",
            error_message=str(exc)[:2000],
            completed_at=datetime.now(timezone.utc),
        )
        # Retry on transient errors (network, external API issues)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        return {"error": str(exc), "analysis_id": analysis_id}
