import os
import sys


def _ensure_repo_root_on_sys_path() -> None:
    tests_dir = os.path.dirname(__file__)
    repo_root = os.path.abspath(os.path.join(tests_dir, "..", ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


_ensure_repo_root_on_sys_path()

os.environ.setdefault("LLM_API_KEY", "test-api-key")
os.environ.setdefault("LLM_BASE_URL", "http://test-llm.local")
os.environ.setdefault("LLM_MODEL", "gpt-4o")
