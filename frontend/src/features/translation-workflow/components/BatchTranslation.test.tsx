import { StrictMode, createRef } from "react"
import { act, fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"

import i18n from "@/i18n"
import { BatchTranslation, type BatchTranslationHandle } from "@/features/translation-workflow/components/BatchTranslation"
import {
  getTaskStatus,
  startBatchTranslation,
  startTranslation,
  uploadFile,
} from "@/lib/api"

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
}))

vi.mock("@/lib/api", () => ({
  startBatchTranslation: vi.fn(),
  getTaskStatus: vi.fn(),
  uploadFile: vi.fn(),
  startTranslation: vi.fn(),
}))

describe("BatchTranslation", () => {
  beforeEach(async () => {
    vi.useFakeTimers()
    vi.clearAllMocks()
    await i18n.changeLanguage("en")

    vi.mocked(startBatchTranslation).mockResolvedValue({
      batch_id: "batch-1",
      task_ids: ["task-1"],
      message: "Queued 1 task",
      queued_count: 1,
    })

    vi.mocked(getTaskStatus).mockResolvedValue({
      task_id: "task-1",
      status: "completed",
      progress: 100,
      stage: "done",
      message: "Translation completed successfully",
      detail_code: "compile_complete",
      detail_params: null,
    })

    vi.mocked(uploadFile).mockResolvedValue({
      task_id: "upload-task-1",
      status: "ready",
      message: "Uploaded",
      source_path: "/tmp/source",
    })
    vi.mocked(startTranslation).mockResolvedValue({
      task_id: "upload-task-1",
      status: "processing",
      message: "started",
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("continues batch polling under StrictMode and updates to terminal state", async () => {
    const ref = createRef<BatchTranslationHandle>()

    const { container } = render(
      <StrictMode>
        <MemoryRouter>
          <BatchTranslation ref={ref} />
        </MemoryRouter>
      </StrictMode>,
    )

    const input = container.querySelector("#batch-arxiv-input") as HTMLTextAreaElement | null
    expect(input).not.toBeNull()

    fireEvent.change(input!, { target: { value: "2106.09685" } })

    await act(async () => {
      ref.current?.submitCurrent()
      await Promise.resolve()
    })

    expect(startBatchTranslation).toHaveBeenCalledTimes(1)
    expect(screen.getByText("Task list")).toBeInTheDocument()
    expect(screen.getByText("Waiting")).toBeInTheDocument()

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000)
      await Promise.resolve()
    })

    expect(getTaskStatus).toHaveBeenCalledWith("task-1")
    expect(screen.getByText("Completed")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "View" })).toBeInTheDocument()
  })
})
