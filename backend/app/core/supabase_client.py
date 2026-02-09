"""
Supabase Client Module - 纯 RLS 模式

提供两种客户端：
1. Admin Client (Service Role Key) - 仅用于系统级操作
2. User Client (Anon Key + Token) - 用于用户操作，受 RLS 约束

核心原则：用户操作应使用 User Client，让 RLS 控制权限。
"""

from typing import Optional
from functools import lru_cache
from supabase import create_client, Client

from backend.app.core.config import get_settings


@lru_cache(maxsize=1)
def get_supabase_admin_client() -> Optional[Client]:
    """
    获取 Admin Client（使用 Service Role Key）。
    
    仅用于需要绕过 RLS 的系统级操作。
    普通用户操作应使用 auth.py 中的 get_supabase_client_from_request。
    
    Returns:
        Admin Client 或 None（未配置时）
    """
    settings = get_settings()
    
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None
    
    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key
    )


# 向后兼容
def get_supabase_client() -> Client:
    """向后兼容：获取 Admin Client。"""
    client = get_supabase_admin_client()
    if client is None:
        raise ValueError("Supabase not configured")
    return client


def get_supabase_client_optional() -> Optional[Client]:
    """向后兼容：获取 Admin Client（可选）。"""
    return get_supabase_admin_client()
