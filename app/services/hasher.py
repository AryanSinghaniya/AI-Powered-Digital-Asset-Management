import hashlib
import os
import logging

logger = logging.getLogger(__name__)

def compute_file_hash(filepath: str, chunk_size: int = 8192) -> str:
    """Computes SHA-256 hash of a file."""
    try:
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(chunk_size), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        logger.error(f"Failed to hash {filepath}: {e}")
        raise
