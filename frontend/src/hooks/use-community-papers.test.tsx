import { act, render, screen } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { useCommunityPapers } from "@/hooks/use-community-papers"

const getCommunityPapersMock = vi.fn()

vi.mock("@/lib/community-api", () => ({
  getCommunityPapers: (...args: unknown[]) => getCommunityPapersMock(...args),
}))

function HookProbe({ sort, query }: { sort: "latest" | "translated" | "hot"; query: string }) {
  const { items, total, loading } = useCommunityPapers(sort, query)

  return (
    <div>
      <span data-testid="loading">{String(loading)}</span>
      <span data-testid="total">{String(total)}</span>
      <span data-testid="title">{items[0]?.title ?? ""}</span>
    </div>
  )
}

describe("useCommunityPapers", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    window.__COMMUNITY_BOOTSTRAP__ = undefined
    window.__COMMUNITY_BOOTSTRAP_PROMISE__ = undefined
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("uses bootstrap feed data immediately on the latest homepage view", () => {
    window.__COMMUNITY_BOOTSTRAP__ = {
      feed: {
        items: [
          {
            id: "paper-1",
            source: "arxiv",
            arxiv_id: "2503.01010",
            title: "Bootstrapped paper",
            authors: [],
            categories: [],
            community_status: "official",
            trans_status: "completed",
            created_at: "2026-03-18T00:00:00Z",
            official_published_at: "2026-03-18T00:00:00Z",
            community_selected_task_id: "task-1",
            community_selected_asset_id: "asset-1",
          },
        ],
        total: 1,
      },
    }
    getCommunityPapersMock.mockResolvedValue({ items: [], total: 0 })

    render(<HookProbe sort="latest" query="" />)

    expect(screen.getByTestId("loading")).toHaveTextContent("false")
    expect(screen.getByTestId("total")).toHaveTextContent("1")
    expect(screen.getByTestId("title")).toHaveTextContent("Bootstrapped paper")
  })

  it("does not delay the initial homepage fetch behind query debounce", () => {
    getCommunityPapersMock.mockResolvedValue({ items: [], total: 0 })

    render(<HookProbe sort="latest" query="" />)

    expect(getCommunityPapersMock).toHaveBeenCalledTimes(1)
    expect(getCommunityPapersMock).toHaveBeenCalledWith({
      sort: "latest",
      q: undefined,
      limit: undefined,
    })
  })

  it("still debounces follow-up query refinement", async () => {
    getCommunityPapersMock.mockResolvedValue({ items: [], total: 0 })

    const { rerender } = render(<HookProbe sort="latest" query="" />)
    expect(getCommunityPapersMock).toHaveBeenCalledTimes(1)

    await act(async () => {
      rerender(<HookProbe sort="latest" query="diffusion" />)
    })

    expect(getCommunityPapersMock).toHaveBeenCalledTimes(1)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(249)
    })
    expect(getCommunityPapersMock).toHaveBeenCalledTimes(1)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1)
      await Promise.resolve()
    })
    expect(getCommunityPapersMock).toHaveBeenCalledTimes(2)
    expect(getCommunityPapersMock).toHaveBeenLastCalledWith({
      sort: "latest",
      q: "diffusion",
      limit: undefined,
    })
  })
})
