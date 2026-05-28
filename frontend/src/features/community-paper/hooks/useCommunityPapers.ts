import { useEffect, useMemo, useState } from "react"

import {
  getCommunityPapers,
  mergeCommunityPaperEngagement,
  subscribeCommunityPaperEngagement,
} from "@/lib/community-api"
import type { CommunityFeedSort, CommunityPaper } from "@/types/community"

/** 搜索去抖延迟（毫秒） */
const SEARCH_DEBOUNCE_MS = 250
/** 社区论文列表每页大小 */
const COMMUNITY_PAGE_SIZE = 12

/**
 * 获取 SSR 预取的 Bootstrap 数据
 * 仅在 latest 排序且无搜索关键词时可用
 */
function getBootstrappedFeed(sort: CommunityFeedSort, query: string) {
  if (sort !== "latest" || query.trim()) {
    return null
  }
  return window.__COMMUNITY_BOOTSTRAP__?.feed ?? null
}

/** 解析论文的主时间戳（优先 arXiv 发布时间，其次正式发布时间，最后创建时间） */
function resolvePrimaryTimestamp(paper: CommunityPaper): number {
  const primary = paper.arxiv_published_at ?? paper.official_published_at ?? paper.created_at
  const resolved = primary ? Date.parse(primary) : Number.NaN
  return Number.isFinite(resolved) ? resolved : 0
}

/** 按排序方式对论文列表排序 */
function sortFeedItems(items: CommunityPaper[], sort: CommunityFeedSort) {
  return [...items].sort((left, right) => {
    if (sort === "views" || sort === "hot") {
      const viewDelta = Number(right.view_count ?? 0) - Number(left.view_count ?? 0)
      if (viewDelta !== 0) {
        return viewDelta
      }
    }

    if (sort === "likes") {
      const likeDelta = Number(right.like_count ?? 0) - Number(left.like_count ?? 0)
      if (likeDelta !== 0) {
        return likeDelta
      }
    }

    return resolvePrimaryTimestamp(right) - resolvePrimaryTimestamp(left)
  })
}

/** 合并互动状态（点赞、收藏等）后重新排序 */
function applyEngagementState(items: CommunityPaper[], sort: CommunityFeedSort) {
  return sortFeedItems(
    items.map((paper) => mergeCommunityPaperEngagement(paper)),
    sort,
  )
}

/**
 * 社区论文列表 Hook
 * 支持分页加载、排序（hot/latest/views/likes）、搜索去抖、
 * SSR Bootstrap 数据注入和互动状态实时同步。
 * 调用 GET /api/community/papers 获取论文列表。
 *
 * @param sort - 排序方式
 * @param query - 搜索关键词
 * @param hotWindow - 热榜时间窗口（仅 hot 排序时有效）
 * @returns 论文列表、总数、加载状态、loadMore 和 refetch 方法
 */
export function useCommunityPapers(sort: CommunityFeedSort, query: string, hotWindow?: string) {
  const bootstrappedFeed = getBootstrappedFeed(sort, query)
  const [items, setItems] = useState<CommunityPaper[]>(() =>
    applyEngagementState(bootstrappedFeed?.items ?? [], sort),
  )
  const [total, setTotal] = useState(bootstrappedFeed?.total ?? 0)
  const [hasMore, setHasMore] = useState(Boolean(bootstrappedFeed?.has_more))
  const [nextOffset, setNextOffset] = useState<number | null>(bootstrappedFeed?.next_offset ?? null)
  const [loading, setLoading] = useState(!bootstrappedFeed)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [reloadToken, setReloadToken] = useState(0)
  const normalizedQuery = useMemo(() => query.trim(), [query])

  // 加载论文列表数据
  useEffect(() => {
    let isCancelled = false
    const shouldUseBootstrap = sort === "latest" && !normalizedQuery
    const bootstrapPromise = shouldUseBootstrap ? window.__COMMUNITY_BOOTSTRAP_PROMISE__ : undefined

    setLoading(!bootstrappedFeed)
    setLoadingMore(false)
    setError(null)

    const load = async () => {
      try {
        // 等待 Bootstrap Promise 完成以复用 SSR 数据
        if (bootstrapPromise && !window.__COMMUNITY_BOOTSTRAP__?.feed) {
          const bootstrapResponse = await bootstrapPromise
          if (!isCancelled && bootstrapResponse) {
            setItems(applyEngagementState(bootstrapResponse.items, sort))
            setTotal(bootstrapResponse.total)
            setHasMore(Boolean(bootstrapResponse.has_more))
            setNextOffset(bootstrapResponse.next_offset ?? null)
            setLoading(false)
          }
        }

        const response = await getCommunityPapers({
          sort,
          q: normalizedQuery || undefined,
          limit: COMMUNITY_PAGE_SIZE,
          offset: 0,
          hotWindow: sort === "hot" ? hotWindow : undefined,
        })
        if (!isCancelled) {
          setItems(applyEngagementState(response.items, sort))
          setTotal(response.total)
          setHasMore(Boolean(response.has_more))
          setNextOffset(response.next_offset ?? null)
        }
      } catch (fetchError) {
        if (!isCancelled) {
          setError(fetchError instanceof Error ? fetchError.message : "unknown_error")
          setItems([])
          setTotal(0)
          setHasMore(false)
          setNextOffset(null)
        }
      } finally {
        if (!isCancelled) {
          setLoading(false)
        }
      }
    }

    // 搜索时去抖，避免频繁请求
    const shouldDebounce = Boolean(normalizedQuery)
    const timer = shouldDebounce ? window.setTimeout(() => void load(), SEARCH_DEBOUNCE_MS) : null
    if (!shouldDebounce) {
      void load()
    }

    return () => {
      isCancelled = true
      if (timer) {
        window.clearTimeout(timer)
      }
    }
  }, [bootstrappedFeed, normalizedQuery, reloadToken, sort, hotWindow])

  // 订阅互动状态实时更新（点赞、收藏计数）
  useEffect(() => {
    return subscribeCommunityPaperEngagement((patch) => {
      setItems((current) => {
        if (!current.some((paper) => paper.id === patch.paperId)) {
          return current
        }
        return applyEngagementState(current, sort)
      })
    })
  }, [sort])

  return {
    items,
    total,
    hasMore,
    loading,
    loadingMore,
    error,
    /** 加载下一页 */
    loadMore: async () => {
      if (loading || loadingMore || !hasMore || nextOffset === null) {
        return
      }
      setLoadingMore(true)
      setError(null)
      try {
        const response = await getCommunityPapers({
          sort,
          q: normalizedQuery || undefined,
          limit: COMMUNITY_PAGE_SIZE,
          offset: nextOffset,
          hotWindow: sort === "hot" ? hotWindow : undefined,
        })
        setItems((current) => applyEngagementState([...current, ...response.items], sort))
        setTotal(response.total)
        setHasMore(Boolean(response.has_more))
        setNextOffset(response.next_offset ?? null)
      } catch (fetchError) {
        setError(fetchError instanceof Error ? fetchError.message : "unknown_error")
      } finally {
        setLoadingMore(false)
      }
    },
    /** 重新加载第一页 */
    refetch: () => setReloadToken((current) => current + 1),
  }
}
