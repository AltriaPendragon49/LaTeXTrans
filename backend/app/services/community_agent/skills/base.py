from __future__ import annotations

import copy
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import sys
from typing import Any, Dict


@dataclass(frozen=True)
class SkillContract:
    name: str
    description: str
    metadata: Dict[str, Any]
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    planner_notes: str
    source_path: Path


_FRONTMATTER_PATTERN = re.compile(r"\A---\s*\n(?P<body>.*?)\n---\s*\n?", re.DOTALL)


def _extract_frontmatter(text: str) -> Dict[str, str]:
    match = _FRONTMATTER_PATTERN.match(text)
    if not match:
        raise ValueError("Skill contract is missing YAML frontmatter")

    payload: Dict[str, str] = {}
    for raw_line in match.group("body").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        payload[key.strip()] = value.strip()
    return payload


def _extract_section_body(text: str, section_name: str) -> str:
    pattern = re.compile(
        rf"^##\s+{re.escape(section_name)}\s*\n(?P<body>.*?)(?=^##\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        raise ValueError(f"Skill contract is missing the '{section_name}' section")
    return match.group("body").strip()


def _extract_json_block(text: str, section_name: str) -> Dict[str, Any]:
    section_body = _extract_section_body(text, section_name)
    match = re.search(r"```json\s*(?P<body>.*?)\s*```", section_body, re.DOTALL)
    if not match:
        raise ValueError(f"Skill contract section '{section_name}' must include a json code fence")
    payload = json.loads(match.group("body"))
    if not isinstance(payload, dict):
        raise ValueError(f"Skill contract section '{section_name}' must decode to an object")
    return payload


def _extract_text_block(text: str, section_name: str) -> str:
    return _extract_section_body(text, section_name)


@lru_cache(maxsize=32)
def load_skill_contract(contract_path: str) -> SkillContract:
    path = Path(contract_path)
    raw_text = path.read_text(encoding="utf-8")
    frontmatter = _extract_frontmatter(raw_text)

    name = frontmatter.get("name", "").strip()
    description = frontmatter.get("description", "").strip()
    if not name or not description:
        raise ValueError(f"Skill contract '{path}' must define name and description in frontmatter")

    return SkillContract(
        name=name,
        description=description,
        metadata=_extract_json_block(raw_text, "Contract"),
        input_schema=_extract_json_block(raw_text, "Input Schema"),
        output_schema=_extract_json_block(raw_text, "Output Schema"),
        planner_notes=_extract_text_block(raw_text, "Planner Notes"),
        source_path=path,
    )


class AgentSkill(ABC):
    contract_slug: str = ""

    @property
    def contract_path(self) -> Path:
        module = sys.modules.get(self.__class__.__module__)
        module_file = getattr(module, "__file__", None)
        if module_file:
            module_dir = Path(module_file).resolve().parent
            local_contract = module_dir / "SKILL.md"
            if local_contract.exists():
                return local_contract
        if not self.contract_slug:
            raise ValueError(f"{self.__class__.__name__} must define contract_slug")
        return Path(__file__).resolve().parent / "contracts" / self.contract_slug / "SKILL.md"

    @property
    def contract(self) -> SkillContract:
        return load_skill_contract(str(self.contract_path))

    @property
    def name(self) -> str:
        return self.contract.name

    @property
    def description(self) -> str:
        return self.contract.description

    @property
    def trace_kind(self) -> str:
        trace = self.contract.metadata.get("trace") or {}
        return str(trace.get("kind") or "tool")

    @property
    def trace_label(self) -> str:
        trace = self.contract.metadata.get("trace") or {}
        return str(trace.get("label") or self.name)

    @property
    def provider(self) -> str:
        trace = self.contract.metadata.get("trace") or {}
        return str(trace.get("provider") or self.name)

    def input_schema(self) -> Dict[str, Any]:
        return copy.deepcopy(self.contract.input_schema)

    def output_schema(self) -> Dict[str, Any]:
        return copy.deepcopy(self.contract.output_schema)

    def planner_notes(self) -> str:
        return self.contract.planner_notes

    def serialize_for_planner(self) -> Dict[str, Any]:
        metadata = self.contract.metadata
        return {
            "name": self.name,
            "description": self.description,
            "purpose": metadata.get("purpose"),
            "input_schema": self.input_schema(),
            "output_schema": self.output_schema(),
            "visibility": copy.deepcopy(metadata.get("visibility")),
            "planner_notes": self.planner_notes(),
            "trace": copy.deepcopy(metadata.get("trace")),
            "source": str(self.contract.source_path),
        }

    def is_visible(self, runtime_state) -> bool:  # type: ignore[no-untyped-def]
        return True

    @abstractmethod
    async def execute(self, arguments: Dict[str, Any], runtime_state) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
        raise NotImplementedError
