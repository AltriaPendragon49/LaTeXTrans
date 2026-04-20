import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"

import i18n from "@/i18n"
import HomePage from "@/pages/home"

vi.mock("@/features/community-paper/components/CommunityFeedSurface", () => ({
  default: () => <div data-testid="community-feed-surface">feed</div>,
}))

describe("HomePage", () => {
  it("removes the oversized hero and keeps the page focused on search/feed content", async () => {
    await i18n.changeLanguage("en")

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    )

    expect(screen.getByTestId("community-feed-surface")).toBeInTheDocument()
    expect(screen.queryByRole("heading", { name: "Community Feed" })).not.toBeInTheDocument()
    expect(screen.queryByRole("link", { name: "Translate" })).not.toBeInTheDocument()
  })
})
