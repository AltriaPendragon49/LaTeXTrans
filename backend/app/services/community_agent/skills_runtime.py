"""技能提示加载与可见性控制"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from .runtime import AgentRuntimeState

# SKILL.md 文件的前置元数据正则
_FRONTMATTER_PATTERN = re.compile(r"\A---\s*\n(?P<body>.*?)\n---\s*\n?", re.DOTALL)
# 技能合约文件根目录
_SKILL_ROOT = Path(__file__).resolve().parent / "skills" / "contracts"
# 排除在外的技能名称
_EXCLUDED_SKILLS = {"compose_academic_answer"}
# 需要论文上下文才有意义的技能
_PAPER_AWARE_SKILLS = {"read_paper_context", "start_translation_kernel"}


@dataclass(frozen=True)
class PromptSkillPack:
    """单个提示技能的元数据与内容包"""
    name: str
    description: str
    visibility: Dict[str, Any]
    source_path: Path
    raw_markdown: str


@dataclass(frozen=True)
class PromptSkillBundle:
    """可见技能的打包集合"""
    skill_names: List[str]
    skill_index_markdown: str
    prompt_markdown: str


def _extract_frontmatter(text: str) -> Dict[str, str]:
    """提取 SKILL.md 文件的 YAML 前置元数据"""
    match = _FRONTMATTER_PATTERN.match(text)
    if not match:
        return {}

    payload: Dict[str, str] = {}
    for raw_line in match.group("body").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        payload[key.strip()] = value.strip()
    return payload


def _extract_json_block(text: str, section_name: str) -> Dict[str, Any]:
    """从 Markdown 文本中提取 JSON 代码块"""
    pattern = re.compile(
        rf"^##\s+{re.escape(section_name)}\s*\n(?P<body>.*?)(?=^##\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return {}

    json_match = re.search(r"```json\s*(?P<body>.*?)\s*```", match.group("body"), re.DOTALL)
    if not json_match:
        return {}

    try:
        payload = json.loads(json_match.group("body"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


@lru_cache(maxsize=1)
def load_prompt_skill_packs() -> List[PromptSkillPack]:
    """从文件系统加载所有提示技能包（带缓存）"""
    packs: List[PromptSkillPack] = []

    for skill_dir in sorted(_SKILL_ROOT.iterdir(), key=lambda path: path.name):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        raw_markdown = skill_file.read_text(encoding="utf-8")
        frontmatter = _extract_frontmatter(raw_markdown)
        name = str(frontmatter.get("name") or skill_dir.name).strip()
        if not name or name in _EXCLUDED_SKILLS:
            continue

        description = str(frontmatter.get("description") or "").strip()
        contract = _extract_json_block(raw_markdown, "Contract")
        visibility = contract.get("visibility") if isinstance(contract.get("visibility"), dict) else {}
        packs.append(
            PromptSkillPack(
                name=name,
                description=description,
                visibility=visibility,
                source_path=skill_file,
                raw_markdown=raw_markdown,
            )
        )

    return packs


def _is_pack_visible(pack: PromptSkillPack, runtime_state: AgentRuntimeState) -> bool:
    """根据运行时状态判断技能包是否可见"""
    if pack.name == "external_tavily_search":
        return bool((runtime_state.skill_toggles or {}).get("external_search"))
    if pack.name in _PAPER_AWARE_SKILLS:
        return bool(runtime_state.context.get("paper_id") or runtime_state.paper_context)
    return True


def build_skill_prompt_bundle(runtime_state: AgentRuntimeState) -> PromptSkillBundle:
    """根据当前运行时状态构建可见技能提示集"""
    visible_packs = [pack for pack in load_prompt_skill_packs() if _is_pack_visible(pack, runtime_state)]

    skill_index_lines = ["# Active Prompt Skills"]
    prompt_sections: List[str] = []
    for pack in visible_packs:
        skill_index_lines.append(f"- `{pack.name}`: {pack.description}")
        prompt_sections.append(pack.raw_markdown.strip())

    return PromptSkillBundle(
        skill_names=[pack.name for pack in visible_packs],
        skill_index_markdown="\n".join(skill_index_lines),
        prompt_markdown="\n\n".join(prompt_sections),
    )
