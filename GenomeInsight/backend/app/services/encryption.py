"""Envelope encryption for user files.

Implements a two-layer key hierarchy:

    Master Key (from env)  ──encrypts──▶  Per-User DEK
    Per-User DEK           ──encrypts──▶  User files on disk

All symmetric operations use AES-256-GCM (authenticated encryption).
"""

import os
import struct
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# --- Key management ----------------------------------------------------------


def _derive_master_key(raw: str) -> bytes:
    """Ensure master key material is exactly 32 bytes for AES-256.

    If the env value is hex-encoded (64 chars), decode it.
    Otherwise, pad/truncate the UTF-8 bytes to 32.
    """
    try:
        if len(raw) == 64:
            return bytes.fromhex(raw)
    except ValueError:
        pass
    key_bytes = raw.encode("utf-8")
    return key_bytes[:32].ljust(32, b"\x00")


def generate_user_dek() -> bytes:
    """Generate a random 256-bit data encryption key for a new user."""
    return AESGCM.generate_key(bit_length=256)


def encrypt_dek(dek: bytes, master_key_raw: str) -> bytes:
    """Encrypt a per-user DEK with the master key.

    Returns ``nonce (12 bytes) || ciphertext+tag``.
    """
    mk = _derive_master_key(master_key_raw)
    nonce = os.urandom(12)
    ct = AESGCM(mk).encrypt(nonce, dek, None)
    return nonce + ct


def decrypt_dek(encrypted_dek: bytes, master_key_raw: str) -> bytes:
    """Decrypt a per-user DEK using the master key."""
    mk = _derive_master_key(master_key_raw)
    nonce = encrypted_dek[:12]
    ct = encrypted_dek[12:]
    return AESGCM(mk).decrypt(nonce, ct, None)


# --- File encryption ---------------------------------------------------------

_HEADER_MAGIC = b"GENI"  # 4-byte file header identifying our format
_HEADER_VERSION = 1


def encrypt_file(src: Path, dest: Path, dek: bytes) -> None:
    """Encrypt *src* to *dest* using AES-256-GCM with the user's DEK.

    File format (binary):
        [4B magic][1B version][12B nonce][ciphertext+tag]

    Entire plaintext is loaded into memory, so callers must enforce size
    limits before calling this function.
    """
    plaintext = src.read_bytes()
    nonce = os.urandom(12)
    ct = AESGCM(dek).encrypt(nonce, plaintext, None)

    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        f.write(_HEADER_MAGIC)
        f.write(struct.pack("B", _HEADER_VERSION))
        f.write(nonce)
        f.write(ct)


def decrypt_file(src: Path, dek: bytes) -> bytes:
    """Decrypt a file previously encrypted with :func:`encrypt_file`."""
    raw = src.read_bytes()

    magic = raw[:4]
    if magic != _HEADER_MAGIC:
        raise ValueError("Not a GenomeInsight encrypted file")

    _version = struct.unpack("B", raw[4:5])[0]
    nonce = raw[5:17]
    ct = raw[17:]
    return AESGCM(dek).decrypt(nonce, ct, None)
