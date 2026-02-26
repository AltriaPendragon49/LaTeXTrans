from typing import Dict, Any, List, Optional, Callable, Tuple
from .base_tool_agent import BaseToolAgent
from .validator_agent import ERROR_TYPE_A, ERROR_TYPE_B, ERROR_TYPE_C
from . import global_llm_semaphore
import backend.app.services.latex.prompts as pm
from backend.app.services.latex.utils import *
from backend.app.services.latex.utils import (
    mask_sensitive_commands,
    unmask_sensitive_commands,
)
from pathlib import Path
import os
import re
import regex
import asyncio
import aiohttp
import time
import pandas as pd
import logging
import json
from collections import Counter

logger = logging.getLogger(__name__)


class TranslatorAgent(BaseToolAgent):
    def __init__(self, 
                 config: Dict[str, Any], 
                 trans_mode: int = 0,
                 project_dir: Optional[str] = None,
                 output_dir: Optional[str] = None,
                 errors_report: Optional[List[Dict]] = None,
                 generate_terminology: bool = False,
                 on_progress: Optional[Callable[[int, str], None]] = None,
                 ):
        super().__init__(agent_name="TranslatorAgent", config=config, on_progress=on_progress)
        self.config = config
        self.update_term = config.get("update_term", False)
        self.model = config["llm_config"].get("model", "gpt-4o")
        self.base_url = config["llm_config"].get("base_url", None)
        self.API_KEY = config["llm_config"].get("api_key", None)
        self.user_term = config.get("user_term", None)
        self.target_language = config.get("target_language", "ch")
        self.category = config.get("category", None)
        self.project_dir = project_dir  # Project path for parsing
        self.output_dir = output_dir  # Output directory for parsed files
        self.fail_section_nums = []
        self.fail_caption_phs = []
        self.fail_env_phs = []
        self.have_fail_parts = False
        self.errors_report = errors_report if errors_report is not None else []
        self.trans_mode = trans_mode if trans_mode is not None else 0
        self.generate_terminology = generate_terminology
        self.terminology_table = []  # 存储术语对: [(源术语, 译术语), ...]
        self.term_dict = {}
        self.summary = ''
        self.prev_text = ''
        self.prev_transed_text = ''
        self.currant_content = ''

    async def execute(self, error_retry_count=0, Maxtry=3):

        self.prompts = pm.create_prompts(self.config["source_language"], self.config["target_language"])
        self.add_placeholder()
        self.build_term_dict()

        sections = self.read_file(Path(self.output_dir, "sections_map.json"), "json")
        captions = self.read_file(Path(self.output_dir, "captions_map.json"), "json")
        envs = self.read_file(Path(self.output_dir, "envs_map.json"), "json")

        # Debug log for trans_mode
        logger.info(f"TranslatorAgent executing with trans_mode={self.trans_mode}")

        if self.trans_mode == 0 or self.trans_mode == 2:
            logger.info(f"Starting translating for project: {os.path.basename(self.project_dir)}")
            self.update_progress(5, f"Starting translating for project: {os.path.basename(self.project_dir)}")

            async with aiohttp.ClientSession() as session:
                sem = asyncio.Semaphore(10)

                async def process_section(i, sec):
                    async with sem:
                        translated = await self.translate(sec, envs, captions, session)
                        return i, translated

                tasks = [process_section(i, sec) for i, sec in enumerate(sections)]

                completed = 0
                total = len(tasks)

                for future in asyncio.as_completed(tasks):
                    i, translated_section = await future
                    sections[i] = translated_section
                    
                    completed += 1
                    progress = int(5 + 90 * completed / total)
                    self.update_progress(progress, f"Translated {completed}/{total} sections")

                    # Save progress
                    self.save_file(Path(self.output_dir, "sections_map.json"), "json", sections)
                    self.save_file(Path(self.output_dir, "captions_map.json"), "json", captions)
                    self.save_file(Path(self.output_dir, "envs_map.json"), "json", envs)

                self.update_progress(95, "Validating translation results")

                await self._val_fail_parts(Maxtry=Maxtry,
                                     sections=sections,
                                     captions=captions,
                                     envs=envs,
                                     session=session)

                logger.info("Successfully translated sections!")
                self.update_progress(100, "Successfully translated sections!")

        elif self.trans_mode == 1:
            async with aiohttp.ClientSession() as session:
                error_parts = [error_part["num_or_ph"] for error_part in self.errors_report]
                logger.info(f"Starting retranslating for error parts: {error_parts}, attempt {error_retry_count + 1}/{Maxtry}")
                
                await self._retranslate_error_parts(secs=sections,
                                                    caps=captions,
                                                    envs=envs,
                                                    session=session)

                self.save_file(Path(self.output_dir, "sections_map.json"), "json", sections)
                self.save_file(Path(self.output_dir, "captions_map.json"), "json", captions)
                self.save_file(Path(self.output_dir, "envs_map.json"), "json", envs)

                self.fail_section_nums.clear()
                self.fail_caption_phs.clear()
                self.fail_env_phs.clear()
                self.have_fail_parts = False

                await self._val_fail_parts(Maxtry=Maxtry,
                                           sections=sections,
                                           captions=captions,
                                           envs=envs,
                                           session=session)

            logger.info("Successfully retranslated error parts!")

        elif self.trans_mode == 3:
            # Quick scan mode: translate only abstract and conclusion
            logger.info(f"Starting quick scan mode for project: {os.path.basename(self.project_dir)}")
            self.update_progress(5, f"Quick scan mode: translating abstract and conclusion only")

            async with aiohttp.ClientSession() as session:
                sem = asyncio.Semaphore(10)

                # 1. Translate abstract environment (in envs)
                abstract_translated = False
                for i, env in enumerate(envs):
                    if env.get("env_name", "").lower() == "abstract" and env.get("need_trans", False):
                        logger.info("Translating abstract environment")
                        self.update_progress(20, "Translating abstract...")
                        envs[i] = await self._translate_env(env, session)
                        abstract_translated = True
                        break

                if not abstract_translated:
                    logger.warning("No abstract environment found to translate")

                # 2. Find and translate conclusion section(s)
                conclusion_patterns = [
                    r'\\section\*?\{[Cc]onclusion[s]?\}',
                    r'\\section\*?\{[Ss]ummary\}',
                    r'\\section\*?\{[Cc]oncluding [Rr]emarks?\}',
                    r'\\section\*?\{[Ff]inal [Rr]emarks?\}',
                ]
                
                conclusion_sections = []
                for i, sec in enumerate(sections):
                    content = sec.get("content", "")
                    for pattern in conclusion_patterns:
                        if re.search(pattern, content):
                            conclusion_sections.append(i)
                            break

                logger.info(f"Found {len(conclusion_sections)} conclusion section(s)")
                self.update_progress(40, f"Found {len(conclusion_sections)} conclusion section(s)")

                # Translate conclusion sections
                async def process_conclusion_section(i, sec):
                    async with sem:
                        translated = await self.translate(sec, envs, captions, session)
                        return i, translated

                if conclusion_sections:
                    tasks = [process_conclusion_section(i, sections[i]) for i in conclusion_sections]
                    completed = 0
                    total = len(tasks)

                    for future in asyncio.as_completed(tasks):
                        i, translated_section = await future
                        sections[i] = translated_section
                        completed += 1
                        progress = int(40 + 50 * completed / total)
                        self.update_progress(progress, f"Translated {completed}/{total} conclusion sections")

                # 3. For all other sections, copy content to trans_content (skip translation)
                for i, sec in enumerate(sections):
                    if i not in conclusion_sections and "trans_content" not in sec:
                        sec["trans_content"] = sec["content"]

                # For all other envs, copy content to trans_content
                for env in envs:
                    if env.get("env_name", "").lower() != "abstract" and "trans_content" not in env:
                        env["trans_content"] = env["content"]

                # For all captions, copy content to trans_content if not translated
                for cap in captions:
                    if "trans_content" not in cap:
                        cap["trans_content"] = cap["content"]

                # Save results
                self.save_file(Path(self.output_dir, "sections_map.json"), "json", sections)
                self.save_file(Path(self.output_dir, "captions_map.json"), "json", captions)
                self.save_file(Path(self.output_dir, "envs_map.json"), "json", envs)

                logger.info("Quick scan mode completed: abstract and conclusion translated")
                self.update_progress(100, "Quick scan completed: abstract and conclusion translated")
        
        # Save terminology table if enabled
        if self.generate_terminology and self.terminology_table:
            self._save_terminology_table()
            logger.info(f"Terminology table generated with {len(self.terminology_table)} terms")

    def _section_has_translatable_content(self, content: str) -> bool:
        """
        Check if a section (especially section 0) contains translatable text.
        Returns True if there's meaningful text content after \begin{document}.
        """
        # Remove placeholders to check for actual text
        text = re.sub(r'<PLACEHOLDER_[A-Z]+_\d+>', '', content)
        # Remove LaTeX commands that don't contain translatable text
        text = re.sub(r'\\(documentclass|usepackage|author|affiliation|email|date|maketitle|newpage|setcounter|makeatletter|makeatother|label|ref|eqref|cite|bibliography|bibliographystyle)\b[^\n]*', '', text)
        # Remove begin/end document
        text = re.sub(r'\\(begin|end)\{document\}', '', text)
        # Remove comments
        text = re.sub(r'%[^\n]*', '', text)
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Check if there's substantial text content (more than just LaTeX markup)
        # Look for actual words (at least 50 characters of text content)
        return len(text) > 50

    async def translate(self,
                        section: Dict[str, Any],
                        envs: List[Dict[str, Any]],
                        captions: List[Dict[str, Any]],
                        session: aiohttp.ClientSession) -> Dict[str, Any]:
        """
        Translates the input data.

        Uses a 3-phase concurrent approach:
          Phase 1: Translate section body (single await, sequential).
          Phase 2: Translate all referenced environments concurrently via asyncio.gather.
                   Caption placeholders inside envs are also discovered here.
          Phase 3: Translate all referenced captions concurrently via asyncio.gather.
        """
        placeholder_pattern_cap = r"<PLACEHOLDER_CAP_\d+>"
        placeholder_pattern_env = r"<PLACEHOLDER_ENV_\d+>"
        placeholders_cap = re.findall(placeholder_pattern_cap, section["content"])
        placeholders_env = re.findall(placeholder_pattern_env, section["content"])

        # ── Phase 1: Translate section body ──────────────────────────────────
        # Section -1 is LaTeX preamble, never translate.
        # Section 0 may contain main body text, translate if it has translatable content.
        if section["section"] == "-1":
            pass  # Skip preamble
        elif section["section"] == "0":
            if self._section_has_translatable_content(section["content"]):
                logger.info(f"Section 0 contains translatable content, translating...")
                section = await self._translate_section(section, session)
            # else: no translatable content, keep original
        else:
            section = await self._translate_section(section, session)

        # ── Phase 2: Translate all environments concurrently ─────────────────
        # Build a lookup: placeholder → index in envs list.
        env_ph_to_idx = {env["placeholder"]: i for i, env in enumerate(envs)}

        async def _translate_env_by_ph(placeholder: str):
            idx = env_ph_to_idx.get(placeholder)
            if idx is None:
                return
            env = envs[idx]
            # Discover captions embedded inside this env's content.
            cap_phs_in_env = re.findall(placeholder_pattern_cap, env["content"])
            placeholders_cap.extend(cap_phs_in_env)
            envs[idx] = await self._translate_env(env, session)

        if placeholders_env:
            await asyncio.gather(*[_translate_env_by_ph(ph) for ph in placeholders_env])

        # ── Phase 3: Translate all captions concurrently ─────────────────────
        # Remove duplicates while preserving order (captions from section + from envs).
        placeholders_cap = list(dict.fromkeys(placeholders_cap))

        cap_ph_to_idx = {cap["placeholder"]: i for i, cap in enumerate(captions)}

        async def _translate_caption_by_ph(placeholder: str):
            idx = cap_ph_to_idx.get(placeholder)
            if idx is None:
                return
            captions[idx] = await self._translate_caption(captions[idx], session)

        if placeholders_cap:
            await asyncio.gather(*[_translate_caption_by_ph(ph) for ph in placeholders_cap])

        return section
    
    async def _val_fail_parts(self, sections, captions, envs, Maxtry, session: aiohttp.ClientSession, fail_retry_count=0) -> str:
            while fail_retry_count < Maxtry and self.have_fail_parts:
                fail_parts = self.fail_section_nums + self.fail_caption_phs + self.fail_env_phs
                if fail_retry_count == Maxtry:
                    logger.error(f"Failed to translate {fail_parts}")
                    break
                    
                logger.info(f"Retranslating fail parts: {fail_parts}, attempt {fail_retry_count+1}/{Maxtry}")
                
                await self._retranslate_fail_parts(secs=sections,
                                            caps=captions,
                                            envs=envs,
                                            session=session)
                self.save_file(Path(self.output_dir, "sections_map.json"), "json", sections)
                self.save_file(Path(self.output_dir, "captions_map.json"), "json", captions)
                self.save_file(Path(self.output_dir, "envs_map.json"), "json", envs)
                
                fail_retry_count += 1

    async def _retranslate_fail_parts(self,
                                secs: List[Dict[str, Any]], 
                                caps: List[Dict[str, Any]], 
                                envs: List[Dict[str, Any]],
                                session: aiohttp.ClientSession) -> Any:
        sec_nums = self.fail_section_nums[:]
        cap_phs = self.fail_caption_phs[:]
        env_phs = self.fail_env_phs[:]
        self.fail_section_nums.clear()
        self.fail_caption_phs.clear()
        self.fail_env_phs.clear()
        self.have_fail_parts = False

        sec_dict = {s["section"]: i for i, s in enumerate(secs)}
        cap_dict = {c["placeholder"]: i for i, c in enumerate(caps)}
        env_dict = {e["placeholder"]: i for i, e in enumerate(envs)}

        if sec_nums:
            self.log(f"Retranslating for {sec_nums}")
            for sec_num in sec_nums:
                # Section -1 is preamble, always skip
                # Section 0 should be translated if it has translatable content
                if sec_num == "-1":
                    continue
                if sec_num == "0" and not self._section_has_translatable_content(secs[sec_dict.get(sec_num, 0)]["content"]):
                    continue
                if sec_num in sec_dict:
                    i = sec_dict[sec_num]
                    secs[i] = await self._translate_section(secs[i], session)
            # else:
            #     print(f"[Warning] Section {sec_num} not found.")
        if cap_phs:
            self.log(f"Retranslating for {cap_phs}")
            for cap_ph in cap_phs:
                if cap_ph in cap_dict:
                    i = cap_dict[cap_ph]
                    caps[i] = await self._translate_caption(caps[i], session) 
            # else:
            #     print(f"[Warning] Caption placeholder {cap_ph} not found.")
        if env_phs:
            self.log(f"Retranslating for {env_phs}")
            for env_ph in env_phs:
                if env_ph in env_dict:
                    i = env_dict[env_ph]
                    envs[i] = await self._translate_env(envs[i], session) 
            # else:
            #     print(f"[Warning] Environment placeholder {env_ph} not found.")

    async def _retranslate_error_parts(self, secs, caps, envs, session) -> Any:
        """
        Retranslate error parts with A/B/C error type routing:
        - Type A (resource missing): Apply degradation, keep existing translation
        - Type B (recoverable): Allow one translation retry
        - Type C (structural): Apply algorithmic fix without LLM retry
        """
        async with aiohttp.ClientSession() as session:
            sem = asyncio.Semaphore(20)
            
            completed = 0
            total = len(self.errors_report)
            
            # Group errors by type for efficient processing
            type_a_errors = []
            type_b_errors = []
            type_c_errors = []
            
            for error_report in self.errors_report:
                error_type = error_report.get("error_type", ERROR_TYPE_B)
                if error_type == ERROR_TYPE_A:
                    type_a_errors.append(error_report)
                elif error_type == ERROR_TYPE_C:
                    type_c_errors.append(error_report)
                else:
                    type_b_errors.append(error_report)
            
            logger.info(f"Error classification: A={len(type_a_errors)}, B={len(type_b_errors)}, C={len(type_c_errors)}")
            
            # Process Type A errors: Degradation (keep existing translation, log warning)
            for error in type_a_errors:
                logger.warning(f"Type A error (degradation): {error.get('num_or_ph')} - keeping existing translation")
                completed += 1
                progress_pct = int(100 * completed / total) if total > 0 else 100
                self.update_progress(progress_pct, f"Processed {completed}/{total} (A:degraded)")
            
            # Process Type C errors: Algorithmic fix
            for error in type_c_errors:
                part = self._find_part_by_error(error, secs, caps, envs)
                if part:
                    fixed = self._apply_structural_fix(part, error)
                    if fixed:
                        logger.info(f"Type C error fixed algorithmically: {error.get('num_or_ph')}")
                    else:
                        logger.warning(f"Type C fix failed, preserving current translation: {error.get('num_or_ph')}")
                completed += 1
                progress_pct = int(100 * completed / total) if total > 0 else 100
                self.update_progress(progress_pct, f"Processed {completed}/{total} (C:fixed)")
            
            # Process Type B errors: Translation retry (existing logic)
            async def process_type_b_error(error_report):
                async with sem:
                    error_message = []
                    if "command_error" in error_report:
                        error_message.append(error_report["command_error"])
                    if "ph_error" in error_report:
                        error_message.append(error_report["ph_error"])
                    if "bracket_error" in error_report:
                        error_message.append(error_report["bracket_error"])
                    error_message = "\n".join(error_message)
                    
                    part_type = error_report["part"]
                    identifier = error_report["num_or_ph"]

                    if part_type == "sec":
                        for i, sec in enumerate(secs):
                            if identifier == sec["section"]:
                                secs[i] = await self._translate_section(
                                    section=sec, error_message=error_message, session=session
                                )
                                return True
                    elif part_type == "env":
                        for i, env in enumerate(envs):
                            if identifier == env["placeholder"]:
                                envs[i] = await self._translate_env(
                                    env=env, error_message=error_message, session=session
                                )
                                return True
                    elif part_type == "cap":
                        for i, cap in enumerate(caps):
                            if identifier == cap["placeholder"]:
                                caps[i] = await self._translate_caption(
                                    caption=cap, error_message=error_message, session=session
                                )
                                return True
                    return False

            tasks_type_b = [process_type_b_error(error) for error in type_b_errors]
            for future in asyncio.as_completed(tasks_type_b):
                result = await future
                completed += 1
                progress_pct = int(100 * completed / total) if total > 0 else 100
                self.update_progress(progress_pct, f"Retranslated {completed}/{total} (B:retry)")
            
            logger.info("Completed retranslation of error parts")
    
    def _find_part_by_error(self, error: Dict, secs: List, caps: List, envs: List) -> Optional[Dict]:
        """Find the part (section/caption/env) referenced by an error report."""
        part_type = error.get("part")
        identifier = error.get("num_or_ph")
        
        if part_type == "sec":
            for sec in secs:
                if sec["section"] == identifier:
                    return sec
        elif part_type == "env":
            for env in envs:
                if env["placeholder"] == identifier:
                    return env
        elif part_type == "cap":
            for cap in caps:
                if cap["placeholder"] == identifier:
                    return cap
        return None
    
    def _apply_structural_fix(self, part: Dict, error: Dict) -> bool:
        """
        Apply algorithmic fix for Type C structural consistency errors.

        Strategies:
        1. Token补齐: Restore missing LaTeX commands from original
        2. Placeholder恢复: Restore missing placeholders from original
        3. Math delimiter repair: Fix missing/extra $ delimiters using original as reference
        4. Fallback: Keep existing translation if available, else use original

        Returns True if fix was successful (or fallback applied).
        """
        original = part.get("content", "")
        translated = part.get("trans_content", "")

        if not translated:
            # No translation exists, use original as fallback
            part["trans_content"] = original
            return True

        try:
            # Strategy 1: Restore missing LaTeX commands
            fixed = self._fix_missing_commands(original, translated)

            # Strategy 2: Restore missing placeholders
            fixed = self._fix_missing_placeholders(original, fixed)

            # Strategy 3: Repair math-mode delimiters ($ / $$)
            # Triggered when the error report contains a math_delimiter_mismatch.
            math_error = error.get("math_error", "") or ""
            if "math_delimiter_mismatch" in math_error:
                from .validator_agent import ValidatorAgent as _VA
                repaired = _VA.repair_math_delimiters(original, fixed)
                if repaired is not None:
                    fixed = repaired
                    logger.info(
                        "Applied math-delimiter repair for part %s",
                        error.get("num_or_ph", "?"),
                    )

            part["trans_content"] = fixed
            return True

        except Exception as e:
            logger.warning(f"Structural fix failed: {e}")
            # Fallback: keep existing translation if available
            if translated:
                return True
            part["trans_content"] = original
            return True

    
    def _fix_missing_commands(self, original: str, translated: str) -> str:
        """Restore missing LaTeX commands from original to translated content."""
        # Extract commands with regex
        cmd_pattern = r'\\([a-zA-Z]+)(?:\{[^}]*\})*'
        
        original_cmds = re.findall(cmd_pattern, original)
        translated_cmds = re.findall(cmd_pattern, translated)
        
        original_counter = Counter(original_cmds)
        translated_counter = Counter(translated_cmds)
        
        # Find missing commands
        for cmd, count in original_counter.items():
            trans_count = translated_counter.get(cmd, 0)
            if trans_count < count:
                # Command is missing in translation, log but don't modify
                # (Complex insertion could break LaTeX structure)
                logger.debug(f"Missing command \\{cmd}: expected {count}, found {trans_count}")
        
        return translated
    
    def _fix_missing_placeholders(self, original: str, translated: str) -> str:
        """Restore missing placeholders from original to translated content."""
        pattern = r'<PLACEHOLDER_[^>]+>'
        
        original_phs = re.findall(pattern, original)
        
        # 1. Before checking translated, restore any LLM-escaped mangled placeholders 
        # that might be hiding as $<$PLACEHOLDER_...>$> or \textless PLACEHOLDER\_... \textgreater
        translated = restore_mangled_placeholders(translated, original_phs)
        
        translated_phs = re.findall(pattern, translated)
        
        # Scenario 1: Exact count match but contents differ (spelling error)
        if len(original_phs) == len(translated_phs) and original_phs != translated_phs:
            for orig_ph, trans_ph in zip(original_phs, translated_phs):
                if orig_ph != trans_ph:
                    logger.debug(f"Correcting misspelled placeholder: {trans_ph} -> {orig_ph}")
                    translated = translated.replace(trans_ph, orig_ph)
            return translated
            
        original_ph_set = set(original_phs)
        translated_ph_set = set(translated_phs)
        missing = original_ph_set - translated_ph_set
        
        # Scenario 2: Placeholders are missing
        for ph in missing:
            if ph in translated:
                continue
                
            logger.debug(f"Restoring missing placeholder: {ph}")
            
            # Extract base tag name to pair _begin and _end using regex
            base_match = re.match(r'<PLACEHOLDER_(.+?)(?:_(begin|end))?>', ph)
            if base_match:
                base_name = base_match.group(1)
                tag_type = base_match.group(2)
                
                inserted = False
                if tag_type == "begin":
                    paired_end = f"<PLACEHOLDER_{base_name}_end>"
                    if paired_end in translated:
                        # Insert right before the paired end
                        idx = translated.find(paired_end)
                        translated = translated[:idx] + ph + " " + translated[idx:]
                        inserted = True
                elif tag_type == "end":
                    paired_begin = f"<PLACEHOLDER_{base_name}_begin>"
                    if paired_begin in translated:
                        # Insert right after the paired begin
                        idx = translated.find(paired_begin) + len(paired_begin)
                        translated = translated[:idx] + " " + ph + translated[idx:]
                        inserted = True
                
                if not inserted:
                    # Fallback: append at the end
                    translated = translated.rstrip() + " " + ph
            else:
                translated = translated.rstrip() + " " + ph
                
        return translated

    async def _translate_section(self, section: Dict[str, Any], session: aiohttp.ClientSession, error_message=None) -> Dict[str, Any]:
        
        transed_section = section.copy()
        section_num = section["section"]
        previous_context = section.get("previous_context")
        
        async def fetch_translation(use_context: bool) -> str:
            ctx = previous_context if use_context else None
            
            if self.trans_mode == 0 or self.trans_mode == 3:
                return await self._request_llm_for_trans(
                    self.prompts["section_system_prompt"],
                    section["content"],
                    fail_part=section_num,
                    type="sec",
                    session=session,
                    previous_context=ctx
                )
            elif self.trans_mode == 2:
                if not self.term_dict:
                    return await self._request_llm_for_trans(
                        self.prompts["section_system_prompt"],
                        section["content"],
                        fail_part=section_num,
                        type="sec",
                        session=session,
                        previous_context=ctx
                    )
                else:
                    return await self._request_llm_for_trans_with_terms(
                        self.prompts["section_system_prompt_with_dict"],
                        section["content"], 
                        fail_part=section_num,
                        type="sec",
                        session=session,
                        previous_context=ctx
                    )
            return None

        # Execute base translation with anti-leakage downgrade loop
        if self.trans_mode in [0, 2, 3]:
            # Attempt 1: With Context
            result = await fetch_translation(use_context=True)
            
            # Leakage Check
            if result and "<REFERENCE_CONTEXT>" in result:
                logger.warning(f"⚠️ Prompt leakage detected in {section_num}. Retrying...")
                # Attempt 2: Retry with Context
                result = await fetch_translation(use_context=True)
                
                if result and "<REFERENCE_CONTEXT>" in result:
                    logger.warning(f"🚨 Persistent leakage in {section_num}. Downgrading context...")
                    # Attempt 3: Downgrade (No Context)
                    result = await fetch_translation(use_context=False)
                    
            transed_section["trans_content"] = result if result is not None else section["content"]

        elif self.trans_mode == 1:
            transed_section["trans_content"] = await self._request_llm_for_retrans_error_parts(
            self.prompts["retrans_error_parts_system_prompt"],
            part=transed_section,
            error_message=error_message,
            fail_part=section_num,
            type="sec",
            session=session)

        # Terminology Extraction execution...
        if self.trans_mode == 2:
            try:
                if self.update_term == True:
                    src_text = self._extract_text_from_tex(transed_section["content"])
                    tgt_text = self._extract_text_from_tex(transed_section.get("trans_content") or transed_section["content"])
                    term_text = await self._request_llm_for_extract_terms(self.prompts["extract_terminology_system_prompt"],
                                                            src_text,
                                                            tgt_text,
                                                            session=session
                                                            )

                    # self._updated_term_dict(term_text)
                    self._updated_term_dict_v2(term_text)
            except Exception as e:
                return transed_section
        
        # Extract terminology if enabled (for all modes except mode 2 which does its own extraction)
        if self.generate_terminology and self.trans_mode != 2:
            try:
                src_text = self._extract_text_from_tex(transed_section["content"])
                tgt_text = self._extract_text_from_tex(transed_section.get("trans_content") or transed_section["content"])
                terms = await self._extract_terminology_from_translation(src_text, tgt_text, session)
                if terms:
                    self.terminology_table.extend(terms)
            except Exception as e:
                logger.warning(f"Failed to extract terminology from section: {e}")
        
        return transed_section

    async def _translate_caption(self, caption: Dict[str, Any], session: aiohttp.ClientSession, error_message=None) -> Dict[str, Any]:
        """
        Translates the captions of the input data.
        """
        transed_caption = caption.copy()
        placeholder = caption["placeholder"]
        if self.trans_mode == 0:
            transed_caption["trans_content"] = await self._request_llm_for_trans(self.prompts["caption_system_prompt"],
                                                        caption["content"],
                                                        fail_part=placeholder,
                                                        type="cap",
                                                        session=session
                                                        )
        elif self.trans_mode == 1:
            """先不改"""
            print("translate_caption_mode_1")
            transed_caption["trans_content"] = await self._request_llm_for_retrans_error_parts(self.prompts["retrans_error_parts_system_prompt"],
                                                                                         part=transed_caption,
                                                                                         error_message=error_message,
                                                                                         fail_part=placeholder,
                                                                                         type="cap",
                                                                                         session=session)
            
        elif self.trans_mode == 2:
            if not self.term_dict:
                transed_caption["trans_content"] = await self._request_llm_for_trans(self.prompts["caption_system_prompt"],
                                                        caption["content"], 
                                                        fail_part=placeholder,
                                                        type="cap",
                                                        session=session
                                                        )
            else:
                transed_caption["trans_content"] = await self._request_llm_for_trans_with_terms(self.prompts["caption_system_prompt_with_dict"],
                                                                                          caption["content"],
                                                                                          fail_part=placeholder,
                                                                                          type="cap",
                                                                                          session=session)
            try:
                if self.update_term == True:
                    src_text = self._extract_text_from_tex(transed_caption["content"])
                    tgt_text = self._extract_text_from_tex(transed_caption["trans_content"])
                    term_text = await self._request_llm_for_extract_terms(pm.extract_terminology_system_prompt,
                                                            src_text,
                                                            tgt_text,
                                                            session=session
                                                            )

                    # self._updated_term_dict(term_text)
                    self._updated_term_dict_v2(term_text)
            except Exception as e:
                return transed_caption

        return transed_caption

    async def _translate_env(self, env: Dict[str, Any], session: aiohttp.ClientSession, error_message=None) -> Dict[str, Any]:
        """
        Translates an environment block (env) based on whether translation is needed.
        """
        transed_env = env.copy()
        placeholder = env["placeholder"]
        if self.trans_mode == 0: # sum
            if env["need_trans"]:
                transed_env["trans_content"] = await self._request_llm_for_trans(self.prompts["env_system_prompt"],
                                                            env["content"], 
                                                            fail_part=placeholder,
                                                            type="env",
                                                            session=session
                                                            )                
            else:
                transed_env["trans_content"] = env["content"]
        elif self.trans_mode == 1:
                transed_env["trans_content"] = await self._request_llm_for_retrans_error_parts(pm.retrans_error_parts_system_prompt,
                                                                                         part=transed_env,
                                                                                         error_message=error_message,
                                                                                         fail_part=placeholder,
                                                                                         type="env",
                                                                                         session = session)
        elif self.trans_mode == 2: # dict or sum+dict
            if not self.term_dict:
                if env["need_trans"]:
                    transed_env["trans_content"] = await self._request_llm_for_trans(self.prompts["env_system_prompt"],
                                                            env["content"], 
                                                            fail_part=placeholder,
                                                            type="env",
                                                            session=session
                                                            )
                else:
                    transed_env["trans_content"] = env["content"]
            else:
                if env["need_trans"]:
                    transed_env["trans_content"] = await self._request_llm_for_trans_with_terms(self.prompts["env_system_prompt_with_dict"],
                                                                                            env["content"],
                                                                                            fail_part=placeholder,
                                                                                            type="env",
                                                                                            session=session)
                else:
                    transed_env["trans_content"] = env["content"]

            if env["need_trans"]:
                try:
                    if self.update_term == True:
                        src_text = self._extract_text_from_tex(transed_env["content"])
                        tgt_text = self._extract_text_from_tex(transed_env["trans_content"])
                        text = await self._request_llm_for_extract_terms(pm.extract_terminology_system_prompt,
                                                                src_text,
                                                                tgt_text,
                                                                session=session
                                                                )

                            # self._updated_term_dict(term_text)
                        self._updated_term_dict_v2(text)
                except Exception as e:
                    return transed_env

        elif self.trans_mode == 3:
            # Quick scan mode: translate if needed (same as mode 0)
            if env["need_trans"]:
                transed_env["trans_content"] = await self._request_llm_for_trans(self.prompts["env_system_prompt"],
                                                            env["content"], 
                                                            fail_part=placeholder,
                                                            type="env",
                                                            session=session
                                                            )                
            else:
                transed_env["trans_content"] = env["content"]

        return transed_env

    async def _request_llm_for_trans(self,
                                     system_prompt: str,
                                     text: str,
                                     fail_part: str,
                                     type: str,
                                     session: aiohttp.ClientSession,
                                     previous_context: Optional[str] = None) -> str:

        # --- Task 12.4: Mask sensitive commands before sending to LLM ---
        masked_text, _mask_mapping = mask_sensitive_commands(text)
        
        # Inject Reference Context Template if available
        if previous_context and "REFERENCE_CONTEXT_TEMPLATE" in self.prompts:
            template = self.prompts["REFERENCE_CONTEXT_TEMPLATE"]
            system_prompt += template.format(context=previous_context)

        payload = {
            "model": f"{self.model}",
            "messages": [
                {"role": "system", "content": f"{system_prompt}"},
                {"role": "user", "content": f"{masked_text}"}
            ],
            "temperature": 0.7,
            "max_new_tokens": 8192
        }

        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }

        _timeout = aiohttp.ClientTimeout(total=180)
        rate_limit_hits = 0    # Consecutive 429 count
        network_failures = 0   # Non-429 failure count (max 3)
        while True:
            try:
                async with global_llm_semaphore:
                    async with session.post(self.base_url, json=payload, headers=headers, timeout=_timeout) as response:
                        if response.status == 429:
                            # Read Retry-After before exiting response context
                            retry_after_raw = response.headers.get("Retry-After", "")
                            rate_limit_hits += 1
                            # Graduated backoff: ≤3 quick, 4-9 progressive, >9 infinite with warning
                            if rate_limit_hits <= 3:
                                wait = min(int(retry_after_raw) if retry_after_raw.isdigit() else 10, 30)
                            elif rate_limit_hits <= 9:
                                wait = min(30 + (rate_limit_hits - 3) * 5, 60)  # 35s, 40s, ... 60s
                            else:
                                wait = 60
                            logger.warning(
                                f"⏳ API rate limited (429) for {fail_part}, "
                                f"waiting {wait}s (429 count: {rate_limit_hits})"
                            )
                            # Only show frontend warning after 9 consecutive 429s
                            if rate_limit_hits > 9:
                                self.update_progress(
                                    -1,
                                    f"⏳ API rate limited, retrying until API recovers. "
                                    f"Consider using your own API key for better performance. "
                                    f"(429 count: {rate_limit_hits}, waiting {wait}s)"
                                )
                        else:
                            response.raise_for_status()
                            result = await response.json()
                            raw_result = result["choices"][0]["message"]["content"].strip()
                            # --- Task 12.4: Restore masked commands after translation ---
                            restored = unmask_sensitive_commands(raw_result, _mask_mapping)
                            self._log_protection_actions(_mask_mapping, fail_part)
                            return restored
                # --- Semaphore RELEASED here ---
                # Sleep for 429 outside semaphore so other tasks can proceed
                await asyncio.sleep(wait)
                continue

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if isinstance(e, aiohttp.ClientResponseError) and e.status in (400, 401, 403, 404):
                    logger.error(f"❌ Fatal API error {e.status} for {fail_part}: {getattr(e, 'message', str(e))}. Aborting retries.")
                    self.have_fail_parts = True
                    if type == 'sec':
                        self.fail_section_nums.append(fail_part)
                    elif type == 'cap':
                        self.fail_caption_phs.append(fail_part)
                    else:
                        self.fail_env_phs.append(fail_part)
                    return text

                network_failures += 1
                backoff = 5 * (2 ** (network_failures - 1))  # 5s, 10s, 20s
                if network_failures < 3:
                    logger.warning(f"LLM request attempt {network_failures}/3 failed for {fail_part}: {e}. Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                else:
                    self.have_fail_parts = True
                    if type == 'sec':
                        self.fail_section_nums.append(fail_part)
                    elif type == 'cap':
                        self.fail_caption_phs.append(fail_part)
                    else:
                        self.fail_env_phs.append(fail_part)

                    logger.error(f"❌ Failed to translate text after 3 attempts, returning original: {fail_part}. {e}")
                    # Return original (unmasked) text on ultimate failure
                    return text


    async def _request_llm_for_trans_with_terms(self,
                                          system_prompt: str,
                                          text: str,
                                          fail_part: str,
                                          type: str,
                                          session: aiohttp.ClientSession,
                                          previous_context: Optional[str] = None) -> str:

        # --- Task 12.4: Mask sensitive commands before sending to LLM ---
        masked_text, _mask_mapping = mask_sensitive_commands(text)
        
        # Inject Reference Context Template if available
        if previous_context and "REFERENCE_CONTEXT_TEMPLATE" in self.prompts:
            template = self.prompts["REFERENCE_CONTEXT_TEMPLATE"]
            system_prompt += template.format(context=previous_context)

        payload = {
            "model": f"{self.model}",
            "messages": [
                {
                    "role": "system",
                    "content": f"{system_prompt}\nWhen translating, you must strictly use the following glossary for substitution. This is the highest priority rule to ensure the consistency of terms throughout the text.\n<Glossary>:\n{self.term_dict}\nNow, please translate the following new paragraph. Maintain the terminology from the glossary provided."
                },
                {
                    "role": "user",
                    "content": f"[Current LaTeX Paragraph]:\n{masked_text}"
                }
            ],
            "temperature": 0.7,
            # "max_length": 100000,
            "max_new_tokens": 8192
        }

        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }

        _timeout = aiohttp.ClientTimeout(total=180)
        rate_limit_hits = 0    # Consecutive 429 count
        network_failures = 0   # Non-429 failure count (max 3)
        while True:
            try:
                async with global_llm_semaphore:
                    async with session.post(self.base_url, json=payload, headers=headers, timeout=_timeout) as response:
                        if response.status == 429:
                            retry_after_raw = response.headers.get("Retry-After", "")
                            rate_limit_hits += 1
                            if rate_limit_hits <= 3:
                                wait = min(int(retry_after_raw) if retry_after_raw.isdigit() else 10, 30)
                            elif rate_limit_hits <= 9:
                                wait = min(30 + (rate_limit_hits - 3) * 5, 60)
                            else:
                                wait = 60
                            logger.warning(
                                f"⏳ API rate limited (429) for {fail_part}, "
                                f"waiting {wait}s (429 count: {rate_limit_hits})"
                            )
                            if rate_limit_hits > 9:
                                self.update_progress(
                                    -1,
                                    f"⏳ API rate limited, retrying until API recovers. "
                                    f"Consider using your own API key for better performance. "
                                    f"(429 count: {rate_limit_hits}, waiting {wait}s)"
                                )
                        else:
                            response.raise_for_status()
                            result = await response.json()
                            raw_result = result["choices"][0]["message"]["content"].strip()
                            # --- Task 12.4: Restore masked commands after translation ---
                            restored = unmask_sensitive_commands(raw_result, _mask_mapping)
                            self._log_protection_actions(_mask_mapping, fail_part)
                            return restored
                # --- Semaphore RELEASED here ---
                await asyncio.sleep(wait)
                continue

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if isinstance(e, aiohttp.ClientResponseError) and e.status in (400, 401, 403, 404):
                    logger.error(f"❌ Fatal API error {e.status} for {fail_part}: {getattr(e, 'message', str(e))}. Aborting retries.")
                    self.have_fail_parts = True
                    if type == 'sec':
                        self.fail_section_nums.append(fail_part)
                    elif type == 'cap':
                        self.fail_caption_phs.append(fail_part)
                    else:
                        self.fail_env_phs.append(fail_part)
                    return text

                network_failures += 1
                backoff = 5 * (2 ** (network_failures - 1))  # 5s, 10s, 20s
                if network_failures < 3:
                    logger.warning(f"LLM request attempt {network_failures}/3 failed for {fail_part}: {e}. Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                else:
                    self.have_fail_parts = True
                    if type == 'sec':
                        self.fail_section_nums.append(fail_part)
                    elif type == 'cap':
                        self.fail_caption_phs.append(fail_part)
                    else:
                        self.fail_env_phs.append(fail_part)

                    logger.error(f"❌ Failed to translate text after 3 attempts, returning original: {fail_part}. {e}")
                    # Return original (unmasked) text on ultimate failure
                    return text


    async def _request_llm_for_retrans_error_parts(self,
                                                   system_prompt: str,
                                                   part: Dict[str, Any],
                                                   error_message: str,
                                                   fail_part: str,
                                                   type: str,
                                                   session: aiohttp.ClientSession) -> str:

        # --- Mask sensitive commands in the combined prompt ---
        # We mask the full user_prompt (original + translation + error) as one
        # string to avoid placeholder index collisions between original and
        # translation, since both could contain the same CCSXML / \\ccsdesc.
        raw_user_prompt = f"[Original]:\n{part['content']}\n[Translation]:\n{part.get('trans_content', '')}\n[Error]:\n{error_message}"
        user_prompt, _mask_mapping = mask_sensitive_commands(raw_user_prompt)
        payload = {
            "model": f"{self.model}",
            "messages": [
                {
                    "role": "system",
                    "content": f"{system_prompt}\nWhen translating, you must strictly use the following glossary for substitution. This is the highest priority rule to ensure the consistency of terms throughout the text.\n<Glossary>:\n{self.term_dict}\nNow, please translate the following new paragraph. Maintain the terminology from the glossary provided."
                },
                {
                    "role": "user",
                    "content": f"{user_prompt}"
                }
            ],
            "temperature": 0.7,
            # "max_length": 100000,
            "max_new_tokens": 8192
        }

        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }

        _timeout = aiohttp.ClientTimeout(total=180)
        rate_limit_hits = 0    # Consecutive 429 count
        network_failures = 0   # Non-429 failure count (max 3)
        while True:
            try:
                async with global_llm_semaphore:
                    async with session.post(self.base_url, json=payload, headers=headers, timeout=_timeout) as response:
                        if response.status == 429:
                            retry_after_raw = response.headers.get("Retry-After", "")
                            rate_limit_hits += 1
                            if rate_limit_hits <= 3:
                                wait = min(int(retry_after_raw) if retry_after_raw.isdigit() else 10, 30)
                            elif rate_limit_hits <= 9:
                                wait = min(30 + (rate_limit_hits - 3) * 5, 60)
                            else:
                                wait = 60
                            logger.warning(
                                f"⏳ API rate limited (429) for {fail_part}, "
                                f"waiting {wait}s (429 count: {rate_limit_hits})"
                            )
                            if rate_limit_hits > 9:
                                self.update_progress(
                                    -1,
                                    f"⏳ API rate limited, retrying until API recovers. "
                                    f"Consider using your own API key for better performance. "
                                    f"(429 count: {rate_limit_hits}, waiting {wait}s)"
                                )
                        else:
                            response.raise_for_status()
                            result = await response.json()
                            raw_result = result["choices"][0]["message"]["content"].strip()
                            # --- Restore masked commands after retranslation ---
                            restored = unmask_sensitive_commands(raw_result, _mask_mapping)
                            return restored
                # --- Semaphore RELEASED here ---
                await asyncio.sleep(wait)
                continue

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if isinstance(e, aiohttp.ClientResponseError) and e.status in (400, 401, 403, 404):
                    logger.error(f"❌ Fatal API error {e.status} for {fail_part}: {getattr(e, 'message', str(e))}. Aborting retries.")
                    self.have_fail_parts = True
                    if type == 'sec':
                        self.fail_section_nums.append(fail_part)
                    elif type == 'cap':
                        self.fail_caption_phs.append(fail_part)
                    else:
                        self.fail_env_phs.append(fail_part)
                    return part.get("trans_content") or part.get("content", "")

                network_failures += 1
                backoff = 5 * (2 ** (network_failures - 1))  # 5s, 10s, 20s
                if network_failures < 3:
                    logger.warning(f"LLM request attempt {network_failures}/3 failed for {fail_part}: {e}. Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                else:
                    self.have_fail_parts = True
                    if type == 'sec':
                        self.fail_section_nums.append(fail_part)
                    elif type == 'cap':
                        self.fail_caption_phs.append(fail_part)
                    else:
                        self.fail_env_phs.append(fail_part)

                    logger.error(f"❌ Failed to retranslate error parts after 3 attempts, returning previous translation: {fail_part}. {e}")
                    # Return original (unmasked) text on ultimate failure
                    return part.get("trans_content") or part.get("content", "")

    async def _request_llm_for_extract_terms(self, system_prompt, src, tgt,
                                       session: aiohttp.ClientSession) -> str:

        payload = {
            "model": f"{self.model}",
            "messages": [
                {
                    "role": "system", 
                    "content": f"{system_prompt}"
                },
                {
                    "role": "user", 
                    "content": f"<en source>\n{src}\n<zh translation>\n{tgt}"
                }
            ],
            "temperature": 0.7,
            # "max_length": 100000,
            # "max_tokens": 50
        }

        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }

        _timeout = aiohttp.ClientTimeout(total=180)
        for attempt in range(1, 4):
            try:
                async with global_llm_semaphore:
                    async with session.post(self.base_url, json=payload, headers=headers, timeout=_timeout) as response:
                        if response.status == 429:
                            retry_after = int(response.headers.get("Retry-After", 10 * attempt))
                            logger.warning(f"Rate limited (429) during term extraction, waiting {retry_after}s")
                            await asyncio.sleep(retry_after)
                            continue
                        response.raise_for_status()
                        result = await response.json()
                        return result["choices"][0]["message"]["content"].strip()

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if isinstance(e, aiohttp.ClientResponseError) and e.status in (400, 401, 403, 404):
                    logger.error(f"❌ Fatal API error {e.status} during term extraction: {getattr(e, 'message', str(e))}. Aborting retries.")
                    return "N/A"

                wait = 5 * (2 ** (attempt - 1))  # 5s, 10s, 20s
                if attempt < 3:
                    logger.warning(f"Term extraction attempt {attempt}/3 failed: {e}. Retrying in {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    logger.warning("Failed to extract terms after 3 attempts, set N/A.")
                    return "N/A"

    async def _request_llm_for_summary(self, system_prompt: str, text: str, session: aiohttp.ClientSession) -> str:
        """
        Requests the LLM to summarize the given text.
        """
        payload = {
            "model": f"{self.model}",
            "messages": [
                {
                    "role": "system", 
                    "content": f"{system_prompt}"
                },
                {
                    "role": "user", 
                    "content": f"<Text to summarize>:\n{text}\n<Summary>:\n"
                }
            ],
            "temperature": 0.7,
            "max_new_tokens": 8192
        }

        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }
        
        _timeout = aiohttp.ClientTimeout(total=180)
        for attempt in range(1, 4):
            try:
                async with global_llm_semaphore:
                    async with session.post(self.base_url, json=payload, headers=headers, timeout=_timeout) as response:
                        if response.status == 429:
                            retry_after = int(response.headers.get("Retry-After", 10 * attempt))
                            logger.warning(f"Rate limited (429) during summarization, waiting {retry_after}s")
                            await asyncio.sleep(retry_after)
                            continue
                        response.raise_for_status()
                        result = await response.json()
                        return result["choices"][0]["message"]["content"].strip()
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                wait = 5 * (2 ** (attempt - 1))
                if attempt < 3:
                    logger.warning(f"Summary attempt {attempt}/3 failed: {e}. Retrying in {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    logger.warning("Failed to summarize text after 3 attempts, set N/A.")
                    return "N/A"

    async def _request_llm_for_refine_summary(self, system_prompt: str, text: str, sum: str, session: aiohttp.ClientSession) -> str:
        """
        Requests the LLM to refine the given summary.
        """
        payload = {
            "model": f"{self.model}",
            "messages": [
                {
                    "role": "system", 
                    "content": f"{system_prompt}"
                },
                {
                    "role": "user", 
                    "content": f"<prev_summary>:\n{sum}\n<new_section>:\n{text}\n<refined_summary>:\n"
                }
            ],
            "temperature": 0.7,
            "max_new_tokens": 8192
        }

        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }
        
        _timeout = aiohttp.ClientTimeout(total=180)
        for attempt in range(1, 4):
            try:
                async with global_llm_semaphore:
                    async with session.post(self.base_url, json=payload, headers=headers, timeout=_timeout) as response:
                        if response.status == 429:
                            retry_after = int(response.headers.get("Retry-After", 10 * attempt))
                            logger.warning(f"Rate limited (429) during refine summary, waiting {retry_after}s")
                            await asyncio.sleep(retry_after)
                            continue
                        response.raise_for_status()
                        result = await response.json()
                        return result["choices"][0]["message"]["content"].strip()
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                wait = 5 * (2 ** (attempt - 1))
                if attempt < 3:
                    logger.warning(f"Refine summary attempt {attempt}/3 failed: {e}. Retrying in {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    logger.warning("Failed to refine summary after 3 attempts, set N/A.")
                    return "N/A"

    def _updated_term_dict(self, text: str) -> None:
        """
        Updates the term dictionary with new terms.
        """
        pattern = r'"([^"]+)"\s*-\s*"([^"]+)"'
        matches = re.findall(pattern, text)

        seen_lower = {k.lower() for k in self.term_dict}
        
        for en, zh in matches:
            en_lower = en.lower()
            if en_lower not in seen_lower:
                self.term_dict[en] = zh  
                seen_lower.add(en_lower)

        self.save_file(Path(self.output_dir, "term_dict.json"), "json", self.term_dict)

    def _updated_term_dict_v2(self, text: str) -> None:

        new_term_dict = {}
        lines = text.split('\n')[1:]
        for line in lines:
            line = line.strip()
            if not line:
                continue  

            match = re.match(r'^"(.+?)"\s*-\s*"(.+?)"$', line)
            if match:
                english = match.group(1)
                chinese = match.group(2)
                new_term_dict[english] = chinese

        for en, zh in new_term_dict.items():
            if en not in self.term_dict:
                self.term_dict[en] = zh

    def _process_latex_to_eva(self, latex_code):
        latex_code = replace_href(latex_code)
        latex_code = replace_includegraphics(latex_code)
        return latex_code

    def _extract_text_from_tex(self, tex):
        # convert = CustomLatexNodes2Text()
        # text = convert.latex_to_text(tex)
        tex = self._process_latex_to_eva(tex)
        text = LatexNodes2Text().latex_to_text(tex)
        text = delete_ph(text)
        return text
    
    def _merge_with_prev_sections(self, sections: list[dict], idx: int) -> str:
        """
        Merge content of current section with previous two sections (if valid).
        Ignore sections whose 'section' field is "-1" or "0".

        Parameters:
            sections (list of dict): A list of sections, each with keys "section" and "content".
            idx (int): The index of the current section in the list.

        Returns:
            str: The merged content string.
        """
        if not (0 <= idx < len(sections)):
            raise IndexError("Index out of range.")

        merged_content = []
        merged_trans_content = []

        # Check second previous section
        # if idx >= 2:
        #     sec = sections[idx - 2]
        #     if sec["section"] not in {"-1", "0"}:
        #         try:
        #             content = self._extract_text_from_tex(sec["content"])
        #             transed_content = self._extract_text_from_tex(sec["trans_content"])
        #             merged_content.append(content)
        #             merged_trans_content.append(transed_content)
        #         except Exception as e:
        #             pass
                

        # Check first previous section
        if idx >= 1:
            sec = sections[idx - 1]
            if sec["section"] not in {"-1", "0"}:
                try:
                    content = self._extract_text_from_tex(sec["content"])
                    transed_content = self._extract_text_from_tex(sec["trans_content"])
                    merged_content.append(content)
                    merged_trans_content.append(transed_content)
                except Exception as e:
                    pass

        # Always include current section
        try:
            content = self._extract_text_from_tex(sections[idx]["content"])
            transed_content = self._extract_text_from_tex(sections[idx]["trans_content"])
            merged_content.append(content)
            merged_trans_content.append(transed_content)
        except Exception as e:
            pass

        return "\n".join(merged_content)

    def build_term_dict(self):
        if self.user_term:
            df = pd.read_csv(self.user_term, header=None, names=['English Term', 'Chinese Translation'])
            self.term_dict.update(zip(df['English Term'], df['Chinese Translation']))
        else:
            arxiv_id = os.path.basename(self.project_dir)
            # Check if category is not None and has the arxiv_id
            if self.category and self.category.get(arxiv_id):
                term_dict_loaded = False
                for category in self.category[arxiv_id]:
                    file_path = os.path.join('terms', f'{category}.csv')
                    try:
                        df = pd.read_csv(file_path, header=None, names=['English Term', 'Chinese Translation'])
                        self.term_dict.update(zip(df['English Term'], df['Chinese Translation']))
                        term_dict_loaded = True

                    except FileNotFoundError:
                        continue

                if not term_dict_loaded:
                    try:
                        df = pd.read_csv('terms/default.csv', header=None,
                                         names=['English Term', 'Chinese Translation'])
                        self.term_dict.update(zip(df['English Term'], df['Chinese Translation']))
                    except FileNotFoundError as e:
                        print(f"Error: Default terminology file not found: {e}")
            else:
                try:
                    df = pd.read_csv('terms/default.csv', header=None,
                                     names=['English Term', 'Chinese Translation'])
                    self.term_dict.update(zip(df['English Term'], df['Chinese Translation']))
                except FileNotFoundError as e:
                    print(f"Error: Default terminology file not found: {e}")

    def add_placeholder(self):

        # Add placeholders from caption, env, input, and newcommand to the vocabulary
        caption_path = os.path.join(self.output_dir, "captions_map.json")
        input_path = os.path.join(self.output_dir, "inputs_map.json")
        env_path = os.path.join(self.output_dir, "envs_map.json")
        command_path = os.path.join(self.output_dir, "newcommands_map.json")

        placeholder_list = []

        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for item in data:
            if "begin" in item:
                placeholder_list.append(item["begin"])
            if "end" in item:
                placeholder_list.append(item["end"])

        with open(env_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for item in data:
            if "placeholder" in item:
                placeholder_list.append(item["placeholder"])

        with open(caption_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for item in data:
            if "placeholder" in item:
                placeholder_list.append(item["placeholder"])

        with open(command_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for item in data:
            if "placeholder" in item:
                placeholder_list.append(item["placeholder"])


        for item in placeholder_list:
            self.term_dict[item] = item

    def _save_terminology_table(self) -> None:
        """
        Save terminology table to CSV file in output directory.
        """
        import csv
        
        if not self.terminology_table:
            logger.warning("Terminology table is empty, skipping save")
            return
        
        # 去重
        unique_terms = list(dict.fromkeys(self.terminology_table))
        
        term_file = Path(self.output_dir) / "terminology_table.csv"
        try:
            with open(term_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Source Term', 'Translation'])
                writer.writerows(unique_terms)
            logger.info(f"Terminology table saved to {term_file} with {len(unique_terms)} unique terms")
        except Exception as e:
            logger.error(f"Failed to save terminology table: {e}")
    
    async def _extract_terminology_from_translation(
        self, 
        src_text: str, 
        tgt_text: str, 
        session: aiohttp.ClientSession
    ) -> List[Tuple[str, str]]:
        """
        Extract terminology pairs from source and target text.
        Returns list of (source_term, target_term) tuples.
        """
        if not self.generate_terminology:
            return []
        
        try:
            # 使用现有的术语提取逻辑
            term_text = await self._request_llm_for_extract_terms(
                self.prompts["extract_terminology_system_prompt"],
                src_text,
                tgt_text,
                session=session
            )
            
            # 解析返回的术语文本为术语对列表
            terms = self._parse_terminology_text(term_text)
            return terms
        except Exception as e:
            logger.warning(f"Failed to extract terminology: {e}")
            return []
    
    def _parse_terminology_text(self, term_text: str) -> List[Tuple[str, str]]:
        """
        Parse terminology text from LLM response into list of tuples.
        Expects format like: "term1: translation1\nterm2: translation2"
        """
        terms = []
        if not term_text or term_text == "N/A":
            return terms
        
        lines = term_text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 尝试多种分隔符
            for sep in [':', '：', '|', '-', '->']:
                if sep in line:
                    parts = line.split(sep, 1)
                    if len(parts) == 2:
                        src = parts[0].strip()
                        tgt = parts[1].strip()
                        if src and tgt:
                            terms.append((src, tgt))
                        break
        return terms

    def _log_protection_actions(
        self,
        mapping: Dict[str, str],
        fail_part: str,
    ) -> None:
        """
        Task 12.5: Persist protection log entries to data/protection_log/<task_id>.json.

        Only writes when *mapping* is non-empty.  Entries are appended to an
        existing JSON array so the file accumulates across all translation calls.
        """
        if not mapping or not self.output_dir:
            return

        try:
            # Convention: output_dir is <data_root>/<task_id>/output  (or similar).
            task_id = Path(self.output_dir).parent.name or Path(self.output_dir).name

            log_dir = Path(self.output_dir).parent.parent / "protection_log"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"{task_id}.json"

            entries: list = []
            if log_file.exists():
                try:
                    with open(log_file, "r", encoding="utf-8") as fh:
                        entries = json.load(fh)
                except (json.JSONDecodeError, OSError):
                    entries = []

            for placeholder, original in mapping.items():
                entries.append({
                    "fail_part": fail_part,
                    "placeholder": placeholder,
                    "original_command": original,
                })

            with open(log_file, "w", encoding="utf-8") as fh:
                json.dump(entries, fh, ensure_ascii=False, indent=2)

            logger.debug(
                "_log_protection_actions: wrote %d entries to %s",
                len(mapping),
                log_file,
            )
        except Exception as exc:
            logger.warning("_log_protection_actions failed: %s", exc)

