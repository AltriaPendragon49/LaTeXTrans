import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n"
import CommunityAdminCurationTasksPage from "@/pages/CommunityAdminCurationTasks"

const { listAdminCurationJobs, deleteAdminCurationJob } = vi.hoisted(() => ({
  listAdminCurationJobs: vi.fn(),
  deleteAdminCurationJob: vi.fn(),
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
    listAdminCurationJobs.mockReset()
    deleteAdminCurationJob.mockReset()
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
})
