import asyncio


def test_default_backend_branding_uses_paperx() -> None:
    from backend.app.core.config import Settings

    settings = Settings()

    assert settings.app_name == "PaperX Backend"


def test_root_endpoint_message_uses_paperx_brand() -> None:
    from backend.app.main import root

    payload = asyncio.run(root())

    assert payload["message"] == "PaperX Backend API"
