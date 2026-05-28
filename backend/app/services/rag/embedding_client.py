"""文本嵌入客户端 - 基于 sentence-transformers 生成稠密向量嵌入"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── 自定义异常 ───────────────────────────────────────────────────────


class EmbeddingError(RuntimeError):
    """嵌入生成失败时抛出"""


# ── 客户端 ───────────────────────────────────────────────────────────


class EmbeddingClient:
    """使用 sentence-transformers 生成文本嵌入向量。

    参数
    ----------
    model_name : str
        与 ``sentence-transformers`` 兼容的 HuggingFace 模型名称。
        默认为 ``"sentence-transformers/all-MiniLM-L6-v2"``（384 维）。
    device : str, 可选
        Torch 设备字符串（如 ``"cpu"``, ``"cuda"``）。为 *None* 时自动选择。
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: Optional[str] = None,
    ) -> None:
        """初始化嵌入客户端

        参数:
            model_name: 模型名称
            device: 计算设备（可选）
        """
        self.model_name = model_name
        self._device = device
        self._model = None

    # ── 延迟加载模型，避免缺失依赖导致导入失败 ────────────────────────

    def _load_model(self) -> None:
        """延迟加载 sentence-transformers 模型"""
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]
        except ImportError as exc:
            raise EmbeddingError(
                "sentence-transformers is not installed. "
                "Install it with: pip install sentence-transformers"
            ) from exc

        logger.info(
            "Loading embedding model %s (device=%s)", self.model_name, self._device
        )
        self._model = SentenceTransformer(self.model_name, device=self._device)

    # ── 公共 API ──────────────────────────────────────────────────────

    def encode(self, texts: list[str]) -> list[list[float]]:
        """将文本列表编码为稠密向量嵌入。

        参数
        ----------
        texts : list[str]
            一个或多个待嵌入的文本字符串。

        返回
        -------
        list[list[float]]
            每个输入文本对应一个嵌入向量。

        异常
        ------
        EmbeddingError
            模型加载失败或编码出错时抛出。
        """
        if not texts:
            return []

        try:
            self._load_model()
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingError(f"Failed to load embedding model: {exc}") from exc

        try:
            embeddings = self._model.encode(texts, show_progress_bar=False)
            return [emb.tolist() for emb in embeddings]
        except Exception as exc:
            logger.warning("Embedding encoding failed: %s", exc)
            raise EmbeddingError(f"Embedding encoding failed: {exc}") from exc


# ── 工具函数 ─────────────────────────────────────────────────────────


def compute_similarity(embedding1: list[float], embedding2: list[float]) -> float:
    """计算两个嵌入向量之间的余弦相似度。

    参数
    ----------
    embedding1, embedding2 : list[float]
        等长的稠密向量。

    返回
    -------
    float
        余弦相似度，范围在 ``[-1, 1]``。零向量输入或长度不等时返回 ``0.0``。
    """
    if len(embedding1) != len(embedding2):
        logger.warning(
            "Embedding dimension mismatch: %d vs %d",
            len(embedding1),
            len(embedding2),
        )
        return 0.0

    dot = sum(a * b for a, b in zip(embedding1, embedding2))
    norm1 = sum(a * a for a in embedding1) ** 0.5
    norm2 = sum(b * b for b in embedding2) ** 0.5

    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0

    return dot / (norm1 * norm2)
