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


def test_validator_skips_chunked_document_root_for_long_english_prose_check():
    validator = _make_validator()
    part = {
        "section": "-1_chunk_1",
        "content": r"\documentclass{article}\author{Alice Smith}",
        "trans_content": r"\documentclass{article}\author{Alice Smith, Bob Johnson, Carol Lee, David Brown, Emma Wilson, Frank Moore, Grace Taylor, Helen Thomas, Ian Martin, Julia Thompson, Kevin White}",
        "chunk_role": "document_root",
    }

    error = validator._validate(part)

    assert error is None


def test_validator_allows_english_author_block_in_non_body_content():
    validator = _make_validator()
    part = {
        "section": "2",
        "content": (
            r"\author{Alice Smith \and Bob Johnson \and Carol Lee}"
            r"\affiliation{Department of Computer Science, Example University}"
        ),
        "trans_content": (
            r"\author{Alice Smith \and Bob Johnson \and Carol Lee}"
            r"\affiliation{Department of Computer Science, Example University, Example City, Example Country}"
        ),
    }

    error = validator._validate(part)

    assert error is None


def test_validator_allows_english_reference_block_in_non_body_content():
    validator = _make_validator()
    part = {
        "section": "8",
        "content": (
            r"\begin{thebibliography}{99}"
            r"\bibitem{smith2024} Alice Smith and Bob Johnson. Example title."
            r"\end{thebibliography}"
        ),
        "trans_content": (
            r"\begin{thebibliography}{99}"
            r"\bibitem{smith2024} Alice Smith and Bob Johnson. Example title. Proceedings of the Example Conference, 2024."
            r"\bibitem{lee2023} Carol Lee and David Brown. Another example title. Journal of Examples, 2023."
            r"\end{thebibliography}"
        ),
    }

    error = validator._validate(part)

    assert error is None


def test_validator_allows_english_macro_and_package_declarations():
    validator = _make_validator()
    part = {
        "section": "9",
        "content": (
            r"\usepackage{amsmath}\usepackage{amssymb}"
            r"\newtheorem{theorem}{Theorem}"
            r"\newcommand{\vect}[1]{\mathbf{#1}}"
        ),
        "trans_content": (
            r"\usepackage{amsmath}\usepackage{amssymb}"
            r"\newtheorem{theorem}{Theorem}"
            r"\newcommand{\vect}[1]{\mathbf{#1}}"
        ),
    }

    error = validator._validate(part)

    assert error is None
