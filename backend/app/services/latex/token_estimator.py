"""
确定性 Token/安全限制估算器，用于超大块降级门控。

V1 策略为反截断保护和重放确定性有意保持保守，
并不旨在与分词器等效。
"""

from __future__ import annotations

from hashlib import sha256
from math import ceil, floor

TOKEN_ESTIMATOR_ID_V1 = "estimate_tokens_v1"
SAFE_LIMIT_ID_V1 = "safe_limit_v1"

# 将公式保存为显式字符串，以便摘要/版本号保持稳定且可重放。
TOKEN_ESTIMATOR_FORMULA_V1 = "ceil(len(utf8_bytes)/3)"
SAFE_LIMIT_FORMULA_V1 = "max(1, floor(model_context_tokens*0.7)-prompt_reserve_tokens)"


def _formula_digest(formula: str) -> str:
    """计算公式字符串的 SHA-256 摘要。"""
    return sha256(formula.encode("utf-8")).hexdigest()


TOKEN_ESTIMATOR_DIGEST_V1 = _formula_digest(
    f"{TOKEN_ESTIMATOR_ID_V1}:{TOKEN_ESTIMATOR_FORMULA_V1}"
)
SAFE_LIMIT_DIGEST_V1 = _formula_digest(f"{SAFE_LIMIT_ID_V1}:{SAFE_LIMIT_FORMULA_V1}")


def estimate_tokens_v1(text: str) -> int:
    """保守的确定性 token 数量估算。

    使用 UTF-8 字节数除以 3 并向上取整，作为 token 数量的近似估计。
    """
    if not text:
        return 0
    return int(ceil(len(text.encode("utf-8")) / 3.0))


def safe_limit_v1(model_context_tokens: int, prompt_reserve_tokens: int) -> int:
    """超大块降级门控的确定性安全输入限制。

    0.7 的系数有意为系统/用户提示和响应余量留出充足预算。
    """
    ctx = max(int(model_context_tokens or 0), 0)
    reserve = max(int(prompt_reserve_tokens or 0), 0)
    return max(1, int(floor(ctx * 0.7) - reserve))
