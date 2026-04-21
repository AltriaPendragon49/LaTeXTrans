import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"

import { API_BASE_URL } from "@/api-base"
import { usePaperDetail } from "@/features/community-paper/hooks/use-paper-detail"
import { createCommunityPaperDownloadSession } from "@/features/community-paper/services/community-paper-api"
import { publishCommunityPaperEngagement } from "@/lib/community-api"
import type { CommunityPaper, CommunityPaperReaderMode, ViewerState } from "@/types/community"

import { PaperDetailHeader } from "./PaperDetailHeader"
import { PaperDetailStateBoundary } from "./PaperDetailStateBoundary"
import { PaperDetailWorkspace } from "./PaperDetailWorkspace"
import { resolveAvailableModes, resolvePreferredMode } from "../utils/paper-detail-mode-resolution"

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

interface PaperDetailScreenProps {
  paperId: string | null
}

interface PaperFavoriteStatePatch {
  paperId: string
  favoriteCount: number
  viewerState: ViewerState
}

export function PaperDetailScreen({ paperId }: PaperDetailScreenProps) {
  const { t } = useTranslation()
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
  const [favoriteStatePatch, setFavoriteStatePatch] = useState<PaperFavoriteStatePatch | null>(null)

  const availableModes = useMemo<CommunityPaperReaderMode[]>(
    () => resolveAvailableModes(paper, preview, reader),
    [paper, preview, reader],
  )

  const derivedPreferredMode = useMemo(
    () => resolvePreferredMode(reader?.preferred_mode, availableModes),
    [availableModes, reader?.preferred_mode],
  )
  const selectedMode =
    selectedModeState.paperId === paperId &&
    selectedModeState.mode &&
    availableModes.includes(selectedModeState.mode)
      ? selectedModeState.mode
      : derivedPreferredMode

  function handleSelectMode(nextMode: CommunityPaperReaderMode) {
    setSelectedModeState({
      paperId,
      mode: nextMode,
    })
  }

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
        const effectivePaper: CommunityPaper =
          favoriteStatePatch?.paperId === activePaper.id
            ? {
                ...activePaper,
                favorite_count: favoriteStatePatch.favoriteCount,
                viewer_state: {
                  ...activePaper.viewer_state,
                  ...favoriteStatePatch.viewerState,
                },
              }
            : activePaper

        return (
          <div className="flex flex-col min-h-0 min-w-0 flex-1 bg-[color:var(--px-shell-bg)] px-2 py-2 md:px-3 md:py-3">
            <div
              data-testid="paper-detail-page-shell"
              className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden rounded-[8px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] shadow-[var(--px-shell-shadow)]"
            >
              <PaperDetailHeader
                paper={effectivePaper}
                selectedMode={selectedMode}
                availableModes={availableModes}
                authorsLabel={authorsLabel}
                canDownload={canDownload}
                onSelectMode={handleSelectMode}
                onDownload={() => void handleDownload()}
                onFavoriteStateChange={(payload) => {
                  const nextViewerState = {
                    liked: Boolean(activePaper.viewer_state?.liked),
                    favorited: payload.favorited,
                    favorite_folder_count: payload.favorite_folder_count,
                  }
                  setFavoriteStatePatch({
                    paperId: activePaper.id,
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

              <div className="relative flex min-h-0 min-w-0 flex-1 overflow-hidden bg-[color:var(--px-shell-panel-strong)]">
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
                />
              </div>
            </div>
          </div>
        )
      }}
    </PaperDetailStateBoundary>
  )
}
