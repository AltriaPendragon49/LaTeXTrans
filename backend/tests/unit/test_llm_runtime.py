import os
import sys
import importlib.util
from pathlib import Path

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


def _load_module(module_name: str, relative_path: str):
    file_path = Path(__file__).resolve().parents[3] / relative_path
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_resolve_llm_max_concurrent_requests_uses_config_override():
    llm_runtime = _load_module("backend_llm_runtime_test", "backend/app/services/agents/llm_runtime.py")

    assert llm_runtime.resolve_llm_max_concurrent_requests(
        {"llm_max_concurrent_requests": 7},
        default=10,
    ) == 7


def test_resolve_task_llm_max_concurrent_requests_caps_to_cli_parity_limit():
    llm_runtime = _load_module("backend_llm_runtime_test", "backend/app/services/agents/llm_runtime.py")

    assert llm_runtime.resolve_task_llm_max_concurrent_requests(
        {"llm_max_concurrent_requests": 30},
        default=30,
        cap=3,
    ) == 3


def test_resolve_task_llm_max_concurrent_requests_keeps_lower_values():
    llm_runtime = _load_module("backend_llm_runtime_test", "backend/app/services/agents/llm_runtime.py")

    assert llm_runtime.resolve_task_llm_max_concurrent_requests(
        {"llm_max_concurrent_requests": 2},
        default=30,
        cap=3,
    ) == 2


def test_backend_settings_match_cli_safe_limit_defaults():
    config = _load_module("backend_config_test", "backend/app/core/config.py")
    settings = config.get_settings()
    assert settings.model_context_tokens == 32000
    assert settings.prompt_reserve_tokens == 4096
    assert settings.llm_max_concurrent_requests == 3
