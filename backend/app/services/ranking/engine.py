"""Pure ranking algorithm functions (no I/O, no side effects).

Implements the hot ranking model from the design doc:
  evidence_score = 0.45 * attention + 0.30 * authority + 0.15 * implementation + 0.10 * local
  hot_score = evidence_score * time_decay
  time_decay = 0.5 ^ (age_days / half_life_days)
"""

import math
from datetime import datetime, timezone, timedelta

from .schemas import RankedCandidate, ScoreBreakdown, SourceEvidence

# ── Scoring constants ──────────────────────────────────────────────

SCORE_WEIGHTS = {
    "attention": 0.45,
    "authority": 0.30,
    "implementation": 0.15,
    "local": 0.10,
}

WINDOW_HALF_LIVES: dict[str, float] = {
    "3d": 1.5,
    "7d": 3.0,
    "30d": 10.0,
    "90d": 30.0,
    "all": 180.0,
}

ALL_TIME_DECAY_FLOOR = 0.15
IMPLEMENTATION_SCORE_CAP = 100.0  # cap before weighting
LOG_SCALE_BASE = 10.0

# Window day ranges (max age in days for eligibility)
WINDOW_DAYS: dict[str, int] = {
    "3d": 3,
    "7d": 7,
    "30d": 30,
    "90d": 90,
}

COMPONENT_KEYS = ("attention", "authority", "implementation", "local")


# ── Math helpers ────────────────────────────────────────────────────


def compute_age_days(publication_date_str: str | None, now: datetime | None = None) -> float:
    """Calculate age in days from publication date to reference time.

    Returns 0.0 if publication_date_str is None or unparseable.
    """
    if not publication_date_str:
        return 0.0

    ref = now or datetime.now(timezone.utc)
    # Handle various ISO-ish formats
    normalized = publication_date_str.replace("Z", "+00:00")
    try:
        pub_dt = datetime.fromisoformat(normalized)
    except ValueError:
        return 0.0

    # Ensure pub_dt is offset-aware; if naive, assume UTC
    if pub_dt.tzinfo is None:
        pub_dt = pub_dt.replace(tzinfo=timezone.utc)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)

    delta = ref - pub_dt
    return max(0.0, delta.total_seconds() / 86400.0)


def compute_time_decay(age_days: float, half_life_days: float, window: str = "30d") -> float:
    """time_decay = 0.5 ^ (age_days / half_life_days).

    For 'all' window, applies ALL_TIME_DECAY_FLOOR as minimum.
    """
    if half_life_days <= 0:
        return 1.0
    decay = 0.5 ** (age_days / half_life_days)
    if window == "all":
        decay = max(decay, ALL_TIME_DECAY_FLOOR)
    return decay


def log_scale(value: float, cap: float | None = None) -> float:
    """Log-scaled value using math.log1p.  Caps raw value before scaling if cap is set."""
    raw = value
    if cap is not None and raw > cap:
        raw = cap
    if raw < 0:
        raw = 0.0
    return math.log1p(raw)


def min_max_normalize(value: float, min_val: float, max_val: float) -> float:
    """Normalize to 0..100 range."""
    if max_val <= min_val:
        return 0.0
    clamped = max(min_val, min(value, max_val))
    return ((clamped - min_val) / (max_val - min_val)) * 100.0


def normalize_component_scores(
    raw_components: list[dict[str, float]],
    component_maxes: dict[str, float] | None = None,
) -> list[ScoreBreakdown]:
    """Given raw component dicts and per-component max values, return normalized 0..100 scores.

    Each element in raw_components should be a dict with keys matching COMPONENT_KEYS.
    For each component:
      1. Log-scale all values across the batch
      2. Cap implementation at IMPLEMENTATION_SCORE_CAP
      3. Find min/max of log-scaled values across the batch
      4. Min-max normalize each value to 0..100

    If component_maxes is not provided, uses the max raw value from the batch.
    """
    if not raw_components:
        return []

    # Collect raw values per component
    comp_raws: dict[str, list[float]] = {key: [] for key in COMPONENT_KEYS}
    for comp in raw_components:
        for key in COMPONENT_KEYS:
            comp_raws[key].append(comp.get(key, 0.0))

    # Log-scale all raw values (with implementation cap)
    comp_logged: dict[str, list[float]] = {key: [] for key in COMPONENT_KEYS}
    for key in COMPONENT_KEYS:
        cap = IMPLEMENTATION_SCORE_CAP if key == "implementation" else None
        for raw_val in comp_raws[key]:
            capped = min(raw_val, cap) if cap is not None else raw_val
            comp_logged[key].append(log_scale(max(0.0, capped)))

    # Compute min/max per component from log-scaled values
    comp_min: dict[str, float] = {}
    comp_max: dict[str, float] = {}
    for key in COMPONENT_KEYS:
        logged_vals = comp_logged[key]
        comp_min[key] = min(logged_vals) if logged_vals else 0.0
        comp_max[key] = max(logged_vals) if logged_vals else 0.0
        # If all values are the same, avoid division by zero but still give meaningful output
        if comp_max[key] <= comp_min[key]:
            comp_max[key] = comp_min[key] + 1.0

    # Build ScoreBreakdown list
    result: list[ScoreBreakdown] = []
    for i, _comp in enumerate(raw_components):
        breakdown = ScoreBreakdown(
            attention=min_max_normalize(comp_logged["attention"][i], comp_min["attention"], comp_max["attention"]),
            authority=min_max_normalize(comp_logged["authority"][i], comp_min["authority"], comp_max["authority"]),
            implementation=min_max_normalize(comp_logged["implementation"][i], comp_min["implementation"], comp_max["implementation"]),
            local=min_max_normalize(comp_logged["local"][i], comp_min["local"], comp_max["local"]),
        )
        result.append(breakdown)

    return result


def compute_evidence_score(breakdown: ScoreBreakdown) -> float:
    """0.45 * attention + 0.30 * authority + 0.15 * implementation + 0.10 * local"""
    return (
        SCORE_WEIGHTS["attention"] * breakdown.attention
        + SCORE_WEIGHTS["authority"] * breakdown.authority
        + SCORE_WEIGHTS["implementation"] * breakdown.implementation
        + SCORE_WEIGHTS["local"] * breakdown.local
    )


def compute_hot_score(evidence_score: float, time_decay: float) -> float:
    """evidence_score * time_decay"""
    return evidence_score * time_decay


def is_in_window(publication_date_str: str | None, window: str = "30d", now: datetime | None = None) -> bool:
    """Check if publication_date falls within the window's day range.

    'all' window always returns True.
    """
    if window == "all":
        return True

    max_days = WINDOW_DAYS.get(window)
    if max_days is None:
        return True  # unknown window → include

    age = compute_age_days(publication_date_str, now=now)
    return age <= max_days


def generate_selected_reason(
    breakdown: ScoreBreakdown,
    source_evidence: list | None = None,
) -> str:
    """Generate a human-readable reason string based on which components dominate."""
    max_component = max(
        ("attention", breakdown.attention),
        ("authority", breakdown.authority),
        ("implementation", breakdown.implementation),
        ("local", breakdown.local),
        key=lambda item: item[1],
    )

    reasons = {
        "attention": "Strong external platform attention signals.",
        "authority": "High scholarly impact and citation authority.",
        "implementation": "Strong code and implementation evidence available.",
        "local": "High local community engagement and readiness.",
    }

    return reasons.get(max_component[0], "Ranked by multi-source hot score.")


def rank_candidates(
    raw_candidates: list[dict],
    window: str = "30d",
    now: datetime | None = None,
) -> list[RankedCandidate]:
    """Full ranking pipeline.

    Args:
        raw_candidates: List of dicts, each with at minimum:
            - arxiv_id (str)
            - publication_date (str | None)
          And optionally:
            - title, authors, categories
            - source_evidence (list of dicts with SourceEvidence shape)
            - raw_attention, raw_authority, raw_implementation, raw_local (float)
        window: Time window key ("3d", "7d", "30d", "90d", "all")
        now: Reference datetime for age/decay calculations.

    Returns:
        list[RankedCandidate] sorted by rank (descending hot_score).
    """
    ref_now = now or datetime.now(timezone.utc)
    half_life = WINDOW_HALF_LIVES.get(window, 10.0)

    # 1. Filter by publication date window
    in_window: list[dict] = []
    for cand in raw_candidates:
        pub_date = cand.get("publication_date")
        if is_in_window(pub_date, window=window, now=ref_now):
            in_window.append(cand)

    if not in_window:
        return []

    # 2. Extract raw component scores
    raw_comps: list[dict[str, float]] = []
    for cand in in_window:
        raw_comps.append({
            "attention": cand.get("raw_attention", 0.0),
            "authority": cand.get("raw_authority", 0.0),
            "implementation": cand.get("raw_implementation", 0.0),
            "local": cand.get("raw_local", 0.0),
        })

    # 3. Normalize component scores (log-scale, cap, min-max across batch)
    breakdowns = normalize_component_scores(raw_comps)

    # 4-6. Build RankedCandidate list with scores
    ranked: list[RankedCandidate] = []
    for i, cand in enumerate(in_window):
        breakdown = breakdowns[i]

        age_days = compute_age_days(cand.get("publication_date"), now=ref_now)
        time_decay = compute_time_decay(age_days, half_life, window=window)
        evidence_score = compute_evidence_score(breakdown)
        hot_score = compute_hot_score(evidence_score, time_decay)

        # Build source_evidence list
        se_raw = cand.get("source_evidence", [])
        source_evidence: list = []
        if se_raw:
            source_evidence = se_raw  # Pass through as-is (could be dicts or SourceEvidence)

        selected_reason = generate_selected_reason(breakdown, source_evidence)

        candidate = RankedCandidate(
            arxiv_id=cand["arxiv_id"],
            window=window,
            hot_score=round(hot_score, 4),
            evidence_score=round(evidence_score, 4),
            age_days=round(age_days, 2),
            half_life_days=half_life,
            time_decay=round(time_decay, 6),
            score_breakdown=breakdown,
            source_evidence=source_evidence,
            title=cand.get("title"),
            authors=cand.get("authors", []),
            categories=cand.get("categories", []),
            publication_date=cand.get("publication_date"),
            selected_reason=selected_reason,
            exclusion_reasons=cand.get("exclusion_reasons", []),
            rank=0,
        )
        ranked.append(candidate)

    # 6. Sort desc by hot_score, assign ranks
    ranked.sort(key=lambda c: -c.hot_score)
    for idx, cand in enumerate(ranked, start=1):
        cand.rank = idx

    return ranked
