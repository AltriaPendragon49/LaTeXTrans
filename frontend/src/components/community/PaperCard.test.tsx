import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it } from "vitest"
import { MemoryRouter } from "react-router-dom"

import i18n from "@/i18n"
import { PaperCard } from "@/components/community/PaperCard"
import type { CommunityPaper } from "@/types/community"

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
  like_count: 7,
  favorite_count: 3,
  comment_count: 2,
  view_count: 21,
}

describe("PaperCard", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en")
  })

  it("renders paper metadata and detail navigation", () => {
    render(
      <MemoryRouter>
        <PaperCard paper={paper} />
      </MemoryRouter>,
    )

    expect(screen.getByText("Attention Residuals for Community Discovery")).toBeInTheDocument()
    expect(screen.getByText("Official")).toBeInTheDocument()
    expect(screen.getByText("Completed")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /view detail/i })).toHaveAttribute("href", "/paper/paper-1")
    expect(screen.getAllByText(/translated pdf/i).length).toBeGreaterThan(0)
  })
})
