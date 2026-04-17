from backend.app.services.agents.validator_agent import ValidatorAgent


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


def test_reordered_placeholder_sequence_is_rejected():
    validator = _make_validator()
    part = {
        "section": "10",
        "content": "A <PLACEHOLDER_ENV_1> B <PLACEHOLDER_CAP_2>",
        "trans_content": "A <PLACEHOLDER_CAP_2> B <PLACEHOLDER_ENV_1>",
    }

    error = validator._validate_placeholder(part)

    assert error is not None
    assert "placeholder sequence mismatch" in error.lower()


def test_duplicate_placeholder_occurrence_is_rejected():
    validator = _make_validator()
    part = {
        "section": "11",
        "content": "A <PLACEHOLDER_ENV_1> B",
        "trans_content": "A <PLACEHOLDER_ENV_1> <PLACEHOLDER_ENV_1> B",
    }

    error = validator._validate_placeholder(part)

    assert error is not None
    assert "placeholder sequence mismatch" in error.lower()


def test_newcommand_placeholder_is_tracked():
    validator = _make_validator()
    part = {
        "section": "12",
        "content": "A <PLACEHOLDER_NEWCOMMAND_1> B",
        "trans_content": "A B",
    }

    error = validator._validate_placeholder(part)

    assert error is not None
    assert "PLACEHOLDER_NEWCOMMAND_1" in error
