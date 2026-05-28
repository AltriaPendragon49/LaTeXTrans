import { useEffect, useMemo, useRef, useState } from "react"

import {
  getCachedCommunityPaperDetail,
  getCommunityPaperDetail,
  recordCommunityPaperView,
} from "@/features/community-paper/services/community-paper-api"
import type {
  CommunityPaper,
  CommunityPaperExperience,
  CommunityPaperPreviewResponse,
  CommunityPaperReader,
  StructuredInsightsPayload,
} from "@/types/community"

/** 论文详情页的远程数据状态 */
interface PaperDetailRemoteState {
  paperId: string | null
  paper: CommunityPaper | null
  preview: CommunityPaperPreviewResponse | null
  readerState: "ready" | "warming" | "unavailable"
  error: string | null
  notFound: boolean
  reader: CommunityPaperReader | null
  experience: CommunityPaperExperience | null
  structuredInsights: StructuredInsightsPayload | null
}

const EMPTY_REMOTE_STATE: PaperDetailRemoteState = {
  paperId: null,
  paper: null,
  preview: null,
  readerState: "unavailable",
  error: null,
  notFound: false,
  reader: null,
  experience: null,
  structuredInsights: null,
}

/**
 * 论文详情 Hook
 * 获取和缓存社区论文的详细信息，包括论文元数据、预览、阅读器状态和结构化洞察。
 * 优先使用缓存数据（从列表页预加载），若无缓存则从后端 GET /api/papers/{paperId} 拉取。
 * 自动记录首次查看事件（POST view 记录）。
 *
 * @param paperId - 论文 ID
 * @returns 论文详情数据、加载/错误状态、refetch 方法
 */
export function usePaperDetail(paperId: string | undefined) {
  const cachedDetail = paperId ? getCachedCommunityPaperDetail(paperId) : null
  const viewedPaperIdRef = useRef<string | null>(null)
  const [remoteState, setRemoteState] = useState<PaperDetailRemoteState>(EMPTY_REMOTE_STATE)

  useEffect(() => {
    if (!paperId) {
      return undefined
    }

    let isCancelled = false

    const fetchDetail = async () => {
      try {
        const response = await getCommunityPaperDetail(paperId)
        if (isCancelled) {
          return
        }

        setRemoteState({
          paperId,
          paper: response.paper ?? null,
          preview: response.preview ?? null,
          readerState: response.reader_state ?? "unavailable",
          error: null,
          notFound: false,
          reader: response.reader ?? null,
          experience: response.experience ?? null,
          structuredInsights: response.structured_insights ?? null,
        })

        // 首次查看时记录浏览事件
        if (viewedPaperIdRef.current !== paperId) {
          viewedPaperIdRef.current = paperId
          void recordCommunityPaperView(paperId).catch(() => undefined)
        }
      } catch (fetchError) {
        if (isCancelled) {
          return
        }

        const message = fetchError instanceof Error ? fetchError.message : "unknown_error"
        setRemoteState({
          paperId,
          paper: null,
          preview: null,
          readerState: "unavailable",
          error: message,
          notFound: /404/.test(message) || /not found/i.test(message),
          reader: null,
          experience: null,
          structuredInsights: null,
        })
      }
    }

    void fetchDetail()

    return () => {
      isCancelled = true
    }
  }, [paperId])

  // 优先使用缓存数据，其次使用远程数据
  const effectiveState = useMemo<PaperDetailRemoteState>(() => {
    if (!paperId) {
      return {
        ...EMPTY_REMOTE_STATE,
        notFound: true,
      }
    }

    if (remoteState.paperId === paperId && remoteState.paper) {
      return remoteState
    }

    if (cachedDetail) {
      return {
        paperId,
        paper: cachedDetail.paper ?? null,
        preview: cachedDetail.preview ?? null,
        readerState: cachedDetail.reader_state ?? "unavailable",
        error: null,
        notFound: false,
        reader: cachedDetail.reader ?? null,
        experience: cachedDetail.experience ?? null,
        structuredInsights: cachedDetail.structured_insights ?? null,
      }
    }

    return remoteState.paperId === paperId ? remoteState : EMPTY_REMOTE_STATE
  }, [cachedDetail, paperId, remoteState])

  return {
    paper: effectiveState.paper,
    preview: effectiveState.preview,
    readerState: effectiveState.readerState,
    loading: Boolean(paperId) && !cachedDetail && remoteState.paperId !== paperId,
    error: effectiveState.error,
    notFound: effectiveState.notFound,
    reader: effectiveState.reader,
    experience: effectiveState.experience,
    structuredInsights: effectiveState.structuredInsights,
    /** 强制重新从后端拉取论文详情 */
    refetch: async () => {
      if (!paperId) {
        return
      }

      const response = await getCommunityPaperDetail(paperId)
      setRemoteState({
        paperId,
        paper: response.paper ?? null,
        preview: response.preview ?? null,
        readerState: response.reader_state ?? "unavailable",
        error: null,
        notFound: false,
        reader: response.reader ?? null,
        experience: response.experience ?? null,
        structuredInsights: response.structured_insights ?? null,
      })
    },
  }
}
