import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter, Route, Routes } from "react-router-dom"

import i18n from "@/i18n"
import PaperDetailPage from "@/pages/PaperDetail"

const usePaperDetailMock = vi.fn()
const translateCommunityPaperMock = vi.fn()
const createCommunityPaperDownloadSessionMock = vi.fn()
const getCommunityPaperPreviewMock = vi.fn()
const loadUserSettingsMock = vi.fn()
const setTaskIdMock = vi.fn()
const setArxivIdMock = vi.fn()
const navigateMock = vi.fn()
const scrollIntoViewMock = vi.fn()
const openMock = vi.fn()

vi.mock("@/hooks/use-paper-detail", () => ({
  usePaperDetail: (...args: unknown[]) => usePaperDetailMock(...args),
}))

vi.mock("@/lib/community-api", () => ({
  getCommunityPaperPreview: (...args: unknown[]) => getCommunityPaperPreviewMock(...args),
  translateCommunityPaper: (...args: unknown[]) => translateCommunityPaperMock(...args),
  createCommunityPaperDownloadSession: (...args: unknown[]) => createCommunityPaperDownloadSessionMock(...args),
}))

vi.mock("@/store/useStore", () => ({
  useStore: () => ({
    config: {
      source_language: "en",
      target_language: "zh",
      advanced_config: {},
    },
    loadUserSettings: loadUserSettingsMock,
    setTaskId: setTaskIdMock,
    setArxivId: setArxivIdMock,
  }),
}))

vi.mock("dompurify", () => ({
  default: {
    sanitize: (value: string) => value,
  },
}))

vi.mock("katex/contrib/auto-render", () => ({
  default: vi.fn(),
}))

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom")
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

describe("PaperDetailPage", () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    await i18n.changeLanguage("en")
    getCommunityPaperPreviewMock.mockResolvedValue({
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
      html_content: "<h2>引言</h2><p>中文段落。</p>",
      generated_at: "2026-03-18T02:00:00Z",
    })
    loadUserSettingsMock.mockResolvedValue(undefined)
    Object.defineProperty(window, "open", {
      configurable: true,
      value: openMock,
    })
    Element.prototype.scrollIntoView = scrollIntoViewMock
    HTMLElement.prototype.scrollIntoView = scrollIntoViewMock
  })

  it("renders metadata, inline reader, and active actions", async () => {
    usePaperDetailMock.mockReturnValue({
      paper: {
        id: "paper-1",
        source: "arxiv",
        arxiv_id: "2503.01010",
        title: "Detail Page Title",
        authors: ["Ada Lovelace"],
        categories: ["cs.AI"],
        abstract_raw: "Abstract body for the detail shell.",
        abstract_translated: "中文摘要",
        community_status: "official",
        trans_status: "completed",
        created_at: "2026-03-18T00:00:00Z",
        official_published_at: "2026-03-18T02:00:00Z",
        community_selected_task_id: "task-1",
        community_selected_asset_id: "asset-preview",
        latest_asset: {
          id: "asset-preview",
          task_id: "task-1",
          asset_type: "preview_html",
          file_name: "preview.html",
          mime_type: "text/html",
          created_at: "2026-03-18T02:00:00Z",
        },
        assets: {
          preview_html: {
            id: "asset-preview",
            task_id: "task-1",
            asset_type: "preview_html",
            file_name: "preview.html",
            mime_type: "text/html",
            created_at: "2026-03-18T02:00:00Z",
          },
        },
        like_count: 7,
        favorite_count: 3,
        comment_count: 2,
        view_count: 21,
      },
      loading: false,
      error: null,
      notFound: false,
    })

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText("Detail Page Title")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Translate" })).toBeEnabled()
    expect(screen.getByRole("button", { name: "Download" })).toBeEnabled()
    expect(await screen.findByText("中文段落。")).toBeInTheDocument()
  })

  it("clicking translate queues the paper and navigates to processing", async () => {
    usePaperDetailMock.mockReturnValue({
      paper: {
        id: "paper-1",
        source: "upload",
        arxiv_id: null,
        title: "Detail Page Title",
        authors: ["Ada Lovelace"],
        categories: ["cs.AI"],
        abstract_raw: "Abstract body for the detail shell.",
        abstract_translated: null,
        community_status: "official",
        trans_status: "not_started",
        created_at: "2026-03-18T00:00:00Z",
        official_published_at: "2026-03-18T02:00:00Z",
        community_selected_task_id: null,
        community_selected_asset_id: "asset-source",
        assets: {
          source_archive: {
            id: "asset-source",
            task_id: null,
            asset_type: "source_archive",
            file_name: "source.zip",
            mime_type: "application/zip",
            created_at: "2026-03-18T01:00:00Z",
          },
        },
        latest_asset: {
          id: "asset-source",
          task_id: null,
          asset_type: "source_archive",
          file_name: "source.zip",
          mime_type: "application/zip",
          created_at: "2026-03-18T01:00:00Z",
        },
      },
      loading: false,
      error: null,
      notFound: false,
    })
    translateCommunityPaperMock.mockResolvedValue({
      paper_id: "paper-1",
      task_id: "task-new",
      status: "queued",
      reused_existing_task: false,
      processing_url: "/processing?taskId=task-new",
    })

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await userEvent.click(screen.getByRole("button", { name: "Translate" }))

    await waitFor(() => {
      expect(loadUserSettingsMock).toHaveBeenCalled()
      expect(translateCommunityPaperMock).toHaveBeenCalledWith(
        "paper-1",
        expect.objectContaining({
          source_language: "en",
          target_language: "zh",
        }),
      )
      expect(setTaskIdMock).toHaveBeenCalledWith("task-new")
      expect(setArxivIdMock).toHaveBeenCalledWith(null)
      expect(navigateMock).toHaveBeenCalledWith("/processing?taskId=task-new")
    })
  })

  it("clicking view progress routes to the existing processing page", async () => {
    usePaperDetailMock.mockReturnValue({
      paper: {
        id: "paper-1",
        source: "arxiv",
        arxiv_id: "2503.01010",
        title: "Detail Page Title",
        authors: ["Ada Lovelace"],
        categories: ["cs.AI"],
        abstract_raw: "Abstract body for the detail shell.",
        abstract_translated: null,
        community_status: "official",
        trans_status: "processing",
        created_at: "2026-03-18T00:00:00Z",
        official_published_at: "2026-03-18T02:00:00Z",
        community_selected_task_id: "task-progress",
        community_selected_asset_id: "asset-source",
        latest_asset: {
          id: "asset-source",
          task_id: "task-progress",
          asset_type: "source_archive",
          file_name: "source.zip",
          mime_type: "application/zip",
          created_at: "2026-03-18T01:00:00Z",
        },
      },
      loading: false,
      error: null,
      notFound: false,
    })

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await userEvent.click(screen.getByRole("button", { name: "View Progress" }))

    expect(setTaskIdMock).toHaveBeenCalledWith("task-progress")
    expect(navigateMock).toHaveBeenCalledWith("/processing?taskId=task-progress")
  })

  it("clicking preview focuses the inline reader and download opens signed url", async () => {
    usePaperDetailMock.mockReturnValue({
      paper: {
        id: "paper-1",
        source: "arxiv",
        arxiv_id: "2503.01010",
        title: "Detail Page Title",
        authors: ["Ada Lovelace"],
        categories: ["cs.AI"],
        abstract_raw: "Abstract body for the detail shell.",
        abstract_translated: "中文摘要",
        community_status: "official",
        trans_status: "completed",
        created_at: "2026-03-18T00:00:00Z",
        official_published_at: "2026-03-18T02:00:00Z",
        community_selected_task_id: "task-1",
        community_selected_asset_id: "asset-preview",
        latest_asset: {
          id: "asset-preview",
          task_id: "task-1",
          asset_type: "preview_html",
          file_name: "preview.html",
          mime_type: "text/html",
          created_at: "2026-03-18T02:00:00Z",
        },
      },
      loading: false,
      error: null,
      notFound: false,
    })
    createCommunityPaperDownloadSessionMock.mockResolvedValue({
      paper_id: "paper-1",
      asset_id: "asset-pdf",
      download_url: "/api/papers/paper-1/download?token=abc",
      expires_at: "2026-03-18T02:05:00Z",
    })

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByText("中文段落。")
    await userEvent.click(screen.getByRole("button", { name: "Preview" }))
    await userEvent.click(screen.getByRole("button", { name: "Download" }))

    expect(scrollIntoViewMock).toHaveBeenCalled()
    await waitFor(() => {
      expect(createCommunityPaperDownloadSessionMock).toHaveBeenCalledWith("paper-1")
      expect(openMock).toHaveBeenCalledWith("/api/papers/paper-1/download?token=abc", "_blank")
    })
  })

  it("renders a not-found state", () => {
    usePaperDetailMock.mockReturnValue({
      paper: null,
      loading: false,
      error: "404",
      notFound: true,
    })

    render(
      <MemoryRouter initialEntries={["/paper/missing"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText("Paper not found")).toBeInTheDocument()
  })
})
