## Context
The current `Hot` homepage tab is backed by internal view-count sorting. That is useful after a paper has already been published on our site, but it does not answer the product question: which recent arXiv papers are objectively worth showing and translating before our own audience has produced enough engagement data?

The previous draft tried to solve this with many sources and many score components. That made the proposal harder to implement and easier to mistake for a copy of another site's ranking. This revision keeps the useful parts: public evidence, source traceability, time-window filters, and decay. It removes unnecessary source families and collapses the model into a small set of explainable signals.

## Goals / Non-Goals
- Goals:
  - Rank arXiv papers with public, auditable evidence instead of only local views.
  - Keep the first-version algorithm simple enough to implement and explain.
  - Support `3 Days`, `7 Days`, `30 Days`, `90 Days`, and `All time` filters.
  - Apply time decay so papers with similar evidence are ordered toward recent activity.
  - Preserve source evidence and score breakdowns for operator review.
  - Feed admin curation or content-pool prewarm without automatically translating every discovered paper.
- Non-Goals:
  - Recreate any external website's hot-ranking formula.
  - Depend on social-media, blog, or forum buzz in the first version.
  - Make OpenReview, Papers-with-Code, Reddit, Hacker News, X/Twitter, or Crossref Event Data required ranking sources.
  - Replace existing admin quality gates.

## Source Policy
Use arXiv as the canonical identity and publication-date source. Every ranked candidate must resolve to an `arxiv_id`, title, authors, categories, publication date, and update date from arXiv metadata.

First-version evidence sources:
- Attention: Hugging Face Papers and alphaXiv when accessible. These sources can show recent platform interest, but neither should be the only reason a paper ranks.
- Authority: OpenAlex and Semantic Scholar. Use citation counts, influential citation counts when available, publication metadata, and topic or field metadata. Citation signals must be age-normalized.
- Implementation: GitHub repository evidence from linked repositories or repository search, including stars, forks, and recent activity. Cap this component to avoid overrepresenting CS and AI papers.
- Local engagement: internal views, likes, saves, translation readiness, and completed translation/read behavior after a paper exists in the community catalog.

Excluded from the first version:
- Reddit, Hacker News, blogs, and social-media mentions because they are noisy and harder to normalize.
- OpenReview because it only covers selected venues and does not work as a general arXiv hotness source.
- Papers-with-Code unless a stable, approved machine interface is available.
- Crossref Event Data because it is not a good new dependency for this workflow.

All non-arXiv sources are fail-soft. Missing optional evidence lowers explainability but must not fail an export when canonical arXiv metadata is present.

## Ranking Model
The model has two stages:

```text
evidence_score =
  0.45 * attention_score
+ 0.30 * authority_score
+ 0.15 * implementation_score
+ 0.10 * local_score

hot_score = evidence_score * time_decay
```

Each component is normalized to `0..100` before weighting. Raw counts should be log-scaled and capped before normalization so a single viral platform or large repository cannot dominate the result.

Component definitions:
- `attention_score`: recent external platform interest from Hugging Face Papers and alphaXiv, using ranks, votes, views, comments, or available trend signals.
- `authority_score`: age-normalized scholarly impact from OpenAlex and Semantic Scholar. For very recent windows this acts as a quality prior, not the main driver.
- `implementation_score`: evidence that the paper has code or reproducible artifacts, mostly from GitHub. This is capped by design.
- `local_score`: our own site engagement and readiness signals. It is small enough that the feed remains externally grounded, but large enough for the homepage to learn from our users.

## Time Windows And Decay
Finite windows filter by canonical arXiv publication date, not by our local publish date. `All time` removes the publication-date eligibility limit but still applies age normalization and decay.

Default homepage window: `30 Days`.

Recommended half-lives:

```text
3 Days   -> 1.5 days
7 Days   -> 3 days
30 Days  -> 10 days
90 Days  -> 30 days
All time -> 180 days, with a minimum decay floor of 0.15
```

Decay formula:

```text
time_decay = 0.5 ^ (age_days / half_life_days)
```

This makes the behavior easy to explain: if two papers have similar evidence, the newer one ranks higher. Older papers can still appear when they have strong authority, implementation, or local engagement, especially in `All time`.

## Artifact Shape
Ranked exports should produce JSON for machines and Markdown for operators.

Recommended paths:
- `backend/arxiv_id/hot_ranked/3d/latest.json`
- `backend/arxiv_id/hot_ranked/7d/latest.json`
- `backend/arxiv_id/hot_ranked/30d/latest.json`
- `backend/arxiv_id/hot_ranked/90d/latest.json`
- `backend/arxiv_id/hot_ranked/all/latest.json`

Each candidate should include:

```json
{
  "arxiv_id": "2501.12345",
  "window": "30d",
  "hot_score": 72.4,
  "evidence_score": 91.2,
  "age_days": 6.2,
  "half_life_days": 10,
  "time_decay": 0.65,
  "score_breakdown": {
    "attention": 81,
    "authority": 52,
    "implementation": 70,
    "local": 15
  },
  "source_evidence": [
    {
      "source": "arXiv",
      "signal": "metadata",
      "fetched_at": "2026-05-25T00:00:00Z"
    }
  ],
  "selected_reason": "Recent arXiv paper with strong external attention and code evidence.",
  "exclusion_reasons": []
}
```

The Markdown artifact should show the top candidates, scores, score components, source coverage, and a short reason so an operator can decide which arXiv IDs to curate.

## Homepage And UI Semantics
The homepage `Hot` tab should request the selected hot window from the backend. The first version should expose:
- A filter icon beside the sort tabs.
- Publication-date choices: `3 Days`, `7 Days`, `30 Days`, `90 Days`, `All time`.
- An active window pill when the selected window differs from the default.
- A desktop popover and mobile bottom sheet.

The UI should not show topic search or extra filters until the backend supports them. Keeping the first version limited to publication-date windows makes the control useful without implying unfinished functionality.

## Data Flow
1. A scheduled or operator-triggered job builds ranked hot artifacts per configured window.
2. arXiv supplies canonical metadata and publication-date eligibility.
3. Optional source adapters enrich candidates with attention, authority, implementation, and local evidence.
4. The ranker normalizes component scores, applies time decay, and writes reasons.
5. Operators review the generated artifacts or admin candidate view.
6. Approved papers enter the existing admin curation or content-pool prewarm flow.
7. Published community papers use the selected window's `hot_score` when available, with the current view-count sort as fallback.

## Risks / Trade-offs
- Hugging Face Papers and alphaXiv are useful attention signals but platform-local; the score must expose source evidence instead of hiding it.
- Citation sources lag behind new papers, so authority is a quality prior for short windows.
- GitHub evidence favors CS/AI papers; capping the implementation component is required.
- Time decay may hide older but still important papers from finite windows; `All time` exists for that use case.
- Missing optional sources reduce evidence coverage, so artifacts must make missing evidence visible.

## Scheduled Auto-Intake (Daily Cron)

### Overview
A periodic Worker-side task refreshes hot rankings once per day, compares the ranked candidates against the existing community catalog, and automatically starts admin-curation translation for new top-ranked papers. Each run produces a daily intake summary (Markdown) for operator review.

### Cron Mechanism
Follow the existing project pattern in `backend/app/main.py`: an `asyncio.create_task` wrapping a `while True` + `asyncio.sleep` loop, identical to how `public_feed_rebuild_task` and `arxiv_metadata_repair_task` work.

```
Worker startup → asyncio.create_task(_hot_ranking_daily_cron())
  └─ while True:
       ├─ 计算距离下一个触发时间的秒数
       ├─ asyncio.sleep(until_next_trigger)
       ├─ 运行排名引擎，写入 latest.json / latest.md
       ├─ 对比 DB 去重，筛选待入库候选
       ├─ 逐篇 import_or_reuse_paper() + submit curation job
       └─ 写入每日入库总结 Markdown
```

### Trigger Time
Default: Beijing time 03:07 daily (using an off-peak hour with jitter to avoid fleet-wide thundering-herd effects). Configurable via `HOT_RANKING_CRON_HOUR` / `HOT_RANKING_CRON_MINUTE` (CST timezone).

### Auto-Intake Flow

1. **Rank**: Run the hot ranking engine for the configured default window (e.g. `30d`), producing ranked JSON + Markdown artifacts.
2. **Filter**: Query DB for all already-translated, already-queued, or already-published arXiv IDs. Exclude them from the candidate pool.
3. **Select**: Take top-N candidates (default 20) by `hot_score` with an optional minimum score threshold (default 50) to avoid auto-intaking low-quality papers.
4. **Intake**: For each selected candidate:
   - Call `import_or_reuse_paper(source="arxiv", arxiv_id=...)` to create or reuse a community paper placeholder
   - Create a curation job with `created_by` set to the admin/system user, source family `hot_ranking`, and the hot score breakdown stored in job metadata
   - Call `_schedule_curation_job(job_id)` to start the async translate → quality-gate → publish pipeline
   - The existing `_run_curation_job` handles translation, compilation, quality gating, and publication — no new translation path needed
5. **Summarize**: Write a daily intake summary Markdown.

### Admin Identity
Auto-intake curation jobs use the designated admin user ID (`HOT_RANKING_SYSTEM_USER_ID` config) as `created_by`. This ensures the intake runs with admin permissions, bypassing user-level daily translation quotas.

### Dedup Protection
- Before intake: check DB for existing papers with the same `arxiv_id` (any `community_status`)
- Before creating a curation job: check for existing `processing`/`translating`/`queued` curation jobs for the same `arxiv_id`
- Within a single cron run: in-memory set tracking already-intaken IDs prevents double-intake if the ranking engine returns duplicates
- Redis lock (`hot_ranking_daily_cron_lock`) with TTL prevents concurrent cron runs across multiple Worker restarts

### Daily Intake Summary Artifact

Path: `backend/arxiv_id/hot_ranked/daily_intake/YYYY-MM-DD.md`

```markdown
# 热榜自动入库总结 — 2026-05-26

- 排名窗口: 30 Days
- 触发时间: 2026-05-26 03:07 CST
- 排名候选总数: 200
- 已存在（跳过）: 178
- 低于阈值（跳过）: 2
- 今日自动入库: 20

## 入库论文

| # | arXiv ID | 标题 | Hot Score | 注意力 | 权威 | 实现 | 本地 | 入库原因 |
|---|----------|------|-----------|--------|------|------|------|----------|
| 1 | 2605.12345 | Title A | 87.3 | 92 | 78 | 55 | 10 | HuggingFace 高关注 + OpenAlex 引用快速增长 |
| 2 | 2605.12346 | Title B | 82.1 | 45 | 95 | 60 | 25 | Semantic Scholar 高影响力 + 站内收藏多 |
| ... | ... | ... | ... | ... | ... | ... | ... | ... |

## 跳过论文

| arXiv ID | 标题 | Hot Score | 跳过原因 |
|----------|------|-----------|----------|
| 2605.11111 | Title X | 91.2 | 已翻译已发布 |
| 2605.11112 | Title Y | 78.5 | 翻译队列中（task_id: xxx） |
| 2605.11113 | Title Z | 48.3 | 低于最低评分阈值 50 |
```

A paired JSON artifact (`YYYY-MM-DD.json`) is also written for machine consumption, containing the same data plus full `source_evidence` arrays for each intaken paper.

### Config Parameters

```python
# Hot Ranking Cron
hot_ranking_cron_enabled: bool = True
hot_ranking_cron_hour: int = 3          # CST hour
hot_ranking_cron_minute: int = 7        # CST minute (off-peak jitter)
hot_ranking_cron_lock_ttl_seconds: int = 7200  # 2h, prevents duplicate runs

# Auto-Intake
hot_ranking_auto_intake_enabled: bool = True
hot_ranking_auto_intake_top_n: int = 20
hot_ranking_auto_intake_min_score: float = 50.0
hot_ranking_auto_intake_default_window: str = "30d"
hot_ranking_system_user_id: str = ""    # admin user for curation jobs
```

### Risks / Trade-offs (Auto-Intake)
- Translation queue pressure: auto-intaking 20 papers/day means 20 new translation tasks/day. Ensure LLM pool and compile capacity can absorb this.
- Quality gate is the safety net: auto-intaken papers still pass through the full `_run_curation_job` quality gate. Papers that fail quality checks are not published and appear in the next summary as "quality gate failed."
- Category bias: the hot ranking model may over-select CS/AI papers due to GitHub and HuggingFace signal dominance. The implementation cap and authority weighting should mitigate this, but the daily summary should be audited weekly for category distribution.
- Operator override: the daily summary is informational — operators can still manually curate, skip, or delete auto-intaken papers through the existing admin curation UI.

## External References Checked
- arXiv API User Manual: https://info.arxiv.org/help/api/user-manual.html
- OpenAlex Works API: https://docs.openalex.org/api-entities/works
- Semantic Scholar API: https://www.semanticscholar.org/product/api
- Semantic Scholar Graph API docs: https://api.semanticscholar.org/api-docs/graph
- Hugging Face Hub API docs: https://huggingface.co/docs/hub/main/api
- GitHub REST search docs: https://docs.github.com/en/rest/search/search
