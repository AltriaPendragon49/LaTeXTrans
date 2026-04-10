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
const navigateMock = vi.fn()
const setTaskIdMock = vi.fn()
const setArxivIdMock = vi.fn()
const openMock = vi.fn()

vi.mock("@/hooks/use-paper-detail", () => ({
  usePaperDetail: (...args: unknown[]) => usePaperDetailMock(...args),
}))

vi.mock("@/lib/community-api", () => ({
  translateCommunityPaper: (...args: unknown[]) => translateCommunityPaperMock(...args),
  createCommunityPaperDownloadSession: (...args: unknown[]) =>
    createCommunityPaperDownloadSessionMock(...args),
}))

vi.mock("@/store/useStore", () => ({
  useStore: () => ({
    config: {
      source_language: "en",
      target_language: "zh",
      advanced_config: {},
    },
    setTaskId: setTaskIdMock,
    setArxivId: setArxivIdMock,
  }),
}))

vi.mock("@/components/community/PaperPreviewReader", () => ({
  PaperPreviewReader: ({ initialPreview }: { initialPreview?: { html_content?: string | null } | null }) => (
    <div data-testid="paper-preview-reader">{initialPreview?.html_content ?? "preview"}</div>
  ),
}))

vi.mock("dompurify", () => ({
  default: {
    sanitize: (value: string) => value,
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
  abstract_raw: "English abstract body.",
  abstract_translated: "中文摘要。",
  community_status: "official" as const,
  trans_status: "completed" as const,
  created_at: "2026-03-18T00:00:00Z",
  official_published_at: "2026-03-18T02:00:00Z",
  community_selected_task_id: "task-1",
  community_selected_asset_id: "asset-1",
  latest_asset: null,
  assets: {
    translated_pdf: {
      id: "asset-pdf",
      task_id: "task-1",
      asset_type: "translated_pdf",
      file_name: "paper.pdf",
      mime_type: "application/pdf",
      created_at: "2026-03-18T02:00:00Z",
    },
  },
  like_count: 2,
  favorite_count: 1,
  comment_count: 0,
  view_count: 10,
}

function buildDetailReturn(overrides?: Record<string, unknown>) {
  return {
    paper: basePaper,
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
      html_content: "<article><h2>Translated section</h2><p>Translated paragraph.</p></article>",
      generated_at: "2026-03-18T02:00:00Z",
    },
    readerState: "ready",
    reader: {
      preferred_mode: "translated",
      available_modes: ["source", "translated"],
      source: {
        kind: "source_html",
        html_content: "<article><h2>Source section</h2><p>English paragraph.</p></article>",
        url: "https://arxiv.org/html/2503.01010",
      },
      translated: {
        kind: "preview_html",
        html_content: "<article><h2>Translated section</h2><p>Translated paragraph.</p></article>",
        url: null,
      },
      state: "translated_ready",
    },
    experience: {
      stage_label: "Translated reading ready",
      can_leave_hint: null,
      failure_type: null,
    },
    structuredInsights: {
      state: "ready",
      sections: [
        {
          section_key: "problem",
          summary_en: "English problem summary",
          summary_zh: "中文问题摘要",
          bullets_en: ["English bullet"],
          bullets_zh: ["中文要点"],
          body_en: "English body",
          body_zh: "中文正文",
          updated_at: "2026-03-18T03:00:00Z",
        },
      ],
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
    Object.defineProperty(window, "open", {
      configurable: true,
      value: openMock,
    })
  })

  it("renders the reader shell and structured insights for completed papers", async () => {
    usePaperDetailMock.mockReturnValue(buildDetailReturn())

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByRole("heading", { level: 1, name: "Detail Page Title" })).toBeInTheDocument()
    expect(screen.getByTestId("paper-detail-reader-panel")).toBeInTheDocument()
    expect(screen.getByTestId("paper-detail-insights-panel")).toBeInTheDocument()
    expect(screen.getByText("Structured insights")).toBeInTheDocument()
    expect(screen.getByText("中文问题摘要")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Download" })).toBeEnabled()
  })

  it("preserves source pdf, translated html, and translated pdf preview modes", async () => {
    const user = userEvent.setup()
    usePaperDetailMock.mockReturnValue(
      buildDetailReturn({
        reader: {
          preferred_mode: "translated_html",
          available_modes: ["source", "translated_html", "translated_pdf"],
          source: {
            kind: "source_pdf",
            html_content: null,
            url: "https://arxiv.org/pdf/2503.01010",
          },
          translated: {
            kind: "preview_html",
            html_content: "<article><h2>Translated section</h2><p>Translated paragraph.</p></article>",
            url: null,
          },
          state: "translated_ready",
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

    expect(screen.getAllByRole("button", { name: "English" })).toHaveLength(2)
    expect(screen.getAllByRole("button", { name: "Chinese translation (HTML)" })).toHaveLength(2)
    expect(screen.getAllByRole("button", { name: "Chinese translation (PDF)" })).toHaveLength(2)
    expect(screen.getByTestId("paper-preview-reader")).toBeInTheDocument()

    await user.click(screen.getAllByRole("button", { name: "English" })[0])
    expect(screen.getByTestId("paper-source-pdf-reader")).toHaveAttribute(
      "src",
      `${API_BASE_URL}/api/papers/paper-1/source-pdf`,
    )

    await user.click(screen.getAllByRole("button", { name: "Chinese translation (PDF)" })[0])
    expect(screen.getByTestId("paper-translated-pdf-reader")).toHaveAttribute(
      "src",
      `${API_BASE_URL}/api/papers/paper-1/translated-pdf`,
    )
  })

  it("starts translation and routes to the processing page", async () => {
    const user = userEvent.setup()
    translateCommunityPaperMock.mockResolvedValue({
      paper_id: "paper-1",
      task_id: "task-new",
      status: "queued",
      reused_existing_task: false,
      processing_url: "/processing?taskId=task-new",
    })
    usePaperDetailMock.mockReturnValue(
      buildDetailReturn({
        paper: {
          ...basePaper,
          trans_status: "not_started",
          community_selected_task_id: null,
          assets: {},
        },
        preview: null,
        readerState: "ready",
        reader: {
          preferred_mode: "source",
          available_modes: ["source"],
          source: {
            kind: "source_html",
            html_content: "<article><p>English paragraph.</p></article>",
            url: "https://arxiv.org/html/2503.01010",
          },
          translated: null,
          state: "source_ready",
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

    await user.click(screen.getByRole("button", { name: "Translate" }))

    await waitFor(() => {
      expect(translateCommunityPaperMock).toHaveBeenCalledWith(
        "paper-1",
        expect.objectContaining({
          source_language: "en",
          target_language: "zh",
        }),
      )
    })
    expect(setTaskIdMock).toHaveBeenCalledWith("task-new")
    expect(setArxivIdMock).toHaveBeenCalledWith("2503.01010")
    expect(navigateMock).toHaveBeenCalledWith("/processing?taskId=task-new")
  })

  it("clicking view progress routes to the processing page for active tasks", async () => {
    const user = userEvent.setup()
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

    await user.click(screen.getByRole("button", { name: "View Progress" }))

    expect(setTaskIdMock).toHaveBeenCalledWith("task-1")
    expect(setArxivIdMock).toHaveBeenCalledWith("2503.01010")
    expect(navigateMock).toHaveBeenCalledWith("/processing?taskId=task-1")
  })

  it("download opens the signed url", async () => {
    const user = userEvent.setup()
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

    await user.click(screen.getByRole("button", { name: "Download" }))

    await waitFor(() => {
      expect(createCommunityPaperDownloadSessionMock).toHaveBeenCalledWith("paper-1")
      expect(openMock).toHaveBeenCalledWith(`${API_BASE_URL}/api/papers/paper-1/download?token=abc`, "_blank")
    })
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
      structuredInsights: null,
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
      structuredInsights: null,
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
})
