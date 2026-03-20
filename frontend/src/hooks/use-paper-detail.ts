import { useEffect, useState } from "react"

import {
  getCachedCommunityPaperDetail,
  getCommunityPaperDetail,
  recordCommunityPaperView,
} from "@/lib/community-api"
import type { CommunityPaper, CommunityPaperPreviewResponse } from "@/types/community"

export function usePaperDetail(paperId: string | undefined) {
  const cachedDetail = paperId ? getCachedCommunityPaperDetail(paperId) : null
  const [paper, setPaper] = useState<CommunityPaper | null>(cachedDetail?.paper ?? null)
  const [preview, setPreview] = useState<CommunityPaperPreviewResponse | null>(cachedDetail?.preview ?? null)
  const [readerState, setReaderState] = useState<"ready" | "warming" | "unavailable">(
    cachedDetail?.reader_state ?? "unavailable",
  )
  const [loading, setLoading] = useState(!cachedDetail)
  const [error, setError] = useState<string | null>(null)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    let isCancelled = false

    if (!paperId) {
      setPaper(null)
      setPreview(null)
      setReaderState("unavailable")
      setLoading(false)
      setError(null)
      setNotFound(true)
      return undefined
    }

    setLoading(true)
    if (cachedDetail) {
      setPaper(cachedDetail.paper)
      setPreview(cachedDetail.preview ?? null)
      setReaderState(cachedDetail.reader_state ?? "unavailable")
      setLoading(false)
    }
    setError(null)
    setNotFound(false)

    void (async () => {
      try {
        const response = await getCommunityPaperDetail(paperId)
        if (isCancelled) {
          return
        }

        setPaper(response.paper)
        setPreview(response.preview ?? null)
        setReaderState(response.reader_state ?? "unavailable")
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
        setPreview(null)
        setReaderState("unavailable")
        setNotFound(/404/.test(message) || /not found/i.test(message))
      }
    })()

    return () => {
      isCancelled = true
    }
  }, [cachedDetail, paperId])

  return {
    paper,
    preview,
    readerState,
    loading,
    error,
    notFound,
  }
}
