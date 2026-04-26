from __future__ import annotations

import json
from pathlib import Path

from backend.app.services.agents.base_tool_agent import BaseToolAgent


class _Agent(BaseToolAgent):
    def __init__(self) -> None:
        super().__init__("TestAgent")

    def execute(self, data=None, **kwargs):
        return None


def test_save_file_recreates_parent_directory(tmp_path: Path) -> None:
    target = tmp_path / "missing" / "nested" / "sections_map.json"

    _Agent().save_file(target, "json", [{"section": "1"}])

    assert target.exists()
    assert json.loads(target.read_text(encoding="utf-8")) == [{"section": "1"}]
