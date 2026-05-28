"""
基础工具 Agent

从原型系统适配而来，包含以下改动：
- 集成 Python logging（替代 print 语句）
- 添加进度回调机制
- 保留所有原有功能
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
    多 Agent 翻译系统中所有工具 Agent 的抽象基类。

    每个工具 Agent 负责翻译工作流中的特定任务，
    例如解析、翻译、润色或验证文档。
    """

    def __init__(
        self,
        agent_name: str,
        config: Optional[Dict[str, Any]] = None,
        on_progress: Optional[Callable[[str, int, str], None]] = None
    ):
        """
        初始化 BaseToolAgent。

        Args:
            agent_name (str): Agent 的唯一名称（如 "ParserAgent"、"TranslatorAgent"）。
            config (Optional[Dict[str, Any]]): Agent 专属配置参数，默认为 None。
            on_progress (Optional[Callable]): 进度回调函数 (stage, percentage, message)
        """
        self.agent_name = agent_name
        self.config = config if config is not None else {}
        self.on_progress = on_progress

    def log(self, message: str, level: str = "info"):
        """
        使用 Python logging 记录不同级别的日志消息。

        Args:
            message (str): 要记录的消息。
            level (str): 日志级别，默认为 "info"。
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
        通过回调函数更新进度（如果可用）。

        Args:
            percentage: 进度百分比 (0-100)
            message: 进度消息
        """
        if self.on_progress:
            self.on_progress(self.agent_name.lower(), percentage, message)

    @abstractmethod
    def execute(self, data: Any, **kwargs: Any) -> Any:
        """
        执行 Agent 的核心任务。

        所有具体工具 Agent 子类必须实现此方法。
        输入 `data` 和返回的 `Any` 类型取决于特定 Agent 在工作流中的角色
        （例如文件路径、文本字符串、解析后的文档对象、翻译结果）。
        """
        raise NotImplementedError(f"{self.__class__.__name__}.execute() must be implemented.")

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        获取 Agent 的配置值。
        如果键不存在，返回提供的默认值。
        """
        return self.config.get(key, default)

    def read_file(self, file_path: str, file_format: str) -> Any:
        """
        读取文件并返回其内容。

        Args:
            file_path: 文件路径
            file_format: 文件格式（json、yaml、toml）

        Returns:
            根据格式解析后的文件内容
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
        将数据保存到文件。

        Args:
            file_path: 保存路径
            file_format: 保存格式（json、yaml、toml）
            data: 要保存的数据
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if file_format == "json":
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        elif file_format == "yaml":
            with open(path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f)
        elif file_format == "toml":
            with open(path, 'w', encoding='utf-8') as f:
                toml.dump(data, f)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")
