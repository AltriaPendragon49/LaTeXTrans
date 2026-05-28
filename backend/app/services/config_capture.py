"""运行时配置快照捕获服务，用于翻译任务"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from backend.app.core.config import get_settings
from backend.app.core.timezone_utils import get_cst_now

logger = logging.getLogger(__name__)


def _json_safe(value: Any) -> Any:
    """将任意对象转换为 JSON 可序列化的值"""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if hasattr(value, "model_dump"):
        try:
            return _json_safe(value.model_dump())
        except Exception:
            return _json_safe(str(value))
    if hasattr(value, "dict"):
        try:
            return _json_safe(value.dict())
        except Exception:
            return _json_safe(str(value))
    return str(value)


def _mask_api_key(api_key: Optional[str]) -> Optional[str]:
    """对 API Key 进行脱敏处理，返回固定长度的星号串"""
    if not api_key:
        return None
    return "*" * 20


def _sanitize_llm_config(llm_config: Mapping[str, Any]) -> Dict[str, Any]:
    """清洗 LLM 配置，对 API Key 脱敏"""
    return {
        "base_url": _json_safe(llm_config.get("base_url", "")),
        "model": _json_safe(llm_config.get("model", "")),
        "timeout": _json_safe(llm_config.get("timeout", 60)),
        "api_key_masked": _mask_api_key(llm_config.get("api_key")),
    }


def _sanitize_agent_config(agent_config: Mapping[str, Any]) -> Dict[str, Any]:
    """清洗 Agent 配置，对 API Key 脱敏"""
    sanitized = _json_safe(agent_config)
    if not isinstance(sanitized, dict):
        return {"raw": sanitized}

    llm = sanitized.get("llm_config")
    if isinstance(llm, dict):
        api_key = llm.pop("api_key", None)
        llm["api_key_masked"] = _mask_api_key(api_key) if api_key else llm.get("api_key_masked")
    return sanitized


def capture_task_config(
    task_id: str,
    advanced_config: Mapping[str, Any],
    agent_config: Mapping[str, Any],
    llm_config: Mapping[str, Any],
    additional_info: Optional[Mapping[str, Any]] = None,
) -> Optional[Path]:
    """为翻译任务捕获运行时配置快照

    参数:
        task_id: 任务 ID
        advanced_config: 高级配置
        agent_config: Agent 配置
        llm_config: LLM 配置
        additional_info: 附加信息（可选）

    返回:
        成功时返回输出文件路径，跳过或失败时返回 None
    """
    settings = get_settings()
    if not settings.enable_task_config_capture:
        return None

    output_dir = Path(settings.task_configs_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    info = _json_safe(additional_info or {})
    if not isinstance(info, dict):
        info = {"raw": info}

    arxiv_id = info.get("arxiv_id")

    now = get_cst_now()

    filename = f"{task_id}.json"
    filepath = output_dir / filename
    tmp_path = output_dir / f".{filename}.tmp"

    try:
        snapshot = {
            "arxiv_id": info.get("arxiv_id"),
            "is_logged_in": bool(info.get("is_logged_in", False)),
            "metadata": {
                "task_id": task_id,
                "captured_at": now.isoformat(),
                "timestamp": now.strftime("%m%d_%H%M"),
            },
            "advanced_config": _json_safe(advanced_config),
            "agent_config": _sanitize_agent_config(agent_config),
            "llm_config": _sanitize_llm_config(llm_config),
            "additional_info": info,
        }

        with open(tmp_path, "w", encoding="utf-8") as file:
            json.dump(snapshot, file, ensure_ascii=False, indent=2)

        tmp_path.replace(filepath)
        logger.info(f"Config captured and saved to: {filepath}")
        return filepath
    except Exception as exc:
        logger.warning(f"Config capture failed for task {task_id}: {exc}", exc_info=True)
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass
        return None
