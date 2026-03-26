import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter, Route, Routes } from "react-router-dom"

import i18n from "@/i18n"
import PaperDetailPage from "@/pages/PaperDetail"

const usePaperDetailMock = vi.fn()
const translateCommunityPaperMock = vi.fn()
const createCommunityPaperDownloadSessionMock = vi.fn()
const getCommunityPaperPreviewMock = vi.fn()
const createCommunityAgentRunMock = vi.fn()
const streamCommunityAgentRunMock = vi.fn()
const importCommunityPaperMock = vi.fn()
const navigateMock = vi.fn()

vi.mock("@/hooks/use-paper-detail", () => ({
  usePaperDetail: (...args: unknown[]) => usePaperDetailMock(...args),
}))

vi.mock("@/lib/community-api", () => ({
  getCommunityPaperPreview: (...args: unknown[]) => getCommunityPaperPreviewMock(...args),
  translateCommunityPaper: (...args: unknown[]) => translateCommunityPaperMock(...args),
  createCommunityPaperDownloadSession: (...args: unknown[]) => createCommunityPaperDownloadSessionMock(...args),
  createCommunityAgentRun: (...args: unknown[]) => createCommunityAgentRunMock(...args),
  streamCommunityAgentRun: (...args: unknown[]) => streamCommunityAgentRunMock(...args),
  importCommunityPaper: (...args: unknown[]) => importCommunityPaperMock(...args),
}))

vi.mock("@/store/useStore", () => ({
  useStore: () => ({
    config: {
      source_language: "en",
      target_language: "zh",
      advanced_config: {},
    },
    loadUserSettings: vi.fn(),
    setTaskId: vi.fn(),
    setArxivId: vi.fn(),
  }),
}))

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom")
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

describe("PaperDetailPage reader-first", () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    await i18n.changeLanguage("en")
    createCommunityAgentRunMock.mockResolvedValue({
      run_id: "run-1",
      status: "completed",
      intent: "answer",
      summary: "Here is a concise Chinese explanation of the paper.",
      tool_trace: [
        {
          id: "trace-1",
          kind: "reasoning",
          label: "Reasoning provider",
          provider: "mock",
          status: "completed",
          detail: "Synthesized the paper context into a concise explanation.",
        },
      ],
      citations: [],
    })
    streamCommunityAgentRunMock.mockImplementation(
      async (
        _payload: unknown,
        options?: { onEvent?: (event: Record<string, unknown>) => void },
      ) => {
        const snapshot = {
          run_id: "run-stream-1",
          status: "completed",
          intent: "answer",
          mode: "chat",
          message: "Streamed paper-detail answer",
          summary: "Streamed paper-detail answer",
          citations: [],
          tool_trace: [],
          action: null,
        }
        options?.onEvent?.({
          type: "assistant_delta",
          run_id: "run-stream-1",
          sequence: 1,
          data: {
            delta: "Streamed ",
          },
        })
        options?.onEvent?.({
          type: "assistant_delta",
          run_id: "run-stream-1",
          sequence: 2,
          data: {
            delta: "paper-detail answer",
          },
        })
        options?.onEvent?.({
          type: "complete",
          run_id: "run-stream-1",
          sequence: 3,
          data: {
            snapshot,
          },
        })
        return snapshot
      },
    )
    usePaperDetailMock.mockReturnValue({
      paper: {
        id: "paper-1",
        source: "arxiv",
        arxiv_id: "2503.01010",
        title: "Detail Page Title",
        authors: ["Ada Lovelace"],
        categories: ["cs.AI"],
        abstract_raw: "English abstract",
        abstract_translated: null,
        community_status: "official",
        trans_status: "not_started",
        created_at: "2026-03-18T00:00:00Z",
        official_published_at: null,
        community_selected_task_id: null,
        community_selected_asset_id: null,
        latest_asset: null,
        assets: {},
      },
      preview: null,
      readerState: "unavailable",
      reader: {
        preferred_mode: "source",
        available_modes: ["source"],
        source: { kind: "source_html", html_content: null, url: "https://arxiv.org/abs/2503.01010" },
        translated: null,
        state: "source_ready",
      },
      experience: {
        stage_label: "已准备英文阅读",
        can_leave_hint: null,
        failure_type: null,
      },
      loading: false,
      error: null,
      notFound: false,
      refetch: vi.fn(),
    })
  })

  it("renders the status bar for the english reading state", async () => {
    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText("English reading is ready")).toBeInTheDocument()
    expect(screen.getByText("Reader workspace")).toBeInTheDocument()
    expect(screen.getByText("Agent workspace")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Explain in Chinese" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "One-line summary" })).toBeInTheDocument()
  })

  it("keeps the agent composer visible without static filler content blocks", async () => {
    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    const agentPanel = await screen.findByTestId("paper-detail-agent-panel")
    const panelQueries = within(agentPanel)

    expect(panelQueries.getByRole("textbox", { name: "Ask the paper agent" })).toBeInTheDocument()
    expect(panelQueries.getByRole("button", { name: "Run agent" })).toBeInTheDocument()
    expect(
      panelQueries.queryByText(
        "Keep a paper-aware assistant beside the reader so explanations, summaries, and follow-up actions never push the article away.",
      ),
    ).not.toBeInTheDocument()
    expect(panelQueries.queryByText("Preview HTML · preview.html")).not.toBeInTheDocument()
  })

  it("starts translation without jumping to the processing page", async () => {
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
      expect(translateCommunityPaperMock).toHaveBeenCalled()
    })

    expect(navigateMock).not.toHaveBeenCalledWith("/processing?taskId=task-new")
    expect(await screen.findByText("Generating the Chinese version")).toBeInTheDocument()
    expect(screen.getByText("You can keep reading. This page updates automatically when the Chinese version is ready.")).toBeInTheDocument()
  })

  it("runs a paper-aware agent shortcut inside the side panel", async () => {
    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await userEvent.click(screen.getByRole("button", { name: "Explain in Chinese" }))

    await waitFor(() => {
      expect(streamCommunityAgentRunMock).toHaveBeenCalledWith(
        expect.objectContaining({
          input: "Explain in Chinese",
          paper_id: "paper-1",
          mode: "chat",
          skill_toggles: {
            external_search: false,
          },
          context: expect.objectContaining({
            source: "paper_detail",
            current_mode: "source",
          }),
        }),
        expect.any(Object),
      )
    })

    expect(screen.getByText("Streamed paper-detail answer")).toBeInTheDocument()
  })

  it("supports explicit source and chinese mode switching when both readers are available", async () => {
    usePaperDetailMock.mockReturnValue({
      paper: {
        id: "paper-1",
        source: "arxiv",
        arxiv_id: "2503.01010",
        title: "Detail Page Title",
        authors: ["Ada Lovelace"],
        categories: ["cs.AI"],
        abstract_raw: "English abstract",
        abstract_translated: "Chinese abstract",
        community_status: "official",
        trans_status: "completed",
        created_at: "2026-03-18T00:00:00Z",
        official_published_at: null,
        community_selected_task_id: "task-1",
        community_selected_asset_id: "asset-1",
        latest_asset: {
          id: "asset-1",
          task_id: "task-1",
          asset_type: "preview_html",
          file_name: "preview.html",
          mime_type: "text/html",
          created_at: "2026-03-18T02:00:00Z",
        },
        assets: {},
      },
      preview: {
        paper_id: "paper-1",
        task_id: "task-1",
        asset: {
          id: "asset-1",
          task_id: "task-1",
          asset_type: "preview_html",
          file_name: "preview.html",
          mime_type: "text/html",
          created_at: "2026-03-18T02:00:00Z",
        },
        html_content: "<article><h2>Chinese HTML</h2><p>中文段落</p></article>",
        generated_at: "2026-03-18T02:00:00Z",
      },
      readerState: "ready",
      reader: {
        preferred_mode: "translated",
        available_modes: ["source", "translated"],
        source: {
          kind: "source_html",
          html_content: "<article><h2>English HTML</h2><p>English paragraph</p></article>",
          url: "https://arxiv.org/html/2503.01010",
        },
        translated: {
          kind: "preview_html",
          html_content: "<article><h2>Chinese HTML</h2><p>中文段落</p></article>",
          url: null,
        },
        state: "translated_ready",
      },
      experience: {
        stage_label: "translated_ready",
        can_leave_hint: null,
        failure_type: null,
      },
      loading: false,
      error: null,
      notFound: false,
      refetch: vi.fn(),
    })

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await userEvent.click(screen.getByTestId("paper-detail-mode-translated"))
    expect(screen.getByTestId("paper-detail-mode-translated")).toHaveAttribute("aria-pressed", "true")

    await userEvent.click(screen.getByTestId("paper-detail-mode-source"))
    expect(screen.getByTestId("paper-detail-mode-source")).toHaveAttribute("aria-pressed", "true")
    expect(await screen.findByText("English HTML")).toBeInTheDocument()
    expect(screen.getByText("English paragraph")).toBeInTheDocument()

    await userEvent.click(screen.getByRole("button", { name: "Explain in Chinese" }))

    await waitFor(() => {
      expect(streamCommunityAgentRunMock).toHaveBeenCalledWith(
        expect.objectContaining({
          input: "Explain in Chinese",
          paper_id: "paper-1",
          context: expect.objectContaining({
            source: "paper_detail",
            current_mode: "source",
          }),
        }),
        expect.any(Object),
      )
    })
  })

  it("uses the arxiv pdf fallback instead of embedding the raw arxiv html page", async () => {
    usePaperDetailMock.mockReturnValue({
      paper: {
        id: "paper-1",
        source: "arxiv",
        arxiv_id: "2508.18791",
        title: "Detail Page Title",
        authors: ["Ada Lovelace"],
        categories: ["cs.AI"],
        abstract_raw: "English abstract",
        abstract_translated: "Chinese abstract",
        community_status: "official",
        trans_status: "completed",
        created_at: "2026-03-18T00:00:00Z",
        official_published_at: null,
        community_selected_task_id: "task-1",
        community_selected_asset_id: "asset-1",
        latest_asset: {
          id: "asset-1",
          task_id: "task-1",
          asset_type: "preview_html",
          file_name: "preview.html",
          mime_type: "text/html",
          created_at: "2026-03-18T02:00:00Z",
        },
        assets: {},
      },
      preview: {
        paper_id: "paper-1",
        task_id: "task-1",
        asset: {
          id: "asset-1",
          task_id: "task-1",
          asset_type: "preview_html",
          file_name: "preview.html",
          mime_type: "text/html",
          created_at: "2026-03-18T02:00:00Z",
        },
        html_content: "<article><h2>Chinese HTML</h2><p>Chinese paragraph</p></article>",
        generated_at: "2026-03-18T02:00:00Z",
      },
      readerState: "ready",
      reader: {
        preferred_mode: "translated",
        available_modes: ["source", "translated"],
        source: {
          kind: "external_arxiv_html",
          html_content: null,
          url: "https://arxiv.org/html/2508.18791",
        },
        translated: {
          kind: "preview_html",
          html_content: "<article><h2>Chinese HTML</h2><p>Chinese paragraph</p></article>",
          url: null,
        },
        state: "translated_ready",
      },
      experience: {
        stage_label: "translated_ready",
        can_leave_hint: null,
        failure_type: null,
      },
      loading: false,
      error: null,
      notFound: false,
      refetch: vi.fn(),
    })

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await userEvent.click(screen.getByTestId("paper-detail-mode-source"))

    const pdfReader = await screen.findByTestId("paper-source-pdf-reader")
    expect(pdfReader).toHaveAttribute("src", "https://arxiv.org/pdf/2508.18791.pdf")
  })

  it("renders sanitized source html when the backend provides local html content", async () => {
    usePaperDetailMock.mockReturnValue({
      paper: {
        id: "paper-1",
        source: "arxiv",
        arxiv_id: "2503.01010",
        title: "Detail Page Title",
        authors: ["Ada Lovelace"],
        categories: ["cs.AI"],
        abstract_raw: "English abstract",
        abstract_translated: null,
        community_status: "official",
        trans_status: "not_started",
        created_at: "2026-03-18T00:00:00Z",
        official_published_at: null,
        community_selected_task_id: null,
        community_selected_asset_id: null,
        latest_asset: null,
        assets: {},
      },
      preview: null,
      readerState: "ready",
      reader: {
        preferred_mode: "source",
        available_modes: ["source"],
        source: {
          kind: "source_html",
          html_content: "<article><h2>Clean HTML</h2><p>Readable section.</p></article>",
          url: "https://arxiv.org/html/2503.01010",
        },
        translated: null,
        state: "source_ready",
      },
      experience: {
        stage_label: "已准备英文阅读",
        can_leave_hint: null,
        failure_type: null,
      },
      loading: false,
      error: null,
      notFound: false,
      refetch: vi.fn(),
    })

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText("Clean HTML")).toBeInTheDocument()
    expect(screen.getByText("Readable section.")).toBeInTheDocument()
  })

  it("keeps the desktop paper detail layout scroll-bound to the reader workspace", async () => {
    usePaperDetailMock.mockReturnValue({
      paper: {
        id: "paper-1",
        source: "arxiv",
        arxiv_id: "2503.01010",
        title: "Detail Page Title",
        authors: ["Ada Lovelace"],
        categories: ["cs.AI"],
        abstract_raw: "English abstract",
        abstract_translated: null,
        community_status: "official",
        trans_status: "not_started",
        created_at: "2026-03-18T00:00:00Z",
        official_published_at: null,
        community_selected_task_id: null,
        community_selected_asset_id: null,
        latest_asset: null,
        assets: {},
      },
      preview: null,
      readerState: "ready",
      reader: {
        preferred_mode: "source",
        available_modes: ["source"],
        source: {
          kind: "source_html",
          html_content: "<article><h1>Clean HTML</h1><p>Readable section.</p></article>",
          url: "https://arxiv.org/html/2503.01010",
        },
        translated: null,
        state: "source_ready",
      },
      experience: {
        stage_label: "English reading is ready",
        can_leave_hint: null,
        failure_type: null,
      },
      loading: false,
      error: null,
      notFound: false,
      refetch: vi.fn(),
    })

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    // 页面外壳不再锁定高度，允许整体滚动（移除了 overflow-hidden）
    expect((await screen.findByTestId("paper-detail-page-shell")).className).toContain("min-h-full")
    expect((await screen.findByTestId("paper-detail-page-shell")).className).not.toContain("overflow-hidden")
    // 阅读区面板内部仍有独立的滚动容器
    expect(screen.getByTestId("paper-source-reader").className).toContain("overflow-y-auto")
  })

  it("falls back to the source pdf reader when sanitized html is unavailable", async () => {
    usePaperDetailMock.mockReturnValue({
      paper: {
        id: "paper-1",
        source: "arxiv",
        arxiv_id: "2503.01010",
        title: "Detail Page Title",
        authors: ["Ada Lovelace"],
        categories: ["cs.AI"],
        abstract_raw: "English abstract",
        abstract_translated: null,
        community_status: "official",
        trans_status: "not_started",
        created_at: "2026-03-18T00:00:00Z",
        official_published_at: null,
        community_selected_task_id: null,
        community_selected_asset_id: null,
        latest_asset: null,
        assets: {},
      },
      preview: null,
      readerState: "ready",
      reader: {
        preferred_mode: "source",
        available_modes: ["source"],
        source: {
          kind: "source_pdf",
          html_content: null,
          url: "https://arxiv.org/pdf/2503.01010.pdf",
        },
        translated: null,
        state: "source_ready",
      },
      experience: {
        stage_label: "已准备英文阅读",
        can_leave_hint: null,
        failure_type: null,
      },
      loading: false,
      error: null,
      notFound: false,
      refetch: vi.fn(),
    })

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    const pdfReader = await screen.findByTestId("paper-source-pdf-reader")
    expect(pdfReader).toBeInTheDocument()
    expect(pdfReader).toHaveAttribute("src", "https://arxiv.org/pdf/2503.01010.pdf")
  })

  it("renders a translated pdf fallback panel when html preview is unavailable", async () => {
    usePaperDetailMock.mockReturnValue({
      paper: {
        id: "paper-1",
        source: "arxiv",
        arxiv_id: "2503.01010",
        title: "Detail Page Title",
        authors: ["Ada Lovelace"],
        categories: ["cs.AI"],
        abstract_raw: "English abstract",
        abstract_translated: "Chinese abstract",
        community_status: "official",
        trans_status: "failed",
        created_at: "2026-03-18T00:00:00Z",
        official_published_at: null,
        community_selected_task_id: "task-failed",
        community_selected_asset_id: "asset-pdf",
        latest_asset: {
          id: "asset-pdf",
          task_id: "task-failed",
          asset_type: "translated_pdf",
          file_name: "paper.pdf",
          mime_type: "application/pdf",
          created_at: "2026-03-18T02:00:00Z",
        },
        assets: {
          translated_pdf: {
            id: "asset-pdf",
            task_id: "task-failed",
            asset_type: "translated_pdf",
            file_name: "paper.pdf",
            mime_type: "application/pdf",
            created_at: "2026-03-18T02:00:00Z",
          },
        },
      },
      preview: null,
      readerState: "ready",
      reader: {
        preferred_mode: "translated",
        available_modes: ["source", "translated"],
        source: {
          kind: "external_arxiv_html",
          html_content: null,
          url: "https://arxiv.org/html/2503.01010",
        },
        translated: {
          kind: "translated_pdf",
          html_content: null,
          url: "/api/papers/paper-1/download-session",
        },
        state: "translated_ready",
      },
      experience: {
        stage_label: "中文版已准备好",
        can_leave_hint: null,
        failure_type: null,
      },
      loading: false,
      error: null,
      notFound: false,
      refetch: vi.fn(),
    })

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    const fallbackPanel = await screen.findByTestId("paper-translated-pdf-fallback")
    expect(fallbackPanel).toBeInTheDocument()
    expect(within(fallbackPanel).getByRole("button", { name: "Download" })).toBeInTheDocument()
  })

  it("keeps preview inside the reader shell instead of downloading translated pdf fallback", async () => {
    usePaperDetailMock.mockReturnValue({
      paper: {
        id: "paper-1",
        source: "arxiv",
        arxiv_id: "2503.01010",
        title: "Detail Page Title",
        authors: ["Ada Lovelace"],
        categories: ["cs.AI"],
        abstract_raw: "English abstract",
        abstract_translated: "Chinese abstract",
        community_status: "official",
        trans_status: "failed",
        created_at: "2026-03-18T00:00:00Z",
        official_published_at: null,
        community_selected_task_id: "task-failed",
        community_selected_asset_id: "asset-pdf",
        latest_asset: {
          id: "asset-pdf",
          task_id: "task-failed",
          asset_type: "translated_pdf",
          file_name: "paper.pdf",
          mime_type: "application/pdf",
          created_at: "2026-03-18T02:00:00Z",
        },
        assets: {
          translated_pdf: {
            id: "asset-pdf",
            task_id: "task-failed",
            asset_type: "translated_pdf",
            file_name: "paper.pdf",
            mime_type: "application/pdf",
            created_at: "2026-03-18T02:00:00Z",
          },
        },
      },
      preview: null,
      readerState: "ready",
      reader: {
        preferred_mode: "translated",
        available_modes: ["source", "translated"],
        source: {
          kind: "source_pdf",
          html_content: null,
          url: "https://arxiv.org/pdf/2503.01010.pdf",
        },
        translated: {
          kind: "translated_pdf",
          html_content: null,
          url: "/api/papers/paper-1/download-session",
        },
        state: "translated_ready",
      },
      experience: {
        stage_label: "Chinese reading is ready",
        can_leave_hint: null,
        failure_type: null,
      },
      loading: false,
      error: null,
      notFound: false,
      refetch: vi.fn(),
    })

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await userEvent.click(screen.getByRole("button", { name: "Preview" }))

    expect(await screen.findByTestId("paper-translated-pdf-fallback")).toBeInTheDocument()
    expect(createCommunityPaperDownloadSessionMock).not.toHaveBeenCalled()
  })

  it("prefers the html preview reader when a preview asset exists even if the detail payload omits preview content", async () => {
    getCommunityPaperPreviewMock.mockResolvedValue({
      paper_id: "paper-1",
      task_id: "task-preview",
      asset: {
        id: "asset-preview",
        task_id: "task-preview",
        asset_type: "preview_html",
        file_name: "preview.html",
        mime_type: "text/html",
        created_at: "2026-03-18T02:00:00Z",
      },
      html_content: "<article><h2>Recovered HTML</h2><p>Recovered preview body.</p></article>",
      generated_at: "2026-03-18T02:00:00Z",
    })

    usePaperDetailMock.mockReturnValue({
      paper: {
        id: "paper-1",
        source: "arxiv",
        arxiv_id: "2503.01010",
        title: "Detail Page Title",
        authors: ["Ada Lovelace"],
        categories: ["cs.AI"],
        abstract_raw: "English abstract",
        abstract_translated: "Chinese abstract",
        community_status: "official",
        trans_status: "completed",
        created_at: "2026-03-18T00:00:00Z",
        official_published_at: null,
        community_selected_task_id: "task-preview",
        community_selected_asset_id: "asset-preview",
        latest_asset: {
          id: "asset-preview",
          task_id: "task-preview",
          asset_type: "preview_html",
          file_name: "preview.html",
          mime_type: "text/html",
          created_at: "2026-03-18T02:00:00Z",
        },
        assets: {
          preview_html: {
            id: "asset-preview",
            task_id: "task-preview",
            asset_type: "preview_html",
            file_name: "preview.html",
            mime_type: "text/html",
            created_at: "2026-03-18T02:00:00Z",
          },
        },
      },
      preview: null,
      readerState: "ready",
      reader: {
        preferred_mode: "translated",
        available_modes: ["source", "translated"],
        source: {
          kind: "source_pdf",
          html_content: null,
          url: "https://arxiv.org/pdf/2503.01010.pdf",
        },
        translated: {
          kind: "preview_html",
          html_content: "<article><h2>Recovered HTML</h2><p>Recovered preview body.</p></article>",
          url: null,
        },
        state: "translated_ready",
      },
      experience: {
        stage_label: "Chinese version is ready",
        can_leave_hint: null,
        failure_type: null,
      },
      loading: false,
      error: null,
      notFound: false,
      refetch: vi.fn(),
    })

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await userEvent.click(screen.getByTestId("paper-detail-mode-translated"))

    expect(await screen.findByText("Recovered HTML")).toBeInTheDocument()
    expect(screen.queryByTestId("paper-translated-pdf-fallback")).not.toBeInTheDocument()
  })

  it("activates and highlights hash anchors after translated preview html resolves asynchronously", async () => {
    getCommunityPaperPreviewMock.mockImplementation(
      () =>
        new Promise((resolve) => {
          window.setTimeout(() => {
            resolve({
              paper_id: "paper-1",
              task_id: "task-preview",
              asset: {
                id: "asset-preview",
                task_id: "task-preview",
                asset_type: "preview_html",
                file_name: "preview.html",
                mime_type: "text/html",
                created_at: "2026-03-18T02:00:00Z",
              },
              html_content: "<article><h2 id=\"section-2\">Deferred section</h2><p>Loaded later.</p></article>",
              generated_at: "2026-03-18T02:00:00Z",
            })
          }, 20)
        }),
    )

    usePaperDetailMock.mockReturnValue({
      paper: {
        id: "paper-1",
        source: "arxiv",
        arxiv_id: "2503.01010",
        title: "Detail Page Title",
        authors: ["Ada Lovelace"],
        categories: ["cs.AI"],
        abstract_raw: "English abstract",
        abstract_translated: "Chinese abstract",
        community_status: "official",
        trans_status: "completed",
        created_at: "2026-03-18T00:00:00Z",
        official_published_at: null,
        community_selected_task_id: "task-preview",
        community_selected_asset_id: "asset-preview",
        latest_asset: {
          id: "asset-preview",
          task_id: "task-preview",
          asset_type: "preview_html",
          file_name: "preview.html",
          mime_type: "text/html",
          created_at: "2026-03-18T02:00:00Z",
        },
        assets: {
          preview_html: {
            id: "asset-preview",
            task_id: "task-preview",
            asset_type: "preview_html",
            file_name: "preview.html",
            mime_type: "text/html",
            created_at: "2026-03-18T02:00:00Z",
          },
        },
      },
      preview: null,
      readerState: "ready",
      reader: {
        preferred_mode: "translated",
        available_modes: ["source", "translated"],
        source: {
          kind: "source_html",
          html_content: "<article><h2>Source section</h2><p>Source content.</p></article>",
          url: "https://arxiv.org/html/2503.01010",
        },
        translated: {
          kind: "preview_html",
          html_content: null,
          url: null,
        },
        state: "translated_ready",
      },
      experience: {
        stage_label: "Chinese version is ready",
        can_leave_hint: null,
        failure_type: null,
      },
      loading: false,
      error: null,
      notFound: false,
      refetch: vi.fn(),
    })

    render(
      <MemoryRouter initialEntries={["/paper/paper-1#section-2"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(getCommunityPaperPreviewMock).toHaveBeenCalledWith("paper-1")
    })

    await waitFor(() => {
      const anchor = document.getElementById("section-2")
      expect(anchor).toBeInTheDocument()
      expect(anchor).toHaveAttribute("data-reader-anchor-active", "true")
    })
  })

  it("scrolls and highlights the local reader anchor when a citation points to the current paper", async () => {
    const scrollIntoViewMock = vi.fn()
    HTMLElement.prototype.scrollIntoView = scrollIntoViewMock

    streamCommunityAgentRunMock.mockImplementationOnce(
      async (_payload: unknown, options?: { onEvent?: (event: Record<string, unknown>) => void }) => {
        const snapshot = {
          run_id: "run-anchor",
          status: "completed",
          intent: "answer",
          mode: "chat",
          summary: "Anchor-aware response",
          message: "Anchor-aware response",
          tool_trace: [],
          citations: [
            {
              id: "citation-anchor",
              title: "Jump to introduction",
              source: "community",
              paper_id: "paper-1",
              anchor_id: "anchor-introduction",
            },
          ],
          action: null,
        }
        options?.onEvent?.({
          type: "complete",
          run_id: "run-anchor",
          sequence: 1,
          data: {
            snapshot,
          },
        })
        return snapshot
      },
    )

    usePaperDetailMock.mockReturnValue({
      paper: {
        id: "paper-1",
        source: "arxiv",
        arxiv_id: "2503.01010",
        title: "Detail Page Title",
        authors: ["Ada Lovelace"],
        categories: ["cs.AI"],
        abstract_raw: "English abstract",
        abstract_translated: null,
        community_status: "official",
        trans_status: "not_started",
        created_at: "2026-03-18T00:00:00Z",
        official_published_at: null,
        community_selected_task_id: null,
        community_selected_asset_id: null,
        latest_asset: null,
        assets: {},
      },
      preview: null,
      readerState: "ready",
      reader: {
        preferred_mode: "source",
        available_modes: ["source"],
        source: {
          kind: "source_html",
          html_content:
            "<article><h2 id=\"anchor-introduction\">Introduction</h2><p>Readable section.</p></article>",
          url: "https://arxiv.org/html/2503.01010",
        },
        translated: null,
        state: "source_ready",
      },
      experience: {
        stage_label: "English reading is ready",
        can_leave_hint: null,
        failure_type: null,
      },
      loading: false,
      error: null,
      notFound: false,
      refetch: vi.fn(),
    })

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await userEvent.click(screen.getByRole("button", { name: "Explain in Chinese" }))
    await userEvent.click(await screen.findByRole("button", { name: "Jump to introduction" }))

    expect(navigateMock).not.toHaveBeenCalled()
    expect(scrollIntoViewMock).toHaveBeenCalled()
    await waitFor(() => {
      const anchor = document.getElementById("anchor-introduction")
      expect(anchor).toHaveAttribute("data-reader-anchor-active", "true")
    })
  })

  it("keeps reader selection visibly highlighted and clears it when canceled", async () => {
    usePaperDetailMock.mockReturnValue({
      paper: {
        id: "paper-1",
        source: "arxiv",
        arxiv_id: "2503.01010",
        title: "Detail Page Title",
        authors: ["Ada Lovelace"],
        categories: ["cs.AI"],
        abstract_raw: "English abstract",
        abstract_translated: null,
        community_status: "official",
        trans_status: "not_started",
        created_at: "2026-03-18T00:00:00Z",
        official_published_at: null,
        community_selected_task_id: null,
        community_selected_asset_id: null,
        latest_asset: null,
        assets: {},
      },
      preview: null,
      readerState: "ready",
      reader: {
        preferred_mode: "source",
        available_modes: ["source"],
        source: {
          kind: "source_html",
          html_content:
            "<article><h2 id=\"section-context\">Context section</h2><p id=\"paragraph-context\">This paragraph explains how privacy-preserving localization works.</p></article>",
          url: "https://arxiv.org/html/2503.01010",
        },
        translated: null,
        state: "source_ready",
      },
      experience: {
        stage_label: "English reading is ready",
        can_leave_hint: null,
        failure_type: null,
      },
      loading: false,
      error: null,
      notFound: false,
      refetch: vi.fn(),
    })

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    const paragraph = await screen.findByText(
      "This paragraph explains how privacy-preserving localization works.",
    )
    const selection = window.getSelection()
    const range = document.createRange()
    range.selectNodeContents(paragraph)
    selection?.removeAllRanges()
    selection?.addRange(range)
    fireEvent.mouseUp(paragraph)

    await waitFor(() => {
      expect(paragraph).toHaveAttribute("data-reader-selection-active", "true")
    })

    await userEvent.click(screen.getByRole("button", { name: "Cancel" }))

    await waitFor(() => {
      expect(paragraph).not.toHaveAttribute("data-reader-selection-active")
    })
  })

  it("runs a true multi-turn paper chat and injects highlighted reader context", async () => {
    usePaperDetailMock.mockReturnValue({
      paper: {
        id: "paper-1",
        source: "arxiv",
        arxiv_id: "2503.01010",
        title: "Detail Page Title",
        authors: ["Ada Lovelace"],
        categories: ["cs.AI"],
        abstract_raw: "English abstract",
        abstract_translated: null,
        community_status: "official",
        trans_status: "not_started",
        created_at: "2026-03-18T00:00:00Z",
        official_published_at: null,
        community_selected_task_id: null,
        community_selected_asset_id: null,
        latest_asset: null,
        assets: {},
      },
      preview: null,
      readerState: "ready",
      reader: {
        preferred_mode: "source",
        available_modes: ["source"],
        source: {
          kind: "source_html",
          html_content:
            "<article><h2 id=\"section-context\">Context section</h2><p id=\"paragraph-context\">This paragraph explains how privacy-preserving localization works.</p></article>",
          url: "https://arxiv.org/html/2503.01010",
        },
        translated: null,
        state: "source_ready",
      },
      experience: {
        stage_label: "English reading is ready",
        can_leave_hint: null,
        failure_type: null,
      },
      loading: false,
      error: null,
      notFound: false,
      refetch: vi.fn(),
    })

    streamCommunityAgentRunMock
      .mockImplementationOnce(async (_payload: unknown, options?: { onEvent?: (event: Record<string, unknown>) => void }) => {
        const snapshot = {
          run_id: "run-stream-turn-1",
          status: "completed",
          intent: "answer",
          mode: "chat",
          message: "First answer from stream",
          summary: "First answer from stream",
          citations: [],
          tool_trace: [],
          action: null,
        }
        options?.onEvent?.({
          type: "complete",
          run_id: "run-stream-turn-1",
          sequence: 1,
          data: {
            snapshot,
          },
        })
        return snapshot
      })
      .mockImplementationOnce(async (_payload: unknown, options?: { onEvent?: (event: Record<string, unknown>) => void }) => {
        const snapshot = {
          run_id: "run-stream-turn-2",
          status: "completed",
          intent: "answer",
          mode: "chat",
          message: "Second answer from stream",
          summary: "Second answer from stream",
          citations: [],
          tool_trace: [],
          action: null,
        }
        options?.onEvent?.({
          type: "complete",
          run_id: "run-stream-turn-2",
          sequence: 1,
          data: {
            snapshot,
          },
        })
        return snapshot
      })

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    const paragraph = await screen.findByText(
      "This paragraph explains how privacy-preserving localization works.",
    )
    const selection = window.getSelection()
    const range = document.createRange()
    range.selectNodeContents(paragraph)
    selection?.removeAllRanges()
    selection?.addRange(range)
    fireEvent.mouseUp(paragraph)

    const chatInput = screen.getByLabelText("Ask the paper agent")
    await userEvent.type(chatInput, "这一段讲了什么？")
    await userEvent.click(screen.getByRole("button", { name: "Run agent" }))

    await screen.findByText("First answer from stream")

    await userEvent.clear(chatInput)
    await userEvent.type(chatInput, "再总结成一句话")
    await userEvent.click(screen.getByRole("button", { name: "Run agent" }))

    await screen.findByText("Second answer from stream")

    await waitFor(() => {
      expect(streamCommunityAgentRunMock).toHaveBeenCalledTimes(2)
    })

    expect(streamCommunityAgentRunMock).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({
        input: "这一段讲了什么？",
        paper_id: "paper-1",
        context: expect.objectContaining({
          source: "paper_detail",
          current_mode: "source",
          reader_selection: expect.objectContaining({
            text: "This paragraph explains how privacy-preserving localization works.",
            mode: "source",
          }),
        }),
      }),
      expect.any(Object),
    )

    expect(streamCommunityAgentRunMock).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({
        input: "再总结成一句话",
        paper_id: "paper-1",
        context: expect.objectContaining({
          source: "paper_detail",
          history: expect.arrayContaining([
            expect.objectContaining({
              role: "user",
              content: "这一段讲了什么？",
            }),
            expect.objectContaining({
              role: "assistant",
              content: "First answer from stream",
            }),
          ]),
        }),
      }),
      expect.any(Object),
    )
  })
})
