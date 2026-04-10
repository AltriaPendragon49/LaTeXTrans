import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"

import i18n from "@/i18n"
import CommunityFeedPage from "@/pages/CommunityFeed"

const useCommunityPapersMock = vi.fn()

vi.mock("@/hooks/use-community-papers", () => ({
  useCommunityPapers: (...args: unknown[]) => useCommunityPapersMock(...args),
}))

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    user: null,
  }),
}))

vi.mock("@/components/community/PaperCard", () => ({
  PaperCard: ({ paper }: { paper: { title: string } }) => <div>{paper.title}</div>,
}))

describe("CommunityFeedPage hidden agent entry", () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    await i18n.changeLanguage("en")
    useCommunityPapersMock.mockReturnValue({
      items: [{ id: "paper-1", title: "Visible paper" }],
      total: 1,
      loading: false,
      error: null,
      refetch: vi.fn(),
    })
  })

  it("removes the public agent composer and conversation launch copy", () => {
    render(
      <MemoryRouter>
        <CommunityFeedPage />
      </MemoryRouter>,
    )

    expect(screen.getByText("Visible paper")).toBeInTheDocument()
    expect(screen.queryByText("Paper Copilot")).not.toBeInTheDocument()
    expect(screen.queryByRole("textbox", { name: "Ask the paper agent" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Run agent" })).not.toBeInTheDocument()
  })
})
