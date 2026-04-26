"""
Parser Agent

Adapted from prototype system with:
- Streamlit dependencies removed
- Python logging integrated
- Progress callback mechanism added
- LLM config from backend.app.core.config
"""

from typing import Dict, Any, Optional, Callable, List
from .base_tool_agent import BaseToolAgent
from .pipeline_invariants import (
    PipelineInvariantViolation,
    assert_no_long_raw_span,
    assert_no_raw_structure,
)
from backend.app.services.latex import prompts as pm
from backend.app.services.latex.parser import LatexParser
from backend.app.services.latex.utils import (
    isolate_env_blocks,
    isolate_math_spans,
    mask_residual_structure_tokens,
    mask_sensitive_commands,
    preprocess_risky_tokens,
)
from backend.app.core.config import get_settings
from .llm_runtime import build_llm_client_timeout, resolve_llm_max_concurrent_requests, resolve_llm_timeout
from .llm_token_pool import post_chat_completion_with_pool
from pathlib import Path
import os
import requests
import aiohttp
import asyncio
import time
from tqdm import tqdm
import logging

logger = logging.getLogger(__name__)

# 不需要 LLM 判断的环境类型列表
# 这些环境类型的翻译需求是确定的，无需调用 LLM
SKIP_LLM_JUDGMENT_ENVS = [
    # 文本类 - 通常需要翻译，但已在父级处理
    'abstract', 'itemize', 'enumerate', 'description',
    # 定理类 - 结构化内容，标题翻译在父级处理，内容由翻译器统一处理
    'theorem', 'lemma', 'proposition', 'corollary', 'remark', 'proof',
    'definition', 'example', 'exercise', 'problem', 'solution', 'note',
    # 引用类 - 通常需要翻译
    'quotation', 'quote', 'verse',
]

# Task 2: Non-translatable environment registry
# These environments must be preserved verbatim — LLM must NEVER touch their content.
# Parser will set need_trans=False for any env whose env_name is in this set.
VERBATIM_ENVS: frozenset = frozenset({
    # Code / listing environments
    'verbatim', 'verbatim*', 'Verbatim', 'lstlisting', 'minted',
    'alltt', 'BVerbatim', 'LVerbatim', 'SaveVerbatim',
    # XML / structural data blocks
    'CCSXML',
    # File content environments
    'filecontents', 'filecontents*',
    # Comment environments (should have been stripped, but guard anyway)
    'comment',
    # TikZ / PGF raw code (fragile)
    'tikzpicture', 'pgfpicture',
    # Algorithm pseudocode (preserve structure)
    'algorithm', 'algorithm2e', 'algorithmic', 'algorithmicx',
    # Theorem-like structured blocks (preserve as Level-A)
    'theorem', 'theorem*', 'lemma', 'lemma*', 'proof', 'proof*', 'definition', 'definition*',
})


class ParserAgent(BaseToolAgent):
    def __init__(self, 
                 config: Dict[str, Any], 
                 project_dir: str = None,
                 output_dir: str = None,
                 on_progress: Optional[Callable[[str, int, str], None]] = None
                 ):
        super().__init__(agent_name="ParserAgent", config=config, on_progress=on_progress)
        self.config = config
        self.project_dir = project_dir
        self.output_dir = output_dir
        
        # Get LLM config
        settings = get_settings()
        llm_config = settings.get_llm_config()
        self.model = config.get("llm_config", {}).get("model", llm_config["model"])
        self.base_url = config.get("llm_config", {}).get("base_url", llm_config["base_url"])
        self.API_KEY = config.get("llm_config", {}).get("api_key", llm_config["api_key"])
        self.request_timeout_seconds = resolve_llm_timeout(config, default=settings.llm_timeout)
        self.llm_max_concurrent_requests = resolve_llm_max_concurrent_requests(
            config,
            default=settings.llm_max_concurrent_requests,
        )
        self.enable_env_llm_judgment = self._coerce_bool(
            config.get("enable_parser_env_llm_judgment", True),
            default=True,
        )

    @staticmethod
    def _coerce_bool(value: Any, default: bool = False) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return default

    def _uses_system_pool(self) -> bool:
        llm_config = self.config.get("llm_config", {})
        if str(llm_config.get("pool_mode") or "").strip() == "system_managed" and llm_config.get("pool_members"):
            return True
        return bool(str(llm_config.get("base_url") or "").strip() and str(llm_config.get("api_key") or "").strip())

    @staticmethod
    def _prepare_llm_payload_text(text: str) -> str:
        isolated_math_text, math_map = isolate_math_spans(text)
        isolated_env_text, _env_map = isolate_env_blocks(isolated_math_text)
        masked_text, mask_mapping = mask_sensitive_commands(isolated_env_text)
        masked_text, _mask_mapping = mask_residual_structure_tokens(
            masked_text,
            mapping=mask_mapping,
        )
        return preprocess_risky_tokens(masked_text, math_map)

    def _prepare_env_judge_payload_text(self, env_text: str) -> str:
        prepared = self._prepare_llm_payload_text(env_text or "")
        assert_no_raw_structure(prepared, context="parser_env_judge")
        assert_no_long_raw_span(
            prepared,
            env_text or "",
            min_span=200,
            context="parser_env_judge",
        )
        return prepared

    async def execute(self) -> Any:
        """Execute parsing task (async version with parallel LLM calls)"""
        self.prompts = pm.create_prompts(
            self.config.get("source_language", "en"),
            self.config.get("target_language", "ch")
        )
        
        self.log(f"Starting parsing for project: {os.path.basename(self.project_dir)}")
        self.update_progress(0, f"Parsing {os.path.basename(self.project_dir)}")

        latex_parser = LatexParser(self.project_dir, self.output_dir)
        await asyncio.to_thread(latex_parser.parse, self.on_progress)

        env_need_trans = []
        skipped_by_type = 0
        skipped_by_length = 0
        
        if latex_parser.envs_json:
            for env in latex_parser.envs_json:
                # Task 2: Force need_trans=False for verbatim/structural environments
                # These must be preserved exactly as-is; LLM must never see their content.
                if env.get("env_name") in VERBATIM_ENVS:
                    env["need_trans"] = False
                    continue
                if not env["need_trans"]:
                    continue
                # 跳过已知不需要 LLM 判断的环境类型
                if env["env_name"] in SKIP_LLM_JUDGMENT_ENVS:
                    skipped_by_type += 1
                    continue
                # 跳过内容太短的环境（通常是占位符或无意义内容）
                content = env.get("content", "")
                if len(content.strip()) <= 20:
                    skipped_by_length += 1
                    continue
                env_need_trans.append(env)
        
        total_envs = len(latex_parser.envs_json) if latex_parser.envs_json else 0
        self.log(f"Environment filter stats: total={total_envs}, "
                 f"need_llm_check={len(env_need_trans)}, "
                 f"skipped_by_type={skipped_by_type}, "
                 f"skipped_by_length={skipped_by_length}")

        if env_need_trans and self.enable_env_llm_judgment:
            self.log(f"Setting need_trans for {len(env_need_trans)} environments (parallel)")
            self.update_progress(70, f"Determining translation for {len(env_need_trans)} environments")

            placeholder_to_index = {
                env["placeholder"]: i for i, env in enumerate(latex_parser.envs_json)
            }
            
            # Use parallel LLM calls for environment judgment
            await self._judge_envs_parallel(env_need_trans, latex_parser, placeholder_to_index)
        elif env_need_trans:
            self.log(
                f"Skipping LLM environment judgment for {len(env_need_trans)} environments; "
                "keeping parser defaults"
            )

        self.update_progress(90, "Saving parsed data to JSON files")
        
        self.save_file(Path(self.output_dir, "inputs_map.json"), "json", latex_parser.inputs_json)
        self.save_file(Path(self.output_dir, "envs_map.json"), "json", latex_parser.envs_json)
        self.save_file(Path(self.output_dir, "captions_map.json"), "json", latex_parser.captions_json)
        self.save_file(Path(self.output_dir, "newcommands_map.json"), "json", latex_parser.newcommands_json)
        self.save_file(Path(self.output_dir, "sections_map.json"), "json", latex_parser.sections_json)

        self.update_progress(100, "Parsing complete")
        self.log(f"Successfully parsed {os.path.basename(self.project_dir)}")
        self.log(f"Parsed files saved in {self.output_dir}")

    def _request_llm_for_judge(self, system_prompt: str, text: str) -> bool:
        """
        Request LLM API to determine if environment needs translation
        """
        try:
            payload_text = self._prepare_env_judge_payload_text(text)
        except PipelineInvariantViolation as inv:
            logger.error("Env-judge payload invariant violation: %s (%s)", inv, inv.error_code)
            return True

        payload = {
            "model": f"{self.model}",
            "messages": [
                {
                    "role": "system", 
                    "content": f"{system_prompt}"
                },
                {
                    "role": "user", 
                    "content": payload_text
                }
            ],
            "temperature": 0,
            "max_tokens": 50
        }

        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }
        
        for attempt in range(1, 4):
            try:
                response = requests.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                    timeout=self.request_timeout_seconds,
                )
                response.raise_for_status()
                result = response.json()
                output = result["choices"][0]["message"]["content"].strip()

                if output.lower() == "true":
                    return True
                elif output.lower() == "false":
                    return False
                else:
                    return True
            except requests.exceptions.RequestException as e:
                if attempt < 3:
                    logger.warning(f"LLM request failed (attempt {attempt}): {e}")
                    time.sleep(3)
                else:
                    logger.error(f"Failed to determine translation need, defaulting to True")
                    return True

    async def _request_llm_for_judge_async(
        self, 
        system_prompt: str, 
        text: str, 
        session: aiohttp.ClientSession,
        semaphore: asyncio.Semaphore
    ) -> bool:
        """
        Async version: Request LLM API to determine if environment needs translation.
        Uses aiohttp and semaphore for concurrent control.
        """
        try:
            payload_text = self._prepare_env_judge_payload_text(text)
        except PipelineInvariantViolation as inv:
            logger.error("Async env-judge payload invariant violation: %s (%s)", inv, inv.error_code)
            return True

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": payload_text}
            ],
            "temperature": 0,
            "max_tokens": 50
        }
        
        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }
        
        async with semaphore:
            for attempt in range(1, 4):
                try:
                    if self._uses_system_pool():
                        result = await post_chat_completion_with_pool(
                            session=session,
                            llm_config=self.config.get("llm_config", {}),
                            payload=payload,
                            timeout=build_llm_client_timeout(self.config, default=self.request_timeout_seconds),
                        )
                        output = result["choices"][0]["message"]["content"].strip()
                        if output.lower() == "true":
                            return True
                        if output.lower() == "false":
                            return False
                        return True
                    async with session.post(
                        self.base_url, 
                        json=payload, 
                        headers=headers, 
                        timeout=build_llm_client_timeout(self.config, default=self.request_timeout_seconds)
                    ) as response:
                        response.raise_for_status()
                        result = await response.json()
                        output = result["choices"][0]["message"]["content"].strip()
                        
                        if output.lower() == "true":
                            return True
                        elif output.lower() == "false":
                            return False
                        else:
                            return True
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    if attempt < 3:
                        logger.warning(f"Async LLM request failed (attempt {attempt}): {e}")
                        await asyncio.sleep(3 * attempt)  # Exponential backoff
                    else:
                        logger.error(f"Failed to determine translation need, defaulting to True")
                        return True
        return True

    async def _judge_envs_parallel(
        self, 
        env_need_trans: List[Dict], 
        latex_parser: 'LatexParser',
        placeholder_to_index: Dict[str, int]
    ) -> None:
        """
        Parallel execution for environment translation judgment.
        Uses asyncio.gather for concurrent LLM calls with progress tracking.
        """
        semaphore = asyncio.Semaphore(self.llm_max_concurrent_requests)
        total_envs = len(env_need_trans)
        completed_count = [0]  # Use list for mutable reference in closure
        
        async with aiohttp.ClientSession() as session:
            async def judge_single_env(env: Dict) -> tuple:
                """Judge a single environment and return (placeholder, result)"""
                result = await self._request_llm_for_judge_async(
                    self.prompts["set_need_trans_for_envs_system_prompt"],
                    env["content"],
                    session,
                    semaphore
                )
                # Update progress counter and report periodically
                completed_count[0] += 1
                if completed_count[0] % 5 == 0 or completed_count[0] == total_envs:
                    progress = 70 + int(20 * completed_count[0] / total_envs)
                    self.update_progress(
                        progress, 
                        f"Judging environments: {completed_count[0]}/{total_envs}"
                    )
                return (env["placeholder"], result)
            
            # Execute all judgments in parallel
            tasks = [judge_single_env(env) for env in env_need_trans]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Apply results to latex_parser
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Parallel env judgment failed: {result}")
                    continue
                placeholder, need_trans = result
                idx = placeholder_to_index.get(placeholder)
                if idx is not None:
                    latex_parser.envs_json[idx]["need_trans"] = need_trans

