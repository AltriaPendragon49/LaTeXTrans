import { render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { usePaperDetail } from "@/features/community-paper/hooks/use-paper-detail"
import {
  clearCommunityPaperDetailCache,
  primeCommunityPaperDetailCache,
} from "@/features/community-paper/services/community-paper-api"

const getCommunityPaperDetailMock = vi.fn()
const recordCommunityPaperViewMock = vi.fn()

vi.mock("@/features/community-paper/services/community-paper-api", async () => {
  const actual = await vi.importActual<typeof import("@/features/community-paper/services/community-paper-api")>(
    "@/features/community-paper/services/community-paper-api",
  )
  return {
    ...actual,
    getCommunityPaperDetail: (...args: unknown[]) => getCommunityPaperDetailMock(...args),
    recordCommunityPaperView: (...args: unknown[]) => recordCommunityPaperViewMock(...args),
  }
})

function HookProbe({ paperId }: { paperId?: string }) {
  const { paper, preview, readerState, loading } = usePaperDetail(paperId)

  return (
    <div>
      <span data-testid="loading">{String(loading)}</span>
      <span data-testid="title">{paper?.title ?? ""}</span>
      <span data-testid="reader-state">{readerState}</span>
      <span data-testid="preview-name">{preview?.asset.file_name ?? ""}</span>
    </div>
  )
}

describe("usePaperDetail", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    clearCommunityPaperDetailCache()
  })

  it("uses prefetched detail cache immediately before refreshing", async () => {
    primeCommunityPaperDetailCache("paper-1", {
      paper: {
        id: "paper-1",
        source: "arxiv",
        arxiv_id: "2503.01010",
        title: "Cached paper",
        authors: [],
        categories: [],
        community_status: "official",
        trans_status: "completed",
        created_at: "2026-03-18T00:00:00Z",
        official_published_at: "2026-03-18T02:00:00Z",
        community_selected_task_id: "task-1",
        community_selected_asset_id: "asset-preview",
      },
      preview: {
        paper_id: "paper-1",
        task_id: "task-1",
        asset: {
          id: "asset-preview",
          task_id: "task-1",
          asset_type: "preview_html",
          file_name: "preview.html",
          mime_type: "text/html",
          created_at: "2026-03-18T02:00:00Z",
        },
        html_content: "<article>Cached</article>",
        generated_at: "2026-03-18T02:00:00Z",
      },
      reader_state: "ready",
    })
    getCommunityPaperDetailMock.mockResolvedValue({
      paper: {
        id: "paper-1",
        source: "arxiv",
        arxiv_id: "2503.01010",
        title: "Fresh paper",
        authors: [],
        categories: [],
        community_status: "official",
        trans_status: "completed",
        created_at: "2026-03-18T00:00:00Z",
        official_published_at: "2026-03-18T02:00:00Z",
        community_selected_task_id: "task-1",
        community_selected_asset_id: "asset-preview",
      },
      preview: null,
      reader_state: "warming",
    })

    render(<HookProbe paperId="paper-1" />)

    expect(screen.getByTestId("loading")).toHaveTextContent("false")
    expect(screen.getByTestId("title")).toHaveTextContent("Cached paper")
    expect(screen.getByTestId("reader-state")).toHaveTextContent("ready")
    expect(screen.getByTestId("preview-name")).toHaveTextContent("preview.html")

    await waitFor(() => expect(getCommunityPaperDetailMock).toHaveBeenCalledWith("paper-1"))
    await waitFor(() => expect(recordCommunityPaperViewMock).toHaveBeenCalledTimes(1))
  })
})
