from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

_fallback_mod = pytest.importorskip("backend.app.services.translation.final_fallback_translator")
_wrap_as_minimal_latex = _fallback_mod._wrap_as_minimal_latex
extract_natural_language_from_source = _fallback_mod.extract_natural_language_from_source
translate_with_final_fallback = _fallback_mod.translate_with_final_fallback


def test_extract_natural_language_from_source_strips_latex_structure():
    src = r"\\begin{itemize} \\item This is a test $x+y$ \\end{itemize}"
    out = extract_natural_language_from_source(src)
    assert "This is a test" in out
    assert r"\\begin" not in out
    assert "$" not in out


def test_wrap_as_minimal_latex_escapes_dangerous_chars():
    out = _wrap_as_minimal_latex("100% & x_0", "sec_1")
    assert out.startswith("% [LaTeX-Trans: final-fallback")
    assert r"\%" in out
    assert r"\&" in out
    assert r"\_" in out


def test_translate_with_final_fallback_returns_empty_without_config():
    result = asyncio.run(
        translate_with_final_fallback(
            source_text="A simple English sentence.",
            fallback_report=None,
            llm_config={},
            source_language="en",
            target_language="zh",
        )
    )
    assert result == ""


def test_translate_with_final_fallback_success_path():
    translated = "这是目标语言译文。"

    async def _fake_json():
        return {"choices": [{"message": {"content": translated}}]}

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = _fake_json

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_resp
    mock_cm.__aexit__.return_value = None

    mock_session = MagicMock()
    mock_session.post.return_value = mock_cm

    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_session
    mock_session_cm.__aexit__.return_value = None

    with patch.object(aiohttp, "ClientSession", return_value=mock_session_cm):
        result = asyncio.run(
            translate_with_final_fallback(
                source_text="This section presents the final results.",
                fallback_report=None,
                llm_config={"model": "x", "base_url": "http://dummy", "api_key": "dummy"},
                source_language="en",
                target_language="zh",
            )
        )

    assert result.startswith("% [LaTeX-Trans: final-fallback")
    assert "This section presents" not in result


