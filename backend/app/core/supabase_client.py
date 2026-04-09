"""
Compatibility shim for legacy Supabase helper imports.

Runtime business flows in the local-auth/MySQL migration no longer create
Supabase clients. These functions remain only so older tests and imports can
continue to resolve stable names during the cutover.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Optional


@lru_cache(maxsize=1)
def get_supabase_admin_client() -> Optional[Any]:
    return None


def create_supabase_admin_client() -> Optional[Any]:
    return None


def get_supabase_client() -> Any:
    raise ValueError("Supabase runtime client is no longer available in local-db mode")


def get_supabase_client_optional() -> Optional[Any]:
    return None
