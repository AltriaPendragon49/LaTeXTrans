def test_cors_origins_accepts_json_array_string() -> None:
    from backend.app.core.config import Settings

    assert Settings._parse_cors_origins(
        '["http://localhost:5173","http://127.0.0.1:5173","https://latextrans.online"]'
    ) == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://latextrans.online",
    ]


def test_cors_origins_accepts_comma_separated_string() -> None:
    from backend.app.core.config import Settings

    assert Settings._parse_cors_origins(
        "http://localhost:5173, http://127.0.0.1:5173, https://latextrans.online"
    ) == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://latextrans.online",
    ]


def test_default_cors_origins_include_production_frontends(monkeypatch) -> None:
    from backend.app.core.config import Settings

    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    settings = Settings(_env_file=None)

    assert "https://latextrans.niutrans.com" in settings.cors_origins
    assert "https://paperx.niutrans.com" in settings.cors_origins


def test_advanced_config_defaults_to_gemini_flash() -> None:
    from backend.app.models.config_models import AdvancedConfig

    assert AdvancedConfig().translation_model == "gemini-2.5-flash"
