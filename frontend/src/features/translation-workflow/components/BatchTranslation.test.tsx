import { StrictMode, createRef } from "react"
import { act, fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"

import i18n from "@/i18n"
import { BatchTranslation, type BatchTranslationHandle } from "@/features/translation-workflow/components/BatchTranslation"
import {
  getDailyLatexQuotaExceededMessage,
  getTaskStatus,
  startBatchUploadTranslation,
  startBatchTranslation,
  startTranslation,
  uploadFile,
} from "@/lib/api"
import { toast } from "sonner"
import { DEFAULT_ADVANCED_CONFIG } from "@/types/config"

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
}))

vi.mock("@/lib/api", () => ({
  startBatchTranslation: vi.fn(),
  startBatchUploadTranslation: vi.fn(),
  getTaskStatus: vi.fn(),
  uploadFile: vi.fn(),
  startTranslation: vi.fn(),
  getDailyLatexQuotaExceededMessage: vi.fn(),
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
    vi.mocked(startBatchUploadTranslation).mockResolvedValue({
      batch_id: "upload-batch-1",
      task_ids: ["upload-task-1", "upload-task-2"],
      message: "Queued 2 tasks",
      queued_count: 2,
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

  it("shows the quota-exceeded message when an arXiv batch exceeds the daily allowance", async () => {
    const ref = createRef<BatchTranslationHandle>()
    const onQuotaChanged = vi.fn()
    const quotaError = {
      response: {
        data: {
          detail: {
            code: "DAILY_LATEX_QUOTA_EXCEEDED",
            requested_count: 2,
            remaining: 0,
            limit: 3,
            used: 3,
            quota_date: "2026-05-07",
            reset_timezone: "Asia/Shanghai",
          },
        },
      },
    }

    vi.mocked(startBatchTranslation).mockRejectedValueOnce(quotaError)
    vi.mocked(getDailyLatexQuotaExceededMessage).mockReturnValueOnce(
      "Daily LaTeX translation quota exceeded. Requested 2, remaining 0.",
    )

    const { container } = render(
      <MemoryRouter>
        <BatchTranslation ref={ref} onQuotaChanged={onQuotaChanged} />
      </MemoryRouter>,
    )

    const input = container.querySelector("#batch-arxiv-input") as HTMLTextAreaElement | null
    expect(input).not.toBeNull()

    fireEvent.change(input!, { target: { value: "2106.09685\n1709.01015" } })

    await act(async () => {
      ref.current?.submitCurrent()
      await Promise.resolve()
    })

    expect(toast.error).toHaveBeenCalledWith(
      "Daily LaTeX translation quota exceeded. Requested 2, remaining 0.",
    )
    expect(onQuotaChanged).toHaveBeenCalledTimes(1)
  })

  it("submits uploaded files through the batch upload API", async () => {
    const ref = createRef<BatchTranslationHandle>()
    const onQuotaChanged = vi.fn()
    const advancedConfig = { ...structuredClone(DEFAULT_ADVANCED_CONFIG), translation_model: "test-model" }
    const firstFile = new File(["first"], "first.tex", { type: "application/x-tex" })
    const secondFile = new File(["second"], "second.zip", { type: "application/zip" })

    const { container } = render(
      <MemoryRouter>
        <BatchTranslation
          ref={ref}
          advancedConfig={advancedConfig}
          sourceLanguage="fr"
          targetLanguage="de"
          onQuotaChanged={onQuotaChanged}
        />
      </MemoryRouter>,
    )

    fireEvent.mouseDown(screen.getByRole("tab", { name: i18n.t("batch.batch_file_upload") }), { button: 0 })
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement
    expect(fileInput).not.toBeNull()

    fireEvent.change(fileInput, { target: { files: [firstFile, secondFile] } })

    await act(async () => {
      ref.current?.submitCurrent()
      await Promise.resolve()
    })

    expect(startBatchUploadTranslation).toHaveBeenCalledWith({
      files: [firstFile, secondFile],
      source_language: "fr",
      target_language: "de",
      advanced_config: advancedConfig,
    })
    expect(uploadFile).not.toHaveBeenCalled()
    expect(startTranslation).not.toHaveBeenCalled()
    expect(onQuotaChanged).toHaveBeenCalledTimes(1)
  })

  it("shows quota toast and refreshes quota when upload batch is rejected by daily allowance", async () => {
    const ref = createRef<BatchTranslationHandle>()
    const onQuotaChanged = vi.fn()
    const quotaError = {
      response: {
        data: {
          detail: {
            code: "DAILY_LATEX_QUOTA_EXCEEDED",
            requested_count: 2,
            remaining: 0,
            limit: 3,
            used: 3,
            quota_date: "2026-05-07",
            reset_timezone: "Asia/Shanghai",
          },
        },
      },
    }
    const quotaMessageKey = "task.error.dailyLatexQuotaExceeded"
    const firstFile = new File(["first"], "first.tex", { type: "application/x-tex" })
    const secondFile = new File(["second"], "second.zip", { type: "application/zip" })

    vi.mocked(startBatchUploadTranslation).mockRejectedValueOnce(quotaError)
    vi.mocked(getDailyLatexQuotaExceededMessage).mockReturnValueOnce(quotaMessageKey)

    const { container } = render(
      <MemoryRouter>
        <BatchTranslation ref={ref} onQuotaChanged={onQuotaChanged} />
      </MemoryRouter>,
    )

    fireEvent.mouseDown(screen.getByRole("tab", { name: i18n.t("batch.batch_file_upload") }), { button: 0 })
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement
    expect(fileInput).not.toBeNull()

    fireEvent.change(fileInput, { target: { files: [firstFile, secondFile] } })

    await act(async () => {
      ref.current?.submitCurrent()
      await Promise.resolve()
    })

    expect(toast.error).toHaveBeenCalledWith(quotaMessageKey)
    expect(onQuotaChanged).toHaveBeenCalledTimes(1)
  })
})
