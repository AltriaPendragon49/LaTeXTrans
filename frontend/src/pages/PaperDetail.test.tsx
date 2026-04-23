import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter, Route, Routes } from "react-router-dom"

import { API_BASE_URL } from "@/api-base"
import i18n from "@/i18n"
import PaperDetailPage from "@/pages/paper-detail"
import { setDesktopViewport, setMobileViewport } from "@/test/viewport"

const usePaperDetailMock = vi.fn()
const translateCommunityPaperMock = vi.fn()
const createCommunityPaperDownloadSessionMock = vi.fn()
const likeCommunityPaperMock = vi.fn()
const unlikeCommunityPaperMock = vi.fn()
const getCommunityPaperSimilarMock = vi.fn()
const toastSuccessMock = vi.hoisted(() => vi.fn())
const toastErrorMock = vi.hoisted(() => vi.fn())
const navigateMock = vi.fn()
const setTaskIdMock = vi.fn()
const setArxivIdMock = vi.fn()
const openMock = vi.fn()
const clipboardWriteTextMock = vi.fn()
const paperDetailStoreState = {
  config: {
    source_language: "en",
    target_language: "zh",
    advanced_config: {},
  },
  setTaskId: setTaskIdMock,
  setArxivId: setArxivIdMock,
}

vi.mock("@/features/community-paper/hooks/use-paper-detail", () => ({
  usePaperDetail: (...args: unknown[]) => usePaperDetailMock(...args),
}))

vi.mock("@/features/community-paper/services/community-paper-api", () => ({
  translateCommunityPaper: (...args: unknown[]) => translateCommunityPaperMock(...args),
  createCommunityPaperDownloadSession: (...args: unknown[]) =>
    createCommunityPaperDownloadSessionMock(...args),
  likeCommunityPaper: (...args: unknown[]) => likeCommunityPaperMock(...args),
  unlikeCommunityPaper: (...args: unknown[]) => unlikeCommunityPaperMock(...args),
  getCommunityPaperSimilar: (...args: unknown[]) => getCommunityPaperSimilarMock(...args),
  getCachedCommunityPaperDetail: vi.fn(() => null),
  getCommunityPaperDetail: vi.fn(),
  recordCommunityPaperView: vi.fn(),
}))

vi.mock("@/features/translation-workflow/store/useTranslationStore", () => ({
  useTranslationStore: (selector?: (state: typeof paperDetailStoreState) => unknown) =>
    selector ? selector(paperDetailStoreState) : paperDetailStoreState,
}))

vi.mock("dompurify", () => ({
  default: {
    sanitize: (value: string) => value,
  },
}))

vi.mock("sonner", () => ({
  toast: {
    success: toastSuccessMock,
    error: toastErrorMock,
  },
}))

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom")
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    isAuthenticated: true,
    user: { id: "user-1" },
    session: null,
    loading: false,
    error: null,
    isAuthAvailable: true,
    signIn: vi.fn(),
    signUp: vi.fn(),
    verifyOtp: vi.fn(),
    signOut: vi.fn(),
    clearError: vi.fn(),
  }),
}))

const basePaper = {
  id: "paper-1",
  source: "arxiv" as const,
  arxiv_id: "2503.01010",
  title: "Detail Page Title",
  authors: ["Ada Lovelace"],
  categories: ["cs.AI"],
  abstract_raw: "English abstract body.",
  abstract_translated: "这是一段中文摘要，用来支持结构化导读模块展示。",
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

const problemContent =
  "论文聚焦复杂 LaTeX 文档翻译任务中的结构损坏问题，并解释了为什么这一问题会直接影响科研协作效率。"
const solutionContent =
  "作者将解析、翻译和重组拆为可衔接的流程阶段，形成清晰 pipeline，使读者能理解各阶段如何协同完成最终输出。"
const innovationContent =
  "创新点在于把多智能体协作与结构保持策略深度绑定，不是简单复用传统端到端翻译，而是强调复杂项目可编译性。"
const experimentContent =
  "实验覆盖多类文档与多项指标，并通过对照设置验证方案在结构保真和可读性上的提升，支撑方法有效性的核心结论。"
const futureContent =
  "论文指出可从长文档鲁棒性、跨领域迁移与自动纠错方向继续扩展，同时对后续科研写作工具研究有启发意义。"
const structuredProblemContent = `LaTeX文档翻译的核心难点在于同时保持语义准确性和文档可编译性。

问题本质
LaTeX文档将自然语言与数学公式、表格和交叉引用等结构深度交织，使翻译不仅是语言转换，还涉及结构解析。

现有方法的局限
主流机器翻译系统缺乏对LaTeX语法结构的理解，无法处理嵌套元素和命令依赖关系，导致翻译后出现格式错乱、符号误译或引用失效等问题。

为什么重要
LaTeX是学术界主流排版系统，翻译质量直接影响论文的可读性和可传播性。`

const inlineStructuredProblemContent =
  "This paper studies LaTeX document translation while preserving semantics and compileability. " +
  "\u95ee\u9898\u672c\u8d28\uff1aLaTeX documents mix natural language with formulas, tables, and references. " +
  "\u73b0\u6709\u65b9\u6cd5\u7684\u5c40\u9650\uff1aGeneral-purpose MT systems often break commands, cross-references, and terminology consistency. " +
  "\u4e3a\u4ec0\u4e48\u91cd\u8981\uff1aResearchers need translations that remain readable, faithful, and directly compilable."
const inlineSpaceSeparatedSolutionContent =
  "This workflow coordinates multiple agents to preserve LaTeX structure during translation. " +
  "\u6838\u5fc3\u601d\u8def LaTeXTrans decomposes translation into specialized agents that each handle one part of the pipeline. " +
  "\u5173\u952e\u6d41\u7a0b The parser isolates protected LaTeX units before translation and the generator rebuilds the final document. " +
  "\u6a21\u5757\u534f\u540c The validator, summarizer, and terminology extractor feed corrections back into the translation loop."

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
      available_modes: ["source", "translated_pdf", "bilingual_compare"],
      source: {
        kind: "source_pdf",
        html_content: null,
        url: "https://arxiv.org/pdf/2503.01010",
      },
      translated: {
        kind: "translated_pdf",
        html_content: null,
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
          content: problemContent,
          updated_at: "2026-03-18T03:00:00Z",
        },
        {
          section_key: "solution",
          content: solutionContent,
          updated_at: "2026-03-18T03:00:00Z",
        },
        {
          section_key: "innovation",
          content: innovationContent,
          updated_at: "2026-03-18T03:00:00Z",
        },
        {
          section_key: "experiment",
          content: experimentContent,
          updated_at: "2026-03-18T03:00:00Z",
        },
        {
          section_key: "future",
          content: futureContent,
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
    setDesktopViewport()
    getCommunityPaperSimilarMock.mockResolvedValue({ items: [] })
    likeCommunityPaperMock.mockResolvedValue({
      paper_id: "paper-1",
      liked: true,
      like_count: 3,
    })
    unlikeCommunityPaperMock.mockResolvedValue({
      paper_id: "paper-1",
      liked: false,
      like_count: 1,
    })
    Object.defineProperty(window, "open", {
      configurable: true,
      value: openMock,
    })
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: clipboardWriteTextMock,
      },
    })
    clipboardWriteTextMock.mockResolvedValue(undefined)
  })

  it("renders the reader shell, minimal toolbar, and five guide modules for completed papers", async () => {
    usePaperDetailMock.mockReturnValue(buildDetailReturn())

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.queryByRole("heading", { level: 1, name: "Detail Page Title" })).not.toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Back to feed" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Like paper" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Like paper" })).toHaveTextContent("2")
    expect(screen.getByRole("button", { name: "Favorite paper" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Download translated PDF" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Paper information" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Copy paper link" })).toBeInTheDocument()
    expect(screen.getByTestId("paper-detail-reader-panel")).toBeInTheDocument()
    expect(screen.getByTestId("paper-detail-insights-panel")).toBeInTheDocument()
    expect(screen.queryByText("Translated reader")).not.toBeInTheDocument()
    expect(screen.queryByText("Detail Page Title")).not.toBeInTheDocument()
    expect(screen.queryByText("Ada Lovelace")).not.toBeInTheDocument()
    expect(screen.getByRole("tab", { name: "Paper analysis" })).toBeInTheDocument()
    expect(screen.getByText(i18n.t("community.detail.insights.section.problem"))).toBeInTheDocument()
    expect(screen.getByText(i18n.t("community.detail.insights.section.solution"))).toBeInTheDocument()
    expect(screen.getByText(i18n.t("community.detail.insights.section.innovation"))).toBeInTheDocument()
    expect(screen.getByText(i18n.t("community.detail.insights.section.experiment"))).toBeInTheDocument()
    expect(screen.getByText(i18n.t("community.detail.insights.section.future"))).toBeInTheDocument()
    await userEvent.setup().click(screen.getByText(i18n.t("community.detail.insights.section.problem")))
    expect(screen.getByText(problemContent)).toBeInTheDocument()
    expect(screen.getByTestId("paper-bilingual-source-pdf-reader")).toHaveAttribute(
      "src",
      "https://arxiv.org/pdf/2503.01010#page=1&view=FitH&pagemode=none&toolbar=0&navpanes=0&scrollbar=0",
    )
    expect(screen.getByTestId("paper-bilingual-translated-pdf-reader")).toHaveAttribute(
      "src",
      `${API_BASE_URL}/api/papers/paper-1/translated-pdf#page=1&view=FitH&pagemode=none&toolbar=0&navpanes=0&scrollbar=0`,
    )
  })

  it("renders light structured insight content with summary and titled subsections", async () => {
    usePaperDetailMock.mockReturnValue(
      buildDetailReturn({
        structuredInsights: {
          state: "ready",
          sections: [
            {
              section_key: "problem",
              content: structuredProblemContent,
              updated_at: "2026-03-18T03:00:00Z",
            },
          ],
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

    await userEvent.setup().click(screen.getByText(i18n.t("community.detail.insights.section.problem")))
    expect(screen.getByText("LaTeX文档翻译的核心难点在于同时保持语义准确性和文档可编译性。")).toBeInTheDocument()
    expect(screen.getByText("问题本质")).toBeInTheDocument()
    expect(screen.getByText("现有方法的局限")).toBeInTheDocument()
    expect(screen.getByText("为什么重要")).toBeInTheDocument()
    expect(screen.getByText(/LaTeX文档将自然语言与数学公式/)).toBeInTheDocument()
  })

  it("parses inline titled insight content from a single long paragraph", async () => {
    usePaperDetailMock.mockReturnValue(
      buildDetailReturn({
        structuredInsights: {
          state: "ready",
          sections: [
            {
              section_key: "problem",
              content: inlineStructuredProblemContent,
              updated_at: "2026-03-18T03:00:00Z",
            },
          ],
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

    await userEvent.setup().click(screen.getByText(i18n.t("community.detail.insights.section.problem")))
    expect(
      screen.getByText(/This paper studies LaTeX document translation while preserving semantics/),
    ).toBeInTheDocument()
    expect(screen.getByText("\u95ee\u9898\u672c\u8d28")).toBeInTheDocument()
    expect(screen.getByText("\u73b0\u6709\u65b9\u6cd5\u7684\u5c40\u9650")).toBeInTheDocument()
    expect(screen.getByText("\u4e3a\u4ec0\u4e48\u91cd\u8981")).toBeInTheDocument()
    expect(screen.getByText(/mix natural language with formulas, tables, and references/)).toBeInTheDocument()
    expect(
      screen.getByText(/General-purpose MT systems often break commands, cross-references/),
    ).toBeInTheDocument()
    expect(screen.getByText(/translations that remain readable, faithful, and directly compilable/)).toBeInTheDocument()
  })

  it("parses inline titled insight content when labels are separated by spaces instead of colons", async () => {
    usePaperDetailMock.mockReturnValue(
      buildDetailReturn({
        structuredInsights: {
          state: "ready",
          sections: [
            {
              section_key: "solution",
              content: inlineSpaceSeparatedSolutionContent,
              updated_at: "2026-03-18T03:00:00Z",
            },
          ],
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

    await userEvent.setup().click(screen.getByText(i18n.t("community.detail.insights.section.solution")))
    expect(
      screen.getByText(/This workflow coordinates multiple agents to preserve LaTeX structure/),
    ).toBeInTheDocument()
    expect(screen.getByText("\u6838\u5fc3\u601d\u8def")).toBeInTheDocument()
    expect(screen.getByText("\u5173\u952e\u6d41\u7a0b")).toBeInTheDocument()
    expect(screen.getByText("\u6a21\u5757\u534f\u540c")).toBeInTheDocument()
    expect(
      screen.getByText(/decomposes translation into specialized agents that each handle one part/),
    ).toBeInTheDocument()
    expect(
      screen.getByText(
        "The parser isolates protected LaTeX units before translation and the generator rebuilds the final document.",
        { selector: "p" },
      ),
    ).toBeInTheDocument()
    expect(
      screen.getByText(
        "The validator, summarizer, and terminology extractor feed corrections back into the translation loop.",
        { selector: "p" },
      ),
    ).toBeInTheDocument()
  })

  it("renders normalized structured insight blocks from the backend contract", async () => {
    usePaperDetailMock.mockReturnValue(
      buildDetailReturn({
        structuredInsights: {
          state: "ready",
          sections: [
            {
              section_key: "problem",
              content: null,
              raw_content:
                "This raw string should no longer be needed by the main renderer once normalized blocks exist.",
              summary: "A stable backend contract should let the UI render without reparsing raw model text.",
              blocks: [
                {
                  heading: "Problem essence",
                  content: "The backend already isolated the core problem description.",
                },
                {
                  heading: "Why it matters",
                  content: "The frontend can now render deterministic sections directly.",
                },
              ],
              updated_at: "2026-03-18T03:00:00Z",
            },
          ],
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

    await userEvent.setup().click(screen.getByText(i18n.t("community.detail.insights.section.problem")))
    expect(
      screen.getByText("A stable backend contract should let the UI render without reparsing raw model text."),
    ).toBeInTheDocument()
    expect(screen.getByText("Problem essence")).toBeInTheDocument()
    expect(screen.getByText("Why it matters")).toBeInTheDocument()
    expect(screen.getByText("The backend already isolated the core problem description.")).toBeInTheDocument()
    expect(screen.getByText("The frontend can now render deterministic sections directly.")).toBeInTheDocument()
  })

  it("keeps only source, translated pdf, and bilingual compare modes", async () => {
    const user = userEvent.setup()
    usePaperDetailMock.mockReturnValue(
      buildDetailReturn({
        reader: {
          preferred_mode: "translated_pdf",
          available_modes: ["source", "translated_pdf", "bilingual_compare"],
          source: {
            kind: "source_pdf",
            html_content: null,
            url: "https://arxiv.org/pdf/2503.01010",
          },
          translated: {
            kind: "translated_pdf",
            html_content: null,
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

    expect(screen.getAllByRole("button", { name: "English" })).toHaveLength(1)
    expect(screen.getAllByRole("button", { name: "Chinese translation (PDF)" })).toHaveLength(1)
    expect(screen.getAllByRole("button", { name: "Bilingual compare" })).toHaveLength(1)
    expect(screen.queryByRole("button", { name: "Chinese translation (HTML)" })).not.toBeInTheDocument()
    expect(screen.getByTestId("paper-translated-pdf-reader")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "English" }))
    expect(screen.getByTestId("paper-source-pdf-reader")).toHaveAttribute(
      "src",
      "https://arxiv.org/pdf/2503.01010#page=1&view=FitH&pagemode=none&toolbar=0&navpanes=0&scrollbar=0",
    )

    await user.click(screen.getByRole("button", { name: "Bilingual compare" }))
    expect(screen.getByTestId("paper-bilingual-translated-pdf-reader")).toHaveAttribute(
      "src",
      `${API_BASE_URL}/api/papers/paper-1/translated-pdf#page=1&view=FitH&pagemode=none&toolbar=0&navpanes=0&scrollbar=0`,
    )
  })

  it("defaults to bilingual compare when the backend only signals generic translated readiness", () => {
    usePaperDetailMock.mockReturnValue(
      buildDetailReturn({
        preview: null,
        reader: {
          preferred_mode: "translated",
          available_modes: ["source", "translated"],
          source: {
            kind: "source_pdf",
            html_content: null,
            url: "https://arxiv.org/pdf/2503.01010",
          },
          translated: {
            kind: "translated_pdf",
            html_content: null,
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

    expect(screen.getByTestId("paper-bilingual-source-pdf-reader")).toHaveAttribute(
      "src",
      "https://arxiv.org/pdf/2503.01010#page=1&view=FitH&pagemode=none&toolbar=0&navpanes=0&scrollbar=0",
    )
    expect(screen.getByTestId("paper-bilingual-translated-pdf-reader")).toHaveAttribute(
      "src",
      `${API_BASE_URL}/api/papers/paper-1/translated-pdf#page=1&view=FitH&pagemode=none&toolbar=0&navpanes=0&scrollbar=0`,
    )
  })

  it("defaults to bilingual compare when the backend signals translated readiness and preserves manual switching", async () => {
    const user = userEvent.setup()
    usePaperDetailMock.mockReturnValue(
      buildDetailReturn({
        preview: null,
        reader: {
          preferred_mode: "translated",
          available_modes: ["source", "translated_pdf"],
          source: {
            kind: "source_pdf",
            html_content: null,
            url: "https://arxiv.org/pdf/2503.01010",
          },
          translated: {
            kind: "translated_pdf",
            html_content: null,
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

    const topButtons = screen.getAllByRole("button").filter((button) =>
      ["English", "Chinese translation (PDF)", "Bilingual compare"].includes(button.textContent ?? ""),
    )
    expect(topButtons.map((button) => button.textContent)).toEqual([
      "English",
      "Chinese translation (PDF)",
      "Bilingual compare",
    ])
    expect(screen.getByTestId("paper-bilingual-source-pdf-reader")).toHaveAttribute(
      "src",
      "https://arxiv.org/pdf/2503.01010#page=1&view=FitH&pagemode=none&toolbar=0&navpanes=0&scrollbar=0",
    )
    expect(screen.getByTestId("paper-bilingual-translated-pdf-reader")).toHaveAttribute(
      "src",
      `${API_BASE_URL}/api/papers/paper-1/translated-pdf#page=1&view=FitH&pagemode=none&toolbar=0&navpanes=0&scrollbar=0`,
    )

    await user.click(screen.getByRole("button", { name: "English" }))

    expect(screen.getByTestId("paper-source-pdf-reader")).toHaveAttribute(
      "src",
      "https://arxiv.org/pdf/2503.01010#page=1&view=FitH&pagemode=none&toolbar=0&navpanes=0&scrollbar=0",
    )
  })

  it("opens a paper info popover instead of a metadata expansion banner", async () => {
    const user = userEvent.setup()
    usePaperDetailMock.mockReturnValue(buildDetailReturn())

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.queryByText("Detail Page Title")).not.toBeInTheDocument()
    expect(screen.queryByText("Ada Lovelace")).not.toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Paper information" }))

    expect(screen.getByText("Detail Page Title")).toBeInTheDocument()
    expect(screen.getByText("Ada Lovelace")).toBeInTheDocument()
    expect(screen.getByText("cs.AI")).toBeInTheDocument()
    expect(screen.getAllByText("2503.01010").length).toBeGreaterThan(0)
  })

  it("keeps the mobile paper information popover scrollable inside the viewport", async () => {
    const user = userEvent.setup()
    setMobileViewport()
    usePaperDetailMock.mockReturnValue(
      buildDetailReturn({
        paper: {
          ...basePaper,
          title: "mHC: Manifold-Constrained Hyper-Connections",
          authors: [
            "Zhenda Xie",
            "Yixuan Wei",
            "Huanqi Cao",
            "Chenggang Zhao",
            "Chengqi Deng",
            "Jiashi Li",
            "Damai Dai",
            "Huazuo Gao",
            "Jiang Chang",
            "Kuai Yu",
            "Liang Zhao",
            "Shangyan Zhou",
            "Zhean Xu",
            "Zhengyan Zhang",
            "Wangding Zeng",
            "Shengding Hu",
            "Yuqing Wang",
            "Jingyang Yuan",
            "Lean Wang",
            "Wenfeng Liang",
          ],
          github_url: "https://github.com/deepseek-ai/example-repository-with-a-long-name",
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

    await user.click(screen.getByRole("button", { name: "Paper information" }))

    const popover = screen.getByTestId("paper-detail-info-popover")
    expect(popover).toHaveClass("max-h-[calc(100svh-5.75rem)]")
    expect(popover).toHaveClass("overflow-y-auto")
    expect(popover).toHaveClass("overscroll-contain")
  })

  it("keeps only insights and similar tabs, collapses insights by default, and loads similar cards lazily", async () => {
    const user = userEvent.setup()
    getCommunityPaperSimilarMock.mockResolvedValue({
      items: [
        {
          arxiv_id: "2504.12345",
          title: "Neighbor Paper",
          abstract: "A nearby paper abstract.",
          arxiv_url: "https://arxiv.org/abs/2504.12345",
          community_paper_id: "paper-neighbor",
          link_type: "community",
        },
      ],
    })
    usePaperDetailMock.mockReturnValue(buildDetailReturn())

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
          <Route path="/paper/paper-neighbor" element={<div>Neighbor detail</div>} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByRole("tab", { name: "Paper analysis" })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: "Similar" })).toBeInTheDocument()
    expect(screen.queryByRole("tab", { name: "Notes" })).not.toBeInTheDocument()
    expect(screen.queryByRole("tab", { name: "Comments" })).not.toBeInTheDocument()
    expect(screen.queryByText("Structured reading")).not.toBeInTheDocument()
    expect(screen.queryByText(problemContent)).not.toBeInTheDocument()

    await user.click(screen.getByRole("tab", { name: "Similar" }))

    expect(getCommunityPaperSimilarMock).toHaveBeenCalledWith("paper-1")
    expect(await screen.findByText("Neighbor Paper")).toBeInTheDocument()
    expect(screen.getByText("2504.12345")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Open in community" })).toHaveAttribute("href", "/paper/paper-neighbor")
    expect(screen.queryByText("A nearby paper abstract.")).not.toBeInTheDocument()
    await user.click(screen.getByText("Neighbor Paper"))
    expect(screen.getByText("A nearby paper abstract.")).toBeInTheDocument()
  })

  it.skip("removes duplicated title and author lead content from the translated html reader body", async () => {
    const user = userEvent.setup()
    usePaperDetailMock.mockReturnValue(
      buildDetailReturn({
        paper: {
          ...basePaper,
          title: "LaTeXTrans: Structured LaTeX Translation with Multi-Agent Coordination",
          authors: ["Ziming Zhu", "Chenglong Wang", "Haosong Xv"],
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
          html_content:
            "<article><header><h1>LaTeXTrans: Structured LaTeX Translation with Multi-Agent Coordination</h1><p>Ziming Zhu, Chenglong Wang, Haosong Xv</p></header><section><h2>引言</h2><p>Actual translated paper body.</p></section></article>",
          generated_at: "2026-03-18T02:00:00Z",
        },
        reader: {
          preferred_mode: "translated_html",
          available_modes: ["source", "translated_html", "translated_pdf"],
          source: {
            kind: "source_html",
            html_content:
              "<article><h1>LaTeXTrans: Structured LaTeX Translation with Multi-Agent Coordination</h1><p>Ziming Zhu, Chenglong Wang</p><h2>Introduction</h2><p>Actual paper body.</p></article>",
            url: "https://arxiv.org/html/2503.01010",
          },
          translated: {
            kind: "preview_html",
            html_content:
              "<article><header><h1>LaTeXTrans: Structured LaTeX Translation with Multi-Agent Coordination</h1><p>Ziming Zhu, Chenglong Wang, Haosong Xv</p></header><section><h2>引言</h2><p>Actual translated paper body.</p></section></article>",
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

    await user.click(screen.getByTestId("paper-detail-mode-translated-html"))
    expect(screen.getByRole("heading", { name: "引言" })).toBeInTheDocument()
    expect(screen.getByText("Actual translated paper body.")).toBeInTheDocument()
    expect(
      screen.queryByText("LaTeXTrans: Structured LaTeX Translation with Multi-Agent Coordination", {
        selector: "[data-testid='paper-preview-reader'] *",
      }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByText("Ziming Zhu, Chenglong Wang, Haosong Xv", {
        selector: "[data-testid='paper-preview-reader'] *",
      }),
    ).not.toBeInTheDocument()
  })

  it("removes translate and view-progress header actions from the minimal toolbar", () => {
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

    expect(screen.queryByRole("button", { name: "Translate" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "View Progress" })).not.toBeInTheDocument()
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

    await user.click(screen.getByRole("button", { name: "Download translated PDF" }))

    await waitFor(() => {
      expect(createCommunityPaperDownloadSessionMock).toHaveBeenCalledWith("paper-1")
      expect(openMock).toHaveBeenCalledWith(`${API_BASE_URL}/api/papers/paper-1/download?token=abc`, "_blank")
    })
  })

  it("copies the current paper detail url when share is clicked", async () => {
    const user = userEvent.setup()
    usePaperDetailMock.mockReturnValue(buildDetailReturn())
    window.history.pushState({}, "", "/paper/paper-1")

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await user.click(screen.getByRole("button", { name: "Copy paper link" }))

    await waitFor(() => {
      expect(screen.getByText("Link copied")).toBeInTheDocument()
    })
  })

  it("shows a visible mobile confirmation after copying the paper link", async () => {
    const user = userEvent.setup()
    setMobileViewport()
    usePaperDetailMock.mockReturnValue(buildDetailReturn())
    window.history.pushState({}, "", "/paper/paper-1")

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await user.click(screen.getByRole("button", { name: "Copy paper link" }))

    await waitFor(() => {
      expect(screen.getByTestId("paper-detail-share-status")).toHaveTextContent("Link copied")
      expect(screen.getByTestId("paper-detail-share-status")).not.toHaveClass("sr-only")
    })
  })

  it("places a subtle like button before favorite and updates the count when clicked", async () => {
    const user = userEvent.setup()
    usePaperDetailMock.mockReturnValue(buildDetailReturn())

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    const actionButtons = screen.getAllByRole("button")
    const likeButton = screen.getByRole("button", { name: "Like paper" })
    const favoriteButton = screen.getByRole("button", { name: "Favorite paper" })

    expect(actionButtons.indexOf(likeButton)).toBeLessThan(actionButtons.indexOf(favoriteButton))
    expect(likeButton).toHaveTextContent("2")

    await user.click(likeButton)

    await waitFor(() => {
      expect(likeCommunityPaperMock).toHaveBeenCalledWith("paper-1")
      expect(screen.getByRole("button", { name: "Unlike paper" })).toHaveTextContent("3")
    })
  })

  it("reflows the mobile detail header into a compact collapsed action row", () => {
    setMobileViewport()
    usePaperDetailMock.mockReturnValue(buildDetailReturn())

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByTestId("paper-detail-header")).toHaveAttribute("data-mobile-layout", "stacked")
    expect(screen.getByTestId("paper-detail-header")).toHaveAttribute("data-mobile-toolbar", "collapsed")
    expect(screen.getByTestId("paper-detail-header-mobile-actions")).toBeInTheDocument()
    expect(screen.queryByTestId("paper-detail-header-mobile-modes")).not.toBeInTheDocument()

    const actionButtons = screen.getAllByRole("button")
    const analysisButton = screen.getByRole("button", { name: "Open analysis" })
    const likeButton = screen.getByRole("button", { name: "Like paper" })
    expect(analysisButton).toHaveAttribute("data-testid", "mobile-analysis-jump-button")
    expect(actionButtons.indexOf(analysisButton)).toBeLessThan(actionButtons.indexOf(likeButton))
  })

  it("allows expanding the default-collapsed mobile detail toolbar", async () => {
    const user = userEvent.setup()
    setMobileViewport()
    usePaperDetailMock.mockReturnValue(buildDetailReturn())

    render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <Routes>
          <Route path="/paper/:paperId" element={<PaperDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByTestId("paper-detail-header")).toHaveAttribute("data-mobile-toolbar", "collapsed")
    expect(screen.queryByTestId("paper-detail-header-mobile-modes")).not.toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Show toolbar" }))

    expect(screen.getByTestId("paper-detail-header")).toHaveAttribute("data-mobile-toolbar", "expanded")
    expect(screen.getByTestId("paper-detail-header-mobile-modes")).toBeInTheDocument()
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
