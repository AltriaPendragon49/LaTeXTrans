from backend.app.services.agents.validator_agent import ERROR_TYPE_B, ValidatorAgent


def _make_validator() -> ValidatorAgent:
    return ValidatorAgent(
        config={
            "llm_config": {"model": "test", "base_url": "http://x", "api_key": "x"},
            "source_language": "en",
            "target_language": "zh",
        },
        project_dir="dummy",
        output_dir="dummy",
    )


def test_validator_flags_long_english_prose_span_as_completeness_error():
    validator = _make_validator()
    part = {
        "section": "4",
        "content": "source",
        "trans_content": (
            "This paragraph remains in English and should definitely be translated into Chinese "
            "before final output because users will notice it immediately and it is not acceptable."
        ),
    }

    error = validator._validate(part)

    assert error is not None
    assert "long_english_prose_span" in error.get("completeness_error", "")
    assert error.get("error_type") == ERROR_TYPE_B


def test_validator_ignores_urls_emails_and_acronyms_for_completeness_scan():
    validator = _make_validator()
    part = {
        "section": "5",
        "content": "source",
        "trans_content": (
            r"\url{https://example.com/resource} "
            r"contact test@example.com GDP ENSO EPB TPT"
        ),
    }

    error = validator._validate(part)

    assert error is None


def test_validator_skips_section_zero_for_long_english_prose_check():
    validator = _make_validator()
    part = {
        "section": "0",
        "content": "source",
        "trans_content": (
            "This front matter can remain in English for this validator path and should not trigger "
            "the body-section completeness rule even if it is long enough to look like prose."
        ),
    }

    error = validator._validate(part)

    assert error is None
