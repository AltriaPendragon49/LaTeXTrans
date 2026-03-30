import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom"

import i18n from "@/i18n"
import CommunityFeedPage from "@/pages/CommunityFeed"

const useCommunityPapersMock = vi.fn()

vi.mock("@/hooks/use-community-papers", () => ({
  useCommunityPapers: (...args: unknown[]) => useCommunityPapersMock(...args),
}))

function ConversationRouteSpy() {
  const location = useLocation()

  return <pre data-testid="conversation-state">{JSON.stringify(location.state)}</pre>
}

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
    expect(screen.getByRole("heading", { name: i18n.t("community.feed.launchTitle") })).toBeInTheDocument()
    expect(screen.getByText(i18n.t("community.agent.intent.search"))).toBeInTheDocument()
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

    expect(screen.getByText("Exploring more papers")).toBeInTheDocument()
  })

  it("opens a seeded agent conversation with the selected prompt and tool toggles", async () => {
    useCommunityPapersMock.mockReturnValue({
      items: [],
      total: 0,
      loading: false,
      error: null,
      refetch: vi.fn(),
    })

    const user = userEvent.setup()

    render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<CommunityFeedPage />} />
          <Route path="/agent/:conversationId" element={<ConversationRouteSpy />} />
        </Routes>
      </MemoryRouter>,
    )

    await user.type(screen.getByRole("textbox", { name: i18n.t("community.agent.aria") }), "Explain this paper")
    await user.click(screen.getByRole("button", { name: i18n.t("community.agent.externalSearch.label") }))
    await user.click(screen.getByRole("button", { name: i18n.t("community.agent.run") }))

    expect(JSON.parse(screen.getByTestId("conversation-state").textContent ?? "{}")).toMatchObject({
      seedInput: "Explain this paper",
      seedSkillToggles: {
        external_search: true,
      },
    })
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
