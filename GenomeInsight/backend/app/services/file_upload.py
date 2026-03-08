"""Secure file upload handling.

Validates file type via magic bytes, enforces size limits, computes
SHA-256 hash, writes to a temp location, then encrypts to the final
encrypted path using the user's DEK.
"""

import hashlib
import uuid
from pathlib import Path

from flask import current_app
from werkzeug.datastructures import FileStorage

from app.services.encryption import decrypt_dek, encrypt_file

# Magic byte signatures for allowed file types
VCF_MAGIC = b"##fileformat=VCF"
GZIP_MAGIC = b"\x1f\x8b"
PDF_MAGIC = b"%PDF"

# Allowed CSV: must be valid UTF-8 text (checked heuristically)


class UploadValidationError(Exception):
    pass


def _validate_vcf_header(data: bytes) -> None:
    # Handle gzip-compressed VCF (.vcf.gz)
    if data[:2] == GZIP_MAGIC:
        import gzip
        try:
            header = gzip.decompress(data[:4096])
        except Exception:
            raise UploadValidationError(
                "File appears to be gzip-compressed but could not be decompressed."
            )
        if not header.startswith(VCF_MAGIC):
            raise UploadValidationError(
                "Gzip file does not contain a valid VCF. "
                "Expected '##fileformat=VCF' header after decompression."
            )
        return

    if not data.startswith(VCF_MAGIC):
        raise UploadValidationError(
            "File does not appear to be a valid VCF file. "
            "Expected header starting with '##fileformat=VCF'."
        )


def _validate_pdf_header(data: bytes) -> None:
    if not data.startswith(PDF_MAGIC):
        raise UploadValidationError(
            "File does not appear to be a valid PDF. "
            "Expected header starting with '%PDF'."
        )


def _validate_csv_header(data: bytes) -> None:
    try:
        data[:4096].decode("utf-8")
    except UnicodeDecodeError:
        raise UploadValidationError(
            "File does not appear to be valid CSV/text (not valid UTF-8)."
        )


_VALIDATORS = {
    "vcf": _validate_vcf_header,
    "pdf": _validate_pdf_header,
    "csv": _validate_csv_header,
}


def save_upload(
    file: FileStorage,
    file_type: str,
    max_size_bytes: int,
    user_encrypted_dek: bytes,
    master_key: str,
) -> tuple[Path, str, int]:
    """Validate, hash, and encrypt an uploaded file.

    Returns:
        (encrypted_path, sha256_hex, file_size_bytes)

    Raises:
        UploadValidationError: on validation failure.
    """
    # Read entire file into memory (size-bounded by caller / nginx)
    data = file.read()
    file_size = len(data)

    if file_size == 0:
        raise UploadValidationError("Uploaded file is empty.")
    if file_size > max_size_bytes:
        raise UploadValidationError(
            f"File exceeds maximum allowed size of {max_size_bytes // (1024 * 1024)} MB."
        )

    # Magic-byte validation
    validator = _VALIDATORS.get(file_type)
    if validator:
        validator(data)

    # SHA-256 hash for integrity
    sha256_hex = hashlib.sha256(data).hexdigest()

    # Write plaintext to temp file, then encrypt
    upload_dir: Path = current_app.config["UPLOAD_DIR"]
    file_id = uuid.uuid4().hex
    tmp_path = upload_dir / "tmp" / file_id
    encrypted_path = upload_dir / "enc" / f"{file_id}.enc"

    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.write_bytes(data)

    try:
        dek = decrypt_dek(user_encrypted_dek, master_key)
        encrypt_file(tmp_path, encrypted_path, dek)
    finally:
        # Always remove plaintext temp file
        tmp_path.unlink(missing_ok=True)

    return encrypted_path, sha256_hex, file_size
