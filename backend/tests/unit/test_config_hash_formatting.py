import asyncio
import os
from pathlib import Path

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.api.routes import translate as translate_route
from backend.app.models.config_models import AdvancedConfig, FormattingConfig


def test_compute_config_hash_changes_when_formatting_changes():
    default_hash = translate_route.compute_config_hash(
        arxiv_id="2508.18971",
        source_language="en",
        target_language="zh",
        translation_mode="full",
        compile_strategy="auto",
        formatting=None,
    )
    formatted_hash = translate_route.compute_config_hash(
        arxiv_id="2508.18971",
        source_language="en",
        target_language="zh",
        translation_mode="full",
        compile_strategy="auto",
        formatting=FormattingConfig(font_size=12.0, line_spacing=1.0, paragraph_indent=True),
    )

    assert formatted_hash != default_hash


def test_run_translation_uses_formatting_aware_reuse_hash(monkeypatch, tmp_path):
    captured_hashes = []
    source_dir = tmp_path / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "main.tex").write_text("\\documentclass{article}\\begin{document}Hi\\end{document}", encoding="utf-8")

    reusable_output_dir = tmp_path / "reusable-output"
    reusable_output_dir.mkdir(parents=True, exist_ok=True)

    class _FakeTaskManager:
        def is_cancelled(self, _task_id):
            return False

        def get_task(self, _task_id):
            return {
                "task_id": "task-1",
                "arxiv_id": "2508.18971",
                "source_type": "arxiv",
                "source_path": str(source_dir),
            }

        def update_task(self, *_args, **_kwargs):
            return True

    async def _fake_find_reusable_output(config_hash: str, _task_id: str):
        captured_hashes.append(config_hash)
        return str(reusable_output_dir)

    async def _fake_copy_output(_source_output: str, task_id: str) -> str:
        copied = tmp_path / task_id
        copied.mkdir(parents=True, exist_ok=True)
        return str(copied)

    monkeypatch.setattr(translate_route, "task_manager", _FakeTaskManager())
    monkeypatch.setattr(translate_route, "find_main_tex_file", lambda _path: Path(source_dir / "main.tex"))
    monkeypatch.setattr(translate_route, "find_reusable_output", _fake_find_reusable_output)
    monkeypatch.setattr(translate_route, "copy_output", _fake_copy_output)

    advanced_config = AdvancedConfig(
        formatting=FormattingConfig(font_size=12.0, line_spacing=1.0, paragraph_indent=True)
    )

    asyncio.run(
        translate_route.run_translation(
            task_id="task-1",
            target_language="zh",
            source_language="en",
            advanced_config=advanced_config,
            user_id="user-1",
        )
    )

    expected_hash = translate_route.compute_config_hash(
        arxiv_id="2508.18971",
        source_language="en",
        target_language="zh",
        translation_mode="full",
        compile_strategy="auto",
        source_path=str(source_dir),
        formatting=advanced_config.formatting,
    )

    assert captured_hashes == [expected_hash]
