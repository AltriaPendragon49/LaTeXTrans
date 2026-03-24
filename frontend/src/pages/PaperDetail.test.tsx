import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter, Route, Routes } from "react-router-dom"

import { API_BASE_URL } from "@/api-base"
import i18n from "@/i18n"
import PaperDetailPage from "@/pages/PaperDetail"

const usePaperDetailMock = vi.fn()
const translateCommunityPaperMock = vi.fn()
const createCommunityPaperDownloadSessionMock = vi.fn()
const getCommunityPaperPreviewMock = vi.fn()
const createCommunityAgentRunMock = vi.fn()
const importCommunityPaperMock = vi.fn()
const loadUserSettingsMock = vi.fn()
const setTaskIdMock = vi.fn()
const setArxivIdMock = vi.fn()
const navigateMock = vi.fn()
const katexRenderToStringMock = vi.fn((value: string) => `<span class="katex">${value}</span>`)
const scrollIntoViewMock = vi.fn()
const openMock = vi.fn()

vi.mock("@/hooks/use-paper-detail", () => ({
  usePaperDetail: (...args: unknown[]) => usePaperDetailMock(...args),
}))

vi.mock("@/lib/community-api", () => ({
  getCommunityPaperPreview: (...args: unknown[]) => getCommunityPaperPreviewMock(...args),
  translateCommunityPaper: (...args: unknown[]) => translateCommunityPaperMock(...args),
  createCommunityPaperDownloadSession: (...args: unknown[]) => createCommunityPaperDownloadSessionMock(...args),
  createCommunityAgentRun: (...args: unknown[]) => createCommunityAgentRunMock(...args),
  importCommunityPaper: (...args: unknown[]) => importCommunityPaperMock(...args),
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

const basePaper = {
  id: "paper-1",
  source: "arxiv" as const,
  arxiv_id: "2503.01010",
  title: "Detail Page Title",
  authors: ["Ada Lovelace"],
  categories: ["cs.AI"],
  abstract_raw: "Abstract body for the detail shell.",
  abstract_translated: "Translated abstract body.",
  community_status: "official" as const,
  trans_status: "completed" as const,
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
    translated_pdf: {
      id: "asset-pdf",
      task_id: "task-1",
      asset_type: "translated_pdf",
      file_name: "paper.pdf",
      mime_type: "application/pdf",
      created_at: "2026-03-18T02:00:00Z",
    },
  },
  like_count: 7,
  favorite_count: 3,
  comment_count: 2,
  view_count: 21,
}

const translatedPreview = {
  paper_id: "paper-1",
  task_id: "task-1",
  asset: basePaper.latest_asset,
  html_content: "<article><h2>Translated section</h2><p>Translated paragraph.</p></article>",
  generated_at: "2026-03-18T02:00:00Z",
}

const translatedReader = {
  preferred_mode: "translated" as const,
  available_modes: ["source", "translated"] as const,
  source: {
    kind: "source_pdf" as const,
    html_content: null,
    url: "https://arxiv.org/pdf/2503.01010.pdf",
  },
  translated: {
    kind: "preview_html" as const,
    html_content: translatedPreview.html_content,
    url: null,
  },
  state: "translated_ready" as const,
}

function buildDetailReturn(overrides?: Record<string, unknown>) {
  return {
    paper: basePaper,
    preview: translatedPreview,
    readerState: "ready",
    reader: translatedReader,
    experience: {
      stage_label: "中文版已准备好",
      can_leave_hint: null,
      failure_type: null,
    },
    loading: false,
    error: null,
    notFound: false,
    refetch: vi.fn(),
    ...overrides,
  }
}

describe("PaperDetailPage", () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    await i18n.changeLanguage("en")
    getCommunityPaperPreviewMock.mockResolvedValue(translatedPreview)
    loadUserSettingsMock.mockResolvedValue(undefined)
    Object.defineProperty(window, "open", {
      configurable: true,
      value: openMock,
    })
    Element.prototype.scrollIntoView = scrollIntoViewMock
    HTMLElement.prototype.scrollIntoView = scrollIntoViewMock
  })

  it("renders header metadata, disables repeat translation for completed papers, and keeps download available", async () => {
    usePaperDetailMock.mockReturnValue(buildDetailReturn())

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByRole("heading", { level: 1, name: "Detail Page Title" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Translate" })).toBeDisabled()
    expect(screen.getByRole("button", { name: "Download" })).toBeEnabled()
    expect(screen.getByTestId("paper-detail-header-metadata")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /Original source/ })).toHaveAttribute(
      "href",
      "https://arxiv.org/abs/2503.01010",
    )
    expect(screen.queryByText("Official")).not.toBeInTheDocument()
    expect(screen.queryByLabelText("21 views")).not.toBeInTheDocument()
    expect(screen.queryByLabelText("7 likes")).not.toBeInTheDocument()
    expect(screen.queryByLabelText("3 favorites")).not.toBeInTheDocument()
    expect(screen.queryByLabelText("2 comments")).not.toBeInTheDocument()
    expect(await screen.findByText("Translated paragraph.")).toBeInTheDocument()
  })

  it("uses preview bootstrap from the detail payload when the reader is ready", async () => {
    usePaperDetailMock.mockReturnValue(buildDetailReturn())

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText("Translated paragraph.")).toBeInTheDocument()
    expect(getCommunityPaperPreviewMock).not.toHaveBeenCalled()
  })

  it("renders a warming state when the preview is not ready yet", async () => {
    usePaperDetailMock.mockReturnValue(
      buildDetailReturn({
        preview: null,
        readerState: "warming",
        reader: {
          ...translatedReader,
          available_modes: ["translated"],
          source: null,
          translated: {
            kind: "preview_html",
            html_content: null,
            url: null,
          },
          state: "warming",
        },
        experience: {
          stage_label: "正在生成中文版本",
          can_leave_hint: "You can keep reading while the Chinese version is prepared.",
          failure_type: null,
        },
      }),
    )

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText("Translated reader is warming up")).toBeInTheDocument()
    expect(
      await screen.findByText(
        "The paper metadata is ready, and the reading view is being prepared in the background. Check back shortly.",
      ),
    ).toBeInTheDocument()
    expect(getCommunityPaperPreviewMock).not.toHaveBeenCalled()
  })

  it("clicking view progress still routes to the processing page for active tasks", async () => {
    usePaperDetailMock.mockReturnValue(
      buildDetailReturn({
        paper: {
          ...basePaper,
          trans_status: "processing",
        },
      }),
    )

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await userEvent.click(screen.getByRole("button", { name: "View Progress" }))

    expect(setTaskIdMock).toHaveBeenCalledWith("task-1")
    expect(setArxivIdMock).toHaveBeenCalledWith("2503.01010")
    expect(navigateMock).toHaveBeenCalledWith("/processing?taskId=task-1")
  })

  it("clicking preview focuses the inline reader and download opens the signed url", async () => {
    usePaperDetailMock.mockReturnValue(buildDetailReturn())
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

    await screen.findByText("Translated paragraph.")
    await userEvent.click(screen.getByRole("button", { name: "Preview" }))
    await userEvent.click(screen.getByRole("button", { name: "Download" }))

    expect(scrollIntoViewMock).toHaveBeenCalled()
    await waitFor(() => {
      expect(createCommunityPaperDownloadSessionMock).toHaveBeenCalledWith("paper-1")
      expect(openMock).toHaveBeenCalledWith(`${API_BASE_URL}/api/papers/paper-1/download?token=abc`, "_blank")
    })
  })

  it("shows a friendly message when the translated pdf is unavailable", async () => {
    usePaperDetailMock.mockReturnValue(
      buildDetailReturn({
        preview: null,
        reader: {
          ...translatedReader,
          available_modes: ["translated"],
          source: null,
          translated: {
            kind: "translated_pdf",
            html_content: null,
            url: "/api/papers/paper-1/download-session",
          },
        },
      }),
    )
    createCommunityPaperDownloadSessionMock.mockRejectedValue(new Error("Translated PDF not available"))

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByRole("heading", { level: 1, name: "Detail Page Title" })
    await userEvent.click(screen.getAllByRole("button", { name: "Download" })[0])

    expect(createCommunityPaperDownloadSessionMock).toHaveBeenCalledWith("paper-1")
    expect(openMock).not.toHaveBeenCalled()
    expect(await screen.findByText("This translated PDF is not compilable yet.")).toBeInTheDocument()
  })

  it("renders a not-found state", () => {
    usePaperDetailMock.mockReturnValue({
      paper: null,
      loading: false,
      error: "404",
      notFound: true,
      preview: null,
      readerState: "unavailable",
      reader: null,
      experience: null,
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

  it("renders an error state", () => {
    usePaperDetailMock.mockReturnValue({
      paper: null,
      loading: false,
      error: "boom",
      notFound: false,
      preview: null,
      readerState: "unavailable",
      reader: null,
      experience: null,
    })

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText("Unable to load paper details")).toBeInTheDocument()
    expect(screen.getByText("boom")).toBeInTheDocument()
  })

  it("renders the split reader workspace layout and removes legacy community-selection details", async () => {
    window.innerWidth = 1440
    window.dispatchEvent(new Event("resize"))
    usePaperDetailMock.mockReturnValue(buildDetailReturn())

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
    expect(screen.getByTestId("paper-detail-top-panels").style.gridTemplateColumns).toContain("fr")
    expect(screen.getByTestId("paper-detail-reader-panel").className).toContain("min-h-[760px]")
    expect(screen.getByTestId("paper-detail-resize-handle")).toBeInTheDocument()
    expect(screen.getByTestId("paper-preview-viewport")).toBeInTheDocument()
    expect(screen.queryByText("Community-selected version")).not.toBeInTheDocument()
    expect(screen.queryByText("Selected task")).not.toBeInTheDocument()
    expect(screen.queryByText("Selected asset")).not.toBeInTheDocument()
  })
})
