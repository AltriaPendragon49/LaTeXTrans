from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional

from fastapi import HTTPException

from backend.app.api.routes.translate import TranslateRequest
from backend.app.services import paper_service

logger = logging.getLogger(__name__)

_PREWARM_STAGES = ("discover", "admit", "source", "translate", "preview", "promote")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


@dataclass(frozen=True)
class PoolCandidate:
    arxiv_id: str
    source: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "PoolCandidate":
        arxiv_id = _normalize_text(payload.get("arxiv_id"))
        if not arxiv_id:
            raise ValueError("candidate arxiv_id is required")
        source = _normalize_text(payload.get("source")) or "unknown"
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        return cls(arxiv_id=arxiv_id, source=source, metadata=metadata)


@dataclass
class ContentPoolDependencies:
    discover_candidates: Callable[[], Awaitable[List[Dict[str, Any]]]] | None = None
    admit_candidate: Callable[[str], Awaitable[Dict[str, Any]]] | None = None
    ensure_source_ready: Callable[[str, str], Awaitable[Dict[str, Any]]] | None = None
    start_translation: Callable[[str], Awaitable[Dict[str, Any]]] | None = None
    ensure_preview_ready: Callable[[str, Optional[str]], Awaitable[Dict[str, Any]]] | None = None
    promote_translated_evidence: Callable[[str], Awaitable[Dict[str, Any]]] | None = None


@dataclass
class _CandidateState:
    arxiv_id: str
    source: str
    status: str = "discovered"
    stage: str = "discover"
    attempts: int = 0
    paper_id: str | None = None
    task_id: str | None = None
    translated_ready: bool = False
    last_error: str | None = None
    discovered_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "arxiv_id": self.arxiv_id,
            "source": self.source,
            "status": self.status,
            "stage": self.stage,
            "attempts": self.attempts,
            "paper_id": self.paper_id,
            "task_id": self.task_id,
            "translated_ready": self.translated_ready,
            "last_error": self.last_error,
            "discovered_at": self.discovered_at,
            "updated_at": self.updated_at,
        }


async def _default_discover_candidates() -> List[Dict[str, Any]]:
    return []


async def _default_admit_candidate(arxiv_id: str) -> Dict[str, Any]:
    return await paper_service.import_or_reuse_paper(source="arxiv", arxiv_id=arxiv_id)


async def _default_ensure_source_ready(paper_id: str, arxiv_id: str) -> Dict[str, Any]:
    del arxiv_id
    detail = await paper_service.get_community_paper_detail(
        paper_id=paper_id,
        viewer_user_id=None,
        fast_path=True,
    )
    reader = detail.get("reader") if isinstance(detail, dict) else {}
    source_resource = reader.get("source") if isinstance(reader, dict) else None
    return {"ready": bool(source_resource)}


async def _default_start_translation(paper_id: str) -> Dict[str, Any]:
    return await paper_service.start_paper_translation(
        paper_id=paper_id,
        request=TranslateRequest(source_language="en", target_language="zh"),
        credentials=None,
    )


async def _default_ensure_preview_ready(paper_id: str, task_id: str | None) -> Dict[str, Any]:
    del task_id
    try:
        payload = await paper_service.get_paper_preview(paper_id=paper_id)
    except HTTPException as exc:
        if exc.status_code == 404:
            return {"ready": False}
        raise
    return {"ready": bool(payload.get("asset"))}


async def _default_promote_translated_evidence(paper_id: str) -> Dict[str, Any]:
    detail = await paper_service.get_community_paper_detail(
        paper_id=paper_id,
        viewer_user_id=None,
        fast_path=True,
    )
    reader = detail.get("reader") if isinstance(detail, dict) else {}
    translated_ready = bool(isinstance(reader, dict) and reader.get("state") == "translated_ready")
    return {
        "translated_ready": translated_ready,
        "indexed": translated_ready,
    }


class CommunityContentPoolService:
    def __init__(
        self,
        *,
        dependencies: ContentPoolDependencies | None = None,
        max_concurrency: int = 2,
        max_retries: int = 1,
        source_fetch_min_interval_seconds: float = 0.2,
    ) -> None:
        deps = dependencies or ContentPoolDependencies()
        self._dependencies = ContentPoolDependencies(
            discover_candidates=deps.discover_candidates or _default_discover_candidates,
            admit_candidate=deps.admit_candidate or _default_admit_candidate,
            ensure_source_ready=deps.ensure_source_ready or _default_ensure_source_ready,
            start_translation=deps.start_translation or _default_start_translation,
            ensure_preview_ready=deps.ensure_preview_ready or _default_ensure_preview_ready,
            promote_translated_evidence=deps.promote_translated_evidence or _default_promote_translated_evidence,
        )
        self._max_retries = max(0, int(max_retries))
        self._source_fetch_min_interval_seconds = max(0.0, float(source_fetch_min_interval_seconds))
        self._semaphore = asyncio.Semaphore(max(1, int(max_concurrency)))

        self._states: Dict[str, _CandidateState] = {}
        self._events: List[Dict[str, Any]] = []
        self._source_fetch_gate = asyncio.Lock()
        self._last_source_fetch_ts = 0.0

    async def _throttle_source_fetch(self) -> None:
        if self._source_fetch_min_interval_seconds <= 0:
            return

        async with self._source_fetch_gate:
            now = asyncio.get_running_loop().time()
            wait_seconds = (self._last_source_fetch_ts + self._source_fetch_min_interval_seconds) - now
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)
                now = asyncio.get_running_loop().time()
            self._last_source_fetch_ts = now

    def _record_event(
        self,
        *,
        arxiv_id: str,
        stage: str,
        status: str,
        attempt: int,
        payload: Dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        event = {
            "timestamp": _utc_now_iso(),
            "arxiv_id": arxiv_id,
            "stage": stage,
            "status": status,
            "attempt": attempt,
            "payload": payload or {},
            "error": error,
        }
        self._events.append(event)
        if len(self._events) > 4000:
            self._events = self._events[-4000:]

    @staticmethod
    def _normalize_candidates(raw_candidates: Iterable[PoolCandidate | Dict[str, Any]]) -> List[PoolCandidate]:
        normalized: List[PoolCandidate] = []
        seen: set[str] = set()
        for item in raw_candidates:
            if isinstance(item, PoolCandidate):
                candidate = item
            elif isinstance(item, dict):
                candidate = PoolCandidate.from_payload(item)
            else:
                continue
            if candidate.arxiv_id in seen:
                continue
            seen.add(candidate.arxiv_id)
            normalized.append(candidate)
        return normalized

    async def run_once(
        self,
        *,
        candidates: Iterable[PoolCandidate | Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        raw_candidates = (
            candidates
            if candidates is not None
            else await self._dependencies.discover_candidates()  # type: ignore[misc]
        )
        normalized_candidates = self._normalize_candidates(raw_candidates)
        if not normalized_candidates:
            return self.get_readiness_snapshot()

        tasks = []
        for candidate in normalized_candidates:
            state = self._states.get(candidate.arxiv_id)
            if state and state.translated_ready:
                self._record_event(
                    arxiv_id=candidate.arxiv_id,
                    stage="discover",
                    status="skipped",
                    attempt=state.attempts,
                    payload={"reason": "already_translated_ready"},
                )
                continue
            tasks.append(asyncio.create_task(self._run_candidate(candidate)))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=False)

        return self.get_readiness_snapshot()

    async def _run_candidate(self, candidate: PoolCandidate) -> None:
        async with self._semaphore:
            state = self._states.get(candidate.arxiv_id)
            if state is None:
                state = _CandidateState(arxiv_id=candidate.arxiv_id, source=candidate.source)
                self._states[candidate.arxiv_id] = state
            else:
                state.source = candidate.source
                state.status = "discovered"
                state.stage = "discover"
                state.updated_at = _utc_now_iso()

            self._record_event(
                arxiv_id=candidate.arxiv_id,
                stage="discover",
                status="completed",
                attempt=state.attempts,
                payload={"source": candidate.source},
            )

            for attempt in range(self._max_retries + 1):
                state.attempts = attempt + 1
                state.status = "running"
                state.last_error = None
                state.updated_at = _utc_now_iso()
                current_stage = "admit"

                try:
                    self._record_event(
                        arxiv_id=candidate.arxiv_id,
                        stage="admit",
                        status="running",
                        attempt=state.attempts,
                    )
                    admitted = await self._dependencies.admit_candidate(candidate.arxiv_id)  # type: ignore[misc]
                    paper_id = _normalize_text(admitted.get("paper_id"))
                    if not paper_id:
                        raise RuntimeError("content pool admission did not return paper_id")
                    state.paper_id = paper_id
                    self._record_event(
                        arxiv_id=candidate.arxiv_id,
                        stage="admit",
                        status="completed",
                        attempt=state.attempts,
                        payload={"paper_id": paper_id, "reused": bool(admitted.get("reused"))},
                    )

                    current_stage = "source"
                    self._record_event(
                        arxiv_id=candidate.arxiv_id,
                        stage="source",
                        status="running",
                        attempt=state.attempts,
                        payload={"paper_id": paper_id},
                    )
                    await self._throttle_source_fetch()
                    source_status = await self._dependencies.ensure_source_ready(paper_id, candidate.arxiv_id)  # type: ignore[misc]
                    if not bool(source_status.get("ready")):
                        raise RuntimeError("source archive is not ready")
                    self._record_event(
                        arxiv_id=candidate.arxiv_id,
                        stage="source",
                        status="completed",
                        attempt=state.attempts,
                    )

                    current_stage = "translate"
                    self._record_event(
                        arxiv_id=candidate.arxiv_id,
                        stage="translate",
                        status="running",
                        attempt=state.attempts,
                    )
                    translation = await self._dependencies.start_translation(paper_id)  # type: ignore[misc]
                    task_id = _normalize_text(translation.get("task_id")) or None
                    state.task_id = task_id
                    self._record_event(
                        arxiv_id=candidate.arxiv_id,
                        stage="translate",
                        status="completed",
                        attempt=state.attempts,
                        payload={
                            "task_id": task_id,
                            "status": _normalize_text(translation.get("status")) or "unknown",
                        },
                    )

                    current_stage = "preview"
                    self._record_event(
                        arxiv_id=candidate.arxiv_id,
                        stage="preview",
                        status="running",
                        attempt=state.attempts,
                    )
                    preview_status = await self._dependencies.ensure_preview_ready(paper_id, task_id)  # type: ignore[misc]
                    if not bool(preview_status.get("ready")):
                        raise RuntimeError("preview is not ready")
                    self._record_event(
                        arxiv_id=candidate.arxiv_id,
                        stage="preview",
                        status="completed",
                        attempt=state.attempts,
                    )

                    current_stage = "promote"
                    self._record_event(
                        arxiv_id=candidate.arxiv_id,
                        stage="promote",
                        status="running",
                        attempt=state.attempts,
                    )
                    promoted = await self._dependencies.promote_translated_evidence(paper_id)  # type: ignore[misc]
                    translated_ready = bool(promoted.get("translated_ready"))
                    if not translated_ready:
                        raise RuntimeError("translated evidence is not queryable yet")
                    state.translated_ready = translated_ready
                    state.status = "translated_ready"
                    state.stage = "promote"
                    state.updated_at = _utc_now_iso()
                    self._record_event(
                        arxiv_id=candidate.arxiv_id,
                        stage="promote",
                        status="completed",
                        attempt=state.attempts,
                        payload={
                            "translated_ready": translated_ready,
                            "indexed": bool(promoted.get("indexed")),
                        },
                    )
                    return
                except Exception as exc:
                    state.status = "failed"
                    state.stage = current_stage
                    state.last_error = str(exc)
                    state.updated_at = _utc_now_iso()
                    self._record_event(
                        arxiv_id=candidate.arxiv_id,
                        stage=current_stage,
                        status="failed",
                        attempt=state.attempts,
                        error=str(exc),
                    )
                    logger.warning(
                        "Community content pool candidate failed at stage=%s arxiv_id=%s attempt=%s error=%s",
                        current_stage,
                        candidate.arxiv_id,
                        state.attempts,
                        exc,
                    )
                    if attempt >= self._max_retries:
                        return
                    await asyncio.sleep(min(0.2 * (2**attempt), 1.0))

    def get_candidate_state(self, arxiv_id: str) -> Dict[str, Any] | None:
        state = self._states.get(_normalize_text(arxiv_id))
        return state.to_public_dict() if state else None

    def get_job_log(self, *, arxiv_id: str | None = None, limit: int = 200) -> List[Dict[str, Any]]:
        normalized_arxiv_id = _normalize_text(arxiv_id)
        events = self._events
        if normalized_arxiv_id:
            events = [event for event in events if event.get("arxiv_id") == normalized_arxiv_id]
        if limit > 0:
            events = events[-limit:]
        return [dict(event) for event in events]

    def get_readiness_snapshot(self) -> Dict[str, Any]:
        states = list(self._states.values())
        stage_totals = {stage: 0 for stage in _PREWARM_STAGES}
        for event in self._events:
            stage = event.get("stage")
            if stage in stage_totals and event.get("status") == "completed":
                stage_totals[stage] += 1

        translated_ready_total = sum(1 for state in states if state.translated_ready)
        failure_total = sum(1 for state in states if state.status == "failed")
        running_total = sum(1 for state in states if state.status == "running")
        freshness_values = [state.updated_at for state in states if state.translated_ready]

        return {
            "candidate_total": len(states),
            "warmed_total": translated_ready_total,
            "translated_ready_total": translated_ready_total,
            "failure_total": failure_total,
            "running_total": running_total,
            "freshness": max(freshness_values) if freshness_values else None,
            "stage_totals": stage_totals,
            "updated_at": _utc_now_iso(),
        }


_default_service = CommunityContentPoolService()


async def run_content_pool_cycle(
    *,
    candidates: Iterable[PoolCandidate | Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    return await _default_service.run_once(candidates=candidates)


def get_content_pool_readiness_snapshot() -> Dict[str, Any]:
    return _default_service.get_readiness_snapshot()


def get_content_pool_job_log(*, arxiv_id: str | None = None, limit: int = 200) -> List[Dict[str, Any]]:
    return _default_service.get_job_log(arxiv_id=arxiv_id, limit=limit)


__all__ = [
    "ContentPoolDependencies",
    "CommunityContentPoolService",
    "PoolCandidate",
    "get_content_pool_job_log",
    "get_content_pool_readiness_snapshot",
    "run_content_pool_cycle",
]
