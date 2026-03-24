import { useEffect, useMemo, useRef, useState } from "react"

import {
  getCachedCommunityPaperDetail,
  getCommunityPaperDetail,
  recordCommunityPaperView,
} from "@/lib/community-api"
import type {
  CommunityPaper,
  CommunityPaperExperience,
  CommunityPaperPreviewResponse,
  CommunityPaperReader,
} from "@/types/community"

export function usePaperDetail(paperId: string | undefined) {
  const cachedDetail = useMemo(
    () => (paperId ? getCachedCommunityPaperDetail(paperId) : null),
    [paperId],
  )
  const viewedPaperIdRef = useRef<string | null>(null)
  const [paper, setPaper] = useState<CommunityPaper | null>(cachedDetail?.paper ?? null)
  const [preview, setPreview] = useState<CommunityPaperPreviewResponse | null>(cachedDetail?.preview ?? null)
  const [readerState, setReaderState] = useState<"ready" | "warming" | "unavailable">(
    cachedDetail?.reader_state ?? "unavailable",
  )
  const [loading, setLoading] = useState(!cachedDetail)
  const [error, setError] = useState<string | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [reader, setReader] = useState<CommunityPaperReader | null>(cachedDetail?.reader ?? null)
  const [experience, setExperience] = useState<CommunityPaperExperience | null>(
    cachedDetail?.experience ?? null,
  )

  useEffect(() => {
    let isCancelled = false

    if (!paperId) {
      setPaper(null)
      setPreview(null)
      setReaderState("unavailable")
      setReader(null)
      setExperience(null)
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
      setReader(cachedDetail.reader ?? null)
      setExperience(cachedDetail.experience ?? null)
      setLoading(false)
    }
    setError(null)
    setNotFound(false)

    const fetchDetail = async () => {
      try {
        const response = await getCommunityPaperDetail(paperId)
        if (isCancelled) {
          return
        }

        setPaper(response.paper)
        setPreview(response.preview ?? null)
        setReaderState(response.reader_state ?? "unavailable")
        setReader(response.reader ?? null)
        setExperience(response.experience ?? null)
        setLoading(false)

        if (viewedPaperIdRef.current !== paperId) {
          viewedPaperIdRef.current = paperId
          void recordCommunityPaperView(paperId).catch(() => {
            return undefined
          })
        }
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
        setReader(null)
        setExperience(null)
        setNotFound(/404/.test(message) || /not found/i.test(message))
      }
    }

    void fetchDetail()

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
    reader,
    experience,
    refetch: async () => {
      if (!paperId) {
        return
      }
      const response = await getCommunityPaperDetail(paperId)
      setPaper(response.paper)
      setPreview(response.preview ?? null)
      setReaderState(response.reader_state ?? "unavailable")
      setReader(response.reader ?? null)
      setExperience(response.experience ?? null)
    },
  }
}
