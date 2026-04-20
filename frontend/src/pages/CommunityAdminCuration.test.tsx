import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n"
import CommunityAdminCurationPage from "@/pages/community-admin-curation"

const {
  submitAdminArxivCurationBatch,
  getAdminCurationBatch,
  submitAdminUploadCurationBatch,
  loadUserSettings,
} = vi.hoisted(() => ({
  submitAdminArxivCurationBatch: vi.fn(),
  getAdminCurationBatch: vi.fn(),
  submitAdminUploadCurationBatch: vi.fn(),
  loadUserSettings: vi.fn(),
}))

const adminCurationStoreState = vi.hoisted(() => ({
  config: {
    source_language: "en",
    target_language: "zh",
  },
  loadUserSettings,
}))

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    isAuthenticated: true,
    user: { roles: ["admin"] },
  }),
}))

vi.mock("@/features/translation-workflow/store/useTranslationStore", () => ({
  useTranslationStore: (selector?: (state: typeof adminCurationStoreState) => unknown) =>
    selector ? selector(adminCurationStoreState) : adminCurationStoreState,
}))

vi.mock("@/lib/community-api", () => ({
  submitAdminArxivCurationBatch,
  getAdminCurationBatch,
  submitAdminUploadCurationBatch,
}))

describe("CommunityAdminCurationPage", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en")
    submitAdminArxivCurationBatch.mockReset()
    getAdminCurationBatch.mockReset()
    submitAdminUploadCurationBatch.mockReset()
    loadUserSettings.mockReset()
  })

  it("parses one arXiv id per line, removes duplicates, and submits the deduplicated batch", async () => {
    submitAdminArxivCurationBatch.mockResolvedValue({
      batch_id: "batch-1",
      status: "queued",
      items: [],
    })

    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <CommunityAdminCurationPage />
      </MemoryRouter>,
    )

    await user.type(
      screen.getByLabelText("arXiv ID"),
      "2312.00752{enter}2106.09685{enter}2312.00752{enter}2104.09864",
    )

    expect(screen.getByText("IDs ready: 3")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Submit arXiv paper" }))

    await waitFor(() => {
      expect(submitAdminArxivCurationBatch).toHaveBeenCalledWith({
        arxiv_ids: ["2312.00752", "2106.09685", "2104.09864"],
        source_language: "en",
        target_language: "zh",
      })
    })
  })
})
