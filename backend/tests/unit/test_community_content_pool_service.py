import asyncio

from backend.app.services.community_content_pool_service import (
    CommunityContentPoolService,
    ContentPoolDependencies,
)


def test_content_pool_run_once_prewarms_candidate_and_records_readiness() -> None:
    calls: list[tuple[str, str]] = []

    async def admit_candidate(arxiv_id: str) -> dict:
        calls.append(("admit", arxiv_id))
        return {"paper_id": "paper-1", "reused": False}

    async def ensure_source_ready(paper_id: str, arxiv_id: str) -> dict:
        calls.append(("source", paper_id))
        assert arxiv_id == "2503.01010"
        return {"ready": True}

    async def start_translation(paper_id: str) -> dict:
        calls.append(("translate", paper_id))
        return {"task_id": "task-1", "status": "queued"}

    async def ensure_preview_ready(paper_id: str, task_id: str | None) -> dict:
        calls.append(("preview", paper_id))
        assert task_id == "task-1"
        return {"ready": True}

    async def promote_translated_evidence(paper_id: str) -> dict:
        calls.append(("promote", paper_id))
        return {"translated_ready": True, "indexed": True}

    service = CommunityContentPoolService(
        dependencies=ContentPoolDependencies(
            admit_candidate=admit_candidate,
            ensure_source_ready=ensure_source_ready,
            start_translation=start_translation,
            ensure_preview_ready=ensure_preview_ready,
            promote_translated_evidence=promote_translated_evidence,
        ),
        max_concurrency=2,
        max_retries=0,
        source_fetch_min_interval_seconds=0.0,
    )

    snapshot = asyncio.run(
        service.run_once(
            candidates=[
                {"arxiv_id": "2503.01010", "source": "hot_feed"},
                {"arxiv_id": "2503.01010", "source": "duplicate"},
            ]
        )
    )

    assert snapshot["candidate_total"] == 1
    assert snapshot["translated_ready_total"] == 1
    assert snapshot["failure_total"] == 0
    assert calls == [
        ("admit", "2503.01010"),
        ("source", "paper-1"),
        ("translate", "paper-1"),
        ("preview", "paper-1"),
        ("promote", "paper-1"),
    ]
    state = service.get_candidate_state("2503.01010")
    assert state is not None
    assert state["paper_id"] == "paper-1"
    assert state["status"] == "translated_ready"
    events = service.get_job_log(arxiv_id="2503.01010")
    assert any(event["stage"] == "promote" and event["status"] == "completed" for event in events)


def test_content_pool_contains_failures_and_continues_other_candidates() -> None:
    async def admit_candidate(arxiv_id: str) -> dict:
        return {"paper_id": f"paper-{arxiv_id}", "reused": True}

    async def ensure_source_ready(paper_id: str, arxiv_id: str) -> dict:
        del paper_id, arxiv_id
        return {"ready": True}

    async def start_translation(paper_id: str) -> dict:
        return {"task_id": f"task-{paper_id}", "status": "queued"}

    async def ensure_preview_ready(paper_id: str, task_id: str | None) -> dict:
        del task_id
        if paper_id.endswith("2503.22222"):
            raise RuntimeError("preview build failed")
        return {"ready": True}

    async def promote_translated_evidence(paper_id: str) -> dict:
        return {"translated_ready": not paper_id.endswith("2503.22222"), "indexed": True}

    service = CommunityContentPoolService(
        dependencies=ContentPoolDependencies(
            admit_candidate=admit_candidate,
            ensure_source_ready=ensure_source_ready,
            start_translation=start_translation,
            ensure_preview_ready=ensure_preview_ready,
            promote_translated_evidence=promote_translated_evidence,
        ),
        max_concurrency=2,
        max_retries=0,
        source_fetch_min_interval_seconds=0.0,
    )

    snapshot = asyncio.run(
        service.run_once(
            candidates=[
                {"arxiv_id": "2503.11111", "source": "hot_feed"},
                {"arxiv_id": "2503.22222", "source": "hot_feed"},
            ]
        )
    )

    assert snapshot["candidate_total"] == 2
    assert snapshot["translated_ready_total"] == 1
    assert snapshot["failure_total"] == 1
    assert service.get_candidate_state("2503.11111")["status"] == "translated_ready"
    assert service.get_candidate_state("2503.22222")["status"] == "failed"


def test_content_pool_retries_stage_failures_within_bound() -> None:
    attempts = {"source": 0}

    async def admit_candidate(arxiv_id: str) -> dict:
        return {"paper_id": f"paper-{arxiv_id}", "reused": False}

    async def ensure_source_ready(paper_id: str, arxiv_id: str) -> dict:
        del paper_id, arxiv_id
        attempts["source"] += 1
        if attempts["source"] == 1:
            raise RuntimeError("transient source timeout")
        return {"ready": True}

    async def start_translation(paper_id: str) -> dict:
        return {"task_id": f"task-{paper_id}", "status": "queued"}

    async def ensure_preview_ready(paper_id: str, task_id: str | None) -> dict:
        del paper_id, task_id
        return {"ready": True}

    async def promote_translated_evidence(paper_id: str) -> dict:
        del paper_id
        return {"translated_ready": True, "indexed": True}

    service = CommunityContentPoolService(
        dependencies=ContentPoolDependencies(
            admit_candidate=admit_candidate,
            ensure_source_ready=ensure_source_ready,
            start_translation=start_translation,
            ensure_preview_ready=ensure_preview_ready,
            promote_translated_evidence=promote_translated_evidence,
        ),
        max_concurrency=1,
        max_retries=1,
        source_fetch_min_interval_seconds=0.0,
    )

    snapshot = asyncio.run(service.run_once(candidates=[{"arxiv_id": "2503.33333", "source": "hot_feed"}]))

    assert attempts["source"] == 2
    assert snapshot["failure_total"] == 0
    assert service.get_candidate_state("2503.33333")["status"] == "translated_ready"


def test_content_pool_respects_max_concurrency() -> None:
    max_inflight = {"value": 0}
    inflight = {"value": 0}

    async def admit_candidate(arxiv_id: str) -> dict:
        return {"paper_id": f"paper-{arxiv_id}", "reused": False}

    async def ensure_source_ready(paper_id: str, arxiv_id: str) -> dict:
        del paper_id, arxiv_id
        inflight["value"] += 1
        max_inflight["value"] = max(max_inflight["value"], inflight["value"])
        await asyncio.sleep(0.02)
        inflight["value"] -= 1
        return {"ready": True}

    async def start_translation(paper_id: str) -> dict:
        return {"task_id": f"task-{paper_id}", "status": "queued"}

    async def ensure_preview_ready(paper_id: str, task_id: str | None) -> dict:
        del paper_id, task_id
        return {"ready": True}

    async def promote_translated_evidence(paper_id: str) -> dict:
        del paper_id
        return {"translated_ready": True, "indexed": True}

    service = CommunityContentPoolService(
        dependencies=ContentPoolDependencies(
            admit_candidate=admit_candidate,
            ensure_source_ready=ensure_source_ready,
            start_translation=start_translation,
            ensure_preview_ready=ensure_preview_ready,
            promote_translated_evidence=promote_translated_evidence,
        ),
        max_concurrency=2,
        max_retries=0,
        source_fetch_min_interval_seconds=0.0,
    )

    asyncio.run(
        service.run_once(
            candidates=[
                {"arxiv_id": "2503.41001"},
                {"arxiv_id": "2503.41002"},
                {"arxiv_id": "2503.41003"},
            ]
        )
    )

    assert max_inflight["value"] <= 2


def test_content_pool_is_idempotent_for_translated_ready_candidates() -> None:
    call_count = {"admit": 0, "translate": 0}

    async def admit_candidate(arxiv_id: str) -> dict:
        call_count["admit"] += 1
        return {"paper_id": f"paper-{arxiv_id}", "reused": False}

    async def ensure_source_ready(paper_id: str, arxiv_id: str) -> dict:
        del paper_id, arxiv_id
        return {"ready": True}

    async def start_translation(paper_id: str) -> dict:
        call_count["translate"] += 1
        return {"task_id": f"task-{paper_id}", "status": "queued"}

    async def ensure_preview_ready(paper_id: str, task_id: str | None) -> dict:
        del paper_id, task_id
        return {"ready": True}

    async def promote_translated_evidence(paper_id: str) -> dict:
        del paper_id
        return {"translated_ready": True, "indexed": True}

    service = CommunityContentPoolService(
        dependencies=ContentPoolDependencies(
            admit_candidate=admit_candidate,
            ensure_source_ready=ensure_source_ready,
            start_translation=start_translation,
            ensure_preview_ready=ensure_preview_ready,
            promote_translated_evidence=promote_translated_evidence,
        ),
        max_concurrency=1,
        max_retries=0,
        source_fetch_min_interval_seconds=0.0,
    )

    asyncio.run(service.run_once(candidates=[{"arxiv_id": "2503.51001"}]))
    asyncio.run(service.run_once(candidates=[{"arxiv_id": "2503.51001"}]))

    assert call_count["admit"] == 1
    assert call_count["translate"] == 1
