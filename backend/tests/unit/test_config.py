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
