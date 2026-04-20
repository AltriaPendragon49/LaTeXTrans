import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router-dom"

import { API_BASE_URL } from "@/api-base"
import { usePaperDetail } from "@/features/community-paper/hooks/use-paper-detail"
import {
  createCommunityPaperDownloadSession,
  translateCommunityPaper,
} from "@/features/community-paper/services/community-paper-api"
import { useTranslationConfig } from "@/features/translation-workflow/hooks/useTranslationConfig"
import { useTranslationTask } from "@/features/translation-workflow/hooks/useTranslationTask"
import type { CommunityPaperReaderMode } from "@/types/community"

import { PaperDetailHeader } from "./PaperDetailHeader"
import { PaperDetailStateBoundary } from "./PaperDetailStateBoundary"
import { PaperDetailWorkspace } from "./PaperDetailWorkspace"
import {
  resolveAvailableModes,
  resolvePreferredMode,
  resolveStageLabel,
} from "../utils/paper-detail-mode-resolution"

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

export function PaperDetailScreen({ paperId }: PaperDetailScreenProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
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
  const { config } = useTranslationConfig()
  const { setTaskId, setArxivId } = useTranslationTask()
  const [isHeaderExpanded, setIsHeaderExpanded] = useState(false)
  const [selectedModeState, setSelectedModeState] = useState<{
    paperId: string | null
    mode: CommunityPaperReaderMode | null
  }>({
    paperId: null,
    mode: null,
  })
  const [actionError, setActionError] = useState<string | null>(null)

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

  async function handleTranslate(activePaperArxivId: string | null | undefined) {
    if (!paperId) {
      return
    }

    try {
      setActionError(null)
      const response = await translateCommunityPaper(paperId, config)
      setTaskId(response.task_id)
      setArxivId(activePaperArxivId ?? null)
      navigate(response.processing_url)
    } catch (translateError) {
      setActionError(extractActionErrorMessage(translateError) ?? t("community.actions.translateError"))
    }
  }

  function handleViewProgress(activePaperTaskId: string | null | undefined, activePaperArxivId: string | null | undefined) {
    if (!activePaperTaskId) {
      return
    }
    setTaskId(activePaperTaskId)
    setArxivId(activePaperArxivId ?? null)
    navigate(`/processing?taskId=${activePaperTaskId}`)
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
        const hasTranslatedMode = availableModes.includes("translated_pdf")
        const stageLabel = resolveStageLabel(activePaper.trans_status, readerState, hasTranslatedMode, t)
        const canTranslate = activePaper.trans_status === "not_started" || activePaper.trans_status === "failed"
        const canViewProgress =
          Boolean(activePaper.community_selected_task_id) &&
          (activePaper.trans_status === "queued" || activePaper.trans_status === "processing")
        const canDownload = activePaper.trans_status === "completed"
        const originalSourceUrl =
          reader?.source?.url ??
          (activePaper.arxiv_id ? `https://arxiv.org/abs/${activePaper.arxiv_id}` : null)
        const abstractText =
          (selectedMode === "source" ? activePaper.abstract_raw : activePaper.abstract_translated) ||
          activePaper.abstract_raw ||
          activePaper.abstract_translated ||
          t("community.detail.abstractUnavailable")

        return (
          <div className="min-w-0 flex-1 bg-[color:var(--px-shell-bg)] px-2 py-2 md:px-3 md:py-3">
            <div
              data-testid="paper-detail-page-shell"
              className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden rounded-[24px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] shadow-[var(--px-shell-shadow)]"
            >
              <PaperDetailHeader
                paper={activePaper}
                selectedMode={selectedMode}
                availableModes={availableModes}
                isHeaderExpanded={isHeaderExpanded}
                authorsLabel={authorsLabel}
                stageLabel={stageLabel}
                actionError={actionError}
                canTranslate={canTranslate}
                canViewProgress={canViewProgress}
                canDownload={canDownload}
                onSelectMode={handleSelectMode}
                onToggleExpanded={setIsHeaderExpanded}
                onTranslate={() => void handleTranslate(activePaper.arxiv_id)}
                onViewProgress={() =>
                  handleViewProgress(activePaper.community_selected_task_id, activePaper.arxiv_id)
                }
                onDownload={() => void handleDownload()}
              />

              <div className="relative flex min-h-0 min-w-0 flex-1 overflow-hidden bg-[color:var(--px-shell-panel-strong)]">
                <PaperDetailWorkspace
                  key={activePaper.id}
                  paper={activePaper}
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
