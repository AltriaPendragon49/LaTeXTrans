import { useEffect, useMemo, useState } from "react"

import { getCommunityPapers } from "@/lib/community-api"
import type { CommunityFeedSort, CommunityPaper } from "@/types/community"

const SEARCH_DEBOUNCE_MS = 250

export function useCommunityPapers(sort: CommunityFeedSort, query: string) {
  const [items, setItems] = useState<CommunityPaper[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadToken, setReloadToken] = useState(0)
  const normalizedQuery = useMemo(() => query.trim(), [query])

  useEffect(() => {
    let isCancelled = false

    setLoading(true)
    setError(null)

    const timer = window.setTimeout(async () => {
      try {
        const response = await getCommunityPapers({
          sort,
          q: normalizedQuery || undefined,
        })
        if (!isCancelled) {
          setItems(response.items)
          setTotal(response.total)
        }
      } catch (fetchError) {
        if (!isCancelled) {
          setError(fetchError instanceof Error ? fetchError.message : "unknown_error")
          setItems([])
          setTotal(0)
        }
      } finally {
        if (!isCancelled) {
          setLoading(false)
        }
      }
    }, SEARCH_DEBOUNCE_MS)

    return () => {
      isCancelled = true
      window.clearTimeout(timer)
    }
  }, [normalizedQuery, reloadToken, sort])

  return {
    items,
    total,
    loading,
    error,
    refetch: () => setReloadToken((current) => current + 1),
  }
}
