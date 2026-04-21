import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter, Route, Routes } from "react-router-dom"

import i18n from "@/i18n"
import FavoritesPage from "@/pages/favorites"

const listFavoriteFoldersMock = vi.fn()
const createFavoriteFolderMock = vi.fn()
const renameFavoriteFolderMock = vi.fn()
const deleteFavoriteFolderMock = vi.fn()
const getFavoriteFolderPapersMock = vi.fn()
const toastSuccessMock = vi.fn()
const toastErrorMock = vi.fn()

vi.mock("@/features/community-paper/services/community-paper-api", () => ({
  listFavoriteFolders: (...args: unknown[]) => listFavoriteFoldersMock(...args),
  createFavoriteFolder: (...args: unknown[]) => createFavoriteFolderMock(...args),
  renameFavoriteFolder: (...args: unknown[]) => renameFavoriteFolderMock(...args),
  deleteFavoriteFolder: (...args: unknown[]) => deleteFavoriteFolderMock(...args),
  getFavoriteFolderPapers: (...args: unknown[]) => getFavoriteFolderPapersMock(...args),
}))

vi.mock("sonner", () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccessMock(...args),
    error: (...args: unknown[]) => toastErrorMock(...args),
  },
}))

describe("FavoritesPage", () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    await i18n.changeLanguage("en")
    listFavoriteFoldersMock.mockResolvedValue({
      items: [
        {
          id: "folder-1",
          name: "Vision",
          paper_count: 1,
          created_at: "2026-04-21T00:00:00Z",
          updated_at: "2026-04-21T00:00:00Z",
        },
      ],
    })
    getFavoriteFolderPapersMock.mockResolvedValue({
      folder: {
        id: "folder-1",
        name: "Vision",
        paper_count: 1,
        created_at: "2026-04-21T00:00:00Z",
        updated_at: "2026-04-21T00:00:00Z",
      },
      items: [
        {
          id: "paper-1",
          source: "arxiv",
          arxiv_id: "2504.00001",
          title: "Visual Token Routing",
          authors: ["Ada Lovelace"],
          categories: ["cs.CV"],
          abstract_raw: "Routing paper abstract",
          abstract_translated: "Routing paper abstract",
          community_status: "official",
          trans_status: "completed",
          created_at: "2026-04-21T00:00:00Z",
          official_published_at: "2026-04-21T00:00:00Z",
          community_selected_task_id: "task-1",
          community_selected_asset_id: "asset-1",
          like_count: 5,
          favorite_count: 2,
          comment_count: 0,
          view_count: 9,
        },
      ],
      total: 1,
    })
  })

  it("renders folders and the selected folder paper list", async () => {
    render(
      <MemoryRouter initialEntries={["/favorites/folder-1"]}>
        <Routes>
          <Route path="/favorites" element={<FavoritesPage />} />
          <Route path="/favorites/:folderId" element={<FavoritesPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByRole("heading", { name: "Favorites" })).toBeInTheDocument()
    const paperTitle = await screen.findByText("Visual Token Routing")
    expect(paperTitle.closest("a")).toHaveAttribute("href", "/paper/paper-1")
    expect(getFavoriteFolderPapersMock).toHaveBeenCalledWith("folder-1")
  })

  it("creates a folder and keeps it visible in the folder list", async () => {
    const user = userEvent.setup()
    listFavoriteFoldersMock.mockResolvedValue({ items: [] })
    createFavoriteFolderMock.mockResolvedValue({
      folder: {
        id: "folder-2",
        name: "Agents",
        paper_count: 0,
        created_at: "2026-04-21T00:00:00Z",
        updated_at: "2026-04-21T00:00:00Z",
      },
    })

    render(
      <MemoryRouter initialEntries={["/favorites"]}>
        <Routes>
          <Route path="/favorites" element={<FavoritesPage />} />
          <Route path="/favorites/:folderId" element={<FavoritesPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByRole("heading", { name: "Favorites" })
    await user.type(screen.getByRole("textbox", { name: "Create a folder" }), "Agents")
    await user.click(screen.getByRole("button", { name: "Create" }))

    await waitFor(() => {
      expect(createFavoriteFolderMock).toHaveBeenCalledWith("Agents")
    })
    expect(await screen.findByRole("heading", { level: 2, name: "Agents" })).toBeInTheDocument()
  })

  it("renames and deletes folders from the management list", async () => {
    const user = userEvent.setup()
    const promptSpy = vi.spyOn(window, "prompt").mockReturnValue("Vision + OCR")
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true)

    renameFavoriteFolderMock.mockResolvedValue({
      folder: {
        id: "folder-1",
        name: "Vision + OCR",
        paper_count: 1,
        created_at: "2026-04-21T00:00:00Z",
        updated_at: "2026-04-21T00:00:00Z",
      },
    })
    deleteFavoriteFolderMock.mockResolvedValue({
      folder_id: "folder-1",
      deleted: true,
    })

    render(
      <MemoryRouter initialEntries={["/favorites"]}>
        <Routes>
          <Route path="/favorites" element={<FavoritesPage />} />
          <Route path="/favorites/:folderId" element={<FavoritesPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByText("Vision")
    await user.click(screen.getByRole("button", { name: "Rename Vision" }))
    await waitFor(() => {
      expect(renameFavoriteFolderMock).toHaveBeenCalledWith("folder-1", "Vision + OCR")
    })
    expect(await screen.findByText("Vision + OCR")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Delete Vision + OCR" }))
    await waitFor(() => {
      expect(confirmSpy).toHaveBeenCalled()
      expect(deleteFavoriteFolderMock).toHaveBeenCalledWith("folder-1")
    })

    promptSpy.mockRestore()
    confirmSpy.mockRestore()
  })
})
