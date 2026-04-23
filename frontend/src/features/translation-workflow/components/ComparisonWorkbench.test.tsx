import type { ReactNode } from "react"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"

import { API_BASE_URL } from "@/api-base"
import i18n from "@/i18n"
import { ComparisonWorkbench } from "@/features/translation-workflow/components/ComparisonWorkbench"
import { setDesktopViewport, setMobileViewport } from "@/test/viewport"

const mockNavigate = vi.fn()
const mockResetTranslationState = vi.fn()
const mockTranslationTaskState: {
  taskId: string | null
  arxivId: string | null
} = {
  taskId: "task-123",
  arxivId: "2401.00001",
}

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom")
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

vi.mock("@/features/translation-workflow/hooks/useTranslationTask", () => ({
  useTranslationTask: () => ({
    taskId: mockTranslationTaskState.taskId,
    arxivId: mockTranslationTaskState.arxivId,
    resetTranslationState: mockResetTranslationState,
  }),
}))

vi.mock("@/features/translation-workflow/components/TerminologyTable", () => ({
  TerminologyTable: () => <div>Glossary action</div>,
}))

vi.mock("@/ui/primitives/resizable", () => ({
  ResizablePanelGroup: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  ResizablePanel: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  ResizableHandle: () => <div aria-hidden="true" />,
}))

describe("ComparisonWorkbench layout", () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    mockTranslationTaskState.taskId = "task-123"
    mockTranslationTaskState.arxivId = "2401.00001"
    await i18n.changeLanguage("en")
    setDesktopViewport()
  })

  it("uses a compact borderless header and opens both pdf readers through the shared viewer surface", () => {
    render(
      <MemoryRouter>
        <ComparisonWorkbench />
      </MemoryRouter>,
    )

    const workbench = screen.getByTestId("comparison-workbench")
    const header = screen.getByTestId("comparison-header")
    const previewRegion = screen.getByTestId("comparison-preview-region")
    const viewToggle = screen.getByTestId("comparison-view-toggle")
    const sourceReader = screen.getByTitle("Original PDF (source document)")
    const translatedReader = screen.getByTitle("Translated PDF (translation result)")

    expect(workbench).toHaveClass("w-full", "min-w-0", "flex-1", "overflow-hidden")
    expect(workbench).toHaveClass("gap-3", "py-3")
    expect(header).toHaveClass("grid", "gap-2", "md:items-center")
    expect(viewToggle).toHaveClass("justify-self-center")
    expect(previewRegion).toHaveClass("flex-1", "min-h-[560px]", "min-w-0")
    expect(previewRegion.className).not.toContain("border")
    expect(screen.queryByText("Reading layout")).not.toBeInTheDocument()
    expect(screen.queryByText("Switch between split comparison and a focused single view.")).not.toBeInTheDocument()
    expect(sourceReader).toHaveAttribute(
      "src",
      `${API_BASE_URL}/api/preview/task-123/source-pdf#page=1&view=FitH&pagemode=none&toolbar=0&navpanes=0&scrollbar=0`,
    )
    expect(translatedReader).toHaveAttribute(
      "src",
      `${API_BASE_URL}/api/preview/task-123/pdf#page=1&view=FitH&pagemode=none&toolbar=0&navpanes=0&scrollbar=0`,
    )
    expect(sourceReader.tagName).toBe("IFRAME")
    expect(translatedReader.tagName).toBe("IFRAME")
  })

  it("keeps the centered toggle available when switching to single view", async () => {
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <ComparisonWorkbench />
      </MemoryRouter>,
    )

    await user.click(screen.getByRole("radio", { name: "Single view" }))

    expect(screen.getByTestId("comparison-view-toggle")).toHaveClass("justify-self-center")
    const translatedReader = screen.getByTitle("Translated PDF (translation result)")
    expect(screen.getAllByTitle("Translated PDF (translation result)")).toHaveLength(1)
    expect(translatedReader).toHaveAttribute(
      "src",
      `${API_BASE_URL}/api/preview/task-123/pdf#page=1&view=FitH&pagemode=none&toolbar=0&navpanes=0&scrollbar=0`,
    )
    expect(screen.queryByTitle("Original PDF (source document)")).not.toBeInTheDocument()
  })

  it("routes source preview through the backend proxy when only an arxiv id is available", () => {
    mockTranslationTaskState.taskId = null

    render(
      <MemoryRouter>
        <ComparisonWorkbench />
      </MemoryRouter>,
    )

    const sourceReader = screen.getByTitle("Original PDF (source document)")

    expect(sourceReader).toHaveAttribute(
      "src",
      "https://arxiv.org/pdf/2401.00001.pdf#page=1&view=FitH&pagemode=none&toolbar=0&navpanes=0&scrollbar=0",
    )
    expect(sourceReader.tagName).toBe("IFRAME")
  })

  it("defaults narrow screens to the translated single-document preview mode", () => {
    setMobileViewport()

    render(
      <MemoryRouter>
        <ComparisonWorkbench />
      </MemoryRouter>,
    )

    expect(screen.getByTitle("Translated PDF (translation result)")).toBeInTheDocument()
    expect(screen.queryByTitle("Original PDF (source document)")).not.toBeInTheDocument()
  })
})
