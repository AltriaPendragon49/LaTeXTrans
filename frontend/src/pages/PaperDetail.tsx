import { ArrowLeft, ChevronDown, ChevronUp, Download, Languages, Timer } from "lucide-react"
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
  ReaderSelectionContext,
  PaperAnnotation,
  PaperAnnotationOverlayRect,
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

const READER_SELECTION_HIGHLIGHT_NAME = "paper-detail-reader-selection"
const READER_ANNOTATION_COLORS = ["red", "orange", "yellow", "green", "blue", "purple", "fuchsia", "cyan"] as const
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

function isSelectionToolbarEventTarget(target: EventTarget | null): boolean {
  if (!(target instanceof Node)) {
    return false
  }
  const element = target instanceof Element ? target : target.parentElement
  return Boolean(element?.closest("[data-reader-selection-toolbar='true']"))
}

function normalizeReaderMode(mode: CommunityPaperReaderMode): "source" | "translated" {
  return mode === "source" ? "source" : "translated"
}

function isAnnotationVisibleInMode(annotationMode: CommunityPaperReaderMode, currentMode: CommunityPaperReaderMode): boolean {
  return normalizeReaderMode(annotationMode) === normalizeReaderMode(currentMode)
}

function hasPersistableRange(range: Range): boolean {
  try {
    if (range.collapsed) {
      return false
    }
    const startNode = range.startContainer
    const endNode = range.endContainer
    const startDoc = startNode.ownerDocument
    const endDoc = endNode.ownerDocument
    if (!startDoc || startDoc !== endDoc) {
      return false
    }
    return startDoc.contains(startNode) && startDoc.contains(endNode)
  } catch {
    return false
  }
}

function buildRangeFromAnnotationText(annotation: PaperAnnotation): Range | null {
  const readerPanel = document.querySelector<HTMLElement>('[data-testid="paper-detail-reader-panel"]')
  if (!readerPanel) {
    return null
  }

  const normalizedText = normalizeSelectionText(annotation.text)
  if (!normalizedText) {
    return null
  }

  const scope = annotation.anchor_id
    ? (findReaderAnchorElement(readerPanel, annotation.anchor_id) ?? readerPanel)
    : readerPanel

  const walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT, null)
  let node = walker.nextNode()
  while (node) {
    const rawText = node.textContent ?? ""
    const exactIndex = rawText.indexOf(annotation.text)
    if (exactIndex >= 0) {
      const range = document.createRange()
      range.setStart(node, exactIndex)
      range.setEnd(node, exactIndex + annotation.text.length)
      if (hasPersistableRange(range)) {
        return range
      }
    }

    const normalizedNodeText = normalizeSelectionText(rawText)
    const normalizedIndex = normalizedNodeText.indexOf(normalizedText)
    if (normalizedIndex >= 0) {
      const prefix = normalizedNodeText.slice(0, normalizedIndex)
      const suffix = normalizedNodeText.slice(0, normalizedIndex + normalizedText.length)
      const startHint = prefix.length
      const endHint = suffix.length
      const start = Math.min(Math.max(startHint, 0), rawText.length)
      const end = Math.min(Math.max(endHint, start + 1), rawText.length)

      if (end > start) {
        const range = document.createRange()
        range.setStart(node, start)
        range.setEnd(node, end)
        if (hasPersistableRange(range)) {
          return range
        }
      }
    }

    node = walker.nextNode()
  }

  return null
}

function isSelectionEquivalent(
  selection: Pick<ReaderSelectionContext, "text" | "anchor_id" | "mode">,
  annotation: Pick<PaperAnnotation, "text" | "anchor_id" | "mode">,
): boolean {
  if (normalizeReaderMode(selection.mode) !== normalizeReaderMode(annotation.mode)) {
    return false
  }
  if ((selection.anchor_id ?? null) !== (annotation.anchor_id ?? null)) {
    return false
  }

  const selectionText = normalizeSelectionText(selection.text)
  const annotationText = normalizeSelectionText(annotation.text)
  if (!selectionText || !annotationText) {
    return false
  }

  return (
    selectionText === annotationText ||
    selectionText.includes(annotationText) ||
    annotationText.includes(selectionText)
  )
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
  const { t } = useTranslation()
  const [isHeaderExpanded, setIsHeaderExpanded] = useState(true)
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
  const [translatedPdfPreviewUrl, setTranslatedPdfPreviewUrl] = useState<string | null>(null)
  const [translatedPdfPreviewLoading, setTranslatedPdfPreviewLoading] = useState(false)
  const [agentBusy, setAgentBusy] = useState(false)
  const [agentError, setAgentError] = useState<string | null>(null)
  const [agentTurns, setAgentTurns] = useState<CommunityConversationTurn[]>([])
  const [agentInput, setAgentInput] = useState("")
  const [agentMode, setAgentMode] = useState<CommunityAgentMode>("chat")
  const [externalSearchEnabled, setExternalSearchEnabled] = useState(false)
  const [readerSelection, setReaderSelection] = useState<ReaderSelectionContext | null>(null)
  const agentContextRef = useRef<ReaderSelectionContext | null>(null)
  const [agentContext, _setAgentContext] = useState<ReaderSelectionContext | null>(null)
  const setAgentContext = useCallback((val: ReaderSelectionContext | null) => {
    agentContextRef.current = val
    _setAgentContext(val)
  }, [])
  // removed duplicate agent context
  const [annotations, setAnnotations] = useState<PaperAnnotation[]>([])
  const [annotationOverlayRects, setAnnotationOverlayRects] = useState<PaperAnnotationOverlayRect[]>([])
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
      if (!agentContextRef.current) clearReaderSelectionVisual()
      setReaderSelection(null)
      return
    }

    const range = selection.getRangeAt(0)
    if (!readerPanel.contains(range.commonAncestorContainer)) {
      if (!agentContextRef.current) clearReaderSelectionVisual()
      setReaderSelection(null)
      return
    }

    const selectedText = normalizeSelectionText(selection.toString())
    if (!selectedText) {
      if (!agentContextRef.current) clearReaderSelectionVisual()
      setReaderSelection(null)
      return
    }

    const anchorId = findSelectionAnchorId(range.startContainer, readerPanel)
    applyReaderSelectionVisual(range, readerPanel)
    let position = { x: 0, y: 0 }
    if (typeof range.getBoundingClientRect === 'function') {
      const rect = range.getBoundingClientRect()
      position = { x: rect.left + rect.width / 2, y: rect.bottom + 8 }
    }

    setReaderSelection({
      text: selectedText,
      anchor_id: anchorId,
      mode: selectedMode,
      position,
      range: range.cloneRange(),
      color: "yellow",
      note: "",
    })
  }, [applyReaderSelectionVisual, clearReaderSelectionVisual, selectedMode])

  useEffect(() => {
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
    const HighlightCtor = (window as Window & { Highlight?: new (...ranges: Range[]) => unknown }).Highlight
    const supportsCssHighlights = Boolean(cssHighlights && HighlightCtor)

    const allHighlights = [...annotations]
    if (readerSelection?.range) {
      allHighlights.push({
        id: "draft",
        text: readerSelection.text,
        range: readerSelection.range,
        anchor_id: readerSelection.anchor_id,
        mode: readerSelection.mode,
        color: readerSelection.color || "yellow",
        note: readerSelection.note || "",
      })
    }
    const resolveVisibleHighlights = (): PaperAnnotation[] =>
      allHighlights
        .filter((ann) => ann.range && isAnnotationVisibleInMode(ann.mode, selectedMode))
        .map((ann) => {
          const range = hasPersistableRange(ann.range)
            ? ann.range
            : buildRangeFromAnnotationText(ann)
          if (!range || !hasPersistableRange(range)) {
            return null
          }
          return {
            ...ann,
            range,
          }
        })
        .filter((ann): ann is PaperAnnotation => Boolean(ann))

    // Always compute absolute overlay rectangles as a robust visual fallback.
    const readerViewport = document.querySelector<HTMLElement>('[data-testid="paper-reader-scroll-root"]')
    const readerPanel = document.querySelector<HTMLElement>('[data-testid="paper-detail-reader-panel"]')
    const previewViewport = readerPanel?.querySelector<HTMLElement>('[data-testid="paper-preview-viewport"]')
      ?? document.querySelector<HTMLElement>('[data-testid="paper-preview-viewport"]')
    if (!readerViewport) {
      setAnnotationOverlayRects([])
      return
    }

    let rafId: number | null = null
    const computeOverlayRects = () => {
      const visibleHighlights = resolveVisibleHighlights()

      if (supportsCssHighlights && cssHighlights && HighlightCtor) {
        READER_ANNOTATION_COLORS.forEach((color) => cssHighlights.delete(`paper-annotation-${color}`))

        const colorRanges: Record<string, Range[]> = {}
        visibleHighlights.forEach((ann) => {
          const color = ann.color || "yellow"
          if (!colorRanges[color]) colorRanges[color] = []
          colorRanges[color].push(ann.range)
        })

        Object.entries(colorRanges).forEach(([color, ranges]) => {
          try {
            cssHighlights.set(`paper-annotation-${color}`, new HighlightCtor(...ranges.map((r) => r.cloneRange())))
          } catch {
            // Ignore invalid range errors caused by disconnected DOM nodes.
          }
        })
      }

      const viewportRect = readerViewport.getBoundingClientRect()
      const nextRects: PaperAnnotationOverlayRect[] = []

      visibleHighlights.forEach((annotation) => {
        const range = annotation.range
        let rects: DOMRectList
        try {
          rects = range.getClientRects()
        } catch {
          return
        }
        Array.from(rects).forEach((rect, index) => {
          if (rect.width < 1 || rect.height < 1) {
            return
          }
          nextRects.push({
            id: `${annotation.id}-${index}`,
            color: annotation.color || "yellow",
            top: rect.top - viewportRect.top + readerViewport.scrollTop,
            left: rect.left - viewportRect.left + readerViewport.scrollLeft,
            width: rect.width,
            height: rect.height,
          })
        })
      })

      setAnnotationOverlayRects(nextRects)
    }

    const scheduleOverlayRecompute = () => {
      if (rafId !== null) {
        window.cancelAnimationFrame(rafId)
      }
      rafId = window.requestAnimationFrame(computeOverlayRects)
    }

    scheduleOverlayRecompute()
    readerViewport.addEventListener("scroll", scheduleOverlayRecompute, { passive: true })
    previewViewport?.addEventListener("scroll", scheduleOverlayRecompute, { passive: true })
    readerPanel?.addEventListener("scroll", scheduleOverlayRecompute, true)
    document.addEventListener("scroll", scheduleOverlayRecompute, true)
    window.addEventListener("resize", scheduleOverlayRecompute)

    return () => {
      if (rafId !== null) {
        window.cancelAnimationFrame(rafId)
      }
      readerViewport.removeEventListener("scroll", scheduleOverlayRecompute)
      previewViewport?.removeEventListener("scroll", scheduleOverlayRecompute)
      readerPanel?.removeEventListener("scroll", scheduleOverlayRecompute, true)
      document.removeEventListener("scroll", scheduleOverlayRecompute, true)
      window.removeEventListener("resize", scheduleOverlayRecompute)
    }
  }, [annotations, readerSelection, selectedMode])

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

    const handleMouseUp = (event: MouseEvent) => {
      if (isSelectionToolbarEventTarget(event.target)) {
        return
      }
      captureReaderSelection()
    }
    const handleKeyUp = (event: KeyboardEvent) => {
      if (isSelectionToolbarEventTarget(event.target)) {
        return
      }
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
    if (!readerSelection) {
      return
    }

    const handlePointerDown = (event: PointerEvent) => {
      if (isSelectionToolbarEventTarget(event.target)) {
        return
      }
      if (!(event.target instanceof Node)) {
        return
      }

      const readerPanel = document.querySelector<HTMLElement>('[data-testid="paper-detail-reader-panel"]')
      if (readerPanel?.contains(event.target)) {
        return
      }

      window.getSelection()?.removeAllRanges()
      setReaderSelection(null)
      if (!agentContextRef.current) {
        clearReaderSelectionVisual()
      }
    }

    document.addEventListener("pointerdown", handlePointerDown)
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown)
    }
  }, [clearReaderSelectionVisual, readerSelection])

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
    if (!readerSelection && !agentContext) {
      clearReaderSelectionVisual()
    }
  }, [clearReaderSelectionVisual, readerSelection, agentContext])

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
    setAgentContext(null)
    setExternalSearchEnabled(false)
    setAgentMode("chat")
  }, [paperId, setAgentContext])

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

  useEffect(() => {
    setTranslatedPdfPreviewUrl(null)
    setTranslatedPdfPreviewLoading(false)
  }, [paperId])

  useEffect(() => {
    if (selectedMode !== "translated_pdf") {
      setTranslatedPdfPreviewLoading(false)
      return
    }

    if (!paperId || translatedPdfPreviewUrl) {
      return
    }

    const hasTranslatedPdfAsset = Boolean(
      paper?.assets?.translated_pdf ||
      reader?.translated?.kind === "translated_pdf" ||
      paper?.latest_asset?.asset_type === "translated_pdf",
    )
    if (!hasTranslatedPdfAsset) {
      return
    }

    setActionError(null)
    setTranslatedPdfPreviewLoading(false)
    setTranslatedPdfPreviewUrl(`${API_BASE_URL}/api/papers/${paperId}/translated-pdf`)
  }, [paperId, paper, reader, selectedMode, translatedPdfPreviewUrl])

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
    const selectionContext = agentContext
      ? {
        text: agentContext.text,
        anchor_id: agentContext.anchor_id,
        mode: agentContext.mode,
        note: agentContext.note,
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

  function handleSaveAnnotation(annotation: PaperAnnotation) {
    let savedRange: Range | null = null
    try {
      const clonedRange = annotation.range.cloneRange()
      if (hasPersistableRange(clonedRange)) {
        savedRange = clonedRange
      }
    } catch {
      savedRange = null
    }

    if (!savedRange) {
      savedRange = buildRangeFromAnnotationText(annotation)
    }

    if (!savedRange) {
      return
    }
    setAnnotations((prev) => {
      const deduped = prev.filter((item) => !isSelectionEquivalent(annotation, item))
      return [...deduped, { ...annotation, range: savedRange }]
    })
  }

  function handleRemoveHighlightForSelection(selection: ReaderSelectionContext) {
    setAnnotations((prev) => prev.filter((item) => !isSelectionEquivalent(selection, item)))
    window.getSelection()?.removeAllRanges()
    setReaderSelection(null)
    if (!agentContextRef.current) {
      clearReaderSelectionVisual()
    }
  }

  function handleFocusAnnotation(annotation: PaperAnnotation) {
    const targetMode: CommunityPaperReaderMode =
      normalizeReaderMode(annotation.mode) === "source" ? "source" : "translated_html"

    if (targetMode === "source" && availableModes.includes("source")) {
      setSelectedMode("source")
    } else if (targetMode !== "source" && availableModes.includes("translated")) {
      setSelectedMode("translated_html")
    }

    setAgentContext({
      text: annotation.text,
      anchor_id: annotation.anchor_id,
      mode: targetMode,
      note: annotation.note,
    })

    if (annotation.note) {
      setAgentInput(annotation.note)
    }

    if (annotation.anchor_id?.trim()) {
      setPendingAnchorId(annotation.anchor_id)
    }
  }

  return (
    <div
      data-testid="paper-detail-page-shell"
      className="flex-1 flex min-h-0 flex-col min-w-0 bg-surface-container-lowest h-full overflow-hidden"
    >
      <nav className="shrink-0 flex flex-col border-b border-outline-variant/30 bg-surface-container-lowest z-10 sticky top-0 transition-all duration-300">
        {/* Row 1: Back + Title */}
        <div className="h-12 flex items-center justify-between px-6 border-b border-outline-variant/10 relative">
          <div className="flex items-center gap-4 min-w-0 flex-1">
            <Link
              to="/"
              className="p-2 text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest rounded-full transition-colors shrink-0 outline-none focus-visible:ring-2 focus-visible:ring-primary"
              aria-label={t("community.detail.backToFeed")}
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <h1 className="text-lg font-bold text-on-surface truncate" title={activePaper.title}>
              {activePaper.title}
            </h1>
          </div>

          <div className="flex items-center gap-3 shrink-0 ml-4">
            <div className="text-xs font-black uppercase tracking-[0.2em] text-primary/40 mr-4 hidden md:block">
              Lumina Archive
            </div>
            
            <div className="flex bg-surface-container-low rounded-xl p-1 border border-outline-variant/30 shadow-sm overflow-hidden">
              <button
                type="button"
                onClick={() => setSelectedMode("source")}
                className={`px-4 py-1.5 text-xs font-bold tracking-wider rounded-lg transition-all ${
                  selectedMode === "source"
                    ? "bg-surface-container-highest text-on-surface shadow-sm border border-outline-variant/30"
                    : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest/50 border border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
                }`}
              >
                原文
              </button>
              <button
                type="button"
                disabled={!availableModes.includes("translated")}
                onClick={() => setSelectedMode("translated_html")}
                className={`px-4 py-1.5 text-xs font-bold tracking-wider rounded-lg transition-all ${
                  selectedMode === "translated_html" || selectedMode === "translated"
                    ? "bg-surface-container-highest text-on-surface shadow-sm border border-outline-variant/30"
                    : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest/50 border border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
                }`}
              >
                译文 (html)
              </button>
              <button
                type="button"
                disabled={!availableModes.includes("translated") && !canDownload}
                onClick={() => setSelectedMode("translated_pdf")}
                className={`px-4 py-1.5 text-xs font-bold tracking-wider rounded-lg transition-all ${
                  selectedMode === "translated_pdf"
                    ? "bg-surface-container-highest text-on-surface shadow-sm border border-outline-variant/30"
                    : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest/50 border border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
                }`}
              >
                译文 (pdf)
              </button>
            </div>

            <div className="w-px h-6 bg-outline-variant/30 mx-1 hidden sm:block" />

            <div className="flex items-center gap-2">
               <div className="w-8 h-8 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-[10px] font-bold text-primary">
                 UA
               </div>
               {!isHeaderExpanded && (
                 <button
                   onClick={() => setIsHeaderExpanded(true)}
                   className="p-1 text-on-surface-variant hover:text-primary transition-colors ml-1"
                   title="Expand Header"
                 >
                   <ChevronDown className="w-4 h-4" />
                 </button>
               )}
            </div>
          </div>
        </div>

        {isHeaderExpanded && (
          <div className="animate-in slide-in-from-top-1 duration-200">
            {/* Row 2: Authors, Date, Tags */}
            <div className="h-8 flex items-center justify-between px-6 border-b border-outline-variant/10 bg-surface-container-lowest/50">
              <div className="flex items-center gap-6 text-[10px] font-bold text-on-surface-variant/70 uppercase tracking-widest overflow-hidden">
                 <div className="flex items-center gap-2 max-w-2xl truncate">
                   <span className="text-on-surface-variant font-black">Authors:</span>
                   <span className="truncate">{authorsLabel}</span>
                 </div>
                 <div className="flex items-center gap-2 shrink-0">
                   <span className="text-on-surface-variant font-black">Published:</span>
                   <span>{activePaper.official_published_at ? new Date(activePaper.official_published_at).toLocaleDateString() : (activePaper.created_at ? new Date(activePaper.created_at).toLocaleDateString() : 'N/A')}</span>
                 </div>
                 <div className="flex items-center gap-2 shrink-0">
                   <span className="bg-primary/10 text-primary px-2 py-0.5 rounded text-[8px] font-black tracking-tighter">PEER REVIEWED</span>
                 </div>
              </div>

              <div className="flex items-center gap-4 shrink-0">
                 {canTranslate && !canViewProgress && (
                   <button
                     type="button"
                     onClick={handleTranslate}
                     className="text-[9px] font-black uppercase tracking-widest text-primary hover:text-primary-dim transition-colors flex items-center gap-1.5"
                   >
                     <Languages className="w-3 h-3" />
                     {t("community.actions.translate")}
                   </button>
                 )}
                 {canViewProgress && (
                   <button
                     type="button"
                     onClick={handleViewProgress}
                     className="text-[9px] font-black uppercase tracking-widest text-primary hover:text-primary-dim transition-colors flex items-center gap-1.5"
                   >
                     <Timer className="w-3 h-3" />
                     {t("community.actions.viewProgress")}
                   </button>
                 )}
                 <button
                   type="button"
                   disabled={!canDownload}
                   onClick={handleDownload}
                   className="text-[9px] font-black uppercase tracking-widest text-on-surface-variant hover:text-on-surface transition-colors flex items-center gap-1.5 disabled:opacity-30"
                 >
                   <Download className="w-3 h-3" />
                   Download
                 </button>
              </div>
            </div>

            {/* Row 3: Metrics */}
            <div className="h-8 flex items-center px-6 gap-8 bg-surface-container-lowest relative">
               <div className="flex items-center gap-2 group cursor-pointer">
                  <div className="text-[9px] font-black text-on-surface-variant/40 group-hover:text-primary transition-colors uppercase tracking-tighter">Likes</div>
                  <div className="text-[10px] font-bold text-on-surface">{activePaper.like_count || 0}</div>
               </div>
               <div className="flex items-center gap-2 group cursor-pointer">
                  <div className="text-[9px] font-black text-on-surface-variant/40 group-hover:text-primary transition-colors uppercase tracking-tighter">Saves</div>
                  <div className="text-[10px] font-bold text-on-surface">{activePaper.favorite_count || 0}</div>
               </div>
               <div className="flex items-center gap-2">
                  <div className="text-[9px] font-black text-on-surface-variant/40 uppercase tracking-tighter">Visibility</div>
                  <div className="text-[10px] font-bold text-on-surface">Public</div>
               </div>
               <div className="flex items-center gap-2">
                  <div className="text-[9px] font-black text-on-surface-variant/40 uppercase tracking-tighter">Views</div>
                  <div className="text-[10px] font-bold text-on-surface">{activePaper.view_count || "1.2k"}</div>
               </div>
               
               <div className="ml-auto flex items-center gap-3">
                 <div className={`px-2 py-0.5 rounded text-[8px] font-black tracking-tighter uppercase ${hasTranslatedReader ? 'bg-green-500/10 text-green-600' : 'bg-primary/10 text-primary animate-pulse'}`}>
                   {actionError ? "Error" : stageLabel.replace('community.detail.stage.', '')}
                 </div>
                 <button
                   onClick={() => setIsHeaderExpanded(false)}
                   className="p-1 text-on-surface-variant hover:text-primary transition-colors"
                   title="Collapse Header"
                 >
                   <ChevronUp className="w-4 h-4" />
                 </button>
               </div>
            </div>
          </div>
        )}
      </nav>
      
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
            translatedPdfPreviewLoading={translatedPdfPreviewLoading}
            translatedPdfPreviewUrl={translatedPdfPreviewUrl}
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
            onReaderSelectionChange={setReaderSelection}
            onSaveAnnotation={handleSaveAnnotation}
            onRemoveHighlightForSelection={handleRemoveHighlightForSelection}
            annotations={annotations}
            annotationOverlayRects={annotationOverlayRects}
            onFocusAnnotation={handleFocusAnnotation}
            agentContext={agentContext}
            agentBusy={agentBusy}
            agentError={agentError}
            onAgentInputChange={setAgentInput}
            onAgentModeChange={setAgentMode}
            onExternalSearchChange={setExternalSearchEnabled}
            onAgentSubmit={() => void handleAgentSubmit()}
            onAskAI={(selection: ReaderSelectionContext) => {
              setAgentContext(selection)
              if (selection.note) {
                setAgentInput(selection.note)
              } else {
                 setAgentInput("")
              }
              setReaderSelection(null)
              window.getSelection()?.removeAllRanges()
            }}
            onSelectionClear={() => {
              window.getSelection()?.removeAllRanges()
              setReaderSelection(null)
              setAgentContext(null)
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
