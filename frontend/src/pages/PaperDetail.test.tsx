import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter, Route, Routes } from "react-router-dom"

import i18n from "@/i18n"
import PaperDetailPage from "@/pages/PaperDetail"

const usePaperDetailMock = vi.fn()

vi.mock("@/hooks/use-paper-detail", () => ({
  usePaperDetail: (...args: unknown[]) => usePaperDetailMock(...args),
}))

describe("PaperDetailPage", () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    await i18n.changeLanguage("en")
  })

  it("renders paper detail metadata and disabled action slots", () => {
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
        trans_status: "completed",
        created_at: "2026-03-18T00:00:00Z",
        official_published_at: "2026-03-18T02:00:00Z",
        community_selected_task_id: "task-1",
        community_selected_asset_id: "asset-1",
        latest_asset: {
          id: "asset-1",
          task_id: "task-1",
          asset_type: "translated_pdf",
          file_path: "/tmp/translated.pdf",
          file_name: "translated.pdf",
          mime_type: "application/pdf",
          created_at: "2026-03-18T02:00:00Z",
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
    expect(screen.getByText("Abstract body for the detail shell.")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Translate" })).toBeDisabled()
    expect(screen.getByRole("button", { name: "Download" })).toBeDisabled()
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
