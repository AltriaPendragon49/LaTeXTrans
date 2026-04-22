import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"

import i18n from "@/i18n"
import HomePage from "@/pages/home"

vi.mock("@/features/community-paper/components/CommunityFeedSurface", () => ({
  default: () => <div data-testid="community-feed-surface">feed</div>,
}))

describe("HomePage", () => {
  it("renders the community feed surface on the homepage", async () => {
    await i18n.changeLanguage("en")

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    )

    expect(screen.getByTestId("community-feed-surface")).toBeInTheDocument()
  })
})
