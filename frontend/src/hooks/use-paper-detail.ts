import { useEffect, useState } from "react"

import { getCommunityPaperDetail, recordCommunityPaperView } from "@/lib/community-api"
import type { CommunityPaper } from "@/types/community"

export function usePaperDetail(paperId: string | undefined) {
  const [paper, setPaper] = useState<CommunityPaper | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    let isCancelled = false

    if (!paperId) {
      setPaper(null)
      setLoading(false)
      setError(null)
      setNotFound(true)
      return undefined
    }

    setLoading(true)
    setError(null)
    setNotFound(false)

    void (async () => {
      try {
        const response = await getCommunityPaperDetail(paperId)
        if (isCancelled) {
          return
        }

        setPaper(response.paper)
        setLoading(false)

        void recordCommunityPaperView(paperId).catch(() => {
          return undefined
        })
      } catch (fetchError) {
        if (isCancelled) {
          return
        }

        const message =
          fetchError instanceof Error ? fetchError.message : "unknown_error"
        setError(message)
        setLoading(false)
        setPaper(null)
        setNotFound(/404/.test(message) || /not found/i.test(message))
      }
    })()

    return () => {
      isCancelled = true
    }
  }, [paperId])

  return {
    paper,
    loading,
    error,
    notFound,
  }
}
