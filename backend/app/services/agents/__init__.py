# Agent 服务模块
import asyncio
from typing import Optional

# ── 基础设施守卫（安全网）────────────────────────────────────────────────
# global_llm_semaphore 限制并发的对外 LLM API 请求总数。
#
# 角色：基础设施级别的保护，防止系统资源耗尽。
#       绝不能用于业务调度决策。
#
# 该值在首次使用时从 Settings 延迟读取。

_global_llm_semaphore: Optional[asyncio.Semaphore] = None


def _get_llm_semaphore() -> asyncio.Semaphore:
    """返回全局 LLM 信号量，在首次调用时创建。"""
    global _global_llm_semaphore
    if _global_llm_semaphore is None:
        try:
            from backend.app.core.config import settings
            limit = settings.llm_max_concurrent_requests
        except Exception:
            limit = 30  # 若 settings 不可用（如测试环境），使用安全回退值
        _global_llm_semaphore = asyncio.Semaphore(limit)
    return _global_llm_semaphore


class _SemaphoreProxy:
    """
    代理类，将 `async with` 转发给延迟创建的全局信号量。
    这样代码中可以自然地使用 `async with global_llm_semaphore:`，
    而实际的 Semaphore 创建则推迟到事件循环运行之后。
    """
    async def __aenter__(self):
        return await _get_llm_semaphore().__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return await _get_llm_semaphore().__aexit__(exc_type, exc_val, exc_tb)


# 供 translator_agent.py 使用的公开接口
global_llm_semaphore: _SemaphoreProxy = _SemaphoreProxy()
