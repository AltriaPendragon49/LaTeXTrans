import os
import shutil
from typing import Any, Dict, List, Optional
from pathlib import Path
import sys

base_dir = os.getcwd()
sys.path.append(base_dir)

from .tool_agents.base_tool_agent import BaseToolAgent
from .tool_agents.parser_agent import ParserAgent
from .tool_agents.translator_agent import TranslatorAgent 
from .tool_agents.generator_agent import GeneratorAgent
# from .tool_agents.refinement_agent import RefinementAgent 
# from .tool_agents.reconstructor_agent import ReconstructorAgent 
from .tool_agents.validator_agent import ValidatorAgent 
from .tool_agents.translator_NMT_agent import TranslatorAgent_NMT
from .tool_agents.translator_llama_qwen_agent import TranslatorAgent_llama_qwen
# from .tool_agents.terminology_agent import TerminologyAgent 


class CoordinatorAgent:
    """
    The main orchestrator agent for the translation system.
    It coordinates the workflow of various tool agents based on document format
    and configuration.
    """

    def __init__(self, 
                 config: Dict[str, Any],
                 project_dir: str = None,
                 output_dir: Optional[str] = None
                 ):
        """
        Initializes the CoordinatorAgent.
        """
        self.config = config
        self.name = config.get("sys_name", "AutoTexTrans")
        self.target_language = config.get("target_language", "ch")
        self.project_dir = project_dir  # Project path for parsing
        self.output_dir = output_dir  # Output directory for parsed files

    def workflow_latextrans(self) -> None:
        """
        initializes the tool agent based on the provided agent name key.
        """
        base_name = os.path.basename(self.project_dir)
        transed_project_dir = os.path.join(self.output_dir, f"{self.target_language}_{base_name}")

        os.makedirs(transed_project_dir, exist_ok=True)  

        parser_agent = ParserAgent(config=self.config, 
                                    project_dir=self.project_dir,
                                    output_dir=transed_project_dir)
        parser_agent.execute()
        translator_agent = TranslatorAgent(config=self.config,
                                            project_dir=self.project_dir,
                                            output_dir=transed_project_dir,
                                            trans_mode=0)
        translator_agent.execute()
        # validator_agent = ValidatorAgent(config=self.config,
        #                                     project_dir=self.project_dir,
        #                                     output_dir=transed_project_dir)
        # errors_report = validator_agent.execute()
        # MAX_RETRIES = 3
        # retry_count = 0
        # if errors_report:
        #     translator_agent.trans_mode = 1

        # while  errors_report and retry_count < MAX_RETRIES: # 3 times
        #     translator_agent.errors_report = errors_report
        #     translator_agent.execute(error_retry_count=retry_count, Maxtry=MAX_RETRIES)
        #     errors_report = validator_agent.execute(errors_report)
        #     retry_count += 1

        generator_agent = GeneratorAgent(config=self.config,
                                          project_dir=self.project_dir,
                                          output_dir=transed_project_dir)
        try:
            PDF_file_path = generator_agent.execute()
        except Exception as e:
            print(f"🤖🚧 {self.name}: Failed to translated {os.path.basename(self.project_dir)}.{e}")
            return

        if PDF_file_path:
            new_PDF_path = os.path.join(transed_project_dir, f"{self.target_language}_{base_name}.pdf")
            shutil.move(PDF_file_path, new_PDF_path)
            print(f"🤖🎉 {self.name}: Successfully translated {os.path.basename(self.project_dir)} to {new_PDF_path}.")
        else:
            print(f"🤖🚧 {self.name}: Failed to translated {os.path.basename(self.project_dir)}.")




