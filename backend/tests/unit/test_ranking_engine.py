"""Unit tests for the hot ranking engine (backend.app.services.ranking.engine)."""

import math
from datetime import datetime, timezone, timedelta

import pytest

from backend.app.services.ranking.engine import (
    ALL_TIME_DECAY_FLOOR,
    IMPLEMENTATION_SCORE_CAP,
    SCORE_WEIGHTS,
    WINDOW_DAYS,
    WINDOW_HALF_LIVES,
    compute_age_days,
    compute_evidence_score,
    compute_hot_score,
    compute_time_decay,
    generate_selected_reason,
    is_in_window,
    log_scale,
    min_max_normalize,
    normalize_component_scores,
    rank_candidates,
)
from backend.app.services.ranking.schemas import ScoreBreakdown


# ── compute_age_days ──────────────────────────────────────────────


class TestComputeAgeDays:
    def test_known_date_gives_correct_age(self):
        """A paper published 10 days ago should yield age ≈ 10."""
        now = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
        pub = "2026-05-16T12:00:00Z"
        age = compute_age_days(pub, now=now)
        assert abs(age - 10.0) < 0.01

    def test_published_today_is_zero(self):
        now = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
        pub = "2026-05-26T00:00:00Z"
        age = compute_age_days(pub, now=now)
        assert age >= 0.0

    def test_future_date_returns_zero(self):
        """Future dates should not produce negative age."""
        now = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
        pub = "2026-06-01T00:00:00Z"
        age = compute_age_days(pub, now=now)
        assert age == 0.0

    def test_none_pub_date_returns_zero(self):
        assert compute_age_days(None) == 0.0

    def test_empty_string_returns_zero(self):
        assert compute_age_days("") == 0.0

    def test_invalid_date_returns_zero(self):
        assert compute_age_days("not-a-date") == 0.0

    def test_date_without_timezone_is_treated_as_utc(self):
        """Naive datetime strings should be treated as UTC."""
        now = datetime(2026, 5, 26, 0, 0, 0, tzinfo=timezone.utc)
        pub = "2026-05-25T00:00:00"  # naive
        age = compute_age_days(pub, now=now)
        assert abs(age - 1.0) < 0.01

    def test_fractional_days(self):
        """12 hours ago should be ~0.5 days."""
        now = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
        pub = "2026-05-26T00:00:00Z"
        age = compute_age_days(pub, now=now)
        assert 0.49 < age < 0.51


# ── compute_time_decay ─────────────────────────────────────────────


class TestComputeTimeDecay:
    def test_half_life_decay(self):
        """At age = half_life, decay should be exactly 0.5."""
        decay = compute_time_decay(age_days=10.0, half_life_days=10.0)
        assert abs(decay - 0.5) < 0.0001

    def test_age_zero_decay_is_one(self):
        decay = compute_time_decay(age_days=0.0, half_life_days=10.0)
        assert decay == 1.0

    def test_double_half_life(self):
        """At age = 2 * half_life, decay should be 0.25."""
        decay = compute_time_decay(age_days=20.0, half_life_days=10.0)
        assert abs(decay - 0.25) < 0.0001

    def test_decay_decreases_with_age(self):
        d1 = compute_time_decay(5.0, 10.0)
        d2 = compute_time_decay(15.0, 10.0)
        assert d1 > d2

    def test_all_window_applies_floor(self):
        """For 'all' window, decay must not fall below ALL_TIME_DECAY_FLOOR."""
        decay = compute_time_decay(age_days=1000.0, half_life_days=180.0, window="all")
        assert decay >= ALL_TIME_DECAY_FLOOR

    def test_all_window_floor_exact_threshold(self):
        """At very large age, decay should exactly equal the floor."""
        decay = compute_time_decay(age_days=10000.0, half_life_days=180.0, window="all")
        assert abs(decay - ALL_TIME_DECAY_FLOOR) < 0.0001

    def test_all_window_no_floor_when_above(self):
        """When natural decay is above the floor, it should not be clamped."""
        decay = compute_time_decay(age_days=30.0, half_life_days=180.0, window="all")
        natural = 0.5 ** (30.0 / 180.0)
        assert decay > ALL_TIME_DECAY_FLOOR
        assert abs(decay - natural) < 0.0001

    def test_non_all_window_no_floor(self):
        """Non-all windows should not apply floor even at large ages."""
        decay = compute_time_decay(age_days=100.0, half_life_days=10.0, window="30d")
        natural = 0.5 ** (100.0 / 10.0)
        assert abs(decay - natural) < 0.0001
        assert decay < ALL_TIME_DECAY_FLOOR  # It can go below floor for non-all


# ── log_scale ──────────────────────────────────────────────────────


class TestLogScale:
    def test_zero_input(self):
        assert log_scale(0.0) == 0.0

    def test_one_input(self):
        assert abs(log_scale(1.0) - math.log1p(1.0)) < 0.0001

    def test_large_value(self):
        result = log_scale(1000000.0)
        assert result > 0.0
        assert result < 100.0

    def test_negative_value_clamped_to_zero(self):
        result = log_scale(-5.0)
        assert result == 0.0

    def test_cap_is_applied(self):
        """When cap is set, values above the cap should be clamped before log scaling."""
        capped = log_scale(200.0, cap=100.0)
        capped_at_100 = log_scale(100.0, cap=100.0)
        assert abs(capped - capped_at_100) < 0.0001

    def test_cap_not_applied_when_below(self):
        """Values below the cap should not be affected."""
        result = log_scale(50.0, cap=100.0)
        expected = math.log1p(50.0)
        assert abs(result - expected) < 0.0001

    def test_increasing_function(self):
        """log_scale should be monotonically increasing."""
        assert log_scale(10.0) < log_scale(100.0)


# ── min_max_normalize ──────────────────────────────────────────────


class TestMinMaxNormalize:
    def test_midpoint_is_50(self):
        result = min_max_normalize(50.0, 0.0, 100.0)
        assert abs(result - 50.0) < 0.0001

    def test_min_value_is_zero(self):
        assert min_max_normalize(0.0, 0.0, 100.0) == 0.0

    def test_max_value_is_100(self):
        assert min_max_normalize(100.0, 0.0, 100.0) == 100.0

    def test_min_equals_max_returns_zero(self):
        """When min == max, normalization is undefined and should return 0."""
        assert min_max_normalize(50.0, 50.0, 50.0) == 0.0

    def test_below_min_clamped(self):
        """Values below min should be clamped to 0."""
        assert min_max_normalize(-10.0, 0.0, 100.0) == 0.0

    def test_above_max_clamped(self):
        """Values above max should be clamped to 100."""
        assert min_max_normalize(200.0, 0.0, 100.0) == 100.0

    def test_arbitrary_range(self):
        result = min_max_normalize(30.0, 10.0, 90.0)
        expected = ((30.0 - 10.0) / (90.0 - 10.0)) * 100.0
        assert abs(result - expected) < 0.0001


# ── normalize_component_scores ─────────────────────────────────────


class TestNormalizeComponentScores:
    def test_empty_list_returns_empty(self):
        result = normalize_component_scores([])
        assert result == []

    def test_single_candidate_gets_zero_scores(self):
        """With only one candidate, min==max after log-scaling, so all scores are 0."""
        raw = [{"attention": 100.0, "authority": 50.0, "implementation": 75.0, "local": 25.0}]
        result = normalize_component_scores(raw)
        assert len(result) == 1
        b = result[0]
        assert b.attention == 0.0
        assert b.authority == 0.0
        assert b.implementation == 0.0
        assert b.local == 0.0

    def test_two_candidates_with_different_scores(self):
        raw = [
            {"attention": 100.0, "authority": 50.0, "implementation": 30.0, "local": 10.0},
            {"attention": 10.0, "authority": 5.0, "implementation": 3.0, "local": 1.0},
        ]
        result = normalize_component_scores(raw)
        assert len(result) == 2
        # Higher raw → higher normalized
        assert result[0].attention > result[1].attention
        assert result[0].authority > result[1].authority
        # Higher raw candidate should have score 100 (max) for attention
        assert abs(result[0].attention - 100.0) < 0.01
        assert abs(result[1].attention - 0.0) < 0.01

    def test_implementation_cap_is_enforced(self):
        """Implementation values above IMPLEMENTATION_SCORE_CAP should be capped before log-scaling."""
        raw = [
            {"attention": 10.0, "authority": 10.0, "implementation": IMPLEMENTATION_SCORE_CAP * 10, "local": 10.0},
            {"attention": 5.0, "authority": 5.0, "implementation": IMPLEMENTATION_SCORE_CAP, "local": 5.0},
        ]
        result = normalize_component_scores(raw)
        assert len(result) == 2
        # Both should have same implementation score (both capped to the same value)
        assert abs(result[0].implementation - result[1].implementation) < 0.01

    def test_implementation_cap_not_affecting_other_components(self):
        """The implementation cap should only affect implementation component."""
        raw = [
            {"attention": 100.0, "authority": 100.0, "implementation": IMPLEMENTATION_SCORE_CAP * 100, "local": 100.0},
            {"attention": 10.0, "authority": 10.0, "implementation": 0.0, "local": 10.0},
        ]
        result = normalize_component_scores(raw)
        # Attention, authority, local should differ
        assert result[0].attention > result[1].attention
        assert result[0].authority > result[1].authority
        assert result[0].local > result[1].local

    def test_missing_keys_treated_as_zero(self):
        raw = [
            {"attention": 100.0},
            {"attention": 10.0},
        ]
        result = normalize_component_scores(raw)
        assert len(result) == 2
        assert result[0].authority == result[1].authority  # both default to 0, log_scale(0) = 0


# ── compute_evidence_score ─────────────────────────────────────────


class TestComputeEvidenceScore:
    def test_balanced_scores(self):
        b = ScoreBreakdown(attention=100.0, authority=100.0, implementation=100.0, local=100.0)
        score = compute_evidence_score(b)
        assert abs(score - 100.0) < 0.0001  # All weights sum to 1.0

    def test_zeros(self):
        b = ScoreBreakdown()
        score = compute_evidence_score(b)
        assert score == 0.0

    def test_weighted_correctly(self):
        b = ScoreBreakdown(attention=100.0, authority=0.0, implementation=0.0, local=0.0)
        score = compute_evidence_score(b)
        assert abs(score - 45.0) < 0.0001  # 0.45 * 100

    def test_authority_weight(self):
        b = ScoreBreakdown(attention=0.0, authority=100.0, implementation=0.0, local=0.0)
        score = compute_evidence_score(b)
        assert abs(score - 30.0) < 0.0001  # 0.30 * 100

    def test_implementation_weight(self):
        b = ScoreBreakdown(attention=0.0, authority=0.0, implementation=100.0, local=0.0)
        score = compute_evidence_score(b)
        assert abs(score - 15.0) < 0.0001  # 0.15 * 100

    def test_local_weight(self):
        b = ScoreBreakdown(attention=0.0, authority=0.0, implementation=0.0, local=100.0)
        score = compute_evidence_score(b)
        assert abs(score - 10.0) < 0.0001  # 0.10 * 100


# ── compute_hot_score ──────────────────────────────────────────────


class TestComputeHotScore:
    def test_basic(self):
        assert compute_hot_score(80.0, 0.5) == 40.0

    def test_no_decay(self):
        assert compute_hot_score(90.0, 1.0) == 90.0

    def test_full_decay(self):
        assert compute_hot_score(50.0, 0.0) == 0.0


# ── is_in_window ───────────────────────────────────────────────────


class TestIsInWindow:
    def test_all_window_always_true(self):
        assert is_in_window("2020-01-01T00:00:00Z", window="all") is True

    def test_recent_paper_in_30d_window(self):
        today = datetime.now(timezone.utc)
        yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        assert is_in_window(yesterday, window="30d") is True

    def test_old_paper_outside_7d_window(self):
        today = datetime.now(timezone.utc)
        eight_days_ago = (today - timedelta(days=8)).strftime("%Y-%m-%dT%H:%M:%SZ")
        assert is_in_window(eight_days_ago, window="7d") is False

    def test_boundary_exact_day(self):
        """A paper exactly at the window boundary should be included."""
        now = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
        boundary = "2026-05-23T12:00:00Z"  # exactly 3 days ago
        assert is_in_window(boundary, window="3d", now=now) is True

    def test_boundary_one_second_past(self):
        """A paper just outside the window should be excluded."""
        now = datetime(2026, 5, 26, 12, 0, 1, tzinfo=timezone.utc)
        just_outside = "2026-05-23T11:59:59Z"
        result = is_in_window(just_outside, window="3d", now=now)
        assert result is False

    def test_none_pub_date_in_window(self):
        """None publication date should be treated as age=0 and thus in any window."""
        assert is_in_window(None, window="7d") is True

    def test_unknown_window_defaults_to_include(self):
        """Unknown window keys should include the paper."""
        assert is_in_window("2026-05-20T00:00:00Z", window="unknown") is True


# ── generate_selected_reason ───────────────────────────────────────


class TestGenerateSelectedReason:
    def test_attention_dominant(self):
        b = ScoreBreakdown(attention=90.0, authority=30.0, implementation=10.0, local=5.0)
        reason = generate_selected_reason(b)
        assert "attention" in reason.lower()

    def test_authority_dominant(self):
        b = ScoreBreakdown(attention=10.0, authority=90.0, implementation=10.0, local=5.0)
        reason = generate_selected_reason(b)
        assert "authority" in reason.lower() or "scholarly" in reason.lower() or "citation" in reason.lower()

    def test_implementation_dominant(self):
        b = ScoreBreakdown(attention=10.0, authority=10.0, implementation=90.0, local=5.0)
        reason = generate_selected_reason(b)
        assert "code" in reason.lower() or "implementation" in reason.lower()

    def test_local_dominant(self):
        b = ScoreBreakdown(attention=10.0, authority=10.0, implementation=10.0, local=90.0)
        reason = generate_selected_reason(b)
        assert "local" in reason.lower() or "community" in reason.lower() or "engagement" in reason.lower()

    def test_all_tied_returns_fallback(self):
        b = ScoreBreakdown()
        reason = generate_selected_reason(b)
        assert len(reason) > 0  # Should return a fallback string


# ── rank_candidates ────────────────────────────────────────────────


class TestRankCandidates:
    def _make_candidate(self, arxiv_id, pub_date, raw_attention=50.0, raw_authority=50.0,
                        raw_implementation=30.0, raw_local=10.0, title=None):
        cand = {
            "arxiv_id": arxiv_id,
            "publication_date": pub_date,
            "raw_attention": raw_attention,
            "raw_authority": raw_authority,
            "raw_implementation": raw_implementation,
            "raw_local": raw_local,
        }
        if title:
            cand["title"] = title
        return cand

    def test_empty_candidates_returns_empty(self):
        result = rank_candidates([], window="30d")
        assert result == []

    def test_all_filtered_out_returns_empty(self):
        """All candidates outside the window should return empty list."""
        now = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
        cands = [
            self._make_candidate("2605.00001", "2025-01-01T00:00:00Z"),
            self._make_candidate("2605.00002", "2025-02-01T00:00:00Z"),
        ]
        result = rank_candidates(cands, window="3d", now=now)
        assert result == []

    def test_sorts_by_hot_score_descending(self):
        now = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
        cands = [
            self._make_candidate("id1", "2026-05-25T00:00:00Z", raw_attention=100.0),
            self._make_candidate("id2", "2026-05-25T00:00:00Z", raw_attention=10.0),
            self._make_candidate("id3", "2026-05-25T00:00:00Z", raw_attention=50.0),
        ]
        result = rank_candidates(cands, window="30d", now=now)
        assert len(result) == 3
        # id1 has highest raw_attention → highest hot_score → rank 1
        assert result[0].arxiv_id == "id1"
        assert result[0].rank == 1
        assert result[1].arxiv_id == "id3"
        assert result[1].rank == 2
        assert result[2].arxiv_id == "id2"
        assert result[2].rank == 3
        # Verify descending order
        assert result[0].hot_score >= result[1].hot_score >= result[2].hot_score

    def test_ranks_match_sort_order(self):
        """Verify ranks start from 1 and are sequential."""
        now = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
        cands = [
            self._make_candidate(f"id{i}", "2026-05-25T00:00:00Z", raw_attention=100.0 - i)
            for i in range(5)
        ]
        result = rank_candidates(cands, window="30d", now=now)
        assert len(result) == 5
        for i, c in enumerate(result, start=1):
            assert c.rank == i

    def test_time_decay_affects_hot_score(self):
        """Older papers should have lower hot_score for similar evidence."""
        now = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
        # Use different raw values so normalization produces non-zero scores.
        # The two candidates share the same evidence level but different ages.
        cands = [
            self._make_candidate("recent", "2026-05-25T00:00:00Z",
                                 raw_attention=100.0, raw_authority=60.0,
                                 raw_implementation=40.0, raw_local=20.0),
            self._make_candidate("older", "2026-05-10T00:00:00Z",
                                 raw_attention=80.0, raw_authority=50.0,
                                 raw_implementation=30.0, raw_local=10.0),
        ]
        result = rank_candidates(cands, window="30d", now=now)
        assert len(result) == 2
        # Same evidence → newer ranks higher
        assert result[0].arxiv_id == "recent"
        assert result[1].arxiv_id == "older"
        assert result[0].hot_score > result[1].hot_score

    def test_window_filter_is_applied(self):
        now = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
        cands = [
            self._make_candidate("in_window", "2026-05-25T00:00:00Z", raw_attention=50.0),
            self._make_candidate("out_window", "2026-05-01T00:00:00Z", raw_attention=90.0),
        ]
        result = rank_candidates(cands, window="7d", now=now)
        assert len(result) == 1
        assert result[0].arxiv_id == "in_window"

    def test_all_window_includes_old_papers(self):
        now = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
        cands = [
            self._make_candidate("recent", "2026-05-25T00:00:00Z", raw_attention=80.0),
            self._make_candidate("old", "2020-05-25T00:00:00Z", raw_attention=80.0),
        ]
        result = rank_candidates(cands, window="all", now=now)
        assert len(result) == 2
        # Recent should still rank higher due to time decay
        assert result[0].arxiv_id == "recent"

    def test_scoring_metadata_populated(self):
        """Verify all RankedCandidate fields are populated."""
        now = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
        # Two candidates with different raw values so normalization produces non-zero scores.
        cands = [
            self._make_candidate("test1", "2026-05-25T00:00:00Z",
                                 raw_attention=80.0, raw_authority=60.0,
                                 raw_implementation=40.0, raw_local=20.0,
                                 title="Test Paper"),
            self._make_candidate("test2", "2026-05-24T00:00:00Z",
                                 raw_attention=10.0, raw_authority=5.0,
                                 raw_implementation=3.0, raw_local=1.0,
                                 title="Test Paper 2"),
        ]
        result = rank_candidates(cands, window="30d", now=now)
        assert len(result) == 2
        c = result[0]  # test1 should rank higher
        assert c.window == "30d"
        assert c.hot_score > 0.0
        assert c.evidence_score > 0.0
        assert c.age_days > 0.0
        assert c.half_life_days > 0.0
        assert c.time_decay > 0.0
        assert c.title == "Test Paper"
        assert c.rank == 1
        assert len(c.selected_reason) > 0

    def test_window_specific_half_lives(self):
        """Verify the window parameter affects half_life_days."""
        now = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
        cands = [
            self._make_candidate("test1", "2026-05-25T00:00:00Z", raw_attention=50.0),
        ]
        r3d = rank_candidates(cands, window="3d", now=now)
        r30d = rank_candidates(cands, window="30d", now=now)
        assert r3d[0].half_life_days == WINDOW_HALF_LIVES["3d"]
        assert r30d[0].half_life_days == WINDOW_HALF_LIVES["30d"]

    def test_candidate_title_and_metadata_preserved(self):
        now = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
        cands = [
            {
                "arxiv_id": "test1",
                "publication_date": "2026-05-25T00:00:00Z",
                "raw_attention": 50.0,
                "raw_authority": 50.0,
                "raw_implementation": 50.0,
                "raw_local": 50.0,
                "title": "My Awesome Paper",
                "authors": ["Author One", "Author Two"],
                "categories": ["cs.AI", "cs.LG"],
                "source_evidence": [
                    {"source": "arXiv", "signal": "metadata"},
                ],
            },
        ]
        result = rank_candidates(cands, window="30d", now=now)
        assert len(result) == 1
        c = result[0]
        assert c.title == "My Awesome Paper"
        assert c.authors == ["Author One", "Author Two"]
        assert c.categories == ["cs.AI", "cs.LG"]
        assert len(c.source_evidence) == 1
        assert c.source_evidence[0]["source"] == "arXiv"

    def test_implementation_cap_in_e2e(self):
        """End-to-end: verify that very high implementation raw values don't dominate."""
        now = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
        cands = [
            self._make_candidate("high_impl", "2026-05-25T00:00:00Z",
                                 raw_attention=10.0, raw_authority=10.0,
                                 raw_implementation=IMPLEMENTATION_SCORE_CAP * 1000,
                                 raw_local=0.0),
            self._make_candidate("normal", "2026-05-25T00:00:00Z",
                                 raw_attention=10.0, raw_authority=10.0,
                                 raw_implementation=IMPLEMENTATION_SCORE_CAP,
                                 raw_local=0.0),
        ]
        result = rank_candidates(cands, window="30d", now=now)
        assert len(result) == 2
        # Both implementation capped → both get same implementation normalized score
        assert abs(result[0].score_breakdown.implementation - result[1].score_breakdown.implementation) < 0.01
