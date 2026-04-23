import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter, Route, Routes } from "react-router-dom"

import i18n from "@/i18n"
import PaperDetailPage from "@/pages/paper-detail"
import { setDesktopViewport, setMobileViewport } from "@/test/viewport"

const usePaperDetailMock = vi.fn()
const paperDetailReaderStoreState = vi.hoisted(() => ({
  config: {
    source_language: "en",
    target_language: "zh",
    advanced_config: {},
  },
  setTaskId: vi.fn(),
  setArxivId: vi.fn(),
}))

vi.mock("@/features/community-paper/hooks/use-paper-detail", () => ({
  usePaperDetail: (...args: unknown[]) => usePaperDetailMock(...args),
}))

vi.mock("@/features/community-paper/services/community-paper-api", () => ({
  translateCommunityPaper: vi.fn(),
  createCommunityPaperDownloadSession: vi.fn(),
  getCommunityPaperSimilar: vi.fn(() => Promise.resolve({ items: [] })),
  getCachedCommunityPaperDetail: vi.fn(() => null),
  getCommunityPaperDetail: vi.fn(),
  recordCommunityPaperView: vi.fn(),
}))

vi.mock("@/features/translation-workflow/store/useTranslationStore", () => ({
  useTranslationStore: (selector?: (state: typeof paperDetailReaderStoreState) => unknown) =>
    selector ? selector(paperDetailReaderStoreState) : paperDetailReaderStoreState,
}))

vi.mock("@/features/community-paper/components/PaperPreviewReader", () => ({
  PaperPreviewReader: ({ initialPreview }: { initialPreview?: { html_content?: string | null } | null }) => (
    <div
      data-testid="paper-preview-reader"
      dangerouslySetInnerHTML={{ __html: initialPreview?.html_content ?? "preview" }}
    />
  ),
}))

vi.mock("dompurify", () => ({
  default: {
    sanitize: (value: string) => value,
  },
}))

const zhGuideContent =
  "作者把方法拆成多个能够衔接的阶段来解释 pipeline，因此读者不需要回到论文原文也能快速理解整体工作方式。"

const detailPayload = {
  paper: {
    id: "paper-1",
    source: "arxiv",
    arxiv_id: "2503.01010",
    title: "Reader First Detail",
    authors: ["Ada Lovelace"],
    categories: ["cs.AI"],
    abstract_raw: "English abstract",
    abstract_translated: "中文摘要",
    community_status: "official",
    trans_status: "completed",
    created_at: "2026-03-18T00:00:00Z",
    official_published_at: null,
    community_selected_task_id: "task-1",
    community_selected_asset_id: "asset-1",
    latest_asset: null,
    assets: {
      translated_pdf: {
        id: "asset-pdf",
        task_id: "task-1",
        asset_type: "translated_pdf",
        file_name: "translated.pdf",
        mime_type: "application/pdf",
        created_at: "2026-03-18T02:00:00Z",
      },
    },
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
    html_content: "<article><h2>Translated section</h2><p>Translated paragraph.</p></article>",
    generated_at: "2026-03-18T02:00:00Z",
  },
  readerState: "ready" as const,
  reader: {
    preferred_mode: "translated" as const,
    available_modes: ["source", "translated"] as const,
    source: {
      kind: "source_html" as const,
      html_content: "<article><h2>Source section</h2><p>English paragraph.</p></article>",
      url: "https://arxiv.org/html/2503.01010",
    },
    translated: {
      kind: "preview_html" as const,
      html_content: "<article><h2>Translated section</h2><p>Translated paragraph.</p></article>",
      url: null,
    },
    state: "translated_ready" as const,
  },
  experience: {
    stage_label: "Translated reading ready",
    can_leave_hint: null,
    failure_type: null,
  },
  loading: false,
  error: null,
  notFound: false,
  refetch: vi.fn(),
}

describe("PaperDetailPage reader-first", () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    vi.useRealTimers()
    await i18n.changeLanguage("en")
    setDesktopViewport()
  })

  it("keeps the five-module chinese guide stable when the reader mode changes", async () => {
    const user = userEvent.setup()
    usePaperDetailMock.mockReturnValue({
      ...detailPayload,
      structuredInsights: {
        state: "ready",
        sections: [
          {
            section_key: "solution",
            content: zhGuideContent,
            updated_at: "2026-03-18T03:00:00Z",
          },
        ],
      },
    })

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText(i18n.t("community.detail.insights.section.solution"))).toBeInTheDocument()
    expect(screen.queryByText(zhGuideContent)).not.toBeInTheDocument()

    await user.click(screen.getByTestId("paper-detail-mode-source"))
    await user.click(screen.getByText(i18n.t("community.detail.insights.section.solution")))

    expect(screen.getByText(zhGuideContent)).toBeInTheDocument()
    expect(screen.getByTestId("paper-source-pdf-reader")).toBeInTheDocument()
  })

  it("shows a pending placeholder while the five-module guide is still processing", () => {
    usePaperDetailMock.mockReturnValue({
      ...detailPayload,
      structuredInsights: {
        state: "processing",
        sections: [],
      },
    })

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText("Structured insights are still being prepared")).toBeInTheDocument()
    expect(
      screen.getByText("This paper will appear in the public library only after the full-paper Chinese analysis modules finish."),
    ).toBeInTheDocument()
  })

  it("shows an empty placeholder when no structured insights are available yet", () => {
    usePaperDetailMock.mockReturnValue({
      ...detailPayload,
      structuredInsights: null,
    })

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText("Structured insights are unavailable")).toBeInTheDocument()
    expect(
      screen.getByText("The reader is available, but this paper does not have a persisted Chinese insight package yet."),
    ).toBeInTheDocument()
  })

  it("defaults mobile reading to the translated single-document view instead of bilingual compare", () => {
    setMobileViewport()
    usePaperDetailMock.mockReturnValue({
      ...detailPayload,
      structuredInsights: null,
    })

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByTestId("paper-translated-pdf-reader")).toBeInTheDocument()
    expect(screen.queryByTestId("paper-bilingual-source-pdf-reader")).not.toBeInTheDocument()
    expect(screen.queryByTestId("paper-bilingual-translated-pdf-reader")).not.toBeInTheDocument()
  })

  it("immerses mobile readers into a full-bleed translated PDF viewport and auto-focuses it", async () => {
    vi.useFakeTimers()
    const scrollIntoViewMock = vi.fn()
    HTMLElement.prototype.scrollIntoView = scrollIntoViewMock
    setMobileViewport()
    usePaperDetailMock.mockReturnValue({
      ...detailPayload,
      structuredInsights: null,
    })

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    vi.runAllTimers()

    expect(scrollIntoViewMock).toHaveBeenCalled()
    expect(screen.getByTestId("paper-detail-page-shell")).toHaveAttribute("data-mobile-shell", "immersive")
    expect(screen.getByTestId("paper-detail-reader-panel")).toHaveAttribute("data-mobile-reader-viewport", "immersive")
    expect(screen.getByTestId("paper-translated-pdf-reader")).toHaveClass("w-full")
    expect(screen.getByTestId("paper-translated-pdf-reader")).not.toHaveClass("w-[60%]")
  })

  it("lets mobile readers jump from the pdf viewport into the analysis panel", async () => {
    const user = userEvent.setup()
    const scrollIntoViewMock = vi.fn()
    HTMLElement.prototype.scrollIntoView = scrollIntoViewMock
    setMobileViewport()
    usePaperDetailMock.mockReturnValue({
      ...detailPayload,
      structuredInsights: null,
    })

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.queryByTestId("mobile-reader-collapse-button")).not.toBeInTheDocument()

    await user.click(screen.getByTestId("mobile-analysis-jump-button"))

    expect(screen.getByTestId("paper-detail-reader-panel")).toHaveAttribute("data-mobile-reader-viewport", "collapsed")
    expect(scrollIntoViewMock).toHaveBeenCalled()
  })

  it("lets mobile readers return from the analysis panel to the immersive reader", async () => {
    const user = userEvent.setup()
    const scrollIntoViewMock = vi.fn()
    HTMLElement.prototype.scrollIntoView = scrollIntoViewMock
    setMobileViewport()
    usePaperDetailMock.mockReturnValue({
      ...detailPayload,
      structuredInsights: null,
    })

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await user.click(screen.getByTestId("mobile-analysis-jump-button"))
    expect(screen.getByTestId("paper-detail-reader-panel")).toHaveAttribute("data-mobile-reader-viewport", "collapsed")

    expect(screen.getByTestId("mobile-analysis-collapse-button")).toHaveClass("bg-[color:var(--px-shell-accent)]")

    await user.click(screen.getByRole("button", { name: "Back to reader" }))

    expect(screen.getByTestId("paper-detail-reader-panel")).toHaveAttribute("data-mobile-reader-viewport", "immersive")
    expect(scrollIntoViewMock).toHaveBeenCalled()
  })
})
