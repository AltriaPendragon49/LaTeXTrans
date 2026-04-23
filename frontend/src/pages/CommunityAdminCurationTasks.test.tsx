import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n"
import CommunityAdminCurationTasksPage from "@/pages/community-admin-curation-tasks"
import { setDesktopViewport, setMobileViewport } from "@/test/viewport"

const { listAdminCurationJobs, deleteAdminCurationJob, batchDeleteAdminCurationJobs } = vi.hoisted(() => ({
  listAdminCurationJobs: vi.fn(),
  deleteAdminCurationJob: vi.fn(),
  batchDeleteAdminCurationJobs: vi.fn(),
}))

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    isAuthenticated: true,
    user: { roles: ["admin"] },
  }),
}))

vi.mock("@/lib/community-api", () => ({
  listAdminCurationJobs,
  deleteAdminCurationJob,
  batchDeleteAdminCurationJobs,
}))

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

describe("CommunityAdminCurationTasksPage", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en")
    setDesktopViewport()
    listAdminCurationJobs.mockReset()
    deleteAdminCurationJob.mockReset()
    batchDeleteAdminCurationJobs.mockReset()
  })

  it("loads admin curation history with failed-task metadata", async () => {
    listAdminCurationJobs.mockResolvedValue({
      items: [
        {
          job_id: "job-1",
          batch_id: "batch-1",
          paper_id: null,
          published_paper_id: null,
          task_id: "task-1",
          source_type: "arxiv",
          arxiv_id: "2312.00752",
          original_filename: null,
          status: "failed",
          terminal_task_status: "failed_compilation",
          error: "compile failed",
          failed_artifact_path: "failed_tasks/task-1",
          created_at: "2026-04-19T00:00:00Z",
          updated_at: "2026-04-19T00:05:00Z",
        },
      ],
      total: 1,
    })

    render(
      <MemoryRouter>
        <CommunityAdminCurationTasksPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText("2312.00752")).toBeInTheDocument()
    expect(screen.getByText("failed_tasks/task-1")).toBeInTheDocument()
    expect(listAdminCurationJobs).toHaveBeenCalledWith({ status: "all", q: "" })
  })

  it("requests the grouped processing filter when the admin selects processing", async () => {
    listAdminCurationJobs.mockResolvedValue({
      items: [],
      total: 0,
    })

    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <CommunityAdminCurationTasksPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(listAdminCurationJobs).toHaveBeenCalledWith({ status: "all", q: "" })
    })

    await user.click(screen.getByRole("combobox"))
    await user.click(screen.getByRole("option", { name: "Processing" }))

    await waitFor(() => {
      expect(listAdminCurationJobs).toHaveBeenLastCalledWith({ status: "processing", q: "" })
    })
  })

  it("hard deletes a retained failed curation job from the history page", async () => {
    listAdminCurationJobs
      .mockResolvedValueOnce({
        items: [
          {
            job_id: "job-1",
            batch_id: "batch-1",
            paper_id: null,
            published_paper_id: null,
            task_id: "task-1",
            source_type: "arxiv",
            arxiv_id: "2312.00752",
            original_filename: null,
            status: "failed",
            terminal_task_status: "failed_compilation",
            error: "compile failed",
            failed_artifact_path: "failed_tasks/task-1",
            created_at: "2026-04-19T00:00:00Z",
            updated_at: "2026-04-19T00:05:00Z",
          },
        ],
        total: 1,
      })
      .mockResolvedValueOnce({
        items: [],
        total: 0,
      })
    deleteAdminCurationJob.mockResolvedValue({
      job_id: "job-1",
      paper_id: null,
      status: "failed",
    })

    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <CommunityAdminCurationTasksPage />
      </MemoryRouter>,
    )

    await screen.findByText("2312.00752")
    await user.click(screen.getByRole("button", { name: /Delete job-1/i }))
    await user.click(screen.getByRole("button", { name: /Permanently delete/i }))

    await waitFor(() => {
      expect(deleteAdminCurationJob).toHaveBeenCalledWith("job-1")
    })
    await waitFor(() => {
      expect(listAdminCurationJobs).toHaveBeenLastCalledWith({ status: "all", q: "" })
    })
  })

  it("selects current filtered jobs and batch deletes only the selected items", async () => {
    listAdminCurationJobs
      .mockResolvedValueOnce({
        items: [
          {
            job_id: "job-1",
            batch_id: "batch-1",
            paper_id: null,
            published_paper_id: null,
            task_id: "task-1",
            source_type: "arxiv",
            arxiv_id: "2312.00752",
            original_filename: null,
            status: "failed",
            terminal_task_status: "failed_compilation",
            error: "compile failed",
            failed_artifact_path: "failed_tasks/task-1",
            created_at: "2026-04-19T00:00:00Z",
            updated_at: "2026-04-19T00:05:00Z",
          },
          {
            job_id: "job-2",
            batch_id: "batch-1",
            paper_id: "paper-2",
            published_paper_id: "paper-2",
            task_id: "task-2",
            source_type: "arxiv",
            arxiv_id: "2510.04871",
            original_filename: null,
            status: "completed",
            terminal_task_status: "completed",
            error: null,
            failed_artifact_path: null,
            created_at: "2026-04-19T00:00:00Z",
            updated_at: "2026-04-19T00:15:00Z",
          },
        ],
        total: 2,
      })
      .mockResolvedValueOnce({
        items: [],
        total: 0,
      })
    batchDeleteAdminCurationJobs.mockResolvedValue({
      deleted: [
        { job_id: "job-1", paper_id: null, status: "failed" },
        { job_id: "job-2", paper_id: "paper-2", status: "completed" },
      ],
      failed: [],
      deleted_count: 2,
      failed_count: 0,
    })

    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <CommunityAdminCurationTasksPage />
      </MemoryRouter>,
    )

    await screen.findByText("2312.00752")
    await user.click(screen.getByRole("button", { name: /Select all visible/i }))
    await user.click(screen.getByRole("button", { name: /Delete selected/i }))
    await user.click(screen.getByRole("button", { name: /Permanently delete/i }))

    await waitFor(() => {
      expect(batchDeleteAdminCurationJobs).toHaveBeenCalledWith(["job-1", "job-2"])
    })
    await waitFor(() => {
      expect(listAdminCurationJobs).toHaveBeenLastCalledWith({ status: "all", q: "" })
    })
  })

  it("degrades the admin task history to a mobile card layout on narrow screens", async () => {
    setMobileViewport()
    listAdminCurationJobs.mockResolvedValue({
      items: [
        {
          job_id: "job-1",
          batch_id: "batch-1",
          paper_id: null,
          published_paper_id: null,
          task_id: "task-1",
          source_type: "arxiv",
          arxiv_id: "2312.00752",
          original_filename: null,
          status: "failed",
          terminal_task_status: "failed_compilation",
          error: "compile failed",
          failed_artifact_path: "failed_tasks/task-1",
          created_at: "2026-04-19T00:00:00Z",
          updated_at: "2026-04-19T00:05:00Z",
        },
      ],
      total: 1,
    })

    render(
      <MemoryRouter>
        <CommunityAdminCurationTasksPage />
      </MemoryRouter>,
    )

    expect(await screen.findByTestId("admin-curation-task-records")).toHaveAttribute("data-layout", "cards")
  })
})
