import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"

import { API_BASE_URL } from "@/api-base"
import { useAuth } from "@/contexts/AuthContext"
import { useIsMobile } from "@/hooks/use-mobile"
import { usePaperDetail } from "@/features/community-paper/hooks/use-paper-detail"
import {
  createCommunityPaperDownloadSession,
  likeCommunityPaper,
  unlikeCommunityPaper,
} from "@/features/community-paper/services/community-paper-api"
import { publishCommunityPaperEngagement } from "@/lib/community-api"
import type { CommunityPaper, CommunityPaperReaderMode, ViewerState } from "@/types/community"

import { PaperDetailHeader } from "./PaperDetailHeader"
import { PaperDetailStateBoundary } from "./PaperDetailStateBoundary"
import { PaperDetailWorkspace } from "./PaperDetailWorkspace"
import { resolveAvailableModes, resolvePreferredMode } from "../utils/paper-detail-mode-resolution"

/**
 * 格式化作者列表为逗号分隔字符串
 */
function formatAuthors(authors: unknown[], fallback: string) {
  if (!authors.length) {
    return fallback
  }

  return authors
    .map((entry) => {
      if (typeof entry === "string") {
        return entry
      }
      if (entry && typeof entry === "object" && "name" in entry) {
        const name = (entry as { name?: unknown }).name
        return typeof name === "string" ? name : null
      }
      return null
    })
    .filter(Boolean)
    .join(", ")
}

/**
 * 从错误对象中提取可显示的错误消息
 */
function extractActionErrorMessage(error: unknown): string | null {
  if (typeof error === "string") {
    return error
  }
  if (error instanceof Error) {
    return error.message
  }
  if (!error || typeof error !== "object") {
    return null
  }
  if ("response" in error) {
    const response = error.response
    if (
      response &&
      typeof response === "object" &&
      "data" in response &&
      response.data &&
      typeof response.data === "object" &&
      "detail" in response.data &&
      typeof response.data.detail === "string"
    ) {
      return response.data.detail
    }
  }
  if ("message" in error && typeof error.message === "string") {
    return error.message
  }
  return null
}

/** 论文详情页 Props */
interface PaperDetailScreenProps {
  /** 论文 ID（可为 null，此时渲染为空） */
  paperId: string | null
}

/** 互动数据（点赞、收藏）的本地变更补丁 */
interface PaperEngagementPatch {
  paperId: string
  likeCount: number
  favoriteCount: number
  viewerState: ViewerState
}

/**
 * 论文详情页主组件
 * 组合 Header + Workspace + StateBoundary 形成完整的论文详情视图。
 * 管理阅读模式选择、下载、点赞/取消点赞和收藏状态变更。
 * 调用 GET /api/papers/{paperId} 获取详情，通过 usePaperDetail hook 驱动
 */
export function PaperDetailScreen({ paperId }: PaperDetailScreenProps) {
  const { t } = useTranslation()
  const { isAuthenticated } = useAuth()
  const isMobile = useIsMobile()
  const {
    paper,
    preview,
    readerState,
    reader,
    structuredInsights,
    loading,
    error,
    notFound,
  } = usePaperDetail(paperId ?? undefined)
  const [selectedModeState, setSelectedModeState] = useState<{
    paperId: string | null
    mode: CommunityPaperReaderMode | null
  }>({
    paperId: null,
    mode: null,
  })
  const [actionError, setActionError] = useState<string | null>(null)
  const [likePending, setLikePending] = useState(false)
  const [engagementPatch, setEngagementPatch] = useState<PaperEngagementPatch | null>(null)
  const [mobileAnalysisJumpRequest, setMobileAnalysisJumpRequest] = useState(0)

  // 解析可用阅读模式和首选模式
  const availableModes = useMemo<CommunityPaperReaderMode[]>(
    () => resolveAvailableModes(paper, preview, reader),
    [paper, preview, reader],
  )

  const derivedPreferredMode = useMemo(
    () => resolvePreferredMode(reader?.preferred_mode, availableModes, { isMobile }),
    [availableModes, isMobile, reader?.preferred_mode],
  )
  const selectedMode =
    selectedModeState.paperId === paperId &&
    selectedModeState.mode &&
    availableModes.includes(selectedModeState.mode)
      ? selectedModeState.mode
      : derivedPreferredMode

  /** 切换阅读模式 */
  function handleSelectMode(nextMode: CommunityPaperReaderMode) {
    setSelectedModeState({
      paperId,
      mode: nextMode,
    })
  }

  /** 创建下载会话并打开下载链接 */
  async function handleDownload() {
    if (!paperId) {
      return
    }

    try {
      setActionError(null)
      const session = await createCommunityPaperDownloadSession(paperId)
      const downloadUrl = session.download_url.startsWith("http")
        ? session.download_url
        : `${API_BASE_URL}${session.download_url}`
      window.open(downloadUrl, "_blank")
    } catch (downloadError) {
      setActionError(extractActionErrorMessage(downloadError) ?? t("community.actions.downloadError"))
    }
  }

  /** 点赞/取消点赞（乐观更新） */
  async function handleLikeToggle(activePaper: CommunityPaper) {
    if (!paperId || likePending) {
      return
    }
    if (!isAuthenticated) {
      toast.error(t("auth.loginRequiredForThisFeature"))
      return
    }

    const currentLiked =
      engagementPatch?.paperId === activePaper.id
        ? engagementPatch.viewerState.liked
        : Boolean(activePaper.viewer_state?.liked)
    const currentLikeCount =
      engagementPatch?.paperId === activePaper.id
        ? engagementPatch.likeCount
        : Number(activePaper.like_count ?? 0)
    const currentFavoriteCount =
      engagementPatch?.paperId === activePaper.id
        ? engagementPatch.favoriteCount
        : Number(activePaper.favorite_count ?? 0)
    const currentViewerState =
      engagementPatch?.paperId === activePaper.id
        ? engagementPatch.viewerState
        : {
            liked: Boolean(activePaper.viewer_state?.liked),
            favorited: Boolean(activePaper.viewer_state?.favorited),
            favorite_folder_count: Number(activePaper.viewer_state?.favorite_folder_count ?? 0),
          }
    const nextLiked = !currentLiked
    const optimisticPatch: PaperEngagementPatch = {
      paperId: activePaper.id,
      likeCount: Math.max(0, currentLikeCount + (nextLiked ? 1 : -1)),
      favoriteCount: currentFavoriteCount,
      viewerState: {
        ...currentViewerState,
        liked: nextLiked,
      },
    }

    try {
      setLikePending(true)
      setActionError(null)
      setEngagementPatch(optimisticPatch)

      const response = nextLiked
        ? await likeCommunityPaper(activePaper.id)
        : await unlikeCommunityPaper(activePaper.id)
      const nextPatch: PaperEngagementPatch = {
        paperId: activePaper.id,
        likeCount: response.like_count,
        favoriteCount: currentFavoriteCount,
        viewerState: {
          ...currentViewerState,
          liked: response.liked,
        },
      }
      setEngagementPatch(nextPatch)
      publishCommunityPaperEngagement({
        paperId: activePaper.id,
        likeCount: response.like_count,
        viewerState: {
          liked: response.liked,
        },
      })
      toast.success(
        response.liked
          ? t("community.likes.toast.liked")
          : t("community.likes.toast.unliked"),
      )
    } catch (likeError) {
      // 回滚乐观更新
      setEngagementPatch({
        paperId: activePaper.id,
        likeCount: currentLikeCount,
        favoriteCount: currentFavoriteCount,
        viewerState: currentViewerState,
      })
      const message = extractActionErrorMessage(likeError) ?? t("community.likes.toast.failed")
      setActionError(message)
      toast.error(message)
    } finally {
      setLikePending(false)
    }
  }

  return (
    <PaperDetailStateBoundary
      loading={loading}
      error={error}
      notFound={notFound}
      paper={paper}
    >
      {(activePaper) => {
        const authorsLabel = formatAuthors(activePaper.authors, t("community.card.authorsUnavailable"))
        const canDownload = activePaper.trans_status === "completed"
        const originalSourceUrl =
          reader?.source?.url ??
          (activePaper.arxiv_id ? `https://arxiv.org/abs/${activePaper.arxiv_id}` : null)
        const abstractText =
          (selectedMode === "source" ? activePaper.abstract_raw : activePaper.abstract_translated) ||
          activePaper.abstract_raw ||
          activePaper.abstract_translated ||
          t("community.detail.abstractUnavailable")
        // 应用乐观互动数据补丁
        const effectivePaper: CommunityPaper =
          engagementPatch?.paperId === activePaper.id
            ? {
                ...activePaper,
                like_count: engagementPatch.likeCount,
                favorite_count: engagementPatch.favoriteCount,
                viewer_state: {
                  ...activePaper.viewer_state,
                  ...engagementPatch.viewerState,
                },
              }
            : activePaper

        return (
          <div
            className={`flex flex-col min-h-0 min-w-0 flex-1 bg-[color:var(--px-shell-bg)] ${
              isMobile ? "px-0 py-0" : "px-2 py-2 md:px-3 md:py-3"
            }`}
          >
            <div
              data-testid="paper-detail-page-shell"
              data-mobile-shell={isMobile ? "immersive" : "default"}
              className={`flex h-full min-h-0 min-w-0 flex-col overflow-hidden bg-[color:var(--px-shell-panel)] ${
                isMobile
                  ? "rounded-none border-0 shadow-none"
                  : "rounded-[8px] border border-[color:var(--px-shell-line)] shadow-[var(--px-shell-shadow)]"
              }`}
            >
              <PaperDetailHeader
                paper={effectivePaper}
                selectedMode={selectedMode}
                availableModes={availableModes}
                authorsLabel={authorsLabel}
                canDownload={canDownload}
                likePending={likePending}
                liked={Boolean(effectivePaper.viewer_state?.liked)}
                likeCount={Number(effectivePaper.like_count ?? 0)}
                onSelectMode={handleSelectMode}
                onDownload={() => void handleDownload()}
                onLikeToggle={() => void handleLikeToggle(activePaper)}
                onMobileOpenAnalysis={() => setMobileAnalysisJumpRequest((current) => current + 1)}
                onFavoriteStateChange={(payload) => {
                  const nextViewerState = {
                    liked:
                      engagementPatch?.paperId === activePaper.id
                        ? engagementPatch.viewerState.liked
                        : Boolean(activePaper.viewer_state?.liked),
                    favorited: payload.favorited,
                    favorite_folder_count: payload.favorite_folder_count,
                  }
                  setEngagementPatch({
                    paperId: activePaper.id,
                    likeCount:
                      engagementPatch?.paperId === activePaper.id
                        ? engagementPatch.likeCount
                        : Number(activePaper.like_count ?? 0),
                    favoriteCount: payload.favorite_count,
                    viewerState: nextViewerState,
                  })
                  publishCommunityPaperEngagement({
                    paperId: activePaper.id,
                    favoriteCount: payload.favorite_count,
                    viewerState: nextViewerState,
                  })
                }}
              />

              <div
                className={`relative flex min-h-0 min-w-0 flex-1 overflow-hidden ${
                  isMobile ? "bg-white" : "bg-[color:var(--px-shell-panel-strong)]"
                }`}
              >
                <PaperDetailWorkspace
                  key={effectivePaper.id}
                  paper={effectivePaper}
                  preview={preview}
                  readerState={readerState}
                  reader={reader}
                  preferredMode={selectedMode}
                  structuredInsights={structuredInsights}
                  originalSourceUrl={originalSourceUrl}
                  abstractText={abstractText}
                  canDownload={canDownload}
                  actionError={actionError}
                  mobileAnalysisJumpRequest={mobileAnalysisJumpRequest}
                />
              </div>
            </div>
          </div>
        )
      }}
    </PaperDetailStateBoundary>
  )
}
