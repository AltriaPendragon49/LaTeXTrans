import os
import shutil
import sys
from pathlib import Path
from uuid import uuid4

import pytest


def _ensure_repo_root_on_sys_path() -> None:
    tests_dir = os.path.dirname(__file__)
    repo_root = os.path.abspath(os.path.join(tests_dir, "..", ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


_ensure_repo_root_on_sys_path()

os.environ.setdefault("LLM_API_KEY", "test-api-key")
os.environ.setdefault("LLM_BASE_URL", "http://test-llm.local")
os.environ.setdefault("LLM_MODEL", "gpt-4o")


def _workspace_test_tmp_root() -> Path:
    tests_dir = Path(__file__).resolve().parent
    root = tests_dir / ".tmp_runtime"
    root.mkdir(parents=True, exist_ok=True)
    return root


_TMP_ROOT = _workspace_test_tmp_root()
os.environ.setdefault("TMP", str(_TMP_ROOT))
os.environ.setdefault("TEMP", str(_TMP_ROOT))
os.environ.setdefault("TMPDIR", str(_TMP_ROOT))


class WorkspaceTempPathFactory:
    def __init__(self, base: Path) -> None:
        self._base = base
        self._base.mkdir(parents=True, exist_ok=True)

    def getbasetemp(self) -> Path:
        return self._base

    def mktemp(self, basename: str, numbered: bool = True) -> Path:
        normalized = basename.strip() or "case"
        if numbered:
            normalized = f"{normalized}-{uuid4().hex}"
        path = self._base / normalized
        path.mkdir(parents=True, exist_ok=True)
        return path


@pytest.fixture(scope="session")
def tmp_path_factory(request: pytest.FixtureRequest) -> WorkspaceTempPathFactory:
    return request.config._workspace_tmp_factory


@pytest.fixture
def tmp_path(tmp_path_factory: WorkspaceTempPathFactory) -> Path:
    """Force all tests to allocate temp dirs under backend/tests/.tmp_runtime."""
    return tmp_path_factory.mktemp("case")


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    factory = getattr(session.config, "_workspace_tmp_factory", None)
    if factory is not None:
        shutil.rmtree(factory.getbasetemp(), ignore_errors=True)


def pytest_configure(config: pytest.Config) -> None:
    config._workspace_tmp_factory = WorkspaceTempPathFactory(_TMP_ROOT / f"session-{uuid4().hex}")
