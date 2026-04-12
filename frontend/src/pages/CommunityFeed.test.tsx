import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"

import i18n from "@/i18n"
import CommunityFeedPage from "@/pages/CommunityFeed"

const useCommunityPapersMock = vi.fn()
const useAuthMock = vi.fn()
const deleteCommunityPaperMock = vi.fn()

vi.mock("@/hooks/use-community-papers", () => ({
  useCommunityPapers: (...args: unknown[]) => useCommunityPapersMock(...args),
}))

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => useAuthMock(),
}))

vi.mock("@/lib/community-api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/community-api")>("@/lib/community-api")
  return {
    ...actual,
    deleteCommunityPaper: (...args: unknown[]) => deleteCommunityPaperMock(...args),
  }
})

vi.mock("@/components/community/PaperCard", () => ({
  PaperCard: ({
    paper,
    onDelete,
  }: {
    paper: { title: string }
    onDelete?: (paper: { title: string }) => void
  }) => (
    <div>
      <span>{paper.title}</span>
      {onDelete ? (
        <button type="button" onClick={() => onDelete(paper)}>
          Delete paper
        </button>
      ) : null}
    </div>
  ),
}))

describe("CommunityFeedPage", () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    await i18n.changeLanguage("en")
    useAuthMock.mockReturnValue({
      user: null,
    })
    useCommunityPapersMock.mockReturnValue({
      items: [],
      total: 0,
      loading: false,
      error: null,
      refetch: vi.fn(),
    })
    vi.stubGlobal("confirm", vi.fn(() => true))
  })

  it("renders the search-first feed shell and defaults to the latest sort", () => {
    render(
      <MemoryRouter>
        <CommunityFeedPage />
      </MemoryRouter>,
    )

    expect(useCommunityPapersMock).toHaveBeenCalledWith("latest", "")
    expect(screen.getByRole("textbox", { name: "Search community papers" })).toBeInTheDocument()
    expect(screen.queryByRole("textbox", { name: "Ask the paper agent" })).not.toBeInTheDocument()
  })

  it("does not render the translated sort tab", () => {
    render(
      <MemoryRouter>
        <CommunityFeedPage />
      </MemoryRouter>,
    )

    expect(screen.getByText("Hot")).toBeInTheDocument()
    expect(screen.getByText("Latest")).toBeInTheDocument()
    expect(screen.queryByText("Translated")).not.toBeInTheDocument()
  })

  it("updates the queried feed when the search is submitted", async () => {
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <CommunityFeedPage />
      </MemoryRouter>,
    )

    await user.type(screen.getByRole("textbox", { name: "Search community papers" }), "transformers")
    await user.click(screen.getByRole("button", { name: "Community search" }))

    expect(useCommunityPapersMock).toHaveBeenLastCalledWith("latest", "transformers")
  })

  it("shows admin-only delete affordances and calls the delete api", async () => {
    const refetch = vi.fn()
    const user = userEvent.setup()

    useAuthMock.mockReturnValue({
      user: {
        id: "user-1",
        roles: ["admin"],
      },
    })
    useCommunityPapersMock.mockReturnValue({
      items: [
        {
          id: "paper-1",
          title: "Admin paper",
        },
      ],
      total: 1,
      loading: false,
      error: null,
      refetch,
    })
    deleteCommunityPaperMock.mockResolvedValue({
      job_id: "job-1",
      paper_id: "paper-1",
      status: "queued",
    })

    render(
      <MemoryRouter>
        <CommunityFeedPage />
      </MemoryRouter>,
    )

    await user.click(screen.getByRole("button", { name: "Delete paper" }))

    expect(deleteCommunityPaperMock).toHaveBeenCalledWith("paper-1")
    expect(refetch).toHaveBeenCalled()
  })

  it("hides delete affordances from non-admin users", () => {
    useAuthMock.mockReturnValue({
      user: {
        id: "user-1",
        roles: ["user"],
      },
    })
    useCommunityPapersMock.mockReturnValue({
      items: [
        {
          id: "paper-1",
          title: "Reader paper",
        },
      ],
      total: 1,
      loading: false,
      error: null,
      refetch: vi.fn(),
    })

    render(
      <MemoryRouter>
        <CommunityFeedPage />
      </MemoryRouter>,
    )

    expect(screen.queryByRole("button", { name: "Delete paper" })).not.toBeInTheDocument()
  })
})
