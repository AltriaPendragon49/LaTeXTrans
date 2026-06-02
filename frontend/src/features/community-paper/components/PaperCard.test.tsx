import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"

import { API_BASE_URL } from "@/api-base"
import { PaperCard } from "@/features/community-paper/components/PaperCard"
import { createCommunityPaperDownloadSession } from "@/features/community-paper/services/community-paper-api"
import i18n from "@/i18n"
import type { CommunityPaper } from "@/types/community"

const prefetchCommunityPaperDetailMock = vi.fn()
const preloadPaperPreviewEnhancerMock = vi.fn()
const fetchMock = vi.fn()
const createObjectUrlMock = vi.fn()
const revokeObjectUrlMock = vi.fn()

vi.mock("@/lib/community-api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/community-api")>("@/lib/community-api")
  return {
    ...actual,
    prefetchCommunityPaperDetail: (...args: unknown[]) => prefetchCommunityPaperDetailMock(...args),
  }
})

vi.mock("@/lib/paper-preview-enhancer", () => ({
  preloadPaperPreviewEnhancer: (...args: unknown[]) => preloadPaperPreviewEnhancerMock(...args),
}))

vi.mock("@/features/community-paper/services/community-paper-api", () => ({
  createCommunityPaperDownloadSession: vi.fn(),
}))

const paper: CommunityPaper = {
  id: "paper-1",
  source: "arxiv",
  arxiv_id: "2503.01010",
  arxiv_url: "https://arxiv.org/abs/2503.01010",
  github_url: "https://github.com/paperx/attention-residuals",
  title: "Attention Residuals for Community Discovery",
  authors: ["Ada Lovelace", "Alan Turing"],
  categories: ["cs.AI", "cs.CL"],
  abstract_raw: "A compact abstract for testing the paper card render path.",
  abstract_translated: "A translated abstract for the community paper card.",
  community_status: "official",
  trans_status: "completed",
  created_at: "2026-03-18T00:00:00Z",
  official_published_at: "2026-03-18T02:00:00Z",
  community_selected_task_id: "task-1",
  community_selected_asset_id: "asset-1",
  latest_asset: {
    id: "asset-1",
    task_id: "task-1",
    asset_type: "translated_pdf",
    file_name: "translated.pdf",
    mime_type: "application/pdf",
    created_at: "2026-03-18T02:00:00Z",
  },
  assets: {
    source_archive: {
      id: "asset-source",
      task_id: null,
      asset_type: "source_archive",
      file_name: "2503.01010",
      mime_type: "application/x-directory",
      created_at: "2026-03-18T00:00:00Z",
    },
    translated_pdf: {
      id: "asset-1",
      task_id: "task-1",
      asset_type: "translated_pdf",
      file_name: "translated.pdf",
      mime_type: "application/pdf",
      created_at: "2026-03-18T02:00:00Z",
    },
  },
  like_count: 7,
  favorite_count: 3,
  comment_count: 2,
  view_count: 21,
}

describe("PaperCard", () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  beforeEach(async () => {
    vi.clearAllMocks()
    fetchMock.mockResolvedValue(
      new Response("source-pdf", {
        status: 200,
        headers: {
          "Content-Disposition": 'attachment; filename="paper-source.pdf"',
          "Content-Type": "application/pdf",
        },
      }),
    )
    vi.mocked(createCommunityPaperDownloadSession).mockResolvedValue({
      paper_id: "paper-1",
      asset_id: "asset-1",
      download_url: "/api/papers/paper-1/download?token=session-token",
      expires_at: "2026-03-18T02:05:00Z",
    })
    vi.stubGlobal("fetch", fetchMock)
    createObjectUrlMock.mockReturnValue("blob:paper-source")
    revokeObjectUrlMock.mockReturnValue(undefined)
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: createObjectUrlMock,
      revokeObjectURL: revokeObjectUrlMock,
    })
    vi.spyOn(window, "open").mockImplementation(() => null)
    await i18n.changeLanguage("en")
  })

  it("renders paper metadata, research actions, and detail navigation", () => {
    render(
      <MemoryRouter>
        <PaperCard paper={paper} />
      </MemoryRouter>,
    )

    const titleLink = screen.getByRole("link", { name: /attention residuals/i })
    const authors = screen.getByText("Ada Lovelace, Alan Turing")
    const abstract = screen.getByText("A compact abstract for testing the paper card render path.")

    expect(titleLink).toHaveAttribute("href", "/paper/paper-1")
    expect(screen.getByRole("link", { name: "Original source" })).toHaveAttribute("href", "/paper/paper-1")
    expect(screen.getByRole("link", { name: "Chinese translation (PDF)" })).toHaveAttribute("href", "/paper/paper-1")
    expect(screen.getByRole("button", { name: "Download source PDF" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Download translated PDF" })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Open arXiv" })).toHaveAttribute(
      "href",
      "https://arxiv.org/abs/2503.01010",
    )
    expect(screen.getByRole("link", { name: "Open GitHub" })).toHaveAttribute(
      "href",
      "https://github.com/paperx/attention-residuals",
    )
    expect(screen.queryByText("Completed")).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Language settings" })).not.toBeInTheDocument()
    expect(authors.closest("a")).toBeNull()
    expect(abstract.closest("a")).toBeNull()
    expect(screen.getByTestId("paper-card-source-preview-image")).toHaveAttribute(
      "src",
      `${API_BASE_URL}/api/papers/paper-1/source-thumbnail`,
    )
    expect(screen.getByTestId("paper-card-translated-preview-image")).toHaveAttribute(
      "src",
      `${API_BASE_URL}/api/papers/paper-1/translated-thumbnail`,
    )
  })

  it("hides the unsupported comment metric while keeping supported engagement stats", () => {
    render(
      <MemoryRouter>
        <PaperCard paper={{ ...paper, comment_count: 42 }} />
      </MemoryRouter>,
    )

    expect(screen.getByText("21")).toBeInTheDocument()
    expect(screen.getByText("7")).toBeInTheDocument()
    expect(screen.getByText("3")).toBeInTheDocument()
    expect(screen.queryByText("42")).not.toBeInTheDocument()
  })

  it("renders the arxiv publication date as a highlighted time badge", () => {
    render(
      <MemoryRouter>
        <PaperCard paper={{ ...paper, arxiv_published_at: "2026-03-10T00:00:00Z" }} />
      </MemoryRouter>,
    )

    const publishedTime = screen.getByLabelText("Published March 10, 2026")

    expect(publishedTime.tagName).toBe("TIME")
    expect(publishedTime).toHaveAttribute("dateTime", "2026-03-10T00:00:00Z")
    expect(screen.getByTestId("paper-card-published-at-row")).toHaveClass("mt-auto", "justify-end")
    expect(screen.getByText("Published")).toBeInTheDocument()
    expect(screen.getByText("March 10, 2026")).toBeInTheDocument()
  })

  it("prefetches detail payload on intent signals", () => {
    render(
      <MemoryRouter>
        <PaperCard paper={paper} />
      </MemoryRouter>,
    )

    const titleLink = screen.getByRole("link", { name: /attention residuals/i })

    fireEvent.mouseEnter(titleLink)
    fireEvent.focus(titleLink)
    fireEvent.pointerDown(titleLink)

    expect(prefetchCommunityPaperDetailMock).toHaveBeenCalledWith("paper-1")
    expect(preloadPaperPreviewEnhancerMock).toHaveBeenCalled()
  })

  it("keeps the favorite entry available even when the admin delete action is shown", () => {
    const onDelete = vi.fn()

    const { rerender } = render(
      <MemoryRouter>
        <PaperCard paper={paper} onDelete={onDelete} />
      </MemoryRouter>,
    )

    expect(screen.getByRole("button", { name: "Favorite paper" })).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Delete paper" }))
    expect(onDelete).toHaveBeenCalledWith(paper)

    rerender(
      <MemoryRouter>
        <PaperCard paper={paper} />
      </MemoryRouter>,
    )

    expect(screen.queryByRole("button", { name: "Delete paper" })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Favorite paper" })).toBeInTheDocument()
  })

  it("uses paper-level preview routes even when the selected task id is missing", () => {
    render(
      <MemoryRouter>
        <PaperCard
          paper={{
            ...paper,
            community_selected_task_id: null,
            assets: {
              ...paper.assets,
              translated_pdf: {
                id: "asset-translated",
                task_id: null,
                asset_type: "translated_pdf",
                file_name: "translated.pdf",
                mime_type: "application/pdf",
                created_at: "2026-03-18T02:00:00Z",
              },
            },
          }}
        />
      </MemoryRouter>,
    )

    expect(screen.getByTestId("paper-card-source-preview-image")).toHaveAttribute(
      "src",
      `${API_BASE_URL}/api/papers/paper-1/source-thumbnail`,
    )
  })

  it("keeps preview navigation separate from copyable metadata", () => {
    render(
      <MemoryRouter>
        <PaperCard paper={paper} />
      </MemoryRouter>,
    )

    expect(screen.getByText("Ada Lovelace, Alan Turing").closest("a")).toBeNull()
    expect(screen.getByText("A compact abstract for testing the paper card render path.").closest("a")).toBeNull()
    expect(screen.getByRole("link", { name: /attention residuals/i })).toHaveAttribute("href", "/paper/paper-1")
    expect(screen.getByRole("link", { name: "Original source" })).toHaveAttribute("href", "/paper/paper-1")
    expect(screen.getByRole("link", { name: "Chinese translation (PDF)" })).toHaveAttribute("href", "/paper/paper-1")
  })

  it("enlarges the hovered preview card in place without rendering a magnifier inspector", async () => {
    render(
      <MemoryRouter>
        <PaperCard paper={paper} />
      </MemoryRouter>,
    )

    const previewFrame = screen.getByTestId("paper-card-source-preview-frame")
    const previewSurface = screen.getByTestId("paper-card-source-preview-surface")

    expect(previewSurface).not.toHaveClass("scale-[1.40]")

    fireEvent.pointerEnter(previewFrame, {
      clientX: 48,
      clientY: 60,
    })

    await waitFor(() => {
      expect(previewSurface).toHaveClass("scale-[1.40]")
    })
    expect(screen.queryByTestId("paper-card-source-preview-inspector")).not.toBeInTheDocument()

    fireEvent.pointerLeave(previewFrame)

    await waitFor(() => {
      expect(previewSurface).not.toHaveClass("scale-[1.40]")
    })
  })

  it("starts a translated pdf download session and opens the returned download url", async () => {
    render(
      <MemoryRouter>
        <PaperCard paper={paper} />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole("button", { name: "Download translated PDF" }))

    await waitFor(() => {
      expect(createCommunityPaperDownloadSession).toHaveBeenCalledWith("paper-1")
      expect(window.open).toHaveBeenCalledWith(
        `${API_BASE_URL}/api/papers/paper-1/download?token=session-token`,
        "_blank",
        "noopener,noreferrer",
      )
    })
  })

  it("downloads the source pdf through the backend route", async () => {
    const appendChildSpy = vi.spyOn(document.body, "appendChild")
    const removeSpy = vi.spyOn(HTMLAnchorElement.prototype, "remove").mockImplementation(() => {})
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {})

    render(
      <MemoryRouter>
        <PaperCard paper={paper} />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole("button", { name: "Download source PDF" }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(`${API_BASE_URL}/api/papers/paper-1/source-download`)
      expect(createObjectUrlMock).toHaveBeenCalled()
      expect(appendChildSpy).toHaveBeenCalled()
      expect(clickSpy).toHaveBeenCalled()
      expect(removeSpy).toHaveBeenCalled()
      expect(revokeObjectUrlMock).toHaveBeenCalledWith("blob:paper-source")
    })
  })

  it("hides the github action when the paper has no repository url", () => {
    render(
      <MemoryRouter>
        <PaperCard paper={{ ...paper, github_url: null }} />
      </MemoryRouter>,
    )

    expect(screen.queryByRole("link", { name: "Open GitHub" })).not.toBeInTheDocument()
  })
})
