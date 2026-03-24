import { ArrowUpRight, Bot, Loader2, MessageSquarePlus, Sparkles, Trash2 } from "lucide-react"
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
  createCommunityAgentRun,
  deleteCommunityAgentConversation,
  importCommunityPaper,
  listCommunityAgentConversations,
  upsertCommunityAgentConversation,
} from "@/lib/community-api"
import { cn } from "@/lib/utils"
import type {
  CommunityAgentCitation,
  CommunityAgentRun,
  CommunityAgentSkillToggles,
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

function createAssistantTurn(run: CommunityAgentRun): CommunityConversationTurn {
  const assistantMessage = run.message ?? run.summary ?? ""
  return {
    id: `assistant-${Date.now()}`,
    role: "assistant",
    content: assistantMessage,
    created_at: new Date().toISOString(),
    run,
    status: run.status === "failed" ? "failed" : "completed",
    error: run.status === "failed" ? assistantMessage || null : null,
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

function getTraceStatusClass(status: string) {
  switch (status) {
    case "completed":
      return "border-emerald-500/20 bg-emerald-500/10 text-emerald-100"
    case "fallback":
      return "border-amber-500/20 bg-amber-500/10 text-amber-100"
    case "failed":
      return "border-rose-500/20 bg-rose-500/10 text-rose-100"
    default:
      return "border-[color:var(--shell-border)] bg-[var(--shell-pill)] text-[var(--shell-text-soft)]"
  }
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
) {
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
    () => buildRunningProgressSteps(t, externalSearchEnabled),
    [externalSearchEnabled, t],
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
  ) {
    setAgentBusy(true)
    setAgentError(null)

    const historySource =
      record.turns.at(-1)?.role === "user" ? record.turns.slice(0, -1) : record.turns

    try {
      const run = await createCommunityAgentRun({
        input: latestUserInput,
        skill_toggles: skillTogglesOverride ?? {
          external_search: externalSearchEnabled,
        },
        context: {
          source: "conversation",
          history: buildConversationHistory(historySource),
          conversation_id: record.id,
        },
      })

      const updatedRecord: CommunityConversationRecord = {
        ...record,
        title: record.title || deriveConversationTitle(latestUserInput),
        updated_at: new Date().toISOString(),
        turns: [...record.turns, createAssistantTurn(run)],
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
    )
  }, [agentBusy, currentConversation, externalSearchEnabled, isAuthenticated, locationState?.seedSkillToggles])

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
    await runConversationTurn(updatedRecord, normalized)
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

        <section className="overflow-hidden rounded-[32px] border border-[color:var(--shell-border)] bg-[linear-gradient(180deg,color-mix(in_srgb,var(--shell-surface)_98%,white_2%),color-mix(in_srgb,var(--shell-surface)_94%,transparent))] shadow-[var(--shell-panel-shadow)]">
          <div className="border-b border-[color:var(--shell-border)] px-4 py-4 sm:px-6">
            <div className="mx-auto flex w-full max-w-[1180px] items-start justify-between gap-4">
              <div className="space-y-3">
                <div className="inline-flex items-center gap-2 rounded-full border border-[color:var(--shell-border)] bg-[var(--shell-pill)] px-3 py-1.5 text-xs uppercase tracking-[0.18em] text-[var(--shell-text-muted)]">
                  <Sparkles className="h-3.5 w-3.5 text-[var(--shell-icon)]" />
                  {t("community.conversation.title")}
                </div>
                <div>
                  <h1 className="text-balance text-[2rem] font-semibold tracking-[-0.04em] text-[var(--shell-heading)] sm:text-[2.4rem]">
                    {currentConversation?.title || t("community.agent.newChat")}
                  </h1>
                  <p className="mt-2 max-w-3xl text-sm leading-7 text-[var(--shell-text-soft)]">
                    {t("community.conversation.subtitle")}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Badge variant="outline" className="rounded-full border-[color:var(--shell-border)] bg-[var(--shell-pill)] px-3 py-1">
                  {lastAssistantTurn?.run ? t(getIntentBadgeKey(lastAssistantTurn.run)) : t("community.agent.intent.answer")}
                </Badge>
                <Badge variant="outline" className="rounded-full border-[color:var(--shell-border)] bg-[var(--shell-pill)] px-3 py-1">
                  {t("community.conversation.historyBadge")}
                </Badge>
              </div>
            </div>
          </div>

          <div ref={messageListRef} className="flex-1 overflow-y-auto px-4 py-5 sm:px-6">
            <div className="mx-auto flex w-full max-w-[1180px] flex-col gap-5">
              {agentBusy ? (
                <div
                  data-testid="community-conversation-progress"
                  className="sticky top-0 z-10 rounded-[28px] border border-[color:var(--shell-border-strong)] bg-[color:color-mix(in_srgb,var(--shell-surface)_94%,white_6%)] px-5 py-4 shadow-[0_18px_48px_rgba(15,23,42,0.08)] backdrop-blur"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 text-sm font-semibold text-[var(--shell-heading)]">
                        <Loader2 className="h-4 w-4 animate-spin text-[var(--shell-accent)]" />
                        <span>{t("community.conversation.progressTitle")}</span>
                      </div>
                      <p className="text-sm text-[var(--shell-text-soft)]">
                        {t("community.conversation.progressDescription")}
                      </p>
                    </div>
                    <Badge
                      variant="outline"
                      className="rounded-full border-[color:var(--shell-border)] bg-[var(--shell-pill)] px-3 py-1 text-[11px] uppercase tracking-[0.16em] text-[var(--shell-text-soft)]"
                    >
                      {runningProgressSteps[runningStageIndex]}
                    </Badge>
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    {runningProgressSteps.map((step, index) => {
                      const isCompleted = index < runningStageIndex
                      const isActive = index === runningStageIndex
                      return (
                        <Badge
                          key={step}
                          variant="outline"
                          className={cn(
                            "rounded-full border px-3 py-1 text-[11px] tracking-[0.14em]",
                            isActive
                              ? "border-[color:var(--shell-accent)] bg-[color:color-mix(in_srgb,var(--shell-accent)_18%,white_82%)] text-[var(--shell-heading)]"
                              : isCompleted
                                ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-700 dark:text-emerald-200"
                                : "border-[color:var(--shell-border)] bg-[var(--shell-pill)] text-[var(--shell-text-muted)]",
                          )}
                        >
                          {step}
                        </Badge>
                      )
                    })}
                  </div>
                </div>
              ) : null}

              {!currentConversation?.turns.length ? (
                <Card className="rounded-[28px] border border-dashed border-[color:var(--shell-border)] bg-[var(--shell-surface)] p-8">
                  <p className="text-base leading-8 text-[var(--shell-text-soft)]">{t("community.conversation.emptyState")}</p>
                </Card>
              ) : null}

              {currentConversation?.turns.map((turn) => {
                const assistantRun = turn.role === "assistant" ? turn.run : null
                const primaryCitation = assistantRun?.citations?.[0] ?? null
                const secondaryCitations = assistantRun?.citations?.slice(1) ?? []

                return (
                  <div key={turn.id} className={cn("flex", turn.role === "user" ? "justify-end" : "justify-start")}>
                    <div
                      className={cn(
                        "w-full sm:px-0",
                        turn.role === "user"
                          ? "max-w-[760px] rounded-[28px] border border-transparent bg-[var(--shell-accent)] px-5 py-4 text-[var(--shell-accent-foreground)] shadow-sm sm:px-6"
                          : "max-w-[1120px] text-[var(--shell-text)]",
                      )}
                    >
                      <div className={cn("flex items-center justify-between gap-4", turn.role === "assistant" ? "px-1" : "")}>
                        <p className="text-xs uppercase tracking-[0.18em] text-current/70">
                          {turn.role === "user" ? t("community.conversation.userLabel") : t("community.conversation.agentLabel")}
                        </p>
                        <p className="text-xs text-current/60">{formatConversationTimestamp(turn.created_at)}</p>
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

                      <div
                        className={cn(
                          "mt-3 whitespace-pre-wrap rounded-[24px] border px-5 py-4 text-sm leading-7 sm:text-[15px]",
                          turn.role === "assistant"
                            ? "border-[color:var(--shell-border)] bg-[var(--shell-surface)] text-[var(--shell-text-soft)]"
                            : "border-transparent text-[var(--shell-accent-foreground)]",
                        )}
                      >
                        {turn.content}
                      </div>

                      {assistantRun ? (
                        <div className="mt-5 space-y-4">
                          {assistantRun.action?.type === "navigate_paper" && assistantRun.action.paper_id ? (
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
                          ) : null}

                          {assistantRun.tool_trace?.length ? (
                            <div className="flex flex-wrap gap-2">
                              {assistantRun.tool_trace.map((trace) => (
                                <Badge
                                  key={trace.id}
                                  variant="outline"
                                  className={cn(
                                    "rounded-full border px-3 py-1 text-[11px] uppercase tracking-[0.16em]",
                                    getTraceStatusClass(trace.status),
                                  )}
                                >
                                  {trace.label}
                                </Badge>
                              ))}
                            </div>
                          ) : null}
                        </div>
                      ) : null}
                    </div>
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

          <div className="border-t border-[color:var(--shell-border)] px-4 py-4 sm:px-6">
            <form onSubmit={handleSubmit} className="mx-auto flex w-full max-w-[1180px] flex-col gap-3">
              <label htmlFor="conversation-agent-input" className="sr-only">
                {t("community.agent.aria")}
              </label>
              <div className="rounded-[28px] border border-[color:var(--shell-border)] bg-[var(--shell-surface)] p-3 shadow-[0_18px_60px_rgba(15,23,42,0.06)]">
                <textarea
                  id="conversation-agent-input"
                  aria-label={t("community.agent.aria")}
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  placeholder={t("community.agent.placeholder")}
                  rows={3}
                  className="min-h-[104px] w-full resize-none border-0 bg-transparent px-2 py-1 text-base leading-7 text-[var(--shell-heading)] outline-none placeholder:text-[var(--shell-text-muted)]"
                />
                <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-[color:var(--shell-border)] pt-3">
                  <div className="flex flex-col gap-3">
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="outline" className="rounded-full border-[color:var(--shell-border)] bg-[var(--shell-pill)] px-3 py-1">
                        {t("community.agent.intent.search")}
                      </Badge>
                      <Badge variant="outline" className="rounded-full border-[color:var(--shell-border)] bg-[var(--shell-pill)] px-3 py-1">
                        {t("community.agent.intent.answer")}
                      </Badge>
                      <Badge variant="outline" className="rounded-full border-[color:var(--shell-border)] bg-[var(--shell-pill)] px-3 py-1">
                        {t("community.agent.intent.translate")}
                      </Badge>
                    </div>
                    <label className="inline-flex items-center gap-3 text-sm text-[var(--shell-text-soft)]">
                      <Switch
                        checked={externalSearchEnabled}
                        onCheckedChange={setExternalSearchEnabled}
                        aria-label={t("community.agent.externalSearch.label")}
                      />
                      <span>{t("community.agent.externalSearch.label")}</span>
                    </label>
                  </div>

                  <Button
                    type="submit"
                    disabled={agentBusy}
                    className="h-11 rounded-full bg-[var(--shell-accent)] px-5 text-[var(--shell-accent-foreground)] hover:bg-[var(--shell-accent-hover)]"
                  >
                    {t("community.agent.run")}
                    <ArrowUpRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </form>
          </div>
        </section>
      </div>
    </div>
  )
}
