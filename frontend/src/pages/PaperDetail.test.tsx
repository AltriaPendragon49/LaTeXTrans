import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter, Route, Routes } from "react-router-dom"

import i18n from "@/i18n"
import { API_BASE_URL } from "@/api-base"
import PaperDetailPage from "@/pages/PaperDetail"

const usePaperDetailMock = vi.fn()
const translateCommunityPaperMock = vi.fn()
const createCommunityPaperDownloadSessionMock = vi.fn()
const getCommunityPaperPreviewMock = vi.fn()
const loadUserSettingsMock = vi.fn()
const setTaskIdMock = vi.fn()
const setArxivIdMock = vi.fn()
const navigateMock = vi.fn()
const katexRenderToStringMock = vi.fn((value: string, _options?: unknown) => `<span class=\"katex\">${value}</span>`)
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

vi.mock("katex", () => ({
  default: {
    renderToString: (value: string, options?: unknown) => katexRenderToStringMock(value, options),
  },
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

  it("renders header metadata, disables repeat translation for completed papers, and keeps download available", async () => {
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
    expect(screen.getByRole("button", { name: "Translate" })).toBeDisabled()
    expect(screen.getByRole("button", { name: "Download" })).toBeEnabled()
    expect(screen.getByTestId("paper-detail-header-metadata")).toBeInTheDocument()
    expect(
      screen.getByRole("link", { name: "Original sourcehttps://arxiv.org/abs/2503.01010" }),
    ).toHaveAttribute("href", "https://arxiv.org/abs/2503.01010")
    expect(await screen.findByText("中文段落。")).toBeInTheDocument()
  })

  it("uses preview bootstrap from the detail payload when the reader is ready", async () => {
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
        html_content: "<h2>中文引言</h2><p>中文段落。</p>",
        generated_at: "2026-03-18T02:00:00Z",
      },
      readerState: "ready",
    })

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText("中文段落。")).toBeInTheDocument()
    expect(getCommunityPaperPreviewMock).not.toHaveBeenCalled()
  })

  it("renders a warming state when the preview is not ready yet", () => {
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
        community_selected_asset_id: "asset-pdf",
        latest_asset: {
          id: "asset-pdf",
          task_id: "task-1",
          asset_type: "translated_pdf",
          file_name: "paper.pdf",
          mime_type: "application/pdf",
          created_at: "2026-03-18T02:00:00Z",
        },
      },
      loading: false,
      error: null,
      notFound: false,
      preview: null,
      readerState: "warming",
    })

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText("Translated reader is warming up")).toBeInTheDocument()
    expect(
      screen.getByText(
        "The paper metadata is ready, and the reading view is being prepared in the background. Check back shortly.",
      ),
    ).toBeInTheDocument()
    expect(getCommunityPaperPreviewMock).not.toHaveBeenCalled()
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

    expect(screen.getByRole("button", { name: "View Progress" })).toBeDisabled()
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
      expect(openMock).toHaveBeenCalledWith(`${API_BASE_URL}/api/papers/paper-1/download?token=abc`, "_blank")
    })
  })

  it("shows a friendly message when the translated pdf is unavailable", async () => {
    usePaperDetailMock.mockReturnValue({
      paper: {
        id: "paper-1",
        source: "arxiv",
        arxiv_id: "2503.01010",
        title: "Detail Page Title",
        authors: ["Ada Lovelace"],
        categories: ["cs.AI"],
        abstract_raw: "Abstract body for the detail shell.",
        abstract_translated: "涓枃鎽樿",
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
    createCommunityPaperDownloadSessionMock.mockRejectedValue(new Error("Translated PDF not available"))

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByText("Detail Page Title")
    await userEvent.click(screen.getByRole("button", { name: "Download" }))

    expect(createCommunityPaperDownloadSessionMock).toHaveBeenCalledWith("paper-1")
    expect(openMock).not.toHaveBeenCalled()
    expect(
      await screen.findByText("This translated PDF is not compilable yet."),
    ).toBeInTheDocument()
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

  it("renders a generic fetch error state for non-404 failures", () => {
    usePaperDetailMock.mockReturnValue({
      paper: null,
      loading: false,
      error: "500",
      notFound: false,
    })

    render(
      <MemoryRouter initialEntries={["/paper/error-paper"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText("Unable to load paper details")).toBeInTheDocument()
  })

  it("renders publication links inside the abstract card as clickable anchors", async () => {
    usePaperDetailMock.mockReturnValue({
      paper: {
        id: "paper-1",
        source: "arxiv",
        arxiv_id: "2503.01010",
        title: "Detail Page Title",
        authors: ["Ada Lovelace"],
        categories: ["cs.AI"],
        abstract_raw: null,
        abstract_translated:
          "源代码[<https://github.com/NiuTrans/LaTeXTrans>]、在线演示平台[<https://latextrans.online>]及演示视频[<https://youtu.be/-ODRUTE-VU8>]均已公开。",
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

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    const githubLink = await screen.findByRole("link", {
      name: "https://github.com/NiuTrans/LaTeXTrans",
    })

    expect(githubLink).toHaveAttribute("href", "https://github.com/NiuTrans/LaTeXTrans")
    expect(
      screen.getByRole("link", { name: "https://latextrans.online" }),
    ).toHaveAttribute("href", "https://latextrans.online")
    expect(
      screen.getByRole("link", { name: "https://youtu.be/-ODRUTE-VU8" }),
    ).toHaveAttribute("href", "https://youtu.be/-ODRUTE-VU8")
  })

  it("renders the split reader workspace layout and removes legacy community-selection details", async () => {
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

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByText("preview.html")

    expect(screen.getByText("Reader workspace")).toBeInTheDocument()
    expect(screen.getByTestId("paper-detail-top-panels")).toBeInTheDocument()
    expect(screen.getByTestId("paper-detail-top-panels").className).toContain("1.95fr")
    expect(screen.getByTestId("paper-detail-reader-panel").className).toContain("min-h-[720px]")
    expect(screen.getByTestId("paper-preview-viewport")).toBeInTheDocument()
    expect(screen.queryByText("Community-selected version")).not.toBeInTheDocument()
    expect(screen.queryByText("Selected task")).not.toBeInTheDocument()
    expect(screen.queryByText("Selected asset")).not.toBeInTheDocument()
  })
})
