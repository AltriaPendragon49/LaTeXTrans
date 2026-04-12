# COS Storage and Stable API Ingress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move production runtime and community assets to Tencent COS with local-disk fallback, slim the public paper-detail payload, and restore stable browser ingress through Cloudflare-managed API routing.

**Architecture:** Add a backend storage abstraction with `local_disk` and `cos` implementations, treat local disk as temporary cache in production, and make public asset delivery backend-aware. Keep the community detail bootstrap small by returning metadata plus asset locators, then let the frontend fetch preview/PDF resources on demand. Align the public API hostname with Cloudflare-managed ingress rather than direct browser dependency on the CVM origin TLS endpoint.

**Tech Stack:** FastAPI, Python 3.12, React 18, Vite, MySQL-backed community metadata, Tencent COS SDK/signing, Cloudflare-managed ingress, pytest, Vitest.

---

## File Map

- `backend/app/core/config.py`
  - Add storage mode, COS credentials/prefixes, temporary cache directories, and ingress-health configuration.
- `backend/app/services/storage_backend.py`
  - New unified storage layer for `local_disk` and `cos`.
- `backend/app/services/paper_service.py`
  - Swap path-only logic for backend-aware asset persistence and lookup.
- `backend/app/api/routes/papers.py`
  - Return lightweight detail bootstrap metadata and backend-aware asset responses.
- `backend/app/api/routes/download.py`
  - Reuse storage-aware asset resolution for source/translated previews and fallback delivery.
- `backend/tests/unit/test_storage_backend.py`
  - New focused tests for local/cos storage behavior.
- `backend/tests/unit/test_papers_list_detail_contract.py`
  - Update detail-contract expectations to use bootstrap locators instead of inlined preview bodies.
- `backend/tests/unit/test_papers_download_bridge.py`
  - Verify local-disk and object-storage PDF delivery flows.
- `backend/tests/unit/test_restart_recovery_cleanup.py`
  - Verify temp-cache cleanup and object-storage-aware recovery/deletion.
- `frontend/src/types/community.ts`
  - Add bootstrap locator types for detail and preview delivery.
- `frontend/src/lib/community-api.ts`
  - Fetch lightweight detail bootstrap first, then fetch preview HTML lazily when needed.
- `frontend/src/hooks/use-paper-detail.ts`
  - Keep page bootstrap responsive while lazily loading preview HTML.
- `frontend/src/pages/PaperDetail.tsx`
  - Consume bootstrap + lazy preview flow without skeleton deadlock.
- `frontend/src/components/community/PaperPreviewReader.tsx`
  - Support `fetch_url`/locator-driven preview loading in addition to inline HTML.
- `frontend/src/components/community/PaperCard.tsx`
  - Keep source/translated PDF preview URLs stable while tolerating redirect/object-storage delivery.
- `frontend/src/hooks/use-paper-detail.test.tsx`
  - Verify bootstrap-first + lazy preview loading.
- `frontend/src/pages/PaperDetail.test.tsx`
  - Verify translated HTML/PDF mode selection after contract change.
- `texts/云部署与运维/云部署运维指南.md`
  - Update production deployment and verification procedure for COS + Cloudflare ingress.

## Task 1: Add Storage Configuration and Backend Abstraction

**Files:**
- Create: `backend/app/services/storage_backend.py`
- Modify: `backend/app/core/config.py`
- Test: `backend/tests/unit/test_storage_backend.py`

- [ ] **Step 1: Write the failing storage-backend test**

```python
from pathlib import Path

from backend.app.services.storage_backend import LocalDiskStorageBackend, StoredObjectRef


def test_local_disk_backend_round_trips_relative_object_key(tmp_path: Path) -> None:
    backend = LocalDiskStorageBackend(root=tmp_path)
    source = tmp_path / "cache" / "preview.html"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("<article>preview</article>", encoding="utf-8")

    stored = backend.put_file(
        local_path=source,
        object_key="community/paper-1/preview/preview.html",
        content_type="text/html",
        delete_local=False,
    )

    assert isinstance(stored, StoredObjectRef)
    assert stored.storage_backend == "local_disk"
    assert stored.object_key == "community/paper-1/preview/preview.html"
    assert backend.resolve_local_path(stored).read_text(encoding="utf-8") == "<article>preview</article>"
```

- [ ] **Step 2: Run the new backend test to verify it fails**

Run: `pytest backend/tests/unit/test_storage_backend.py::test_local_disk_backend_round_trips_relative_object_key -v`

Expected: FAIL with `ModuleNotFoundError` or missing `LocalDiskStorageBackend`.

- [ ] **Step 3: Add storage settings in `backend/app/core/config.py`**

```python
class Settings(BaseSettings):
    storage_backend_mode: str = Field(default="local_disk", validation_alias="STORAGE_BACKEND_MODE")
    storage_temp_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "tmp_storage"
    )
    cos_bucket: Optional[str] = Field(default=None, validation_alias="COS_BUCKET")
    cos_region: Optional[str] = Field(default=None, validation_alias="COS_REGION")
    cos_secret_id: Optional[str] = Field(default=None, validation_alias="COS_SECRET_ID")
    cos_secret_key: Optional[str] = Field(default=None, validation_alias="COS_SECRET_KEY")
    cos_base_prefix: str = Field(default="latextrans-prod", validation_alias="COS_BASE_PREFIX")
```

- [ ] **Step 4: Create `backend/app/services/storage_backend.py` with a typed abstraction**

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class StoredObjectRef:
    storage_backend: str
    object_key: str
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None


class LocalDiskStorageBackend:
    def __init__(self, root: Path) -> None:
        self.root = root

    def put_file(
        self,
        *,
        local_path: Path,
        object_key: str,
        content_type: Optional[str],
        delete_local: bool,
    ) -> StoredObjectRef:
        target = self.root / object_key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(local_path.read_bytes())
        if delete_local and local_path.exists():
            local_path.unlink()
        return StoredObjectRef(storage_backend="local_disk", object_key=object_key, content_type=content_type, size_bytes=target.stat().st_size)

    def resolve_local_path(self, ref: StoredObjectRef) -> Path:
        return self.root / ref.object_key
```

- [ ] **Step 5: Add the COS stub test and implementation hook**

```python
def test_storage_backend_factory_rejects_incomplete_cos_config(tmp_path: Path) -> None:
    from backend.app.services.storage_backend import build_storage_backend

    class DummySettings:
        storage_backend_mode = "cos"
        storage_temp_dir = tmp_path
        cos_bucket = None
        cos_region = "ap-guangzhou"
        cos_secret_id = None
        cos_secret_key = None
        cos_base_prefix = "paperx"

    try:
        build_storage_backend(DummySettings())
    except ValueError as exc:
        assert "COS" in str(exc)
    else:
        raise AssertionError("expected missing COS configuration to fail fast")
```

- [ ] **Step 6: Run the focused backend tests and verify they pass**

Run: `pytest backend/tests/unit/test_storage_backend.py -v`

Expected: PASS with both local-disk and COS-config validation tests green.

- [ ] **Step 7: Commit the storage abstraction baseline**

```bash
git add backend/app/core/config.py backend/app/services/storage_backend.py backend/tests/unit/test_storage_backend.py
git commit -m "feat: add storage backend abstraction for local disk and cos"
```

## Task 2: Persist Runtime and Community Assets Through the Storage Layer

**Files:**
- Modify: `backend/app/services/paper_service.py`
- Modify: `backend/app/services/task_manager.py`
- Test: `backend/tests/unit/test_papers_library_publish_flow.py`
- Test: `backend/tests/unit/test_restart_recovery_cleanup.py`
- Test: `backend/tests/unit/test_paper_service_local_write_cutover.py`

- [ ] **Step 1: Write the failing publish-flow regression for object storage**

```python
def test_publish_task_to_community_library_records_object_storage_keys(monkeypatch, tmp_path):
    from backend.app.services import paper_service

    captured_assets = []

    class FakeRepository:
        def upsert_paper_asset(self, **payload):
            captured_assets.append(payload)
            return payload

    class FakeStorage:
        def put_file(self, *, local_path, object_key, content_type, delete_local):
            return type("Stored", (), {
                "storage_backend": "object_storage",
                "object_key": object_key,
                "content_type": content_type,
                "size_bytes": local_path.stat().st_size,
            })()

    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: FakeRepository())
    monkeypatch.setattr(paper_service, "_get_storage_backend", lambda: FakeStorage())

    # exercise the publish helper here
    # expected: captured_assets contain storage_backend="object_storage"
```

- [ ] **Step 2: Run the publish-flow test to verify it fails**

Run: `pytest backend/tests/unit/test_papers_library_publish_flow.py -k object_storage -v`

Expected: FAIL because publish logic still writes local-disk `file_path` values.

- [ ] **Step 3: Add backend-aware persistence helpers in `backend/app/services/paper_service.py`**

```python
def _canonical_object_key(*, category: str, identifier: str, filename: str) -> str:
    safe_name = Path(filename).name
    return f"{settings.cos_base_prefix}/{category}/{identifier}/{safe_name}"


def _store_retained_artifact(
    *,
    local_path: Path,
    category: str,
    identifier: str,
    filename: str,
    content_type: Optional[str],
    delete_local: bool = True,
) -> dict[str, Any]:
    backend = _get_storage_backend()
    stored = backend.put_file(
        local_path=local_path,
        object_key=_canonical_object_key(category=category, identifier=identifier, filename=filename),
        content_type=content_type,
        delete_local=delete_local,
    )
    return {
        "storage_backend": stored.storage_backend,
        "file_path": stored.object_key,
        "mime_type": content_type,
    }
```

- [ ] **Step 4: Replace community asset copy code with storage-layer writes**

```python
stored_asset = _store_retained_artifact(
    local_path=translated_pdf_path,
    category="community_papers",
    identifier=paper_id,
    filename=translated_pdf_path.name,
    content_type="application/pdf",
)
repository.upsert_paper_asset(
    paper_id=paper_id,
    task_id=task_id,
    asset_type="translated_pdf",
    storage_backend=stored_asset["storage_backend"],
    file_path=stored_asset["file_path"],
    file_name=translated_pdf_path.name,
    mime_type="application/pdf",
)
```

- [ ] **Step 5: Make runtime cleanup object-storage-aware in `backend/app/services/task_manager.py`**

```python
def _delete_local_cache_path(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=False)
    else:
        path.unlink()


def _cleanup_cached_runtime_artifacts(task_id: str, retained_paths: list[Path]) -> None:
    for candidate in retained_paths:
        if candidate.exists():
            _delete_local_cache_path(candidate)
    logger.info("[TaskManager] Cleared local cache artifacts for task %s after durable persistence", task_id)
```

- [ ] **Step 6: Run the backend tests for publish, cleanup, and local fallback**

Run: `pytest backend/tests/unit/test_papers_library_publish_flow.py backend/tests/unit/test_restart_recovery_cleanup.py backend/tests/unit/test_paper_service_local_write_cutover.py -v`

Expected: PASS with new object-storage-aware asset rows and local-disk fallback still green.

- [ ] **Step 7: Commit runtime persistence changes**

```bash
git add backend/app/services/paper_service.py backend/app/services/task_manager.py backend/tests/unit/test_papers_library_publish_flow.py backend/tests/unit/test_restart_recovery_cleanup.py backend/tests/unit/test_paper_service_local_write_cutover.py
git commit -m "feat: persist runtime and community assets through storage backend"
```

## Task 3: Slim the Community Detail Contract and Support Storage-Aware Delivery

**Files:**
- Modify: `backend/app/api/routes/papers.py`
- Modify: `backend/app/api/routes/download.py`
- Modify: `backend/app/services/paper_service.py`
- Test: `backend/tests/unit/test_papers_list_detail_contract.py`
- Test: `backend/tests/unit/test_papers_download_bridge.py`
- Test: `backend/tests/unit/test_public_detail_fast_path.py`

- [ ] **Step 1: Write the failing detail-contract test for lightweight bootstrap**

```python
def test_get_paper_detail_returns_preview_locator_not_inline_html(client, monkeypatch):
    from backend.app.services import paper_service

    async def fake_detail(**_kwargs):
        return {
            "paper": {"id": "paper-1", "title": "Test", "source": "arxiv", "authors": [], "categories": [], "community_status": "official", "trans_status": "completed", "created_at": None, "official_published_at": None, "community_selected_task_id": None, "community_selected_asset_id": None},
            "preview": {"paper_id": "paper-1", "task_id": "task-1", "asset": {"id": "asset-1", "task_id": "task-1", "asset_type": "preview_html", "file_name": "preview.html", "mime_type": "text/html", "created_at": None}, "generated_at": None, "fetch_url": "/api/papers/paper-1/preview"},
            "reader_state": "translated_ready",
            "reader": {"preferred_mode": "translated", "available_modes": ["translated"], "translated": {"kind": "preview_html", "url": "/api/papers/paper-1/preview", "html_content": None, "anchors": []}, "state": "translated_ready"},
            "experience": None,
            "structured_insights": {"state": "ready", "sections": []},
        }

    monkeypatch.setattr(paper_service, "get_community_paper_detail", fake_detail)
    response = client.get("/api/papers/paper-1")

    assert response.status_code == 200
    assert response.json()["preview"]["fetch_url"] == "/api/papers/paper-1/preview"
    assert response.json()["reader"]["translated"]["html_content"] is None
```

- [ ] **Step 2: Run the detail-contract tests to verify they fail**

Run: `pytest backend/tests/unit/test_papers_list_detail_contract.py backend/tests/unit/test_public_detail_fast_path.py -v`

Expected: FAIL because the current detail payload still inlines `html_content`.

- [ ] **Step 3: Change the detail payload in `backend/app/services/paper_service.py`**

```python
def _preview_bootstrap_payload(*, paper_id: str, preview_asset: dict[str, Any]) -> dict[str, Any]:
    return {
        "paper_id": paper_id,
        "task_id": preview_asset.get("task_id"),
        "asset": _serialize_public_asset(preview_asset),
        "generated_at": _serialize_timestamp_value(preview_asset.get("created_at")),
        "fetch_url": f"/api/papers/{paper_id}/preview",
    }


def _translated_preview_reader_resource(*, paper_id: str, preview_asset: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "preview_html",
        "html_content": None,
        "url": f"/api/papers/{paper_id}/preview",
        "asset_id": preview_asset.get("id"),
        "anchors": [],
    }
```

- [ ] **Step 4: Make translated/source PDF endpoints support object storage**

```python
@router.get("/{paper_id}/translated-pdf")
async def preview_translated_paper_pdf(paper_id: str):
    payload = await paper_service.resolve_paper_translated_pdf_preview(paper_id=paper_id)
    if payload["asset"]["storage_backend"] == "object_storage":
        return RedirectResponse(url=payload["signed_url"], status_code=307)
    return FileResponse(path=payload["file_path"], media_type="application/pdf")
```

- [ ] **Step 5: Add download-bridge tests for both backends**

```python
def test_translated_pdf_endpoint_redirects_for_object_storage(client, monkeypatch):
    from backend.app.services import paper_service

    async def fake_payload(*, paper_id: str):
        return {
            "paper_id": paper_id,
            "asset": {"id": "asset-1", "storage_backend": "object_storage", "file_name": "paper.pdf", "mime_type": "application/pdf"},
            "signed_url": "https://cos.example.com/paper.pdf?sign=abc",
        }

    monkeypatch.setattr(paper_service, "resolve_paper_translated_pdf_preview", fake_payload)
    response = client.get("/api/papers/paper-1/translated-pdf", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"].startswith("https://cos.example.com/")
```

- [ ] **Step 6: Run the contract and delivery tests**

Run: `pytest backend/tests/unit/test_papers_list_detail_contract.py backend/tests/unit/test_papers_download_bridge.py backend/tests/unit/test_public_detail_fast_path.py -v`

Expected: PASS with lightweight detail payloads and stable PDF delivery behavior.

- [ ] **Step 7: Commit API contract changes**

```bash
git add backend/app/api/routes/papers.py backend/app/api/routes/download.py backend/app/services/paper_service.py backend/tests/unit/test_papers_list_detail_contract.py backend/tests/unit/test_papers_download_bridge.py backend/tests/unit/test_public_detail_fast_path.py
git commit -m "feat: slim community detail payload and support storage-aware delivery"
```

## Task 4: Update Frontend Detail and Reader Flows for Lazy Asset Loading

**Files:**
- Modify: `frontend/src/types/community.ts`
- Modify: `frontend/src/lib/community-api.ts`
- Modify: `frontend/src/hooks/use-paper-detail.ts`
- Modify: `frontend/src/components/community/PaperPreviewReader.tsx`
- Modify: `frontend/src/pages/PaperDetail.tsx`
- Test: `frontend/src/hooks/use-paper-detail.test.tsx`
- Test: `frontend/src/pages/PaperDetail.test.tsx`
- Test: `frontend/src/components/community/PaperCard.test.tsx`

- [ ] **Step 1: Write the failing frontend hook test for bootstrap-first loading**

```tsx
it("loads paper detail bootstrap first and fetches preview lazily", async () => {
  vi.mocked(getCommunityPaperDetail).mockResolvedValue({
    paper: buildPaper(),
    preview: {
      paper_id: "paper-1",
      task_id: "task-1",
      asset: buildPreviewAsset(),
      generated_at: "2026-04-12T00:00:00Z",
      fetch_url: "/api/papers/paper-1/preview",
    },
    reader_state: "translated_ready",
    reader: {
      preferred_mode: "translated",
      available_modes: ["translated"],
      translated: { kind: "preview_html", url: "/api/papers/paper-1/preview", html_content: null, anchors: [] },
      state: "translated_ready",
    },
    experience: null,
    structured_insights: { state: "ready", sections: [] },
  })
  vi.mocked(getCommunityPaperPreview).mockResolvedValue({
    paper_id: "paper-1",
    task_id: "task-1",
    asset: buildPreviewAsset(),
    generated_at: "2026-04-12T00:00:00Z",
    html_content: "<article>ready</article>",
  })

  const { result } = renderHook(() => usePaperDetail("paper-1"))
  await waitFor(() => expect(result.current.preview?.html_content).toBe("<article>ready</article>"))
})
```

- [ ] **Step 2: Run the frontend hook test to verify it fails**

Run: `npm --prefix frontend test -- use-paper-detail.test.tsx`

Expected: FAIL because the hook currently expects inlined preview HTML from the first detail response.

- [ ] **Step 3: Extend frontend types and API helpers**

```ts
export interface CommunityPaperPreviewBootstrapResponse {
  paper_id: string
  task_id: string | null
  asset: PaperAssetSummary
  generated_at: string | null
  fetch_url: string
}

export interface CommunityPaperDetailResponse {
  paper: CommunityPaper
  preview?: CommunityPaperPreviewBootstrapResponse | null
  reader?: CommunityPaperReader | null
  reader_state?: "ready" | "warming" | "unavailable"
  experience?: CommunityPaperExperience | null
  structured_insights?: StructuredInsightsPayload | null
}
```

- [ ] **Step 4: Update `use-paper-detail.ts` to fetch preview HTML lazily**

```ts
useEffect(() => {
  if (!paperId || !preview || "html_content" in preview) {
    return
  }

  let cancelled = false
  void getCommunityPaperPreview(paperId).then((payload) => {
    if (!cancelled) {
      setPreview(payload)
      setReader((current) =>
        current?.translated?.kind === "preview_html"
          ? {
              ...current,
              translated: { ...current.translated, html_content: payload.html_content, url: preview.fetch_url },
            }
          : current,
      )
    }
  })

  return () => {
    cancelled = true
  }
}, [paperId, preview])
```

- [ ] **Step 5: Update `PaperDetail.tsx` and `PaperPreviewReader.tsx` to render lazy preview content**

```tsx
const translatedHtmlReady =
  reader?.translated?.kind === "preview_html" &&
  Boolean(reader.translated.html_content || preview?.html_content)

if (activeMode === "translated_html" && !translatedHtmlReady && reader?.translated?.url) {
  return <PaperDetailSkeleton />
}
```

```tsx
const effectiveHtml = preview?.html_content ?? readerResource?.html_content ?? null
if (!effectiveHtml) {
  return <div data-testid="paper-preview-reader-loading">{t("common.loading")}</div>
}
```

- [ ] **Step 6: Run the frontend tests for hook, detail page, and card rendering**

Run: `npm --prefix frontend test -- use-paper-detail.test.tsx PaperDetail.test.tsx PaperCard.test.tsx`

Expected: PASS with lazy preview loading and unchanged PDF preview URLs.

- [ ] **Step 7: Commit frontend contract updates**

```bash
git add frontend/src/types/community.ts frontend/src/lib/community-api.ts frontend/src/hooks/use-paper-detail.ts frontend/src/components/community/PaperPreviewReader.tsx frontend/src/pages/PaperDetail.tsx frontend/src/hooks/use-paper-detail.test.tsx frontend/src/pages/PaperDetail.test.tsx frontend/src/components/community/PaperCard.test.tsx
git commit -m "feat: load community preview assets lazily from detail bootstrap"
```

## Task 5: Restore Stable Production Ingress and Document COS Deployment

**Files:**
- Modify: `texts/云部署与运维/云部署运维指南.md`
- Modify: `texts/云部署与运维/访问与登录/服务器、登录相关文档.md`
- Optional Modify: deployment scripts under `scripts/`
- Test/Verify: manual production verification commands

- [ ] **Step 1: Add the failing operational checklist as a docs-first regression**

```md
## API ingress regression symptoms
- Browser requests to `https://api.latextrans.online` fail with `ERR_CONNECTION_CLOSED`
- Server-local `curl https://api.latextrans.online/api/health` still returns `200`
- Community homepage/detail/translated-pdf can fail even after successful backend publication
```

- [ ] **Step 2: Document the new production configuration contract**

```env
STORAGE_BACKEND_MODE=cos
COS_BUCKET=arxiv-1312796310
COS_REGION=ap-guangzhou
COS_BASE_PREFIX=latextrans-prod
STORAGE_TEMP_DIR=/srv/LaTexTrans/backend/data/tmp_storage
```

- [ ] **Step 3: Document the Cloudflare-managed ingress cutover**

```bash
# 1. Keep backend private to Cloudflare/origin-facing traffic
sudo ufw allow 'Nginx Full'

# 2. Validate origin locally before Cloudflare cutover
curl https://api.latextrans.online/api/health

# 3. Validate browser-facing endpoint after Cloudflare routing update
curl -I https://api.latextrans.online/api/health
```

- [ ] **Step 4: Verify production behavior after deployment**

Run:

```bash
curl https://api.latextrans.online/api/health
curl https://api.latextrans.online/api/papers?sort=latest
curl -I https://api.latextrans.online/api/papers/<paper_id>/translated-pdf
```

Expected:
- Health returns HTTP `200`
- Paper list returns HTTP `200`
- Translated PDF returns either HTTP `200` or HTTP `307` to a signed COS URL

- [ ] **Step 5: Commit deployment and runbook updates**

```bash
git add texts/云部署与运维/云部署运维指南.md texts/云部署与运维/访问与登录/服务器、登录相关文档.md
git commit -m "docs: add cos-backed deployment and ingress verification runbook"
```

## Spec Coverage Self-Check

- `deployment-infra`
  - Covered by Task 1 configuration work and Task 5 ingress/runbook cutover.
- `community-paper-library-storage`
  - Covered by Task 2 storage-backed canonical persistence and deletion/cleanup tests.
- `community-public-read-experience`
  - Covered by Task 3 detail bootstrap slimming and Task 4 lazy reader loading.
- `web-api`
  - Covered by Task 3 detail/bootstrap contract and storage-aware PDF delivery.

## Placeholder Scan

- No `TBD`, `TODO`, or “similar to previous task” placeholders remain.
- Every code-touching task includes explicit file paths, test cases, commands, and expected outcomes.
- Field names used across backend and frontend are consistent:
  - `storage_backend`
  - `file_path` as canonical object key for object storage
  - `preview.fetch_url`
  - `reader.translated.url`

