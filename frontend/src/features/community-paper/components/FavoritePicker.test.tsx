import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"

import { FavoritePicker } from "@/features/community-paper/components/FavoritePicker"
import i18n from "@/i18n"

const getPaperFavoriteFoldersMock = vi.fn()
const createFavoriteFolderMock = vi.fn()
const updatePaperFavoriteFoldersMock = vi.fn()
const navigateMock = vi.fn()
const toastSuccessMock = vi.fn()
const toastErrorMock = vi.fn()

let mockAuthState = {
  isAuthenticated: true,
}

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => mockAuthState,
}))

vi.mock("@/features/community-paper/services/community-paper-api", () => ({
  getPaperFavoriteFolders: (...args: unknown[]) => getPaperFavoriteFoldersMock(...args),
  createFavoriteFolder: (...args: unknown[]) => createFavoriteFolderMock(...args),
  updatePaperFavoriteFolders: (...args: unknown[]) => updatePaperFavoriteFoldersMock(...args),
}))

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom")
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

vi.mock("sonner", () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccessMock(...args),
    error: (...args: unknown[]) => toastErrorMock(...args),
  },
}))

describe("FavoritePicker", () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    await i18n.changeLanguage("en")
    mockAuthState = { isAuthenticated: true }
    getPaperFavoriteFoldersMock.mockResolvedValue({
      paper_id: "paper-1",
      items: [
        {
          id: "folder-1",
          name: "Core",
          paper_count: 2,
          created_at: "2026-04-21T00:00:00Z",
          updated_at: "2026-04-21T00:00:00Z",
        },
      ],
      selected_folder_ids: ["folder-1"],
      favorited: true,
      favorite_folder_count: 1,
    })
    createFavoriteFolderMock.mockResolvedValue({
      folder: {
        id: "folder-2",
        name: "Fresh",
        paper_count: 0,
        created_at: "2026-04-21T00:00:00Z",
        updated_at: "2026-04-21T00:00:00Z",
      },
    })
    updatePaperFavoriteFoldersMock.mockResolvedValue({
      paper_id: "paper-1",
      favorited: true,
      favorite_folder_count: 2,
      favorite_count: 8,
      selected_folder_ids: ["folder-1", "folder-2"],
    })
  })

  it("highlights the trigger when the paper is already favorited", () => {
    render(
      <MemoryRouter>
        <FavoritePicker
          paperId="paper-1"
          favoriteCount={3}
          viewerState={{ liked: false, favorited: true, favorite_folder_count: 1 }}
          variant="icon"
        />
      </MemoryRouter>,
    )

    expect(screen.getByRole("button", { name: "Favorited" })).toHaveAttribute("aria-pressed", "true")
  })

  it("creates a folder, auto-selects it, and waits for confirm before saving", async () => {
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <FavoritePicker
          paperId="paper-1"
          favoriteCount={3}
          viewerState={{ liked: false, favorited: true, favorite_folder_count: 1 }}
          variant="card"
        />
      </MemoryRouter>,
    )

    await user.click(screen.getByRole("button", { name: "Favorited" }))
    await screen.findByText("Core")

    await user.type(screen.getByRole("textbox", { name: "Create a folder" }), "Fresh")
    await user.click(screen.getByRole("button", { name: "Create" }))

    await waitFor(() => {
      expect(createFavoriteFolderMock).toHaveBeenCalledWith("Fresh")
    })
    expect(updatePaperFavoriteFoldersMock).not.toHaveBeenCalled()

    const confirmButton = screen.getByRole("button", { name: "Save favorites" })
    expect(confirmButton).toBeEnabled()

    await user.click(confirmButton)

    await waitFor(() => {
      expect(updatePaperFavoriteFoldersMock).toHaveBeenCalledWith("paper-1", ["folder-1", "folder-2"])
    })
  })

  it("redirects unauthenticated users to login before opening the picker", async () => {
    const user = userEvent.setup()
    mockAuthState = { isAuthenticated: false }

    render(
      <MemoryRouter>
        <FavoritePicker
          paperId="paper-1"
          favoriteCount={0}
          viewerState={{ liked: false, favorited: false, favorite_folder_count: 0 }}
          variant="icon"
        />
      </MemoryRouter>,
    )

    await user.click(screen.getByRole("button", { name: "Favorite paper" }))

    expect(navigateMock).toHaveBeenCalledWith("/login")
    expect(getPaperFavoriteFoldersMock).not.toHaveBeenCalled()
  })
})
