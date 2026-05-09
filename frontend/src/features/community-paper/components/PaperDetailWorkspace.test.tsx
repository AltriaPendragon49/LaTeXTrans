import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"

import { PAPER_PREVIEW_API_BASE_URL } from "@/api-base"
import i18n from "@/i18n"
import { PaperDetailWorkspace } from "@/features/community-paper/components/PaperDetailWorkspace"
import type { CommunityPaper, CommunityPaperReader } from "@/types/community"

vi.mock("@/features/community-paper/services/community-paper-api", () => ({
  getCommunityPaperSimilar: vi.fn(),
}))

const paper: CommunityPaper = {
  id: "paper-1",
  source: "arxiv",
  arxiv_id: "2604.15395",
  arxiv_url: "https://arxiv.org/abs/2604.15395",
  title: "Foundation Models in Robotics",
  authors: ["Ada Lovelace"],
  categories: ["cs.RO"],
  abstract_raw: "A source abstract.",
  abstract_translated: "A translated abstract.",
  community_status: "official",
  trans_status: "completed",
  created_at: "2026-04-16T00:00:00Z",
  official_published_at: "2026-04-16T02:00:00Z",
  community_selected_task_id: "task-1",
  community_selected_asset_id: "asset-1",
}

const reader: CommunityPaperReader = {
  preferred_mode: "bilingual_compare",
  available_modes: ["source", "translated_pdf", "bilingual_compare"],
  source: {
    kind: "source_pdf",
    url: "/api/papers/paper-1/source-pdf",
  },
  translated: {
    kind: "translated_pdf",
    url: "/api/papers/paper-1/translated-pdf",
  },
  state: "translated_ready",
}

function renderWorkspace() {
  render(
    <MemoryRouter>
      <PaperDetailWorkspace
        paper={paper}
        preview={null}
        readerState="ready"
        reader={reader}
        preferredMode="bilingual_compare"
        structuredInsights={null}
        originalSourceUrl="https://arxiv.org/abs/2604.15395"
        abstractText="A source abstract."
        canDownload
        actionError={null}
      />
    </MemoryRouter>,
  )
}

describe("PaperDetailWorkspace", () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    window.localStorage.clear()
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 2048,
    })
    await i18n.changeLanguage("en")
  })

  it("defaults the desktop reader/sidebar split to the balanced reading layout", () => {
    renderWorkspace()

    expect(screen.getByTestId("paper-detail-top-panels")).toHaveStyle({
      gridTemplateColumns: "0.74fr 12px 0.26fr",
    })
  })

  it("does not reuse the older wide-reader split cache as the default layout", () => {
    window.localStorage.setItem("community-paper-reader-split-ratio-v2", "0.8")

    renderWorkspace()

    expect(screen.getByTestId("paper-detail-top-panels")).toHaveStyle({
      gridTemplateColumns: "0.74fr 12px 0.26fr",
    })
  })

  it("loads PDF preview iframes from the dedicated preview API base", () => {
    renderWorkspace()

    expect(screen.getByTestId("paper-bilingual-source-pdf-reader")).toHaveAttribute(
      "src",
      `${PAPER_PREVIEW_API_BASE_URL}/api/papers/paper-1/source-pdf#page=1&view=FitH&pagemode=none&toolbar=0&navpanes=0&scrollbar=0`,
    )
    expect(screen.getByTestId("paper-bilingual-translated-pdf-reader")).toHaveAttribute(
      "src",
      `${PAPER_PREVIEW_API_BASE_URL}/api/papers/paper-1/translated-pdf#page=1&view=FitH&pagemode=none&toolbar=0&navpanes=0&scrollbar=0`,
    )
  })
})
