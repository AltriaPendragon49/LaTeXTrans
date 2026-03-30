import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"

import i18n from "@/i18n"
import CommunityFeedPage from "@/pages/CommunityFeed"

const useCommunityPapersMock = vi.fn()
const navigateMock = vi.fn()

vi.mock("@/hooks/use-community-papers", () => ({
  useCommunityPapers: (...args: unknown[]) => useCommunityPapersMock(...args),
}))

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom")
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

describe("CommunityFeedPage agent-first", () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    localStorage.clear()
    await i18n.changeLanguage("en")
    useCommunityPapersMock.mockReturnValue({
      items: [],
      total: 0,
      loading: false,
      error: null,
      refetch: vi.fn(),
    })
  })

  it("renders a single agent composer and removes summary cards", () => {
    render(
      <MemoryRouter>
        <CommunityFeedPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole("textbox", { name: "Ask the paper agent" })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Ask the paper agent, then move into a focused reader workspace." })).toBeInTheDocument()
    expect(screen.getByText("Paper search")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Enable external search" })).toHaveAttribute("aria-pressed", "false")
    expect(
      screen.queryByText(
        "Officially published translations lead the community surface. User fallback papers only hold a community slot while official coverage is still missing.",
      ),
    ).not.toBeInTheDocument()
    expect(screen.queryByText("Official")).not.toBeInTheDocument()
    expect(screen.queryByText("Tracked")).not.toBeInTheDocument()
    expect(screen.queryByRole("textbox", { name: "Search community papers" })).not.toBeInTheDocument()
  })

  it("routes the first submit into a dedicated conversation workspace", () => {
    render(
      <MemoryRouter>
        <CommunityFeedPage />
      </MemoryRouter>,
    )

    fireEvent.change(screen.getByRole("textbox", { name: "Ask the paper agent" }), {
      target: { value: "What is V-JEPA 2.1 about?" },
    })
    fireEvent.click(screen.getByRole("button", { name: "Enable external search" }))
    fireEvent.click(screen.getByRole("button", { name: "Run agent" }))

    expect(navigateMock).toHaveBeenCalledTimes(1)
    const [target, options] = navigateMock.mock.calls[0]
    expect(String(target)).toMatch(/^\/agent\//)
    expect(options).toMatchObject({
      state: {
        seedInput: "What is V-JEPA 2.1 about?",
        seedSkillToggles: {
          external_search: true,
        },
      },
    })
  })
})
