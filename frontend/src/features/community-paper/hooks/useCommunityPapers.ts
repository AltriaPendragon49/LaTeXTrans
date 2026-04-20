import { useEffect, useMemo, useState } from "react"

import { getCommunityPapers } from "@/lib/community-api"
import type { CommunityFeedSort, CommunityPaper } from "@/types/community"

const SEARCH_DEBOUNCE_MS = 250
const COMMUNITY_PAGE_SIZE = 12

function getBootstrappedFeed(sort: CommunityFeedSort, query: string) {
  if (sort !== "latest" || query.trim()) {
    return null
  }
  return window.__COMMUNITY_BOOTSTRAP__?.feed ?? null
}

export function useCommunityPapers(sort: CommunityFeedSort, query: string) {
  const bootstrappedFeed = getBootstrappedFeed(sort, query)
  const [items, setItems] = useState<CommunityPaper[]>(bootstrappedFeed?.items ?? [])
  const [total, setTotal] = useState(bootstrappedFeed?.total ?? 0)
  const [hasMore, setHasMore] = useState(Boolean(bootstrappedFeed?.has_more))
  const [nextOffset, setNextOffset] = useState<number | null>(bootstrappedFeed?.next_offset ?? null)
  const [loading, setLoading] = useState(!bootstrappedFeed)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [reloadToken, setReloadToken] = useState(0)
  const normalizedQuery = useMemo(() => query.trim(), [query])

  useEffect(() => {
    let isCancelled = false
    const shouldUseBootstrap = sort === "latest" && !normalizedQuery
    const bootstrapPromise = shouldUseBootstrap ? window.__COMMUNITY_BOOTSTRAP_PROMISE__ : undefined

    setLoading(!bootstrappedFeed)
    setLoadingMore(false)
    setError(null)

    const load = async () => {
      try {
        if (bootstrapPromise && !window.__COMMUNITY_BOOTSTRAP__?.feed) {
          const bootstrapResponse = await bootstrapPromise
          if (!isCancelled && bootstrapResponse) {
            setItems(bootstrapResponse.items)
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
        })
        if (!isCancelled) {
          setItems(response.items)
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
  }, [bootstrappedFeed, normalizedQuery, reloadToken, sort])

  return {
    items,
    total,
    hasMore,
    loading,
    loadingMore,
    error,
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
        })
        setItems((current) => [...current, ...response.items])
        setTotal(response.total)
        setHasMore(Boolean(response.has_more))
        setNextOffset(response.next_offset ?? null)
      } catch (fetchError) {
        setError(fetchError instanceof Error ? fetchError.message : "unknown_error")
      } finally {
        setLoadingMore(false)
      }
    },
    refetch: () => setReloadToken((current) => current + 1),
  }
}
