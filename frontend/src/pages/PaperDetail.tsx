import { ArrowLeft, Clock3, Link2, Download, Languages, Timer } from "lucide-react"
import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { Link, useLocation, useNavigate, useParams } from "react-router-dom"

import { API_BASE_URL } from "@/api-base"
import { PaperDetailSkeleton } from "@/components/community/PaperDetailSkeleton"
import { PaperDetailWorkspace } from "@/components/community/PaperDetailWorkspace"
import { Button } from "@/components/ui/button"
import { usePaperDetail } from "@/hooks/use-paper-detail"
import {
  createCommunityPaperDownloadSession,
  importCommunityPaper,
  streamCommunityAgentRun,
  translateCommunityPaper,
} from "@/lib/community-api"
import { buildConversationHistory } from "@/lib/community-agent-conversations"
import { useStore } from "@/store/useStore"
import type {
  CommunityAgentCitation,
  CommunityAgentMode,
  CommunityAgentRun,
  CommunityAgentSkillToggles,
  CommunityAgentStreamEvent,
  CommunityAgentToolTrace,
  CommunityConversationTurn,
  CommunityPaper,
  CommunityPaperExperience,
  CommunityPaperReader,
  CommunityPaperReaderMode,
} from "@/types/community"

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

function formatDetailDate(value: string | null | undefined, locale: string, fallback: string) {
  if (!value) {
    return fallback
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return fallback
  }

  return new Intl.DateTimeFormat(locale, {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(parsed)
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

const ACTIVE_TRANSLATION_STATUSES = new Set<CommunityPaper["trans_status"]>(["queued", "processing"])
const FAILED_TRANSLATION_STATUSES = new Set<CommunityPaper["trans_status"]>(["failed"])

function hasSourceReader(reader: CommunityPaperReader | null | undefined) {
  return reader?.state === "source_ready" || Boolean(reader?.source)
}

function hasTranslatedReaderResource(reader: CommunityPaperReader | null | undefined) {
  return reader?.state === "translated_ready" || Boolean(reader?.translated)
}

function resolveStageKey(
  paper: Pick<CommunityPaper, "trans_status"> | null | undefined,
  reader: CommunityPaperReader | null | undefined,
  experience: CommunityPaperExperience | null | undefined,
) {
  if (hasTranslatedReaderResource(reader)) {
    return "community.detail.stage.translatedReady"
  }

  if (reader?.state === "warming" || ACTIVE_TRANSLATION_STATUSES.has(paper?.trans_status ?? "not_started")) {
    return "community.detail.stage.generating"
  }

  if (
    hasSourceReader(reader) &&
    (experience?.failure_type === "translation_failed" ||
      FAILED_TRANSLATION_STATUSES.has(paper?.trans_status ?? "not_started"))
  ) {
    return "community.detail.stage.sourceFallback"
  }

  if (hasSourceReader(reader)) {
    return "community.detail.stage.sourceReady"
  }

  return "community.detail.stage.unavailable"
}

function findReaderAnchorElement(
  root: ParentNode | null,
  anchorId: string,
): HTMLElement | null {
  if (!root || !anchorId.trim()) {
    return null
  }
  if (root instanceof HTMLElement && root.id === anchorId) {
    return root
  }

  const candidates = root.querySelectorAll<HTMLElement>("[id],[data-section-id],[data-block-id]")
  for (const candidate of candidates) {
    if (
      candidate.id === anchorId ||
      candidate.dataset.sectionId === anchorId ||
      candidate.dataset.blockId === anchorId
    ) {
      return candidate
    }
  }
  return null
}

interface ReaderSelectionContext {
  text: string
  anchor_id: string | null
  mode: CommunityPaperReaderMode
}

const READER_SELECTION_HIGHLIGHT_NAME = "paper-detail-reader-selection"
const READER_SELECTION_BLOCK_TAGS = new Set([
  "p",
  "li",
  "blockquote",
  "pre",
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
  "figcaption",
  "td",
  "th",
])

function normalizeSelectionText(value: string) {
  return value.replace(/\s+/g, " ").trim()
}

function findSelectionAnchorId(target: Node | null, root: HTMLElement | null): string | null {
  if (!target || !root) {
    return null
  }

  let current: Node | null = target
  while (current) {
    if (current instanceof HTMLElement) {
      const anchorId = current.id || current.dataset.sectionId || current.dataset.blockId
      if (anchorId) {
        return anchorId
      }
      if (current === root) {
        return null
      }
    }
    current = current.parentNode
  }
  return null
}

function findSelectionHighlightElement(target: Node | null, root: HTMLElement | null): HTMLElement | null {
  if (!target || !root) {
    return null
  }

  let current: Node | null = target
  while (current && current !== root) {
    if (current instanceof HTMLElement) {
      if (READER_SELECTION_BLOCK_TAGS.has(current.tagName.toLowerCase())) {
        return current
      }
    }
    current = current.parentNode
  }

  if (target instanceof HTMLElement) {
    return target
  }
  if (target.parentElement instanceof HTMLElement) {
    return target.parentElement
  }
  return null
}

function createUserTurn(content: string): CommunityConversationTurn {
  return {
    id: `user-${Date.now()}`,
    role: "user",
    content,
    created_at: new Date().toISOString(),
    status: "completed",
  }
}

function createRunningAssistantTurn(mode: CommunityAgentMode): CommunityConversationTurn {
  const createdAt = new Date().toISOString()
  return {
    id: `assistant-${Date.now()}`,
    role: "assistant",
    content: "",
    created_at: createdAt,
    run: {
      run_id: `pending-${Date.now()}`,
      status: "running",
      intent: "answer",
      mode,
      message: "",
      summary: "",
      citations: [],
      tool_trace: [],
      action: null,
    },
    status: "running",
    error: null,
  }
}

function createAssistantTurnFromRun(
  run: CommunityAgentRun,
  id: string,
  createdAt: string,
): CommunityConversationTurn {
  const assistantMessage = run.message ?? run.summary ?? ""
  return {
    id,
    role: "assistant",
    content: assistantMessage,
    created_at: createdAt,
    run,
    status: run.status === "failed" ? "failed" : "completed",
    error: run.status === "failed" ? assistantMessage || null : null,
  }
}

function upsertTrace(
  currentTrace: CommunityAgentToolTrace[] | undefined,
  nextTrace: CommunityAgentToolTrace,
): CommunityAgentToolTrace[] {
  const existing = currentTrace ?? []
  return [...existing.filter((trace) => trace.id !== nextTrace.id), nextTrace]
}

function upsertCitation(
  currentCitations: CommunityAgentCitation[] | undefined,
  nextCitation: CommunityAgentCitation,
): CommunityAgentCitation[] {
  const existing = currentCitations ?? []
  return [...existing.filter((citation) => citation.id !== nextCitation.id), nextCitation]
}

function applyStreamEventToRun(
  currentRun: CommunityAgentRun,
  event: CommunityAgentStreamEvent,
): CommunityAgentRun {
  const nextRunId = event.run_id ?? currentRun.run_id
  const data = event.data ?? {}

  switch (event.type) {
    case "status": {
      const status = typeof data.status === "string" ? data.status : currentRun.status
      const intent = typeof data.intent === "string" ? data.intent : currentRun.intent
      return {
        ...currentRun,
        run_id: nextRunId,
        status: status as CommunityAgentRun["status"],
        intent: intent as CommunityAgentRun["intent"],
      }
    }
    case "assistant_delta": {
      const delta = typeof data.delta === "string" ? data.delta : ""
      const nextMessage = `${currentRun.message ?? currentRun.summary ?? ""}${delta}`
      return {
        ...currentRun,
        run_id: nextRunId,
        status: "running",
        message: nextMessage,
        summary: nextMessage,
      }
    }
    case "citation": {
      const citation = data.citation
      if (!citation || typeof citation !== "object") {
        return currentRun
      }
      return {
        ...currentRun,
        run_id: nextRunId,
        citations: upsertCitation(currentRun.citations, citation as CommunityAgentCitation),
      }
    }
    case "tool_start":
    case "tool_result": {
      const trace = data.trace
      if (!trace || typeof trace !== "object") {
        return currentRun
      }
      return {
        ...currentRun,
        run_id: nextRunId,
        tool_trace: upsertTrace(currentRun.tool_trace, trace as CommunityAgentToolTrace),
      }
    }
    case "action": {
      const action = data.action
      if (!action || typeof action !== "object") {
        return currentRun
      }
      return {
        ...currentRun,
        run_id: nextRunId,
        action: action as CommunityAgentRun["action"],
      }
    }
    case "complete": {
      const snapshot = data.snapshot
      if (!snapshot || typeof snapshot !== "object") {
        return currentRun
      }
      return snapshot as CommunityAgentRun
    }
    case "error": {
      const message = typeof data.message === "string" ? data.message : currentRun.message ?? currentRun.summary ?? ""
      return {
        ...currentRun,
        run_id: nextRunId,
        status: "failed",
        message,
        summary: message,
      }
    }
    default:
      return currentRun
  }
}

export default function PaperDetailPage() {
  const { i18n, t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()
  const previewRef = useRef<HTMLDivElement>(null)
  const { paperId } = useParams<{ paperId: string }>()
  const { paper, preview, readerState, reader, experience, loading, error, notFound, refetch } =
    usePaperDetail(paperId)
  const { config, loadUserSettings, setTaskId, setArxivId } = useStore()
  const [actionError, setActionError] = useState<string | null>(null)
  const [statusOverride, setStatusOverride] = useState<string | null>(null)
  const [canLeaveHint, setCanLeaveHint] = useState<string | null>(null)
  const [softBanner, setSoftBanner] = useState<string | null>(null)
  const [readerHighlight, setReaderHighlight] = useState(false)
  const [agentBusy, setAgentBusy] = useState(false)
  const [agentError, setAgentError] = useState<string | null>(null)
  const [agentTurns, setAgentTurns] = useState<CommunityConversationTurn[]>([])
  const [agentInput, setAgentInput] = useState("")
  const [agentMode, setAgentMode] = useState<CommunityAgentMode>("chat")
  const [externalSearchEnabled, setExternalSearchEnabled] = useState(false)
  const [readerSelection, setReaderSelection] = useState<ReaderSelectionContext | null>(null)
  const [selectedMode, setSelectedMode] = useState<CommunityPaperReaderMode>("source")
  const [activeAnchorId, setActiveAnchorId] = useState<string | null>(null)
  const [pendingAnchorId, setPendingAnchorId] = useState<string | null>(null)
  const anchorResetTimerRef = useRef<number | null>(null)
  const highlightedSelectionElementRef = useRef<HTMLElement | null>(null)
  const hasTranslatedReader = Boolean(reader?.translated)
  const resolvedStageKey = resolveStageKey(paper, reader, experience)
  const resolvedPreferredMode: CommunityPaperReaderMode =
    reader?.preferred_mode ??
    (preview ||
    paper?.trans_status === "completed" ||
    paper?.trans_status === "processing" ||
    paper?.trans_status === "queued" ||
    paper?.latest_asset?.asset_type === "preview_html"
      ? "translated"
      : "source")
  const availableModes: CommunityPaperReaderMode[] = reader?.available_modes?.length
    ? reader.available_modes
    : (hasTranslatedReader ? ["source", "translated"] : ["source"])

  const tryActivateReaderAnchor = useCallback((anchorId: string) => {
    const normalizedAnchorId = anchorId.trim()
    if (!normalizedAnchorId) {
      return false
    }

    const readerPanel = document.querySelector<HTMLElement>('[data-testid="paper-detail-reader-panel"]')
    if (!readerPanel) {
      return false
    }

    const target =
      findReaderAnchorElement(readerPanel, normalizedAnchorId) ??
      findReaderAnchorElement(previewRef.current, normalizedAnchorId)
    if (!target) {
      return false
    }

    target.scrollIntoView({ behavior: "smooth", block: "center" })
    setActiveAnchorId(normalizedAnchorId)
    setReaderHighlight(true)
    if (anchorResetTimerRef.current !== null) {
      window.clearTimeout(anchorResetTimerRef.current)
    }
    anchorResetTimerRef.current = window.setTimeout(() => {
      setReaderHighlight(false)
      setActiveAnchorId((current) => (current === normalizedAnchorId ? null : current))
    }, 2200)
    return true
  }, [])

  const clearReaderSelectionVisual = useCallback(() => {
    if (highlightedSelectionElementRef.current) {
      highlightedSelectionElementRef.current.removeAttribute("data-reader-selection-active")
      highlightedSelectionElementRef.current = null
    }

    const cssHighlights = (
      window as Window & {
        CSS?: {
          highlights?: {
            delete: (name: string) => void
            set: (name: string, highlight: unknown) => void
          }
        }
      }
    ).CSS?.highlights

    cssHighlights?.delete(READER_SELECTION_HIGHLIGHT_NAME)
  }, [])

  const applyReaderSelectionVisual = useCallback(
    (range: Range, readerPanel: HTMLElement) => {
      clearReaderSelectionVisual()

      const cssHighlights = (
        window as Window & {
          CSS?: {
            highlights?: {
              delete: (name: string) => void
              set: (name: string, highlight: unknown) => void
            }
          }
        }
      ).CSS?.highlights
      const HighlightCtor = (
        window as Window & { Highlight?: new (...ranges: Range[]) => unknown }
      ).Highlight

      if (cssHighlights && HighlightCtor) {
        try {
          cssHighlights.set(READER_SELECTION_HIGHLIGHT_NAME, new HighlightCtor(range.cloneRange()))
        } catch {
          // Ignore invalid range errors and keep attribute fallback below.
        }
      }

      const blockElement = findSelectionHighlightElement(range.startContainer, readerPanel)
      if (blockElement) {
        blockElement.setAttribute("data-reader-selection-active", "true")
        highlightedSelectionElementRef.current = blockElement
      }
    },
    [clearReaderSelectionVisual],
  )

  const captureReaderSelection = useCallback(() => {
    const readerPanel = document.querySelector<HTMLElement>('[data-testid="paper-detail-reader-panel"]')
    if (!readerPanel) {
      return
    }

    const selection = window.getSelection()
    if (!selection || selection.isCollapsed || !selection.rangeCount) {
      clearReaderSelectionVisual()
      setReaderSelection(null)
      return
    }

    const range = selection.getRangeAt(0)
    if (!readerPanel.contains(range.commonAncestorContainer)) {
      clearReaderSelectionVisual()
      setReaderSelection(null)
      return
    }

    const selectedText = normalizeSelectionText(selection.toString())
    if (!selectedText) {
      clearReaderSelectionVisual()
      setReaderSelection(null)
      return
    }

    const anchorId = findSelectionAnchorId(range.startContainer, readerPanel)
    applyReaderSelectionVisual(range, readerPanel)
    setReaderSelection({
      text: selectedText,
      anchor_id: anchorId,
      mode: selectedMode,
    })
  }, [applyReaderSelectionVisual, clearReaderSelectionVisual, selectedMode])

  useEffect(() => {
    return () => {
      if (anchorResetTimerRef.current !== null) {
        window.clearTimeout(anchorResetTimerRef.current)
      }
      clearReaderSelectionVisual()
    }
  }, [clearReaderSelectionVisual])

  useEffect(() => {
    const readerPanel = document.querySelector<HTMLElement>('[data-testid="paper-detail-reader-panel"]')
    if (!readerPanel) {
      return
    }

    const handleMouseUp = () => {
      captureReaderSelection()
    }
    const handleKeyUp = () => {
      captureReaderSelection()
    }

    readerPanel.addEventListener("mouseup", handleMouseUp)
    readerPanel.addEventListener("keyup", handleKeyUp)
    return () => {
      readerPanel.removeEventListener("mouseup", handleMouseUp)
      readerPanel.removeEventListener("keyup", handleKeyUp)
    }
  }, [captureReaderSelection, selectedMode, reader, preview])

  useEffect(() => {
    const readerPanel = document.querySelector<HTMLElement>('[data-testid="paper-detail-reader-panel"]')
    if (!readerPanel) {
      return
    }

    readerPanel
      .querySelectorAll<HTMLElement>("[data-reader-anchor-active='true']")
      .forEach((element) => element.removeAttribute("data-reader-anchor-active"))

    if (!activeAnchorId) {
      return
    }

    const target = findReaderAnchorElement(readerPanel, activeAnchorId)
    if (!target) {
      return
    }

    target.setAttribute("data-reader-anchor-active", "true")
    return () => {
      target.removeAttribute("data-reader-anchor-active")
    }
  }, [activeAnchorId, selectedMode, reader, preview])

  useEffect(() => {
    if (!readerSelection) {
      clearReaderSelectionVisual()
    }
  }, [clearReaderSelectionVisual, readerSelection])

  useEffect(() => {
    if (!pendingAnchorId) {
      return
    }

    if (tryActivateReaderAnchor(pendingAnchorId)) {
      setPendingAnchorId(null)
      return
    }

    const readerPanel = document.querySelector<HTMLElement>('[data-testid="paper-detail-reader-panel"]')
    if (!readerPanel) {
      return
    }

    const observer = new MutationObserver(() => {
      if (tryActivateReaderAnchor(pendingAnchorId)) {
        setPendingAnchorId(null)
        observer.disconnect()
        window.clearTimeout(timeoutId)
      }
    })

    observer.observe(readerPanel, {
      childList: true,
      subtree: true,
      attributes: true,
    })

    const timeoutId = window.setTimeout(() => {
      observer.disconnect()
    }, 3000)

    return () => {
      observer.disconnect()
      window.clearTimeout(timeoutId)
    }
  }, [pendingAnchorId, selectedMode, reader, preview, tryActivateReaderAnchor])

  useEffect(() => {
    const currentHash = window.location.hash || location.hash
    const rawHash = currentHash.startsWith("#") ? currentHash.slice(1) : ""
    if (!rawHash) {
      return
    }

    let decoded = rawHash
    try {
      decoded = decodeURIComponent(rawHash)
    } catch {
      decoded = rawHash
    }

    const normalized = decoded.trim()
    if (normalized) {
      setPendingAnchorId(normalized)
    }
  }, [location.hash, location.key, paperId])

  useEffect(() => {
    const currentHash = window.location.hash || location.hash
    const rawHash = currentHash.startsWith("#") ? currentHash.slice(1) : ""
    if (!rawHash) {
      return
    }

    let decoded = rawHash
    try {
      decoded = decodeURIComponent(rawHash)
    } catch {
      decoded = rawHash
    }

    const normalized = decoded.trim()
    if (!normalized || activeAnchorId === normalized) {
      return
    }

    if (tryActivateReaderAnchor(normalized)) {
      setPendingAnchorId(null)
    }
  }, [activeAnchorId, location.hash, location.key, paperId, selectedMode, reader, preview, tryActivateReaderAnchor])

  useEffect(() => {
    setActiveAnchorId(null)
    const currentHash = window.location.hash || location.hash
    if (!currentHash) {
      setPendingAnchorId(null)
    }
  }, [location.hash, location.key, paperId])

  useEffect(() => {
    setAgentTurns([])
    setAgentInput("")
    setAgentError(null)
    setAgentBusy(false)
    setReaderSelection(null)
    setExternalSearchEnabled(false)
    setAgentMode("chat")
  }, [paperId])

  useEffect(() => {
    setReaderSelection(null)
    clearReaderSelectionVisual()
  }, [clearReaderSelectionVisual, selectedMode])

  useEffect(() => {
    if (resolvedStageKey === "community.detail.stage.translatedReady") {
      setSoftBanner(t("community.detail.softReady"))
      setReaderHighlight(true)
      const timer = window.setTimeout(() => {
        setReaderHighlight(false)
      }, 1500)
      return () => window.clearTimeout(timer)
    }
    return undefined
  }, [resolvedStageKey, t])

  useEffect(() => {
    if (statusOverride === "community.detail.stage.generating") {
      const intervalId = window.setInterval(() => {
        void refetch().catch(() => undefined)
      }, 3000)
      return () => window.clearInterval(intervalId)
    }
    return undefined
  }, [refetch, statusOverride])

  useEffect(() => {
    setSelectedMode((currentMode) => {
      if (availableModes.includes(currentMode)) {
        return currentMode
      }
      return resolvedPreferredMode
    })
  }, [availableModes, resolvedPreferredMode])

  useEffect(() => {
    if (resolvedStageKey === "community.detail.stage.translatedReady") {
      setSelectedMode("translated")
    }
  }, [resolvedStageKey])

  if (loading) {
    return (
      <div className="min-h-full bg-[var(--shell-bg)] px-4 py-6 text-[var(--shell-text)] transition-colors sm:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-[2520px]">
          <PaperDetailSkeleton />
        </div>
      </div>
    )
  }

  if (error && !notFound && !paper) {
    return (
      <div className="min-h-full bg-[var(--shell-bg)] px-4 py-6 text-[var(--shell-text)] transition-colors sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl rounded-[32px] border border-rose-500/20 bg-rose-500/5 px-6 py-14 text-center">
          <h1 className="text-3xl font-semibold text-rose-950 dark:text-white">
            {t("community.detail.errorTitle")}
          </h1>
          <p className="mt-3 text-sm text-rose-900/80 dark:text-slate-300">
            {t("community.detail.errorDescription")}
          </p>
          <p className="mt-4 text-xs text-rose-800/80 dark:text-slate-400">{error}</p>
          <Button
            asChild
            variant="outline"
            className="mt-6 rounded-2xl border-[color:var(--shell-border)] bg-[var(--shell-pill)] text-[var(--shell-heading)]"
          >
            <Link to="/">{t("community.detail.backToFeed")}</Link>
          </Button>
        </div>
      </div>
    )
  }

  if (notFound || !paper) {
    return (
      <div className="min-h-full bg-[var(--shell-bg)] px-4 py-6 text-[var(--shell-text)] transition-colors sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl rounded-[32px] border border-[color:var(--shell-border)] bg-[var(--shell-surface)] px-6 py-14 text-center">
          <h1 className="text-3xl font-semibold text-[var(--shell-heading)]">
            {t("community.detail.notFoundTitle")}
          </h1>
          <p className="mt-3 text-sm text-[var(--shell-text-muted)]">
            {t("community.detail.notFoundDescription")}
          </p>
          <Button
            asChild
            variant="outline"
            className="mt-6 rounded-2xl border-[color:var(--shell-border)] bg-[var(--shell-pill)] text-[var(--shell-heading)]"
          >
            <Link to="/">{t("community.detail.backToFeed")}</Link>
          </Button>
        </div>
      </div>
    )
  }

  const activePaper = paper
  const includedAtLabel = formatDetailDate(
    activePaper.created_at,
    i18n.language,
    t("community.detail.unavailable"),
  )
  const originalSourceUrl =
    activePaper.source === "arxiv" && activePaper.arxiv_id
      ? `https://arxiv.org/abs/${activePaper.arxiv_id}`
      : null
  const authorsLabel = formatAuthors(activePaper.authors, t("community.card.authorsUnavailable"))
  const abstractText =
    selectedMode === "translated"
      ? activePaper.abstract_translated || activePaper.abstract_raw || t("community.detail.abstractUnavailable")
      : activePaper.abstract_raw || activePaper.abstract_translated || t("community.detail.abstractUnavailable")
  const canTranslate = !hasTranslatedReader && ["not_started", "failed"].includes(activePaper.trans_status)
  const canViewProgress = Boolean(
    activePaper.community_selected_task_id && ["queued", "processing"].includes(activePaper.trans_status),
  )
  const canDownload = Boolean(
    activePaper.assets?.translated_pdf ||
      reader?.translated?.kind === "translated_pdf" ||
      activePaper.latest_asset?.asset_type === "translated_pdf" ||
      activePaper.trans_status === "completed",
  )
  const stageLabel = t(
    statusOverride ??
      resolvedStageKey ??
      (selectedMode === "source"
        ? "community.detail.stage.sourceReady"
        : "community.detail.stage.translatedReady"),
  )
  const detailMetaItems = [
    {
      key: "includedAt",
      icon: Clock3,
      label: t("community.detail.includedAt", { value: includedAtLabel }),
      ariaLabel: t("community.detail.includedAt", { value: includedAtLabel }),
    },
  ]

  async function handleTranslate() {
    if (!paperId) {
      return
    }

    try {
      setActionError(null)
      await loadUserSettings()
      const response = await translateCommunityPaper(paperId, {
        source_language: config.source_language,
        target_language: config.target_language,
        advanced_config: config.advanced_config,
      })
      setTaskId(response.task_id)
      setArxivId(activePaper.arxiv_id)
      setStatusOverride("community.detail.stage.generating")
      setCanLeaveHint(t("community.detail.canLeave"))
      setSoftBanner(null)
      const processingRoute = response.processing_url?.trim() || `/processing?taskId=${response.task_id}`
      navigate(processingRoute)
    } catch (translateError) {
      setActionError(extractActionErrorMessage(translateError) ?? t("community.actions.translateError"))
    }
  }

  async function runPaperDetailConversationTurn(prompt: string) {
    if (!paperId || !prompt.trim() || agentBusy) {
      return
    }

    const normalizedPrompt = prompt.trim()
    const userTurn = createUserTurn(normalizedPrompt)
    const runningAssistantTurn = createRunningAssistantTurn(agentMode)
    const history = buildConversationHistory(agentTurns)
    const skillToggles: CommunityAgentSkillToggles = {
      external_search: externalSearchEnabled,
    }
    const selectionContext = readerSelection
      ? {
        text: readerSelection.text,
        anchor_id: readerSelection.anchor_id,
        mode: readerSelection.mode,
      }
      : null

    setAgentInput("")
    setAgentBusy(true)
    setAgentError(null)
    setAgentTurns((current) => [...current, userTurn, runningAssistantTurn])

    try {
      const run = await streamCommunityAgentRun(
        {
          input: normalizedPrompt,
          paper_id: paperId,
          mode: agentMode,
          skill_toggles: skillToggles,
          context: {
            source: "paper_detail",
            current_mode: selectedMode,
            history,
            reader_selection: selectionContext,
          },
        },
        {
          onEvent: (event) => {
            const streamEvent = event as CommunityAgentStreamEvent
            setAgentTurns((current) =>
              current.map((turn) => {
                if (turn.id !== runningAssistantTurn.id) {
                  return turn
                }

                const currentRun =
                  turn.run ??
                  ({
                    run_id: runningAssistantTurn.run?.run_id ?? `pending-${Date.now()}`,
                    status: "running",
                    intent: "answer",
                    mode: agentMode,
                    message: turn.content,
                    summary: turn.content,
                    citations: [],
                    tool_trace: [],
                    action: null,
                  } as CommunityAgentRun)
                const nextRun = applyStreamEventToRun(currentRun, streamEvent)
                const nextContent = nextRun.message ?? nextRun.summary ?? turn.content

                return {
                  ...turn,
                  content: nextContent,
                  run: nextRun,
                  status:
                    nextRun.status === "failed"
                      ? "failed"
                      : nextRun.status === "completed"
                        ? "completed"
                        : "running",
                  error:
                    nextRun.status === "failed"
                      ? (nextRun.message ?? nextRun.summary ?? t("community.agent.error"))
                      : null,
                }
              }),
            )
          },
        },
      )

      setAgentTurns((current) =>
        current.map((turn) =>
          turn.id === runningAssistantTurn.id
            ? createAssistantTurnFromRun(run, runningAssistantTurn.id, runningAssistantTurn.created_at)
            : turn,
        ),
      )
    } catch (runError) {
      const message = extractActionErrorMessage(runError) ?? t("community.agent.error")
      setAgentError(message)
      setAgentTurns((current) =>
        current.map((turn) =>
          turn.id === runningAssistantTurn.id
            ? {
              ...turn,
              status: "failed",
              error: message,
              content: message,
            }
            : turn,
        ),
      )
    } finally {
      setAgentBusy(false)
    }
  }

  async function handleAgentSubmit() {
    await runPaperDetailConversationTurn(agentInput)
  }

  async function handleAgentQuickRun(input: string) {
    await runPaperDetailConversationTurn(input)
  }

  async function handleAgentCitationOpen(citation: CommunityAgentCitation) {
    const citationPaperId = citation.paper_id?.trim() ?? ""
    const citationAnchorId = citation.anchor_id?.trim() ?? ""

    if (citationPaperId && paperId && citationPaperId === paperId && citationAnchorId) {
      const translatedAnchorIds = new Set((reader?.translated?.anchors ?? []).map((item) => item.anchor_id))
      const sourceAnchorIds = new Set((reader?.source?.anchors ?? []).map((item) => item.anchor_id))

      if (translatedAnchorIds.has(citationAnchorId) && selectedMode !== "translated" && availableModes.includes("translated")) {
        setSelectedMode("translated")
      } else if (sourceAnchorIds.has(citationAnchorId) && selectedMode !== "source" && availableModes.includes("source")) {
        setSelectedMode("source")
      }

      setPendingAnchorId(citationAnchorId)
      return
    }

    if (citationPaperId) {
      navigate(
        citationAnchorId
          ? `/paper/${citationPaperId}#${encodeURIComponent(citationAnchorId)}`
          : `/paper/${citationPaperId}`,
      )
      return
    }

    if (citation.arxiv_id) {
      const imported = await importCommunityPaper({
        source: "arxiv",
        arxiv_id: citation.arxiv_id,
      })
      navigate(`/paper/${imported.paper_id}`)
      return
    }

    if (citation.url) {
      window.open(citation.url, "_blank", "noopener,noreferrer")
    }
  }

  function handleViewProgress() {
    if (!activePaper.community_selected_task_id) {
      return
    }

    setTaskId(activePaper.community_selected_task_id)
    setArxivId(activePaper.arxiv_id)
    navigate(`/processing?taskId=${activePaper.community_selected_task_id}`)
  }

  function handlePreview() {
    if (availableModes.includes("translated")) {
      setSelectedMode("translated")
    }
    window.setTimeout(() => {
      const target =
        previewRef.current ??
        document.getElementById("paper-preview-reader") ??
        document.querySelector<HTMLElement>('[data-testid="paper-detail-reader-panel"]')
      target?.scrollIntoView({ behavior: "smooth", block: "start" })
    }, 0)
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
      const detail = extractActionErrorMessage(downloadError)
      setActionError(
        detail?.includes("Translated PDF")
          ? t("community.actions.downloadUnavailable")
          : (detail ?? t("community.actions.downloadError")),
      )
    }
  }

  return (
    <div
      data-testid="paper-detail-page-shell"
      className="flex-1 flex min-h-0 flex-col min-w-0 bg-surface-container-lowest h-full overflow-hidden"
    >
      <header className="h-14 shrink-0 flex items-center justify-between px-6 border-b border-outline-variant/30 bg-surface-container-lowest z-10 relative">
        <div className="flex items-center gap-4 min-w-0 flex-1">
          <Link
            to="/"
            className="p-2 text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest rounded-full transition-colors shrink-0 outline-none focus-visible:ring-2 focus-visible:ring-primary"
            aria-label={t("community.detail.backToFeed")}
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <h1 className="text-base font-medium text-on-surface truncate max-w-2xl" title={activePaper.title}>
            {activePaper.title}
          </h1>
          <span className="text-sm text-on-surface-variant truncate max-w-md hidden lg:inline border-l border-outline-variant/30 pl-4" title={authorsLabel}>
            {authorsLabel}
          </span>
        </div>

        <div className="flex items-center gap-3 shrink-0 ml-4">
          <div className="hidden sm:flex bg-surface-container-low rounded-lg p-1 border border-outline-variant/30">
            <button
              type="button"
              disabled={!availableModes.includes("source")}
              onClick={() => setSelectedMode("source")}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all border ${
                selectedMode === "source"
                  ? "bg-surface-container-highest text-on-surface shadow-sm border-outline-variant/30"
                  : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest/50 border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
              }`}
            >
              {t("community.detail.mode.source")}
            </button>
            <button
              type="button"
              disabled={!availableModes.includes("translated")}
              onClick={() => setSelectedMode("translated")}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all border ${
                selectedMode === "translated"
                  ? "bg-surface-container-highest text-on-surface shadow-sm border-outline-variant/30"
                  : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest/50 border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
              }`}
            >
              {t("community.detail.mode.translated")}
            </button>
          </div>

          <div className="hidden sm:block w-px h-6 bg-outline-variant/30" />
          
          <div className="hidden md:flex items-center gap-2 text-xs text-on-surface-variant px-2">
             <span className={`flex h-2 w-2 rounded-full ${actionError ? 'bg-error' : (hasTranslatedReader ? 'bg-primary' : 'bg-primary/50 animate-pulse')}`} />
             {actionError ? "Error" : stageLabel}
          </div>

          {canTranslate && !canViewProgress && (
            <Button
              type="button"
              variant="default"
              size="sm"
              onClick={handleTranslate}
              className="flex items-center gap-2 px-3 py-1.5"
            >
              <Languages className="w-4 h-4" />
              <span className="hidden sm:inline">{t("community.actions.translate")}</span>
            </Button>
          )}

          {canViewProgress && (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={handleViewProgress}
              className="flex items-center gap-2 px-3 py-1.5"
            >
              <Timer className="w-4 h-4" />
              <span className="hidden sm:inline">{t("community.actions.viewProgress")}</span>
            </Button>
          )}

          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={!canDownload}
            onClick={handleDownload}
            className="flex items-center gap-2 text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest rounded-lg px-3 py-1.5 transition-colors font-medium border border-transparent shadow-none disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download className="w-4 h-4" />
            <span className="hidden sm:inline">{t("community.actions.download")}</span>
          </Button>
        </div>
      </header>
      
      <div className="flex-1 flex min-h-0 min-w-0 overflow-hidden relative">

          <PaperDetailWorkspace
            paper={activePaper}
            preview={preview}
            readerState={readerState}
            reader={reader}
            preferredMode={selectedMode}
            availableModes={availableModes}
            stageLabel={stageLabel}
            softBanner={softBanner}
            canLeaveHint={canLeaveHint ?? experience?.can_leave_hint ?? null}
            originalSourceUrl={originalSourceUrl}
            abstractText={abstractText}
            readerHighlight={readerHighlight}
            previewRef={previewRef}
            canTranslate={canTranslate}
            canViewProgress={canViewProgress}
            canDownload={canDownload}
            actionError={actionError ?? error}
            onTranslate={handleTranslate}
            onViewProgress={handleViewProgress}
            onPreview={handlePreview}
            onDownload={handleDownload}
            onModeChange={setSelectedMode}
            agentTurns={agentTurns}
            agentInput={agentInput}
            agentMode={agentMode}
            externalSearchEnabled={externalSearchEnabled}
            readerSelection={readerSelection}
            agentBusy={agentBusy}
            agentError={agentError}
            onAgentInputChange={setAgentInput}
            onAgentModeChange={setAgentMode}
            onExternalSearchChange={setExternalSearchEnabled}
            onAgentSubmit={() => void handleAgentSubmit()}
            onSelectionClear={() => {
              window.getSelection()?.removeAllRanges()
              setReaderSelection(null)
              clearReaderSelectionVisual()
            }}
            onQuickExplain={() => void handleAgentQuickRun(t("community.detail.quickExplain"))}
            onQuickSummary={() => void handleAgentQuickRun(t("community.detail.quickSummary"))}
            onCitationOpen={(citation) => void handleAgentCitationOpen(citation)}
          />
      </div>
    </div>
  )
}
