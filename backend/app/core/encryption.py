"""
API Key Encryption Module

Provides AES-256 encryption for user custom API keys using Fernet (symmetric encryption).
The encryption key is derived from the ENCRYPTION_KEY environment variable.
"""

from typing import Optional
from functools import lru_cache
from cryptography.fernet import Fernet, InvalidToken
import base64
import hashlib

from backend.app.core.config import get_settings


@lru_cache(maxsize=1)
def _get_fernet() -> Optional[Fernet]:
    """
    Get the Fernet instance for encryption/decryption.
    
    Uses lru_cache to ensure the Fernet instance is only created once.
    The key is derived from ENCRYPTION_KEY environment variable.
    
    Returns:
        Fernet instance or None if encryption key is not configured
    """
    settings = get_settings()
    
    if not settings.encryption_key:
        return None
    
    # Derive a valid Fernet key from the encryption key
    # Fernet requires a 32-byte URL-safe base64-encoded key
    key_bytes = hashlib.sha256(settings.encryption_key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    
    return Fernet(fernet_key)


def encrypt_api_key(api_key: str) -> Optional[str]:
    """
    Encrypt an API key using AES-256 (Fernet).
    
    Args:
        api_key: The plaintext API key to encrypt
        
    Returns:
        The encrypted API key (base64 encoded) or None if encryption is not configured
    """
    if not api_key:
        return None
        
    fernet = _get_fernet()
    if fernet is None:
        # If encryption is not configured, store plaintext (not recommended for production)
        return api_key
    
    try:
        encrypted = fernet.encrypt(api_key.encode())
        return encrypted.decode()
    except Exception:
        return None


def decrypt_api_key(encrypted_key: str) -> Optional[str]:
    """
    Decrypt an API key.
    
    Args:
        encrypted_key: The encrypted API key (base64 encoded)
        
    Returns:
        The plaintext API key or None if decryption fails
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if not encrypted_key:
        logger.warning("decrypt_api_key: encrypted_key is empty or None")
        return None
    
    logger.debug(f"decrypt_api_key: attempting to decrypt key (length={len(encrypted_key)}, prefix={encrypted_key[:20]}...)")
        
    fernet = _get_fernet()
    if fernet is None:
        # If encryption is not configured, assume plaintext
        logger.info("decrypt_api_key: Fernet not configured, returning key as plaintext")
        return encrypted_key
    
    try:
        decrypted = fernet.decrypt(encrypted_key.encode())
        result = decrypted.decode()
        logger.info(f"decrypt_api_key: Successfully decrypted API key (length={len(result)}, prefix={result[:4]}...)")
        return result
    except InvalidToken:
        # Invalid token or wrong key
        logger.error(f"decrypt_api_key: InvalidToken - wrong encryption key or corrupted data")
        logger.error(f"   Encrypted key prefix: {encrypted_key[:30]}...")
        return None
    except Exception as e:
        logger.error(f"decrypt_api_key: Exception during decryption: {e}")
        return None


def is_encryption_configured() -> bool:
    """
    Check if encryption is properly configured.
    
    Returns:
        True if encryption key is set, False otherwise
    """
    return _get_fernet() is not None
