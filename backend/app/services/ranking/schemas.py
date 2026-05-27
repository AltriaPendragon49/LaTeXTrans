"""Dataclasses for the hot ranking system."""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class SourceEvidence:
    source: str  # "arXiv", "OpenAlex", "SemanticScholar", "HuggingFace", "alphaXiv", "GitHub", "local"
    signal: str  # "metadata", "citations", "influential_citations", "stars", "forks", "views", "likes", "saves"
    raw_value: Optional[float] = None
    normalized_value: Optional[float] = None
    fetched_at: str = ""


@dataclass
class ScoreBreakdown:
    attention: float = 0.0  # 0..100
    authority: float = 0.0  # 0..100
    implementation: float = 0.0  # 0..100
    local: float = 0.0  # 0..100


@dataclass
class RankedCandidate:
    arxiv_id: str
    window: str = "30d"
    hot_score: float = 0.0
    evidence_score: float = 0.0
    age_days: float = 0.0
    half_life_days: float = 10.0
    time_decay: float = 1.0
    score_breakdown: ScoreBreakdown = field(default_factory=ScoreBreakdown)
    source_evidence: list = field(default_factory=list)  # list[SourceEvidence]
    title: Optional[str] = None
    authors: list = field(default_factory=list)
    categories: list = field(default_factory=list)
    publication_date: Optional[str] = None
    selected_reason: str = ""
    exclusion_reasons: list = field(default_factory=list)
    rank: int = 0


@dataclass
class DailyIntakeSummary:
    date: str = ""  # "YYYY-MM-DD"
    window: str = "30d"
    triggered_at: str = ""  # ISO timestamp
    total_candidates: int = 0
    existing_count: int = 0
    below_threshold_count: int = 0
    intaken_count: int = 0
    intaken_papers: list = field(default_factory=list)  # list[dict]
    skipped_papers: list = field(default_factory=list)  # list[dict]
    quality_gate_failures_from_prior_runs: list = field(default_factory=list)


@dataclass
class RankResult:
    window: str = "30d"
    candidates: list = field(default_factory=list)  # list[RankedCandidate]
    exported_at: str = ""
    total_count: int = 0
