"""
Deterministic token/safe-limit estimators for oversize downgrade gating.

V1 policy is intentionally conservative for anti-truncation protection and
replay determinism. It is not intended to be tokenizer-equivalent.
"""

from __future__ import annotations

from hashlib import sha256
from math import ceil, floor

TOKEN_ESTIMATOR_ID_V1 = "estimate_tokens_v1"
SAFE_LIMIT_ID_V1 = "safe_limit_v1"

# Keep formulas as explicit strings so digest/versioning is stable and replayable.
TOKEN_ESTIMATOR_FORMULA_V1 = "ceil(len(utf8_bytes)/3)"
SAFE_LIMIT_FORMULA_V1 = "max(1, floor(model_context_tokens*0.7)-prompt_reserve_tokens)"


def _formula_digest(formula: str) -> str:
    return sha256(formula.encode("utf-8")).hexdigest()


TOKEN_ESTIMATOR_DIGEST_V1 = _formula_digest(
    f"{TOKEN_ESTIMATOR_ID_V1}:{TOKEN_ESTIMATOR_FORMULA_V1}"
)
SAFE_LIMIT_DIGEST_V1 = _formula_digest(f"{SAFE_LIMIT_ID_V1}:{SAFE_LIMIT_FORMULA_V1}")


def estimate_tokens_v1(text: str) -> int:
    """Conservative deterministic token estimate."""
    if not text:
        return 0
    return int(ceil(len(text.encode("utf-8")) / 3.0))


def safe_limit_v1(model_context_tokens: int, prompt_reserve_tokens: int) -> int:
    """
    Deterministic safe input limit for oversize downgrade gate.

    The 0.7 factor intentionally leaves substantial budget for system/user
    prompts and response headroom.
    """
    ctx = max(int(model_context_tokens or 0), 0)
    reserve = max(int(prompt_reserve_tokens or 0), 0)
    return max(1, int(floor(ctx * 0.7) - reserve))

