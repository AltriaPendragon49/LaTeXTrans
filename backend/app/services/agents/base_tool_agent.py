"""
Base Tool Agent

Adapted from prototype system with:
- Python logging integrated (replacing print statements)
- Progress callback mechanism added
- All functionality preserved
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable
import json
import yaml
import toml
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class BaseToolAgent(ABC):
    """
    Abstract base class for all tool agents in the multi-agent translation system.

    Each tool agent is responsible for a specific task in the translation workflow,
    such as parsing, translating, refining, or validating documents.
    """

    def __init__(
        self,
        agent_name: str,
        config: Optional[Dict[str, Any]] = None,
        on_progress: Optional[Callable[[str, int, str], None]] = None
    ):
        """
        Initializes the BaseToolAgent.

        Args:
            agent_name (str): The unique name of this agent (e.g., "ParserAgent", "TranslatorAgent").
            config (Optional[Dict[str, Any]]): Agent-specific configuration parameters. Defaults to None.
            on_progress (Optional[Callable]): Progress callback function(stage, percentage, message)
        """
        self.agent_name = agent_name
        self.config = config if config is not None else {}
        self.on_progress = on_progress
        
    def log(self, message: str, level: str = "info"):
        """
        Logs messages at different levels using Python logging.

        Args:
            message (str): The message to log.
            level (str): The logging level. Defaults to "info".
        """
        full_message = f"[{self.agent_name}] {message}"
        
        if level == "info":
            logger.info(full_message)
        elif level == "debug":
            logger.debug(full_message)
        elif level == "warning":
            logger.warning(full_message)
        elif level == "error":
            logger.error(full_message)
        else:
            raise ValueError(f"Unknown log level: {level}")
    
    def update_progress(self, percentage: int, message: str):
        """
        Update progress through callback if available
        
        Args:
            percentage: Progress percentage (0-100)
            message: Progress message
        """
        if self.on_progress:
            self.on_progress(self.agent_name.lower(), percentage, message)

    @abstractmethod
    def execute(self, data: Any, **kwargs: Any) -> Any:
        """
        Executes the core task of the agent.

        This method must be implemented by all concrete tool agent subclasses.
        The input `data` and the returned `Any` type will vary depending on the
        specific agent's role in the workflow (e.g., file path, text string,
        parsed document object, translation result).
        """
        raise NotImplementedError(f"{self.__class__.__name__}.execute() must be implemented.")

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value for the agent.
        If the key does not exist, returns the provided default value.
        """
        return self.config.get(key, default)
    
    def read_file(self, file_path: str, file_format: str) -> Any:
        """
        Reads a file and returns its content.
        
        Args:
            file_path: Path to file
            file_format: Format of file (json, yaml, toml)
            
        Returns:
            File content parsed according to format
        """
        if file_format == "json":
            with open(file_path, "r", encoding='utf-8') as f:
                return json.load(f)
        elif file_format == "yaml":
            with open(file_path, "r", encoding='utf-8') as f:
                return yaml.safe_load(f)
        elif file_format == "toml":
            with open(file_path, "r", encoding='utf-8') as f:
                return toml.load(f)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")
        
    def save_file(self, file_path: str, file_format: str, data: Any):
        """
        Saves data to a file.
        
        Args:
            file_path: Path to save file
            file_format: Format to save in (json, yaml, toml)
            data: Data to save
        """
        if file_format == "json":
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)   
        elif file_format == "yaml":
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f)
        elif file_format == "toml":
            with open(file_path, 'w', encoding='utf-8') as f:
                toml.dump(data, f)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")
