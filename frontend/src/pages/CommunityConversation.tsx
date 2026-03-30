import { ArrowUpRight, Bot, Loader2, MessageSquarePlus, Sparkles, Trash2, User } from "lucide-react"
import { useEffect, useMemo, useRef, useState, type FormEvent } from "react"
import { useTranslation } from "react-i18next"
import { useLocation, useNavigate, useParams } from "react-router-dom"

import { LoginPrompt } from "@/components/LoginPrompt"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { useAuth } from "@/contexts/AuthContext"
import {
  buildConversationHistory,
  createSeedConversationRecord,
  deriveConversationTitle,
} from "@/lib/community-agent-conversations"
import {
  deleteCommunityAgentConversation,
  importCommunityPaper,
  listCommunityAgentConversations,
  streamCommunityAgentRun,
  upsertCommunityAgentConversation,
} from "@/lib/community-api"
import { cn } from "@/lib/utils"
import type {
  CommunityAgentCitation,
  CommunityAgentMode,
  CommunityAgentRun,
  CommunityAgentSkillToggles,
  CommunityAgentStreamEvent,
  CommunityAgentToolTrace,
  CommunityConversationRecord,
  CommunityConversationTurn,
} from "@/types/community"

interface LocationState {
  seedInput?: string
  seedSkillToggles?: CommunityAgentSkillToggles
}

function createConversationId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID()
  }
  return `conversation-${Date.now()}`
}

function createAssistantTurnFromRun(
  run: CommunityAgentRun,
  id: string = `assistant-${Date.now()}`,
  createdAt: string = new Date().toISOString(),
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

function upsertTrace(
  currentTrace: CommunityAgentToolTrace[] | undefined,
  nextTrace: CommunityAgentToolTrace,
): CommunityAgentToolTrace[] {
  const existing = currentTrace ?? []
  return [
    ...existing.filter((trace) => trace.id !== nextTrace.id),
    nextTrace,
  ]
}

function upsertCitation(
  currentCitations: CommunityAgentCitation[] | undefined,
  nextCitation: CommunityAgentCitation,
): CommunityAgentCitation[] {
  const existing = currentCitations ?? []
  return [
    ...existing.filter((citation) => citation.id !== nextCitation.id),
    nextCitation,
  ]
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

function createUserTurn(content: string): CommunityConversationTurn {
  return {
    id: `user-${Date.now()}`,
    role: "user",
    content,
    created_at: new Date().toISOString(),
    status: "completed",
  }
}

function getConversationScopedPaperId(record: CommunityConversationRecord): string | undefined {
  for (let index = record.turns.length - 1; index >= 0; index -= 1) {
    const turn = record.turns[index]
    if (turn.role !== "assistant" || !turn.run) {
      continue
    }

    const actionPaperId = turn.run.action?.paper_id
    if (typeof actionPaperId === "string" && actionPaperId.trim()) {
      return actionPaperId.trim()
    }

    const citationPaperId = turn.run.citations?.find(
      (citation) => typeof citation.paper_id === "string" && citation.paper_id.trim(),
    )?.paper_id
    if (typeof citationPaperId === "string" && citationPaperId.trim()) {
      return citationPaperId.trim()
    }
  }
  return undefined
}

function getIntentBadgeKey(run: CommunityAgentRun | null | undefined) {
  switch (run?.intent) {
    case "search":
      return "community.agent.intent.search"
    case "translate":
      return "community.agent.intent.translate"
    case "answer":
    default:
      return "community.agent.intent.answer"
  }
}

function getModeBadgeKey(mode: CommunityAgentMode | null | undefined) {
  return mode === "deep_research"
    ? "community.agent.mode.deepResearch"
    : "community.agent.mode.chat"
}

function formatConversationTimestamp(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ""
  }

  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  })
}

function buildRunningProgressSteps(
  t: (key: string) => string,
  externalSearchEnabled: boolean,
  mode: CommunityAgentMode,
) {
  if (mode === "deep_research") {
    const deepResearchSteps = [
      t("community.conversation.progressStepAnalyze"),
      t("community.conversation.progressStepSearchLocal"),
    ]
    if (externalSearchEnabled) {
      deepResearchSteps.push(t("community.conversation.progressStepSearchExternal"))
    }
    deepResearchSteps.push(
      t("community.conversation.progressStepSynthesizeReport"),
      t("community.conversation.progressStepFinalizeReport"),
    )
    return deepResearchSteps
  }

  const steps = [
    t("community.conversation.progressStepAnalyze"),
    t("community.conversation.progressStepSearchLocal"),
  ]

  if (externalSearchEnabled) {
    steps.push(t("community.conversation.progressStepSearchExternal"))
  }

  steps.push(
    t("community.conversation.progressStepCompose"),
    t("community.conversation.progressStepFinalize"),
  )

  return steps
}

export default function CommunityConversationPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const { conversationId = "" } = useParams()
  const { user, isAuthenticated, loading: authLoading } = useAuth()
  const locationState = (location.state ?? null) as LocationState | null

  const [conversations, setConversations] = useState<CommunityConversationRecord[]>([])
  const [conversationsLoading, setConversationsLoading] = useState(false)
  const [conversationsHydrated, setConversationsHydrated] = useState(false)
  const [deletingConversationId, setDeletingConversationId] = useState<string | null>(null)
  const [input, setInput] = useState("")
  const [agentMode, setAgentMode] = useState<CommunityAgentMode>("chat")
  const [externalSearchEnabled, setExternalSearchEnabled] = useState(
    Boolean(locationState?.seedSkillToggles?.external_search),
  )
  const [agentBusy, setAgentBusy] = useState(false)
  const [agentError, setAgentError] = useState<string | null>(null)
  const [runningStageIndex, setRunningStageIndex] = useState(0)
  const messageListRef = useRef<HTMLDivElement | null>(null)
  const seededConversationIdRef = useRef<string | null>(null)
  const suppressedBootstrapConversationIdRef = useRef<string | null>(null)

  const runningProgressSteps = useMemo(
    () => buildRunningProgressSteps(t, externalSearchEnabled, agentMode),
    [agentMode, externalSearchEnabled, t],
  )

  useEffect(() => {
    if (authLoading || !isAuthenticated) {
      setConversations([])
      setConversationsLoading(false)
      setConversationsHydrated(false)
      return
    }

    let cancelled = false
    setConversationsLoading(true)
    setConversationsHydrated(false)
    void listCommunityAgentConversations()
      .then((records) => {
        if (!cancelled) {
          setConversations(records)
        }
      })
      .catch((error) => {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : t("community.agent.error")
          setAgentError(message)
        }
      })
      .finally(() => {
        if (!cancelled) {
          setConversationsLoading(false)
          setConversationsHydrated(true)
        }
      })

    return () => {
      cancelled = true
    }
  }, [authLoading, isAuthenticated, t])

  useEffect(() => {
    setExternalSearchEnabled(Boolean(locationState?.seedSkillToggles?.external_search))
  }, [conversationId, locationState?.seedSkillToggles?.external_search])

  useEffect(() => {
    if (
      suppressedBootstrapConversationIdRef.current &&
      suppressedBootstrapConversationIdRef.current !== conversationId
    ) {
      suppressedBootstrapConversationIdRef.current = null
    }
  }, [conversationId])

  useEffect(() => {
    if (authLoading || !conversationsHydrated || conversationsLoading || !isAuthenticated || !conversationId) {
      return
    }

    if (suppressedBootstrapConversationIdRef.current === conversationId) {
      return
    }

    const existing = conversations.find((entry) => entry.id === conversationId)
    if (existing) {
      return
    }

    const seedInput = locationState?.seedInput?.trim()
    const nextRecord = seedInput
      ? createSeedConversationRecord(conversationId, seedInput)
      : {
          id: conversationId,
          title: t("community.agent.newChat"),
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          turns: [],
        }

    seededConversationIdRef.current = seedInput ? nextRecord.id : null
    setConversations((current) =>
      [nextRecord, ...current.filter((entry) => entry.id !== nextRecord.id)].sort((left, right) =>
        right.updated_at.localeCompare(left.updated_at),
      ),
    )
    void upsertCommunityAgentConversation(nextRecord).catch(() => undefined)
  }, [authLoading, conversationId, conversations, conversationsHydrated, conversationsLoading, isAuthenticated, locationState?.seedInput, t])

  const currentConversation = useMemo(
    () => conversations.find((entry) => entry.id === conversationId) ?? null,
    [conversationId, conversations],
  )

  function mergeConversationRecord(record: CommunityConversationRecord) {
    setConversations((current) =>
      [record, ...current.filter((entry) => entry.id !== record.id)].sort((left, right) =>
        right.updated_at.localeCompare(left.updated_at),
      ),
    )
  }

  function updateConversationTurn(
    targetConversationId: string,
    targetTurnId: string,
    updater: (turn: CommunityConversationTurn) => CommunityConversationTurn,
  ) {
    setConversations((current) =>
      current.map((entry) => {
        if (entry.id !== targetConversationId) {
          return entry
        }
        return {
          ...entry,
          updated_at: new Date().toISOString(),
          turns: entry.turns.map((turn) => (turn.id === targetTurnId ? updater(turn) : turn)),
        }
      }),
    )
  }

  useEffect(() => {
    if (!agentBusy) {
      setRunningStageIndex(0)
      return
    }

    setRunningStageIndex(0)
    const intervalId = window.setInterval(() => {
      setRunningStageIndex((currentIndex) => Math.min(currentIndex + 1, runningProgressSteps.length - 1))
    }, 2500)

    return () => window.clearInterval(intervalId)
  }, [agentBusy, runningProgressSteps.length])

  useEffect(() => {
    const container = messageListRef.current
    if (!container) {
      return
    }

    const frameId = window.requestAnimationFrame(() => {
      if (typeof container.scrollTo === "function") {
        container.scrollTo({
          top: container.scrollHeight,
          behavior: "smooth",
        })
        return
      }
      container.scrollTop = container.scrollHeight
    })

    return () => window.cancelAnimationFrame(frameId)
  }, [agentBusy, conversationId, currentConversation?.turns.length, runningStageIndex])

  async function runConversationTurn(
    record: CommunityConversationRecord,
    latestUserInput: string,
    skillTogglesOverride?: CommunityAgentSkillToggles,
    modeOverride?: CommunityAgentMode,
  ) {
    setAgentBusy(true)
    setAgentError(null)
    const runMode = modeOverride ?? agentMode
    const scopedPaperId = getConversationScopedPaperId(record)

    const historySource =
      record.turns.at(-1)?.role === "user" ? record.turns.slice(0, -1) : record.turns

    try {
      const runningAssistantTurn = createRunningAssistantTurn(runMode)
      const runningRecord: CommunityConversationRecord = {
        ...record,
        title: record.title || deriveConversationTitle(latestUserInput),
        updated_at: new Date().toISOString(),
        turns: [...record.turns, runningAssistantTurn],
      }
      mergeConversationRecord(runningRecord)

      const run = await streamCommunityAgentRun({
        input: latestUserInput,
        ...(scopedPaperId ? { paper_id: scopedPaperId } : {}),
        skill_toggles: skillTogglesOverride ?? {
          external_search: externalSearchEnabled,
        },
        mode: runMode,
        context: {
          source: "conversation",
          history: buildConversationHistory(historySource),
          conversation_id: record.id,
        },
      }, {
        onEvent: (event) => {
          updateConversationTurn(record.id, runningAssistantTurn.id, (turn) => {
            const currentRun = turn.run ?? {
              run_id: runningAssistantTurn.run?.run_id ?? `pending-${Date.now()}`,
              status: "running",
              intent: "answer",
              mode: runMode,
              message: turn.content,
              summary: turn.content,
              citations: [],
              tool_trace: [],
              action: null,
            }
            const nextRun = applyStreamEventToRun(currentRun, event)
            const nextContent = nextRun.message ?? nextRun.summary ?? turn.content
            return {
              ...turn,
              content: nextContent ?? "",
              run: nextRun,
              status: nextRun.status === "failed" ? "failed" : nextRun.status === "completed" ? "completed" : "running",
              error: nextRun.status === "failed" ? (nextRun.message ?? nextRun.summary ?? t("community.agent.error")) : null,
            }
          })
        },
      })

      const updatedRecord: CommunityConversationRecord = {
        ...runningRecord,
        updated_at: new Date().toISOString(),
        turns: runningRecord.turns.map((turn) =>
          turn.id === runningAssistantTurn.id
            ? createAssistantTurnFromRun(run, runningAssistantTurn.id, runningAssistantTurn.created_at)
            : turn,
        ),
      }
      mergeConversationRecord(updatedRecord)
      const persisted = await upsertCommunityAgentConversation(updatedRecord)
      mergeConversationRecord(persisted)
    } catch (error) {
      const message = error instanceof Error ? error.message : t("community.agent.error")
      setAgentError(message)
    } finally {
      setAgentBusy(false)
    }
  }

  useEffect(() => {
    if (!isAuthenticated || !currentConversation || agentBusy) {
      return
    }

    if (seededConversationIdRef.current !== currentConversation.id) {
      return
    }

    const lastTurn = currentConversation.turns.at(-1)
    if (!lastTurn || lastTurn.role !== "user") {
      seededConversationIdRef.current = null
      return
    }

    seededConversationIdRef.current = null
    void runConversationTurn(
      currentConversation,
      lastTurn.content,
      locationState?.seedSkillToggles ?? {
        external_search: externalSearchEnabled,
      },
      agentMode,
    )
  }, [agentBusy, agentMode, currentConversation, externalSearchEnabled, isAuthenticated, locationState?.seedSkillToggles])

  async function handleCitationOpen(citation: CommunityAgentCitation) {
    if (citation.paper_id) {
      navigate(`/paper/${citation.paper_id}`)
      return
    }

    if (citation.arxiv_id) {
      try {
        const imported = await importCommunityPaper({
          source: "arxiv",
          arxiv_id: citation.arxiv_id,
        })
        navigate(`/paper/${imported.paper_id}`)
      } catch {
        window.open(`https://arxiv.org/abs/${citation.arxiv_id}`, "_blank", "noopener,noreferrer")
      }
      return
    }

    if (citation.url) {
      window.open(citation.url, "_blank", "noopener,noreferrer")
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!isAuthenticated || !currentConversation || agentBusy) {
      return
    }

    const normalized = input.trim()
    if (!normalized) {
      return
    }

    const updatedRecord: CommunityConversationRecord = {
      ...currentConversation,
      title: currentConversation.title || deriveConversationTitle(normalized),
      updated_at: new Date().toISOString(),
      turns: [...currentConversation.turns, createUserTurn(normalized)],
    }
    mergeConversationRecord(updatedRecord)
    await upsertCommunityAgentConversation(updatedRecord)
    setInput("")
    await runConversationTurn(updatedRecord, normalized, undefined, agentMode)
  }

  function handleNewChat() {
    if (!isAuthenticated) {
      navigate("/login")
      return
    }
    seededConversationIdRef.current = null
    suppressedBootstrapConversationIdRef.current = null
    navigate(`/agent/${createConversationId()}`)
  }

  async function handleDeleteConversation(targetConversationId: string) {
    if (!isAuthenticated || deletingConversationId) {
      return
    }

    setDeletingConversationId(targetConversationId)
    try {
      await deleteCommunityAgentConversation(targetConversationId)
      const remaining = conversations.filter((entry) => entry.id !== targetConversationId)
      setConversations(remaining)
      if (targetConversationId === conversationId) {
        seededConversationIdRef.current = null
        suppressedBootstrapConversationIdRef.current = targetConversationId
        const nextConversationId = remaining[0]?.id ?? createConversationId()
        navigate(`/agent/${nextConversationId}`)
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : t("community.agent.error")
      setAgentError(message)
    } finally {
      setDeletingConversationId(null)
    }
  }

  const lastAssistantTurn = [...(currentConversation?.turns ?? [])]
    .reverse()
    .find((turn) => turn.role === "assistant" && turn.run)

  if (authLoading) {
    return (
      <div className="min-h-[60vh] bg-[var(--shell-bg)] px-3 py-8 text-[var(--shell-text)] sm:px-4 lg:px-6">
        <Card className="mx-auto max-w-[960px] rounded-[28px] border border-[color:var(--shell-border)] bg-[var(--shell-surface)] p-8">
          <div className="flex items-center gap-3 text-sm text-[var(--shell-text-soft)]">
            <Loader2 className="h-4 w-4 animate-spin text-[var(--shell-accent)]" />
            <span>{t("common.status.loading")}</span>
          </div>
        </Card>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-[60vh] bg-[var(--shell-bg)] px-3 py-8 text-[var(--shell-text)] sm:px-4 lg:px-6">
        <div className="mx-auto max-w-[980px]">
          <LoginPrompt
            messageKey="auth.loginRequiredForThisFeature"
            descriptionKey="community.conversation.loginRequiredDescription"
            className="min-h-[360px] rounded-[32px] border-[color:var(--shell-border)] bg-[var(--shell-surface)]"
          />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-full bg-[var(--shell-bg)] px-3 py-4 text-[var(--shell-text)] sm:px-4 lg:px-6">
      <div className="mx-auto grid w-full max-w-[1920px] gap-4 xl:grid-cols-[248px_minmax(0,1fr)]">
        <aside className="flex min-h-[calc(100vh-6.8rem)] flex-col overflow-hidden rounded-[30px] border border-[color:var(--shell-border)] bg-[color:color-mix(in_srgb,var(--shell-surface)_95%,transparent)] shadow-[0_18px_48px_rgba(15,23,42,0.045)]">
          <div className="border-b border-[color:var(--shell-border)] px-4 py-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[var(--shell-pill)]">
                <Bot className="h-5 w-5 text-[var(--shell-icon)]" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-[var(--shell-heading)]">{t("community.conversation.savedTitle")}</p>
                <p className="truncate text-xs text-[var(--shell-text-muted)]">
                  {user?.email ?? ""}
                </p>
              </div>
            </div>

            <Button
              type="button"
              onClick={handleNewChat}
              className="mt-4 h-11 w-full justify-start rounded-2xl bg-[var(--shell-accent)] px-4 text-[var(--shell-accent-foreground)] hover:bg-[var(--shell-accent-hover)]"
            >
              <MessageSquarePlus className="h-4 w-4" />
              {t("community.agent.newChat")}
            </Button>
          </div>

          <div className="flex-1 space-y-2 overflow-y-auto px-3 py-3">
            {conversationsLoading ? (
              <div className="rounded-[22px] border border-[color:var(--shell-border)] bg-[var(--shell-surface)] px-3 py-4 text-sm text-[var(--shell-text-soft)]">
                {t("common.status.loading")}
              </div>
            ) : null}

            {!conversationsLoading && !conversations.length ? (
              <div className="rounded-[22px] border border-dashed border-[color:var(--shell-border)] bg-[var(--shell-surface)] px-3 py-4 text-sm text-[var(--shell-text-soft)]">
                {t("community.conversation.savedEmpty")}
              </div>
            ) : null}

            {conversations.map((conversation) => (
              <div
                key={conversation.id}
                className={cn(
                  "flex items-start gap-2 rounded-[22px] border px-3 py-3 transition duration-200",
                  conversation.id === conversationId
                    ? "border-[color:var(--shell-border-strong)] bg-[var(--shell-surface)] shadow-[0_16px_40px_rgba(15,23,42,0.06)]"
                    : "border-transparent bg-transparent hover:border-[color:var(--shell-border)] hover:bg-[var(--shell-surface)]",
                )}
              >
                <button
                  type="button"
                  onClick={() => navigate(`/agent/${conversation.id}`)}
                  className="min-w-0 flex-1 text-left"
                >
                  <p className="line-clamp-2 text-sm font-semibold text-[var(--shell-heading)]">
                    {conversation.title || t("community.agent.newChat")}
                  </p>
                  <p className="mt-1 text-xs text-[var(--shell-text-muted)]">
                    {new Date(conversation.updated_at).toLocaleString()}
                  </p>
                </button>

                <button
                  type="button"
                  aria-label={t("community.conversation.deleteConversationAria", { title: conversation.title })}
                  disabled={deletingConversationId === conversation.id}
                  onClick={() => void handleDeleteConversation(conversation.id)}
                  className="rounded-full p-2 text-[var(--shell-text-muted)] transition hover:bg-[var(--shell-pill)] hover:text-[var(--shell-heading)] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </aside>

        <section className="relative flex-col flex overflow-hidden rounded-[32px] border border-outline-variant/20 bg-surface shadow-sm max-h-[calc(100vh-6.8rem)]">
          <header className="flex-none flex items-center justify-between px-6 py-4 bg-surface/80 backdrop-blur-xl z-20 border-b border-outline-variant/10">
            <div className="flex items-center gap-4 min-w-0">
              <div className="flex flex-col min-w-0 pr-4">
                <h1 className="text-on-surface text-lg font-bold leading-tight tracking-[-0.01em] truncate">
                  {currentConversation?.title || t("community.agent.newChat")}
                </h1>
                <p className="text-tertiary text-sm font-medium truncate">
                  {t("community.conversation.title")} · {t("community.conversation.historyBadge")}
                </p>
              </div>
            </div>
            <div className="hidden sm:flex flex-wrap items-center justify-end gap-3 shrink-0">
              <Badge variant="outline" className="rounded-full border-outline-variant/30 bg-surface-container-low px-3 py-1 text-on-surface-variant font-medium shrink-0">
                {lastAssistantTurn?.run ? t(getIntentBadgeKey(lastAssistantTurn.run)) : t("community.agent.intent.answer")}
              </Badge>
              <Badge variant="outline" className="rounded-full border-outline-variant/30 bg-surface-container-low px-3 py-1 text-on-surface-variant font-medium shrink-0">
                {t(getModeBadgeKey(lastAssistantTurn?.run?.mode ?? agentMode))}
              </Badge>
            </div>
          </header>

          <div ref={messageListRef} className="flex-1 overflow-y-auto px-4 md:px-8 lg:px-24 py-6 pb-48">
            <div className="mx-auto flex w-full max-w-4xl flex-col gap-8">
              {!currentConversation?.turns.length ? (
                <Card className="rounded-[28px] border border-dashed border-[color:var(--shell-border)] bg-[var(--shell-surface)] p-8">
                  <p className="text-base leading-8 text-[var(--shell-text-soft)]">{t("community.conversation.emptyState")}</p>
                </Card>
              ) : null}

              {currentConversation?.turns.map((turn) => {
                const assistantRun = turn.role === "assistant" ? turn.run : null
                const primaryCitation = assistantRun?.citations?.[0] ?? null
                const secondaryCitations = assistantRun?.citations?.slice(1) ?? []
                const deepResearchReport = assistantRun?.mode === "deep_research" ? assistantRun.report : null
                const renderedContent = deepResearchReport?.body_markdown ?? turn.content

                return (
                  <div key={turn.id} className={cn("flex items-end gap-4 w-full", turn.role === "user" ? "justify-end" : "justify-start")}>
                    {turn.role === "assistant" && (
                      <div className="size-10 rounded-full bg-surface-container-highest items-center justify-center shrink-0 shadow-sm border border-outline-variant/20 mt-6 hidden sm:flex">
                        <Bot className="w-5 h-5 text-primary" />
                      </div>
                    )}
                    <div
                      className={cn(
                        "flex flex-col gap-1.5 w-full",
                        turn.role === "user" ? "max-w-[85%] md:max-w-[70%] items-end" : "max-w-[85%] md:max-w-[70%]"
                      )}
                    >
                      <div className={cn("flex items-center gap-2", turn.role === "user" ? "pr-2" : "pl-2")}>
                        {turn.role === "user" ? (
                          <>
                            <span className="text-tertiary text-xs">{formatConversationTimestamp(turn.created_at)}</span>
                            <span className="text-on-surface font-semibold text-sm">{t("community.conversation.userLabel", "You")}</span>
                          </>
                        ) : (
                          <>
                            <span className="text-on-surface font-semibold text-sm">{t("community.conversation.agentLabel", "Paper Agent")}</span>
                            <span className="text-tertiary text-xs">{formatConversationTimestamp(turn.created_at)}</span>
                          </>
                        )}
                      </div>

                      {turn.role === "assistant" && primaryCitation ? (
                        <div className="mt-4 space-y-3" data-testid="community-conversation-primary-paper">
                          <button
                            type="button"
                            onClick={() => void handleCitationOpen(primaryCitation)}
                            className="w-full rounded-[28px] border border-[color:var(--shell-border)] bg-[linear-gradient(135deg,rgba(255,255,255,0.99),rgba(244,247,255,0.96))] p-6 text-left transition duration-200 hover:border-[color:var(--shell-border-strong)] hover:shadow-[0_18px_46px_rgba(15,23,42,0.08)]"
                          >
                            <div className="flex flex-wrap items-start justify-between gap-4">
                              <div className="max-w-3xl space-y-3.5">
                                <div className="flex flex-wrap items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-slate-500">
                                  <Badge
                                    variant="outline"
                                    className="rounded-full border-[color:var(--shell-border)] bg-[var(--shell-surface)] px-2.5 py-1 text-[10px] uppercase tracking-[0.18em] text-[var(--shell-text-muted)]"
                                  >
                                    {primaryCitation.source}
                                  </Badge>
                                  {primaryCitation.arxiv_id ? <span>{`arXiv:${primaryCitation.arxiv_id}`}</span> : null}
                                  <span>·</span>
                                  <span>{t("community.conversation.openPaperTitle")}</span>
                                </div>
                                <p className="text-[1.45rem] font-semibold tracking-[-0.035em] text-slate-900">
                                  {primaryCitation.title}
                                </p>
                                {primaryCitation.snippet ? (
                                  <p className="line-clamp-4 max-w-3xl text-[15px] leading-7 text-slate-600">
                                    {primaryCitation.snippet}
                                  </p>
                                ) : null}
                              </div>
                              <div className="inline-flex items-center gap-2 rounded-full border border-[color:var(--shell-border-strong)] bg-[var(--shell-heading)] px-4 py-2 text-sm font-medium text-[var(--shell-surface)] shadow-[0_12px_30px_rgba(15,23,42,0.12)]">
                                {t("community.conversation.openPaperAction")}
                                <ArrowUpRight className="h-4 w-4" />
                              </div>
                            </div>
                          </button>

                          {secondaryCitations.length ? (
                            <div className="grid gap-3 lg:grid-cols-2">
                              {secondaryCitations.map((citation) => (
                                <button
                                  key={citation.id}
                                  type="button"
                                  onClick={() => void handleCitationOpen(citation)}
                                  className="rounded-[22px] border border-[color:var(--shell-border)] bg-[var(--shell-surface-muted)] p-4 text-left transition hover:bg-[var(--shell-surface)]"
                                >
                                  <p className="text-sm font-semibold text-[var(--shell-heading)]">{citation.title}</p>
                                  <p className="mt-2 text-xs uppercase tracking-[0.16em] text-[var(--shell-text-muted)]">
                                    {citation.source}
                                    {citation.arxiv_id ? ` · arXiv:${citation.arxiv_id}` : ""}
                                  </p>
                                  {citation.snippet ? (
                                    <p className="mt-3 line-clamp-3 text-sm leading-6 text-[var(--shell-text-soft)]">
                                      {citation.snippet}
                                    </p>
                                  ) : null}
                                </button>
                              ))}
                            </div>
                          ) : null}
                        </div>
                      ) : null}

                      {deepResearchReport ? (
                        <div
                          data-testid="community-deep-research-report"
                          className="mt-4 rounded-[24px] border border-[color:var(--shell-border)] bg-[var(--shell-surface-muted)] px-5 py-4"
                        >
                          <p className="text-sm font-semibold text-[var(--shell-heading)]">
                            {t("community.conversation.deepResearchReportTitle")}
                          </p>
                          <p className="mt-1 text-sm text-[var(--shell-text-soft)]">
                            {deepResearchReport.coverage_note}
                          </p>
                        </div>
                      ) : null}

                      <div
                        className={cn(
                          "whitespace-pre-wrap text-[15px] leading-relaxed w-full",
                          turn.role === "assistant"
                            ? "bg-surface-container-lowest text-on-surface p-5 rounded-xl rounded-bl-none shadow-[0_4px_20px_rgba(27,28,28,0.03)] border border-outline-variant/15"
                            : "bg-gradient-to-br from-primary to-primary-container text-on-primary p-5 rounded-xl rounded-br-none shadow-[0_8px_24px_rgba(182,23,34,0.15)]"
                        )}
                      >
                        {renderedContent}
                      </div>

                      {assistantRun?.action?.type === "navigate_paper" && assistantRun.action.paper_id ? (
                        <div className="mt-5 space-y-4">
                          <div className="rounded-[24px] border border-[color:var(--shell-border)] bg-[var(--shell-surface)] p-4 shadow-[0_12px_30px_rgba(15,23,42,0.04)]">
                            <div className="flex flex-wrap items-center justify-between gap-3">
                              <div className="space-y-1">
                                <p className="text-sm font-semibold text-[var(--shell-heading)]">
                                  {t("community.conversation.openPaperTitle")}
                                </p>
                                <p className="text-sm text-[var(--shell-text-soft)]">
                                  {assistantRun.action.auto_started_translation
                                    ? t("community.conversation.openPaperDescriptionTranslating")
                                    : t("community.conversation.openPaperDescription")}
                                </p>
                              </div>
                              <Button
                                type="button"
                                onClick={() => navigate(`/paper/${assistantRun.action?.paper_id}`)}
                                className="h-11 rounded-full bg-[var(--shell-accent)] px-4 text-[var(--shell-accent-foreground)] hover:bg-[var(--shell-accent-hover)]"
                              >
                                {t("community.conversation.openPaperAction")}
                                <ArrowUpRight className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>
                        </div>
                      ) : null}
                    </div>
                    {turn.role === "user" && (
                      <div className="size-10 rounded-full bg-surface-container-highest items-center justify-center shrink-0 shadow-sm border border-outline-variant/20 mt-6 hidden sm:flex">
                        <User className="w-5 h-5 text-tertiary" />
                      </div>
                    )}
                  </div>
                )
              })}

              {agentBusy ? (
                <div className="flex items-center gap-3 rounded-[24px] border border-[color:var(--shell-border)] bg-[var(--shell-surface)] px-5 py-4 text-sm text-[var(--shell-text-soft)]">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <div className="space-y-1">
                    <p>{t("community.conversation.running")}</p>
                    <p className="text-xs text-[var(--shell-text-muted)]">
                      {runningProgressSteps[runningStageIndex]}
                    </p>
                  </div>
                </div>
              ) : null}

              {agentError ? (
                <div className="rounded-[24px] border border-rose-500/20 bg-rose-500/5 px-5 py-4 text-sm text-rose-600 dark:text-rose-300">
                  {agentError}
                </div>
              ) : null}
            </div>
          </div>

          <div className="absolute bottom-0 left-0 w-full bg-gradient-to-t from-surface via-surface to-transparent pt-10 pb-6 px-4 md:px-8 z-20 pointer-events-none">
            <div className="max-w-4xl mx-auto flex flex-col gap-3 pointer-events-auto">
              <div className="flex flex-wrap items-center gap-2 self-start sm:ml-4 bg-surface-container-low p-1.5 rounded-full border border-outline-variant/15 shadow-[0_2px_8px_rgba(27,28,28,0.02)]">
                <button
                  type="button"
                  onClick={() => setAgentMode("chat")}
                  className={cn(
                    "relative px-4 py-1.5 rounded-full transition-all duration-200 text-xs font-bold uppercase tracking-wider",
                    agentMode === "chat" ? "bg-surface-container-lowest shadow-sm text-primary" : "text-tertiary hover:text-on-surface"
                  )}
                >
                  <span className="relative z-10 flex items-center gap-1.5">
                    <MessageSquarePlus className="w-4 h-4" /> {t("community.agent.mode.chat")}
                  </span>
                </button>
                <button
                  type="button"
                  onClick={() => setAgentMode("deep_research")}
                  className={cn(
                    "relative px-4 py-1.5 rounded-full transition-all duration-200 text-xs font-bold uppercase tracking-wider",
                    agentMode === "deep_research" ? "bg-surface-container-lowest shadow-sm text-primary" : "text-tertiary hover:text-on-surface"
                  )}
                >
                  <span className="relative z-10 flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4" /> {t("community.agent.mode.deepResearch")}
                  </span>
                </button>
                
                <label className="relative flex items-center gap-2 px-4 py-1.5 rounded-full transition-all duration-200 sm:border-l border-outline-variant/30 sm:ml-1 pl-4 cursor-pointer">
                  <Switch
                    checked={externalSearchEnabled}
                    onCheckedChange={setExternalSearchEnabled}
                    aria-label={t("community.agent.externalSearch.label")}
                    className="data-[state=checked]:bg-primary"
                  />
                  <span className="text-xs font-bold uppercase tracking-wider text-tertiary">{t("community.agent.externalSearch.label")}</span>
                </label>
              </div>

              <form onSubmit={handleSubmit} className="relative flex items-end gap-2 bg-surface-container-lowest rounded-xl p-2 shadow-[0_8px_30px_rgba(27,28,28,0.06)] border border-outline-variant/20 focus-within:border-primary/30 focus-within:ring-1 focus-within:ring-primary/10 transition-all">
                <div className="flex-1 max-h-32 overflow-y-auto min-h-[44px]">
                  <textarea
                    id="conversation-agent-input"
                    aria-label={t("community.agent.aria")}
                    value={input}
                    onChange={(event) => setInput(event.target.value)}
                    placeholder={t("community.agent.placeholder")}
                    rows={1}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        if (!agentBusy && input.trim()) {
                          handleSubmit(e as unknown as FormEvent<HTMLFormElement>);
                        }
                      }
                    }}
                    className="w-full bg-transparent border-none focus:ring-0 resize-none text-on-surface placeholder:text-tertiary text-[15px] py-2.5 px-3 leading-relaxed outline-none"
                    style={{ fieldSizing: "content" } as any}
                  />
                </div>
                <div className="flex items-center gap-1 pr-1 pb-1 shrink-0">
                  <button type="submit" disabled={agentBusy} aria-label="Send message" className="flex items-center justify-center size-10 bg-gradient-to-br from-primary to-primary-container text-on-primary rounded-full shadow-[0_4px_12px_rgba(182,23,34,0.2)] hover:shadow-[0_6px_16px_rgba(182,23,34,0.3)] transition-all focus:outline-none ml-2 disabled:opacity-50 disabled:cursor-not-allowed">
                    {agentBusy ? <Loader2 className="w-5 h-5 animate-spin" /> : <ArrowUpRight className="w-5 h-5 font-bold" />}
                  </button>
                </div>
              </form>
              <div className="text-center">
                <p className="text-[10px] text-tertiary uppercase tracking-widest font-semibold">{t("community.agent.markdownSupported", "Supports Markdown")}</p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
