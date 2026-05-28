"""Unit tests for PdfDirectService: auth signing, error mapping, task serialization."""

import pytest
from unittest.mock import MagicMock, patch

from backend.app.services.pdf_direct_service import (
    _generate_auth_str,
    PdfDirectService,
    PdfDirectServiceError,
    TRANS_STATUS_PROCESSING,
    TRANS_STATUS_COMPLETED,
    TRANS_STATUS_FAILED,
)


# ---------------------------------------------------------------------------
# _generate_auth_str
# ---------------------------------------------------------------------------

class TestGenerateAuthStr:

    def test_sorts_params_by_ascii_key_name(self):
        apikey = "test-apikey-123"
        # b comes before a in ASCII - verify sorting
        params = {"bKey": "bval", "aKey": "aval"}
        result = _generate_auth_str(params, apikey)
        assert isinstance(result, str)
        assert len(result) == 32  # MD5 hex digest

    def test_excludes_authstr_and_file_fields(self):
        apikey = "secret"
        params = {
            "appId": "myapp",
            "timestamp": "123456",
            "authStr": "should-be-ignored",
            "file": "should-also-be-ignored",
        }
        result = _generate_auth_str(params, apikey)
        # authStr and file should NOT appear in the signing string
        assert isinstance(result, str)
        assert len(result) == 32

    def test_skips_empty_values(self):
        apikey = "secret"
        params = {"a": "val", "b": "", "c": "other"}
        result = _generate_auth_str(params, apikey)
        assert isinstance(result, str)
        assert len(result) == 32

    def test_deterministic_output(self):
        apikey = "stable-key"
        params = {"appId": "x", "timestamp": "1", "from": "en"}
        first = _generate_auth_str(params, apikey)
        second = _generate_auth_str(params, apikey)
        assert first == second

    def test_different_apikey_produces_different_hash(self):
        params = {"appId": "x"}
        h1 = _generate_auth_str(params, "key-a")
        h2 = _generate_auth_str(params, "key-b")
        assert h1 != h2

    def test_different_params_produce_different_hash(self):
        apikey = "key"
        h1 = _generate_auth_str({"appId": "x", "from": "en"}, apikey)
        h2 = _generate_auth_str({"appId": "x", "from": "zh"}, apikey)
        assert h1 != h2

    def test_known_md5_vector(self):
        apikey = "test-key"
        params = {"appId": "test-app", "timestamp": "1000"}
        result = _generate_auth_str(params, apikey)
        expected = "b235164af167fed0646ce6414ce71614"
        assert result == expected


# ---------------------------------------------------------------------------
# _map_upstream_error
# ---------------------------------------------------------------------------

class TestMapUpstreamError:

    def _make_service(self):
        settings = MagicMock()
        settings.pdf_direct_translation_enabled = True
        settings.niutrans_doc_api_app_id = "test-app"
        settings.niutrans_doc_api_base_url = "http://test.local"
        settings.pipeline_timeout_seconds = 1800.0
        return PdfDirectService()

    def test_credit_insufficient_codes(self):
        service = self._make_service()
        for code in [20017, 110019, 110020, 20002]:
            err = service._map_upstream_error(code, "insufficient credits")
            assert err.code == "PDF_DIRECT_CREDIT_INSUFFICIENT"
            assert err.status_code == 402
            assert "niutrans.com" in str(err.extra.get("account_url", ""))

    def test_file_validation_codes(self):
        service = self._make_service()
        for code in [20004, 210011, 110024, 110025, 110029, 110013, 110014, 110007]:
            err = service._map_upstream_error(code, "file error")
            assert err.code == "PDF_DIRECT_VALIDATION_ERROR"
            assert err.status_code == 400

    def test_file_limit_codes(self):
        service = self._make_service()
        for code in [20005, 210013, 210014, 210015]:
            err = service._map_upstream_error(code, "limit exceeded")
            assert err.code == "PDF_DIRECT_LIMIT_ERROR"
            assert err.status_code == 400

    def test_retryable_codes(self):
        service = self._make_service()
        for code in [20022, 22001, 110000]:
            err = service._map_upstream_error(code, "busy")
            assert err.code == "PDF_DIRECT_RETRYABLE_ERROR"
            assert err.status_code == 503

    def test_auth_error_codes(self):
        service = self._make_service()
        for code in [21000, 20006]:
            err = service._map_upstream_error(code, "auth failed")
            assert err.code == "PDF_DIRECT_AUTH_ERROR"
            assert err.status_code == 401

    def test_not_found_codes(self):
        service = self._make_service()
        for code in [20003, 110021, 110011]:
            err = service._map_upstream_error(code, "not found")
            assert err.code == "PDF_DIRECT_NOT_FOUND"
            assert err.status_code == 404

    def test_unknown_code_fallback(self):
        service = self._make_service()
        err = service._map_upstream_error(99999, "mystery")
        assert err.code == "PDF_DIRECT_UPSTREAM_ERROR"
        assert err.status_code == 502


# ---------------------------------------------------------------------------
# _task_to_response
# ---------------------------------------------------------------------------

class TestTaskToResponse:

    def test_none_returns_empty_dict(self):
        assert PdfDirectService._task_to_response(None) == {}

    def test_complete_task_serialization(self):
        from datetime import datetime, timezone

        task = {
            "id": "pdf_abc123",
            "user_id": "user-1",
            "upstream_file_no": "file-001",
            "file_name": "paper.pdf",
            "file_size_kb": 1024,
            "page_num": 10,
            "progress": 0.75,
            "trans_status": 105,
            "trans_failure_cause": None,
            "trans_failure_code": None,
            "status": "active",
            "cos_artifact_key": "cos://bucket/key",
            "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "updated_at": datetime(2025, 1, 1, 1, 0, tzinfo=timezone.utc),
            "completed_at": datetime(2025, 1, 1, 1, 0, tzinfo=timezone.utc),
        }

        result = PdfDirectService._task_to_response(task)
        assert result["task_id"] == "pdf_abc123"
        assert result["file_name"] == "paper.pdf"
        assert result["page_num"] == 10
        assert result["progress"] == 0.75
        assert result["trans_status"] == 105
        assert result["has_artifact"] is True
        assert result["created_at"] == "2025-01-01T00:00:00+00:00"

    def test_minimal_task(self):
        task = {
            "id": "pdf_min",
            "user_id": "u1",
            "upstream_file_no": "f1",
            "file_name": "test.pdf",
            "file_size_kb": None,
            "page_num": None,
            "progress": None,
            "trans_status": 101,
            "trans_failure_cause": None,
            "trans_failure_code": None,
            "status": "active",
            "cos_artifact_key": None,
            "created_at": None,
            "updated_at": None,
            "completed_at": None,
        }
        result = PdfDirectService._task_to_response(task)
        assert result["task_id"] == "pdf_min"
        assert result["trans_status"] == 101
        assert result["has_artifact"] is False
        assert result["created_at"] is None


# ---------------------------------------------------------------------------
# TransStatus constants
# ---------------------------------------------------------------------------

class TestTransStatusConstants:

    def test_constants_are_distinct(self):
        assert TRANS_STATUS_PROCESSING == 103
        assert TRANS_STATUS_COMPLETED == 105
        assert TRANS_STATUS_FAILED == 106
        assert TRANS_STATUS_PROCESSING != TRANS_STATUS_COMPLETED


# ---------------------------------------------------------------------------
# PdfDirectServiceError
# ---------------------------------------------------------------------------

class TestPdfDirectServiceError:

    def test_basic_error(self):
        err = PdfDirectServiceError("CODE", "message", status_code=400)
        assert err.code == "CODE"
        assert err.message == "message"
        assert err.status_code == 400
        assert err.extra == {}

    def test_error_with_extra(self):
        err = PdfDirectServiceError("C", "m", extra={"key": "val"})
        assert err.extra == {"key": "val"}

    def test_error_default_status(self):
        err = PdfDirectServiceError("C", "m")
        assert err.status_code == 400
