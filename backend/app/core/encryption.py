"""
API 密钥加密模块

使用 Fernet（对称加密）提供 AES-256 加密，用于加密用户自定义 API 密钥。
加密密钥从 ENCRYPTION_KEY 环境变量派生。
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
    获取用于加密/解密的 Fernet 实例。

    使用 lru_cache 确保 Fernet 实例只创建一次。
    密钥从 ENCRYPTION_KEY 环境变量派生。

    返回：
        Fernet 实例，如果未配置加密密钥则返回 None
    """
    settings = get_settings()

    if not settings.encryption_key:
        return None

    # 从加密密钥派生出有效的 Fernet 密钥
    # Fernet 需要一个 32 字节的 URL 安全 base64 编码密钥
    key_bytes = hashlib.sha256(settings.encryption_key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)

    return Fernet(fernet_key)


def encrypt_api_key(api_key: str) -> Optional[str]:
    """
    使用 AES-256（Fernet）加密 API 密钥。

    参数：
        api_key: 要加密的明文 API 密钥

    返回：
        加密后的 API 密钥（base64 编码），如果加密未配置则返回 None
    """
    if not api_key:
        return None

    fernet = _get_fernet()
    if fernet is None:
        # 如果未配置加密，则存储明文（不推荐用于生产环境）
        return api_key

    try:
        encrypted = fernet.encrypt(api_key.encode())
        return encrypted.decode()
    except Exception:
        return None


def decrypt_api_key(encrypted_key: str) -> Optional[str]:
    """
    解密 API 密钥。

    参数：
        encrypted_key: 加密后的 API 密钥（base64 编码）

    返回：
        解密后的明文 API 密钥，解密失败则返回 None
    """
    import logging
    logger = logging.getLogger(__name__)

    if not encrypted_key:
        logger.warning("decrypt_api_key: encrypted_key is empty or None")
        return None

    logger.debug(f"decrypt_api_key: attempting to decrypt key (length={len(encrypted_key)}, prefix={encrypted_key[:20]}...)")

    fernet = _get_fernet()
    if fernet is None:
        # 如果未配置加密，则假设为明文
        logger.info("decrypt_api_key: Fernet not configured, returning key as plaintext")
        return encrypted_key

    try:
        decrypted = fernet.decrypt(encrypted_key.encode())
        result = decrypted.decode()
        logger.info(f"decrypt_api_key: Successfully decrypted API key (length={len(result)}, prefix={result[:4]}...)")
        return result
    except InvalidToken:
        # 无效令牌或错误的密钥
        logger.error(f"decrypt_api_key: InvalidToken - wrong encryption key or corrupted data")
        logger.error(f"   Encrypted key prefix: {encrypted_key[:30]}...")
        return None
    except Exception as e:
        logger.error(f"decrypt_api_key: Exception during decryption: {e}")
        return None


def is_encryption_configured() -> bool:
    """
    检查加密是否正确配置。

    返回：
        如果加密密钥已设置返回 True，否则返回 False
    """
    return _get_fernet() is not None
