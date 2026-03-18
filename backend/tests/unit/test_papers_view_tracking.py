import asyncio
import os

import pytest
from fastapi import HTTPException

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.services import paper_service


class _Result:
    def __init__(self, data):
        self.data = data


class _RpcCall:
    def __init__(self, data):
        self._data = data

    def execute(self):
        return _Result(self._data)


class _Client:
    def __init__(self, data):
        self._data = data

    def rpc(self, function_name, params):
        assert function_name == "increment_paper_view_count"
        assert "target_paper_id" in params
        return _RpcCall(self._data)


def test_record_view_increments_visible_paper(monkeypatch):
    monkeypatch.setattr(paper_service, "get_supabase_admin_client", lambda: _Client([{"view_count": 3}]))
    monkeypatch.setattr(paper_service, "run_db_blocking", lambda fn, **_kwargs: asyncio.sleep(0, result=fn()))

    result = asyncio.run(paper_service.record_community_paper_view(paper_id="paper-view"))

    assert result == {"paper_id": "paper-view", "view_count": 3}


def test_record_view_returns_404_for_missing_or_hidden_paper(monkeypatch):
    monkeypatch.setattr(paper_service, "get_supabase_admin_client", lambda: _Client([]))
    monkeypatch.setattr(paper_service, "run_db_blocking", lambda fn, **_kwargs: asyncio.sleep(0, result=fn()))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(paper_service.record_community_paper_view(paper_id="missing"))

    assert exc_info.value.status_code == 404
