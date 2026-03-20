import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"

import i18n from "@/i18n"
import CommunityFeedPage from "@/pages/CommunityFeed"

const useCommunityPapersMock = vi.fn()

vi.mock("@/hooks/use-community-papers", () => ({
  useCommunityPapers: (...args: unknown[]) => useCommunityPapersMock(...args),
}))

describe("CommunityFeedPage", () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    await i18n.changeLanguage("en")
  })

  it("renders the feed shell and defaults to latest sort", () => {
    useCommunityPapersMock.mockReturnValue({
      items: [],
      total: 0,
      loading: false,
      error: null,
      refetch: vi.fn(),
    })

    render(
      <MemoryRouter>
        <CommunityFeedPage />
      </MemoryRouter>,
    )

    expect(useCommunityPapersMock).toHaveBeenCalledWith("latest", "")
    expect(screen.getByRole("heading", { name: "Community Feed" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Latest" })).toBeInTheDocument()
  })

  it("renders loading placeholders while the feed is pending", () => {
    useCommunityPapersMock.mockReturnValue({
      items: [],
      total: 0,
      loading: true,
      error: null,
      refetch: vi.fn(),
    })

    render(
      <MemoryRouter>
        <CommunityFeedPage />
      </MemoryRouter>,
    )

    expect(screen.getByTestId("community-feed-loading")).toBeInTheDocument()
  })

  it("re-renders when switching sort tabs", () => {
    useCommunityPapersMock.mockReturnValue({
      items: [],
      total: 0,
      loading: false,
      error: null,
      refetch: vi.fn(),
    })

    render(
      <MemoryRouter>
        <CommunityFeedPage />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole("button", { name: "Translated" }))

    expect(useCommunityPapersMock).toHaveBeenLastCalledWith("translated", "")
  })

  it("renders an empty state when no papers match the current view", () => {
    useCommunityPapersMock.mockReturnValue({
      items: [],
      total: 0,
      loading: false,
      error: null,
      refetch: vi.fn(),
    })

    render(
      <MemoryRouter>
        <CommunityFeedPage />
      </MemoryRouter>,
    )

    expect(screen.getByText("No community papers match this view yet")).toBeInTheDocument()
  })

  it("renders an error state when the feed fails", () => {
    useCommunityPapersMock.mockReturnValue({
      items: [],
      total: 0,
      loading: false,
      error: "boom",
      refetch: vi.fn(),
    })

    render(
      <MemoryRouter>
        <CommunityFeedPage />
      </MemoryRouter>,
    )

    expect(screen.getByText("Unable to load the community feed")).toBeInTheDocument()
  })
})
