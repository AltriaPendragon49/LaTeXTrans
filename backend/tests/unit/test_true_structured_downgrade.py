from backend.app.services.translation.ultimate_downgrade import (
    is_target_language_downgrade_candidate,
)


def test_target_language_candidate_accepts_real_chinese_translation():
    assert is_target_language_downgrade_candidate(
        "这是已经翻译好的中文段落，用于保守结构化降级。",
        source_text="This is the original English paragraph for downgrade.",
        target_language="zh",
    )


def test_target_language_candidate_rejects_source_english():
    assert not is_target_language_downgrade_candidate(
        "This is still the original English paragraph for downgrade.",
        source_text="This is still the original English paragraph for downgrade.",
        target_language="zh",
    )


def test_target_language_candidate_rejects_fixed_fallback_boilerplate():
    assert not is_target_language_downgrade_candidate(
        "相关内容已转为简要中文表述。相关内容已转为简要中文表述。",
        source_text="A long English paragraph remained untranslated.",
        target_language="zh",
    )
