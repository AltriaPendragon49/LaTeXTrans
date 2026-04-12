import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n"
import { PaperPreviewReader } from "@/components/community/PaperPreviewReader"

const getCommunityPaperPreviewMock = vi.fn()
const sanitizeMock = vi.fn((value: string) => value)
const enhancePaperPreviewElementMock = vi.fn().mockResolvedValue(undefined)
const preloadPaperPreviewEnhancerMock = vi.fn().mockResolvedValue(undefined)

vi.mock("@/lib/community-api", () => ({
  getCommunityPaperPreview: (...args: unknown[]) => getCommunityPaperPreviewMock(...args),
}))

vi.mock("@/lib/paper-preview-enhancer", () => ({
  preloadPaperPreviewEnhancer: (...args: unknown[]) => preloadPaperPreviewEnhancerMock(...args),
  enhancePaperPreviewElement: (...args: unknown[]) => enhancePaperPreviewElementMock(...args),
}))

vi.mock("dompurify", () => ({
  default: {
    sanitize: (value: string) => sanitizeMock(value),
  },
}))

describe("PaperPreviewReader", () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    await i18n.changeLanguage("en")
  })

  it("reuses prepared html when an equivalent preview payload refreshes", async () => {
    const preview = {
      paper_id: "paper-1",
      task_id: "task-1",
      asset: {
        id: "asset-preview-stable",
        task_id: "task-1",
        asset_type: "preview_html" as const,
        file_name: "preview.html",
        mime_type: "text/html",
        created_at: "2026-03-18T02:00:00Z",
      },
      html_content: "<h2>Intro</h2><p>Stable reader body</p>",
      generated_at: "2026-03-18T02:00:00Z",
    }

    const { rerender } = render(
      <PaperPreviewReader
        paperId="paper-1"
        initialPreview={preview}
        readerState="ready"
      />,
    )

    expect(await screen.findByText("Intro")).toBeInTheDocument()
    await waitFor(() => {
      expect(enhancePaperPreviewElementMock).toHaveBeenCalledTimes(1)
    })
    expect(sanitizeMock).toHaveBeenCalledTimes(1)

    rerender(
      <PaperPreviewReader
        paperId="paper-1"
        initialPreview={{
          ...preview,
          asset: { ...preview.asset },
        }}
        readerState="ready"
      />,
    )

    await waitFor(() => {
      expect(screen.getByText("Stable reader body")).toBeInTheDocument()
    })
    expect(sanitizeMock).toHaveBeenCalledTimes(1)
    expect(enhancePaperPreviewElementMock).toHaveBeenCalledTimes(1)
  })

  it("renders inline translated html and lazy-loads reader enhancement only after preview arrives", async () => {
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
      html_content: "<h2>Intro</h2><p>Reader body $E=mc^2$</p>",
      generated_at: "2026-03-18T02:00:00Z",
    })

    render(<PaperPreviewReader paperId="paper-1" />)

    expect(await screen.findByText("Intro")).toBeInTheDocument()
    await waitFor(() => {
      expect(enhancePaperPreviewElementMock).toHaveBeenCalledWith(
        expect.any(HTMLElement),
        expect.objectContaining({
          previewAssetId: "asset-preview",
          previewSignature: expect.any(String),
        }),
      )
    })
    expect(screen.getByTestId("paper-preview-content")).toHaveAttribute("data-reader-layout", "scholarly")
    expect(screen.getByTestId("paper-preview-viewport").className).toContain("overflow-x-hidden")
  })

  it("hydrates translated html when detail only provides a preview locator", async () => {
    getCommunityPaperPreviewMock.mockResolvedValue({
      paper_id: "paper-1",
      task_id: "task-1",
      asset: {
        id: "asset-preview-bootstrap",
        task_id: "task-1",
        asset_type: "preview_html",
        file_name: "preview.html",
        mime_type: "text/html",
        created_at: "2026-03-18T02:00:00Z",
      },
      fetch_url: "/api/papers/paper-1/preview",
      html_content: "<h2>Hydrated intro</h2><p>Bootstrapped reader body</p>",
      generated_at: "2026-03-18T02:00:00Z",
    })

    render(
      <PaperPreviewReader
        paperId="paper-1"
        initialPreview={{
          paper_id: "paper-1",
          task_id: "task-1",
          asset: {
            id: "asset-preview-bootstrap",
            task_id: "task-1",
            asset_type: "preview_html",
            file_name: "preview.html",
            mime_type: "text/html",
            created_at: "2026-03-18T02:00:00Z",
          },
          fetch_url: "/api/papers/paper-1/preview",
          generated_at: "2026-03-18T02:00:00Z",
        }}
        readerState="ready"
      />,
    )

    expect(await screen.findByText("Hydrated intro")).toBeInTheDocument()
    await waitFor(() => {
      expect(getCommunityPaperPreviewMock).toHaveBeenCalledWith("paper-1")
    })
  })

  it("strips duplicated paper title and author lead content from hydrated previews", async () => {
    getCommunityPaperPreviewMock.mockResolvedValue({
      paper_id: "paper-1",
      task_id: "task-1",
      asset: {
        id: "asset-preview-bootstrap",
        task_id: "task-1",
        asset_type: "preview_html",
        file_name: "preview.html",
        mime_type: "text/html",
        created_at: "2026-03-18T02:00:00Z",
      },
      fetch_url: "/api/papers/paper-1/preview",
      html_content:
        "<article><header><h1>Structured LaTeX Translation</h1><p>Ada Lovelace, Alan Turing</p></header><section><h2>Introduction</h2><p>Hydrated reader body</p></section></article>",
      generated_at: "2026-03-18T02:00:00Z",
    })

    render(
      <PaperPreviewReader
        paperId="paper-1"
        paperMetadata={{ title: "Structured LaTeX Translation", authors: ["Ada Lovelace", "Alan Turing"] }}
        initialPreview={{
          paper_id: "paper-1",
          task_id: "task-1",
          asset: {
            id: "asset-preview-bootstrap",
            task_id: "task-1",
            asset_type: "preview_html",
            file_name: "preview.html",
            mime_type: "text/html",
            created_at: "2026-03-18T02:00:00Z",
          },
          fetch_url: "/api/papers/paper-1/preview",
          generated_at: "2026-03-18T02:00:00Z",
        }}
        readerState="ready"
      />,
    )

    expect(await screen.findByText("Introduction")).toBeInTheDocument()
    expect(screen.getByText("Hydrated reader body")).toBeInTheDocument()
    expect(sanitizeMock).toHaveBeenCalledWith(expect.not.stringContaining("Structured LaTeX Translation"))
    expect(sanitizeMock).toHaveBeenCalledWith(expect.not.stringContaining("Ada Lovelace, Alan Turing"))
    expect(
      screen.queryByText("Structured LaTeX Translation", {
        selector: "[data-testid='paper-preview-reader'] *",
      }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByText("Ada Lovelace, Alan Turing", {
        selector: "[data-testid='paper-preview-reader'] *",
      }),
    ).not.toBeInTheDocument()
  })

  it("does not load reader enhancement while warming", async () => {
    render(<PaperPreviewReader paperId="paper-1" readerState="warming" />)

    expect(await screen.findByText("Translated reader is warming up")).toBeInTheDocument()
    expect(preloadPaperPreviewEnhancerMock).not.toHaveBeenCalled()
    expect(enhancePaperPreviewElementMock).not.toHaveBeenCalled()
  })

  it("renders an empty state when the preview is unavailable", async () => {
    getCommunityPaperPreviewMock.mockRejectedValue(new Error("404"))

    render(<PaperPreviewReader paperId="paper-1" />)

    expect(await screen.findByText("Translated reader not available")).toBeInTheDocument()
  })

  it("adds a table expand affordance and opens the expanded reader sheet", async () => {
    const preview = {
      paper_id: "paper-1",
      task_id: "task-1",
      asset: {
        id: "asset-preview-table",
        task_id: "task-1",
        asset_type: "preview_html" as const,
        file_name: "preview.html",
        mime_type: "text/html",
        created_at: "2026-03-18T02:00:00Z",
      },
      html_content:
        "<article class=\"paper-preview\"><section class=\"paper-preview__section\"><figure class=\"paper-preview__figure paper-preview__figure--table\"><div class=\"paper-preview__table-wrap\"><table class=\"paper-preview__table\"><tbody><tr><th>Model</th><th>Score</th></tr><tr><td>Alpha</td><td>98</td></tr></tbody></table></div><figcaption class=\"paper-preview__caption\">Leaderboard</figcaption></figure></section></article>",
      generated_at: "2026-03-18T02:00:00Z",
    }

    render(<PaperPreviewReader paperId="paper-1" initialPreview={preview} readerState="ready" />)

    const expandButton = await screen.findByRole("button", { name: "Expand table" })
    await userEvent.click(expandButton)

    expect(await screen.findByRole("dialog")).toBeInTheDocument()
    expect(screen.getAllByText("Leaderboard").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Alpha").length).toBeGreaterThan(0)
  })

  it("scrolls to internal reader references inside the preview viewport", async () => {
    const scrollIntoViewMock = vi.fn()
    HTMLElement.prototype.scrollIntoView = scrollIntoViewMock

    const preview = {
      paper_id: "paper-1",
      task_id: "task-1",
      asset: {
        id: "asset-preview-xref",
        task_id: "task-1",
        asset_type: "preview_html" as const,
        file_name: "preview.html",
        mime_type: "text/html",
        created_at: "2026-03-18T02:00:00Z",
      },
      html_content:
        "<article class=\"paper-preview\"><section class=\"paper-preview__section\"><p><a class=\"paper-preview__xref\" href=\"#section-2\">Section</a></p><h2 id=\"section-2\">Section 2</h2></section></article>",
      generated_at: "2026-03-18T02:00:00Z",
    }

    render(<PaperPreviewReader paperId="paper-1" initialPreview={preview} readerState="ready" />)

    await userEvent.click(await screen.findByRole("link", { name: "Section" }))

    expect(scrollIntoViewMock).toHaveBeenCalled()
  })

  it("normalizes legacy latex residue blocks before rendering", async () => {
    const preview = {
      paper_id: "paper-1",
      task_id: "task-1",
      asset: {
        id: "asset-preview-legacy",
        task_id: "task-1",
        asset_type: "preview_html" as const,
        file_name: "preview.html",
        mime_type: "text/html",
        created_at: "2026-03-18T02:00:00Z",
      },
      html_content:
        "<article class=\"paper-preview\"><section class=\"paper-preview__section\"><div class=\"paper-preview__block paper-preview__block--latex\"><pre class=\"paper-preview__latex\">\\begin{quote}Legacy quote.</pre></div><div class=\"paper-preview__block\"><p>\\flushright{Legacy author}\\n\\end{quote}</p></div><div class=\"paper-preview__block\"><p>\\end{snugshade*}</p></div><div class=\"paper-preview__block\"><p>\\lettrine[findent=2pt]{T}{his paragraph survives.}</p></div></section></article>",
      generated_at: "2026-03-18T02:00:00Z",
    }

    render(<PaperPreviewReader paperId="paper-1" initialPreview={preview} readerState="ready" />)

    expect(await screen.findByText("Legacy quote.")).toBeInTheDocument()
    expect(await screen.findByText("Legacy author")).toBeInTheDocument()
    expect(await screen.findByText("This paragraph survives.")).toBeInTheDocument()
    expect(screen.queryByText("\\begin{quote}Legacy quote.")).not.toBeInTheDocument()
    expect(screen.queryByText("\\end{snugshade*}")).not.toBeInTheDocument()
  })
})
