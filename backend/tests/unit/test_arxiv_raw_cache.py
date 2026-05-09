from types import SimpleNamespace

import pytest

from backend.app.services import arxiv_raw_cache


class _FakeBackend:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def build_download_url(self, *, object_key: str, expires_in: int, params=None):
        self.calls.append(
            {
                "object_key": object_key,
                "expires_in": expires_in,
                "params": params,
            }
        )
        return f"https://cos.example.com/{object_key}?sign=abc"


def _settings(**overrides):
    values = {
        "storage_backend_mode": "cos",
        "arxiv_raw_cache_enabled": True,
        "arxiv_raw_cache_prefix": "arxiv/raw",
        "arxiv_raw_cache_signed_url_expires_seconds": 900,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_raw_cache_builds_pdf_and_eprint_keys() -> None:
    settings = _settings(arxiv_raw_cache_prefix="arxiv/raw")

    assert arxiv_raw_cache.raw_pdf_object_key("2501.12345", settings=settings) == "arxiv/raw/pdf/2501.12345"
    assert arxiv_raw_cache.raw_eprint_object_key("2501.12345", settings=settings) == "arxiv/raw/e-print/2501.12345"
    assert arxiv_raw_cache.raw_pdf_object_key("hep-th/9901001", settings=settings) == "arxiv/raw/pdf/hep-th/9901001"


def test_raw_cache_default_keys_match_arxiv_origin_paths() -> None:
    settings = _settings(arxiv_raw_cache_prefix="")

    assert arxiv_raw_cache.raw_pdf_object_key("2501.12345", settings=settings) == "pdf/2501.12345"
    assert arxiv_raw_cache.raw_eprint_object_key("2501.12345", settings=settings) == "e-print/2501.12345"


def test_raw_cache_rejects_unsafe_arxiv_id() -> None:
    with pytest.raises(ValueError):
        arxiv_raw_cache.raw_pdf_object_key("../secret")


def test_raw_cache_builds_signed_pdf_url_with_inline_headers() -> None:
    backend = _FakeBackend()

    url = arxiv_raw_cache.build_pdf_download_url(
        "2501.12345",
        settings=_settings(),
        backend=backend,
        filename="source_2501.12345.pdf",
        inline=True,
    )

    assert url == "https://cos.example.com/arxiv/raw/pdf/2501.12345?sign=abc"
    assert backend.calls == [
        {
            "object_key": "arxiv/raw/pdf/2501.12345",
            "expires_in": 900,
            "params": {
                "response-content-disposition": 'inline; filename="source_2501.12345.pdf"',
                "response-content-type": "application/pdf",
            },
        }
    ]


def test_raw_cache_constructs_cos_backend_without_business_base_prefix(monkeypatch) -> None:
    captured = {}

    class _FakeCosBackend(_FakeBackend):
        def __init__(self, **kwargs):
            super().__init__()
            captured.update(kwargs)

    monkeypatch.setattr(arxiv_raw_cache, "_ensure_cos_config", lambda _settings: None)
    monkeypatch.setattr(arxiv_raw_cache, "CosStorageBackend", _FakeCosBackend)

    settings = _settings(
        arxiv_raw_cache_prefix="",
        cos_bucket="bucket-1",
        cos_region="ap-beijing",
        cos_secret_id="id",
        cos_secret_key="key",
        cos_base_prefix="latextrans-prod",
    )

    url = arxiv_raw_cache.build_pdf_download_url("2501.12345", settings=settings)

    assert url == "https://cos.example.com/pdf/2501.12345?sign=abc"
    assert captured["base_prefix"] == ""


def test_raw_cache_identifies_legacy_pdf_object_key() -> None:
    settings = _settings(arxiv_raw_cache_prefix="arxiv/raw")

    assert arxiv_raw_cache.is_raw_pdf_object_key("arxiv/raw/pdf/2501.12345", "2501.12345", settings=settings)
    assert arxiv_raw_cache.is_raw_pdf_object_key("arxiv/raw/pdf/2501.12345.pdf", "2501.12345", settings=settings)


def test_raw_cache_returns_none_when_disabled() -> None:
    backend = _FakeBackend()

    url = arxiv_raw_cache.build_pdf_download_url(
        "2501.12345",
        settings=_settings(arxiv_raw_cache_enabled=False),
        backend=backend,
    )

    assert url is None
    assert backend.calls == []


def test_raw_cache_eprint_source_urls_prepend_cos_url() -> None:
    backend = _FakeBackend()

    urls = arxiv_raw_cache.build_eprint_source_urls(
        "2501.12345",
        settings=_settings(),
        backend=backend,
    )

    assert urls[0] == "https://cos.example.com/arxiv/raw/e-print/2501.12345?sign=abc"
    assert "https://export.arxiv.org/e-print/2501.12345" in urls
    assert "https://arxiv.org/e-print/2501.12345" in urls
