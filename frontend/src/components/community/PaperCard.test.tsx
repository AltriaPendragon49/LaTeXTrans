import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"

import { API_BASE_URL } from "@/api-base"
import i18n from "@/i18n"
import { PaperCard } from "@/components/community/PaperCard"
import type { CommunityPaper } from "@/types/community"

const prefetchCommunityPaperDetailMock = vi.fn()
const preloadPaperDetailRouteMock = vi.fn()
const preloadPaperPreviewEnhancerMock = vi.fn()

vi.mock("@/lib/community-api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/community-api")>("@/lib/community-api")
  return {
    ...actual,
    prefetchCommunityPaperDetail: (...args: unknown[]) => prefetchCommunityPaperDetailMock(...args),
    preloadPaperDetailRoute: (...args: unknown[]) => preloadPaperDetailRouteMock(...args),
  }
})

vi.mock("@/lib/paper-preview-enhancer", () => ({
  preloadPaperPreviewEnhancer: (...args: unknown[]) => preloadPaperPreviewEnhancerMock(...args),
}))

vi.mock("react-pdf", () => ({
  Document: ({ file }: { file: string | null }) => <div data-testid="pdf-document" data-file={file ?? ""} />,
  Page: () => <div data-testid="pdf-page" />,
  pdfjs: {
    version: "test",
    GlobalWorkerOptions: {
      workerSrc: "",
    },
  },
}))

const paper: CommunityPaper = {
  id: "paper-1",
  source: "arxiv",
  arxiv_id: "2503.01010",
  title: "Attention Residuals for Community Discovery",
  authors: ["Ada Lovelace", "Alan Turing"],
  categories: ["cs.AI", "cs.CL"],
  abstract_raw: "A compact abstract for testing the paper card render path.",
  abstract_translated: null,
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
  beforeEach(async () => {
    vi.clearAllMocks()
    await i18n.changeLanguage("en")
  })

  it("renders paper metadata and detail navigation", () => {
    render(
      <MemoryRouter>
        <PaperCard paper={paper} />
      </MemoryRouter>,
    )

    expect(screen.getByText("Attention Residuals for Community Discovery")).toBeInTheDocument()
    expect(screen.queryByText("Official")).not.toBeInTheDocument()
    expect(screen.getByText("Completed")).toBeInTheDocument()
    expect(screen.getByRole("link")).toHaveAttribute("href", "/paper/paper-1")
    expect(screen.getAllByTestId("pdf-document")).toHaveLength(2)
  })

  it("prefetches route code and detail payload on intent signals", () => {
    render(
      <MemoryRouter>
        <PaperCard paper={paper} />
      </MemoryRouter>,
    )

    const titleLink = screen.getByRole("link", { name: /attention residuals/i })

    fireEvent.mouseEnter(titleLink)
    fireEvent.focus(titleLink)
    fireEvent.pointerDown(titleLink)

    expect(preloadPaperDetailRouteMock).toHaveBeenCalled()
    expect(prefetchCommunityPaperDetailMock).toHaveBeenCalledWith("paper-1")
    expect(preloadPaperPreviewEnhancerMock).toHaveBeenCalled()
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

    const pdfDocuments = screen.getAllByTestId("pdf-document")
    expect(pdfDocuments[0]).toHaveAttribute("data-file", `${API_BASE_URL}/api/papers/paper-1/source-pdf`)
    expect(pdfDocuments[1]).toHaveAttribute("data-file", `${API_BASE_URL}/api/papers/paper-1/translated-pdf`)
  })
})
