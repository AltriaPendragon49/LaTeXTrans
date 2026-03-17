import { act, render, screen } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"

import i18n from "@/i18n"
import HistoryPage from "@/pages/History"
import { getAccessToken } from "@/lib/supabase"

const authState = vi.hoisted(() => ({
  isAuthenticated: true,
  loading: false,
  session: { access_token: "token-1" },
}))

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => authState,
}))

vi.mock("@/store/useStore", () => ({
  useStore: () => ({
    setTaskId: vi.fn(),
    setArxivId: vi.fn(),
  }),
}))

vi.mock("@/lib/supabase", () => ({
  getAccessToken: vi.fn(),
}))

describe("HistoryPage", () => {
  beforeEach(async () => {
    vi.useFakeTimers()
    vi.clearAllMocks()
    await i18n.changeLanguage("en")
    authState.isAuthenticated = true
    authState.loading = false
    authState.session = { access_token: "token-1" }
    vi.mocked(getAccessToken).mockResolvedValue("token-1")
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it("retries automatically after a transient history fetch failure", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 500,
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          tasks: [
            {
              task_id: "task-1",
              source_type: "arxiv",
              arxiv_id: "2508.18791",
              translation_mode: "full",
              status: "completed",
              progress: 100,
              created_at: "2026-03-18T00:00:00Z",
              completed_at: "2026-03-18T00:10:00Z",
              source_language: "en",
              target_language: "zh",
              compile_strategy: "auto",
              translation_model: "deepseek-ai/deepseek-v3.2",
              generate_glossary: true,
              use_author_api: true,
              formatting: null,
            },
          ],
          total: 1,
          page: 1,
          page_size: 10,
          has_more: false,
        }),
      })

    vi.stubGlobal("fetch", fetchMock)

    render(
      <MemoryRouter>
        <HistoryPage />
      </MemoryRouter>,
    )

    await act(async () => {
      await Promise.resolve()
    })

    expect(fetchMock).toHaveBeenCalledTimes(1)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000)
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(screen.getByText("2508.18791")).toBeInTheDocument()
  })
})
