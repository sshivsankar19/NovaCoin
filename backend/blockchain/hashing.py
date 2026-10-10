"""Explicit cryptographic hashing primitives used by NovaCoin."""

import hashlib


def sha256_digest(data: bytes) -> bytes:
    """Return the raw SHA-256 digest for deterministic byte input."""
    return hashlib.sha256(data).digest()


def sha256_hex(data: bytes) -> str:
    """Return a lowercase hexadecimal SHA-256 digest."""
    return sha256_digest(data).hex()


def blake2b_hex(data: bytes, digest_size: int = 32) -> str:
    """Return a lowercase hexadecimal BLAKE2b digest."""
    return hashlib.blake2b(data, digest_size=digest_size).hexdigest()


def sha256_then_blake2b_hex(data: bytes, digest_size: int = 32) -> str:
    """Hash bytes with SHA-256, then hash the raw digest with BLAKE2b."""
    return blake2b_hex(sha256_digest(data), digest_size=digest_size)


def proof_of_work_hex(data: bytes, algorithm: str) -> str:
    """Return the protocol-selected proof-of-work digest."""
    normalized = str(algorithm).upper()
    if normalized in {"SHA256", "SHA256_PROOF_OF_WORK"}:
        return sha256_hex(data)
    if normalized in {"BLAKE2B", "BLAKE2B_256", "BLAKE2B_PROOF_OF_WORK"}:
        return blake2b_hex(data, digest_size=32)
    raise ValueError(f"Unsupported proof-of-work algorithm: {algorithm}")
