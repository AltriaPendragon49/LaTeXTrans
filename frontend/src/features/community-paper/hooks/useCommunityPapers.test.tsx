import { act, render, screen } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import {
  clearCommunityPaperEngagementState,
  publishCommunityPaperEngagement,
} from "@/lib/community-api"
import { useCommunityPapers } from "@/features/community-paper/hooks/useCommunityPapers"

const getCommunityPapersMock = vi.fn()

vi.mock(import("@/lib/community-api"), async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/community-api")>()
  return {
    ...actual,
    getCommunityPapers: (...args: unknown[]) => getCommunityPapersMock(...args),
  }
})

function HookProbe({ sort, query }: { sort: "latest" | "views" | "likes"; query: string }) {
  const { items, total, loading, hasMore, loadMore, loadingMore } = useCommunityPapers(sort, query)

  return (
    <div>
      <span data-testid="loading">{String(loading)}</span>
      <span data-testid="loading-more">{String(loadingMore)}</span>
      <span data-testid="total">{String(total)}</span>
      <span data-testid="title">{items[0]?.title ?? ""}</span>
      <span data-testid="titles">{JSON.stringify(items.map((item) => item.title))}</span>
      <span data-testid="first-like-count">{String(items[0]?.like_count ?? 0)}</span>
      <span data-testid="first-favorited">{String(Boolean(items[0]?.viewer_state?.favorited))}</span>
      <span data-testid="first-liked">{String(Boolean(items[0]?.viewer_state?.liked))}</span>
      <span data-testid="count">{String(items.length)}</span>
      <span data-testid="has-more">{String(hasMore)}</span>
      <button type="button" onClick={() => void loadMore()}>
        load more
      </button>
    </div>
  )
}

describe("useCommunityPapers", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    clearCommunityPaperEngagementState()
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
    getCommunityPapersMock.mockResolvedValue({ items: [], total: 0, has_more: false, next_offset: null })

    render(<HookProbe sort="latest" query="" />)

    expect(screen.getByTestId("loading")).toHaveTextContent("false")
    expect(screen.getByTestId("total")).toHaveTextContent("1")
    expect(screen.getByTestId("title")).toHaveTextContent("Bootstrapped paper")
  })

  it("does not delay the initial homepage fetch behind query debounce", () => {
    getCommunityPapersMock.mockResolvedValue({ items: [], total: 0, has_more: false, next_offset: null })

    render(<HookProbe sort="latest" query="" />)

    expect(getCommunityPapersMock).toHaveBeenCalledTimes(1)
    expect(getCommunityPapersMock).toHaveBeenCalledWith({
      sort: "latest",
      q: undefined,
      limit: 12,
      offset: 0,
    })
  })

  it("still debounces follow-up query refinement", async () => {
    getCommunityPapersMock.mockResolvedValue({ items: [], total: 0, has_more: false, next_offset: null })

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
      limit: 12,
      offset: 0,
    })
  })

  it("loads the next page and appends items", async () => {
    getCommunityPapersMock
      .mockResolvedValueOnce({
        items: [
          {
            id: "paper-1",
            source: "arxiv",
            arxiv_id: "2503.01010",
            title: "First page",
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
        total: 2,
        has_more: true,
        next_offset: 1,
      })
      .mockResolvedValueOnce({
        items: [
          {
            id: "paper-2",
            source: "arxiv",
            arxiv_id: "2503.02020",
            title: "Second page",
            authors: [],
            categories: [],
            community_status: "official",
            trans_status: "completed",
            created_at: "2026-03-18T00:00:00Z",
            official_published_at: "2026-03-18T00:00:00Z",
            community_selected_task_id: "task-2",
            community_selected_asset_id: "asset-2",
          },
        ],
        total: 2,
        has_more: false,
        next_offset: null,
      })

    render(<HookProbe sort="latest" query="" />)
    await act(async () => {
      await Promise.resolve()
    })

    expect(screen.getByTestId("count")).toHaveTextContent("1")
    expect(screen.getByTestId("has-more")).toHaveTextContent("true")

    await act(async () => {
      screen.getByRole("button", { name: "load more" }).click()
      await Promise.resolve()
    })

    expect(getCommunityPapersMock).toHaveBeenNthCalledWith(2, {
      sort: "latest",
      q: undefined,
      limit: 12,
      offset: 1,
    })
    expect(screen.getByTestId("count")).toHaveTextContent("2")
    expect(screen.getByTestId("has-more")).toHaveTextContent("false")
  })

  it("applies favorite state updates to the active feed without waiting for a refetch", async () => {
    getCommunityPapersMock.mockResolvedValue({
      items: [
        {
          id: "paper-1",
          source: "arxiv",
          arxiv_id: "2503.01010",
          title: "Favorited paper",
          authors: [],
          categories: [],
          community_status: "official",
          trans_status: "completed",
          created_at: "2026-03-18T00:00:00Z",
          official_published_at: "2026-03-18T00:00:00Z",
          community_selected_task_id: "task-1",
          community_selected_asset_id: "asset-1",
          favorite_count: 1,
          viewer_state: {
            liked: false,
            favorited: true,
            favorite_folder_count: 1,
          },
        },
      ],
      total: 1,
      has_more: false,
      next_offset: null,
    })

    render(<HookProbe sort="latest" query="" />)
    await act(async () => {
      await Promise.resolve()
    })

    expect(screen.getByTestId("first-favorited")).toHaveTextContent("true")

    await act(async () => {
      publishCommunityPaperEngagement({
        paperId: "paper-1",
        favoriteCount: 0,
        viewerState: {
          favorited: false,
          favorite_folder_count: 0,
        },
      })
      await Promise.resolve()
    })

    expect(screen.getByTestId("first-favorited")).toHaveTextContent("false")
  })

  it("keeps the patched favorite state when the latest feed remounts from bootstrap data", async () => {
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
            favorite_count: 1,
            viewer_state: {
              liked: false,
              favorited: true,
              favorite_folder_count: 1,
            },
          },
        ],
        total: 1,
      },
    }
    getCommunityPapersMock.mockResolvedValue({ items: [], total: 0, has_more: false, next_offset: null })

    const { unmount } = render(<HookProbe sort="latest" query="" />)
    expect(screen.getByTestId("first-favorited")).toHaveTextContent("true")

    await act(async () => {
      publishCommunityPaperEngagement({
        paperId: "paper-1",
        favoriteCount: 0,
        viewerState: {
          favorited: false,
          favorite_folder_count: 0,
        },
      })
      await Promise.resolve()
    })

    unmount()

    render(<HookProbe sort="latest" query="" />)
    expect(screen.getByTestId("first-favorited")).toHaveTextContent("false")
  })

  it("re-sorts the likes feed immediately after a like count change", async () => {
    getCommunityPapersMock.mockResolvedValue({
      items: [
        {
          id: "paper-older",
          source: "arxiv",
          arxiv_id: "2503.01010",
          title: "Older paper",
          authors: [],
          categories: [],
          community_status: "official",
          trans_status: "completed",
          created_at: "2026-03-18T00:00:00Z",
          official_published_at: "2026-03-18T00:00:00Z",
          community_selected_task_id: "task-1",
          community_selected_asset_id: "asset-1",
          like_count: 0,
          viewer_state: {
            liked: false,
            favorited: false,
            favorite_folder_count: 0,
          },
        },
        {
          id: "paper-newer",
          source: "arxiv",
          arxiv_id: "2503.02020",
          title: "Newer paper",
          authors: [],
          categories: [],
          community_status: "official",
          trans_status: "completed",
          created_at: "2026-03-19T00:00:00Z",
          official_published_at: "2026-03-19T00:00:00Z",
          community_selected_task_id: "task-2",
          community_selected_asset_id: "asset-2",
          like_count: 0,
          viewer_state: {
            liked: false,
            favorited: false,
            favorite_folder_count: 0,
          },
        },
      ],
      total: 2,
      has_more: false,
      next_offset: null,
    })

    render(<HookProbe sort="likes" query="" />)
    await act(async () => {
      await Promise.resolve()
    })

    expect(screen.getByTestId("titles")).toHaveTextContent("[\"Newer paper\",\"Older paper\"]")

    await act(async () => {
      publishCommunityPaperEngagement({
        paperId: "paper-older",
        likeCount: 1,
        viewerState: {
          liked: true,
        },
      })
      await Promise.resolve()
    })

    expect(screen.getByTestId("titles")).toHaveTextContent("[\"Older paper\",\"Newer paper\"]")
    expect(screen.getByTestId("first-liked")).toHaveTextContent("true")
    expect(screen.getByTestId("first-like-count")).toHaveTextContent("1")
  })

  it("sorts the latest feed by original arxiv publish time before official publish time", async () => {
    getCommunityPapersMock.mockResolvedValue({
      items: [
        {
          id: "paper-later-official",
          source: "arxiv",
          arxiv_id: "2503.01010",
          title: "Later official publish",
          authors: [],
          categories: [],
          community_status: "official",
          trans_status: "completed",
          created_at: "2026-03-18T00:00:00Z",
          official_published_at: "2026-03-20T00:00:00Z",
          arxiv_published_at: "2026-03-10T00:00:00Z",
          community_selected_task_id: "task-1",
          community_selected_asset_id: "asset-1",
        },
        {
          id: "paper-newer-arxiv",
          source: "arxiv",
          arxiv_id: "2503.02020",
          title: "Newer arxiv publish",
          authors: [],
          categories: [],
          community_status: "official",
          trans_status: "completed",
          created_at: "2026-03-18T00:00:00Z",
          official_published_at: "2026-03-19T00:00:00Z",
          arxiv_published_at: "2026-03-15T00:00:00Z",
          community_selected_task_id: "task-2",
          community_selected_asset_id: "asset-2",
        },
      ],
      total: 2,
      has_more: false,
      next_offset: null,
    })

    render(<HookProbe sort="latest" query="" />)
    await act(async () => {
      await Promise.resolve()
    })

    expect(screen.getByTestId("titles")).toHaveTextContent(
      "[\"Newer arxiv publish\",\"Later official publish\"]",
    )
  })

  it("does not re-prioritize official papers ahead of newer published community papers", async () => {
    getCommunityPapersMock.mockResolvedValue({
      items: [
        {
          id: "paper-official",
          source: "arxiv",
          arxiv_id: "2503.01010",
          title: "Older official paper",
          authors: [],
          categories: [],
          community_status: "official",
          trans_status: "completed",
          created_at: "2026-03-18T00:00:00Z",
          official_published_at: "2026-03-18T00:00:00Z",
          community_selected_task_id: "task-1",
          community_selected_asset_id: "asset-1",
        },
        {
          id: "paper-community",
          source: "arxiv",
          arxiv_id: "2503.02020",
          title: "Newer community paper",
          authors: [],
          categories: [],
          community_status: "user_fallback",
          trans_status: "completed",
          created_at: "2026-03-19T00:00:00Z",
          official_published_at: null,
          community_selected_task_id: "task-2",
          community_selected_asset_id: "asset-2",
        },
      ],
      total: 2,
      has_more: false,
      next_offset: null,
    })

    render(<HookProbe sort="latest" query="" />)
    await act(async () => {
      await Promise.resolve()
    })

    expect(screen.getByTestId("titles")).toHaveTextContent(
      "[\"Newer community paper\",\"Older official paper\"]",
    )
  })
})
