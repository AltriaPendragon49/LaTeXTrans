"""Cross-Encoder 重排序器 - 对候选术语进行精细相关性评分"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── 重排序器 ─────────────────────────────────────────────────────────


class CrossEncoderReranker:
    """Cross-Encoder 重排序器，用于对候选术语进行细粒度评分。

    底层使用 ``sentence-transformers`` 的 ``CrossEncoder``。

    参数
    ----------
    model_name : str
        HuggingFace cross-encoder 模型名称。
        默认为 ``"cross-encoder/ms-marco-MiniLM-L-6-v2"``。
    device : str, 可选
        Torch 设备（``"cpu"``, ``"cuda"``）。为 *None* 时自动选择。
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        device: Optional[str] = None,
    ) -> None:
        """初始化 Cross-Encoder 重排序器

        参数:
            model_name: 模型名称
            device: 计算设备（可选）
        """
        self.model_name = model_name
        self._device = device
        self._model = None
        self._load_error: Optional[str] = None

    # ── 模型加载 ─────────────────────────────────────────────────────

    def _load_model(self) -> None:
        """延迟加载 CrossEncoder 模型，已加载则跳过"""
        if self._model is not None:
            return
        try:
            from sentence_transformers import CrossEncoder  # type: ignore[import-untyped]
        except ImportError as exc:
            msg = (
                "sentence-transformers is not installed. "
                "Install with: pip install sentence-transformers"
            )
            logger.warning(msg)
            self._load_error = msg
            return

        try:
            logger.info(
                "Loading CrossEncoder model %s (device=%s)",
                self.model_name,
                self._device,
            )
            self._model = CrossEncoder(self.model_name, device=self._device)
            self._load_error = None
        except Exception as exc:
            msg = f"Failed to load CrossEncoder model {self.model_name}: {exc}"
            logger.warning(msg)
            self._load_error = msg

    # ── 公共 API ─────────────────────────────────────────────────────

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        top_n: int = 10,
    ) -> list[dict]:
        """对候选术语评分，返回按相关性排序的前 ``top_n`` 个结果。

        参数
        ----------
        query : str
            查询文本（如 LaTeX 文本块）。
        candidates : list[dict]
            候选术语字典。每个必须包含 ``"source_term"`` 键。
            可以同时有 ``"bm25_score"`` 和/或 ``"vector_score"``。
        top_n : int
            返回的最高评分候选数量。

        返回
        -------
        list[dict]
            输入字典附加 ``"rerank_score"`` 字段，按降序排列，
            截断至 ``top_n``。失败时原样返回按现有评分排序的候选项。
        """
        if not query or not query.strip() or not candidates:
            return candidates[:top_n] if candidates else []

        # 模型不可用时的回退策略。
        if self._model is None:
            logger.warning(
                "CrossEncoder model not loaded; "
                "falling back to existing candidate scores."
            )
            return self._fallback_sort(candidates, top_n)

        # 构建 (query, source_term) 配对。
        pairs = []
        valid_candidates = []
        for c in candidates:
            source_term = str(c.get("source_term", "") or "")
            if source_term.strip():
                pairs.append((query, source_term))
                valid_candidates.append(c)

        if not pairs:
            return candidates[:top_n] if candidates else []

        try:
            scores = self._model.predict(pairs)
        except Exception as exc:
            logger.warning("CrossEncoder prediction failed: %s", exc)
            return self._fallback_sort(candidates, top_n)

        for idx, c in enumerate(valid_candidates):
            c["rerank_score"] = float(scores[idx]) if idx < len(scores) else 0.0

        valid_candidates.sort(key=lambda c: c.get("rerank_score", 0.0), reverse=True)
        return valid_candidates[:top_n]

    def is_available(self) -> bool:
        """CrossEncoder 模型是否已成功加载"""
        return self._model is not None

    # ── 内部辅助方法 ─────────────────────────────────────────────────

    @staticmethod
    def _fallback_sort(candidates: list[dict], top_n: int) -> list[dict]:
        """回退策略：按最佳可用评分排序候选项"""
        for c in candidates:
            c.setdefault("rerank_score", 0.0)

        def _best_score(c: dict) -> float:
            return max(
                float(c.get("rerank_score", 0.0) or 0.0),
                float(c.get("bm25_score", 0.0) or 0.0),
                float(c.get("vector_score", 0.0) or 0.0),
            )

        candidates.sort(key=_best_score, reverse=True)
        return candidates[:top_n]
