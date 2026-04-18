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


def test_extra_inline_math_wrappers_trigger_mismatch():
    validator = _make_validator()
    part = {
        "content": (
            r"In order to generalize to any $\x_i \in \mathbb{R}^d$ where d is even, "
            r"we divide the d-dimension space into $d/2$ sub-spaces."
        ),
        "trans_content": (
            r"为了推广到任意 $\x_i \in \mathbb{R}^d$ 其中 $d$ 为偶数，"
            r"我们将 $d$ 维空间划分为 $d/2$ 个子空间。"
        ),
    }

    err = validator._validate_math_delimiters(part)

    assert err is not None
    assert "math_delimiter_mismatch" in err
    assert "original has 4 inline $, translation has 8" in err
