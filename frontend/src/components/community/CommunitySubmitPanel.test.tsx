import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"

import i18n from "@/i18n"
import { CommunitySubmitPanel } from "@/components/community/CommunitySubmitPanel"

const submitCommunityPaperFromArxivMock = vi.fn()
const submitCommunityPaperFromUploadMock = vi.fn()
const loadUserSettingsMock = vi.fn()
const navigateMock = vi.fn()

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    user: { email: "test@example.com" },
  }),
}))

vi.mock("@/store/useStore", () => ({
  useStore: () => ({
    config: {
      source_language: "en",
      target_language: "zh",
      advanced_config: {},
    },
    loadUserSettings: loadUserSettingsMock,
  }),
}))

vi.mock("@/lib/community-api", () => ({
  submitCommunityPaperFromArxiv: (...args: unknown[]) => submitCommunityPaperFromArxivMock(...args),
  submitCommunityPaperFromUpload: (...args: unknown[]) => submitCommunityPaperFromUploadMock(...args),
}))

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom")
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

describe("CommunitySubmitPanel", () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    await i18n.changeLanguage("en")
    loadUserSettingsMock.mockResolvedValue(undefined)
  })

  it("renders idle guidance before any submit action", () => {
    render(
      <MemoryRouter>
        <CommunitySubmitPanel />
      </MemoryRouter>,
    )

    expect(screen.getByText("Start the Week 1 paper-first path")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Submit arXiv paper" })).toBeInTheDocument()
  })

  it("submits an arXiv paper and navigates to the paper detail page", async () => {
    submitCommunityPaperFromArxivMock.mockResolvedValue({
      paper: { id: "paper-arxiv" },
      task: { task_id: "task-arxiv", status: "processing" },
      admission_result: "created",
    })

    render(
      <MemoryRouter>
        <CommunitySubmitPanel />
      </MemoryRouter>,
    )

    await userEvent.type(screen.getByLabelText("arXiv ID"), "2503.01010")
    await userEvent.click(screen.getByRole("button", { name: "Submit arXiv paper" }))

    await waitFor(() => {
      expect(submitCommunityPaperFromArxivMock).toHaveBeenCalledWith(
        expect.objectContaining({
          arxiv_id: "2503.01010",
          source_language: "en",
          target_language: "zh",
        }),
      )
      expect(navigateMock).toHaveBeenCalledWith("/paper/paper-arxiv")
    })
  })

  it("submits an uploaded paper and navigates to the paper detail page", async () => {
    submitCommunityPaperFromUploadMock.mockResolvedValue({
      paper: { id: "paper-upload" },
      task: { task_id: "task-upload", status: "pending" },
      admission_result: "created",
    })

    render(
      <MemoryRouter>
        <CommunitySubmitPanel />
      </MemoryRouter>,
    )

    await userEvent.click(screen.getByRole("tab", { name: "Upload source" }))

    const file = new File(["zip-bytes"], "paper.zip", { type: "application/zip" })
    await userEvent.upload(screen.getByLabelText("Upload paper source"), file)
    await userEvent.click(screen.getByRole("button", { name: "Submit uploaded paper" }))

    await waitFor(() => {
      expect(submitCommunityPaperFromUploadMock).toHaveBeenCalledWith(
        file,
        expect.objectContaining({
          source_language: "en",
          target_language: "zh",
        }),
      )
      expect(navigateMock).toHaveBeenCalledWith("/paper/paper-upload")
    })
  })

  it("renders an inline error and allows retry after a failed submit", async () => {
    submitCommunityPaperFromArxivMock.mockRejectedValueOnce(new Error("submit failed"))

    render(
      <MemoryRouter>
        <CommunitySubmitPanel />
      </MemoryRouter>,
    )

    await userEvent.type(screen.getByLabelText("arXiv ID"), "2503.01010")
    await userEvent.click(screen.getByRole("button", { name: "Submit arXiv paper" }))

    expect(await screen.findByText("submit failed")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Submit arXiv paper" })).toBeEnabled()
  })

  it("disables submit controls while a submit request is pending", async () => {
    let resolvePromise: ((value: unknown) => void) | undefined
    submitCommunityPaperFromArxivMock.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolvePromise = resolve
        }),
    )

    render(
      <MemoryRouter>
        <CommunitySubmitPanel />
      </MemoryRouter>,
    )

    await userEvent.type(screen.getByLabelText("arXiv ID"), "2503.01010")
    await userEvent.click(screen.getByRole("button", { name: "Submit arXiv paper" }))

    expect(screen.getByRole("button", { name: "Submitting paper..." })).toBeDisabled()

    resolvePromise?.({
      paper: { id: "paper-arxiv" },
      task: { task_id: "task-arxiv", status: "processing" },
      admission_result: "created",
    })

    await waitFor(() => {
      expect(navigateMock).toHaveBeenCalledWith("/paper/paper-arxiv")
    })
  })
})
