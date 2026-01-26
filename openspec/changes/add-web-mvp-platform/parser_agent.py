"""
Parser Agent

Adapted from prototype system with:
- Streamlit dependencies removed
- Python logging integrated
- Progress callback mechanism added
- LLM config from backend.app.core.config
"""

from typing import Dict, Any, Optional, Callable
from .base_tool_agent import BaseToolAgent
from backend.app.services.latex import prompts as pm
from backend.app.services.latex.parser import LatexParser
from backend.app.core.config import get_llm_config
from pathlib import Path
import os
import requests
import time
from tqdm import tqdm
import logging

logger = logging.getLogger(__name__)


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
        llm_config = get_llm_config()
        self.model = config.get("llm_config", {}).get("model", llm_config.model)
        self.base_url = config.get("llm_config", {}).get("base_url", llm_config.base_url)
        self.API_KEY = config.get("llm_config", {}).get("api_key", llm_config.api_key)

    def execute(self) -> Any:
        """Execute parsing task"""
        pm.init_prompts(self.config.get("source_language", "en"), 
                       self.config.get("target_language", "ch"))
        
        self.log(f"Starting parsing for project: {os.path.basename(self.project_dir)}")
        self.update_progress(0, f"Parsing {os.path.basename(self.project_dir)}")

        latex_parser = LatexParser(self.project_dir, self.output_dir)
        latex_parser.parse(on_progress=self.on_progress)

        env_need_trans = []
        if latex_parser.envs_json:
            for env in latex_parser.envs_json:
                if env["need_trans"] and env["env_name"] not in ['abstract', 'itemize']:
                    env_need_trans.append(env)

        if env_need_trans:
            self.log(f"Setting need_trans for {len(env_need_trans)} environments")
            self.update_progress(70, "Determining translation requirements for environments")

            placeholder_to_index = {
                env["placeholder"]: i for i, env in enumerate(latex_parser.envs_json)
            }
            
            for env in tqdm(env_need_trans, desc=f"Setting need trans", total=len(env_need_trans), unit="env"):
                i = placeholder_to_index.get(env["placeholder"])
                if i is not None:
                    latex_parser.envs_json[i]["need_trans"] = self._request_llm_for_judge(
                        pm.set_need_trans_for_envs_system_prompt,
                        env["content"]
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
        payload = {
            "model": f"{self.model}",
            "messages": [
                {
                    "role": "system", 
                    "content": f"{system_prompt}"
                },
                {
                    "role": "user", 
                    "content": f"{text}"
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
                response = requests.post(self.base_url, json=payload, headers=headers, timeout=100)
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
