import { Loader2 } from "lucide-react"
import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react"
import { useTranslation } from "react-i18next"
import { useLocation, useNavigate, useParams } from "react-router-dom"

import { LoginPrompt } from "@/features/auth-shell/components/LoginPrompt"
import { useAuth } from "@/contexts/AuthContext"
import { PanelShell } from "@/ui/panel-shell/PanelShell"
import { Pill } from "@/ui/pill/Pill"
import type {
  CommunityAgentCitation,
  CommunityAgentMode,
  CommunityAgentSkillToggles,
  CommunityConversationRecord,
  CommunityConversationTurn,
} from "@/types/community"

import { ConversationComposer } from "./ConversationComposer"
import { ConversationRail } from "./ConversationRail"
import { ConversationThread } from "./ConversationThread"
import {
  deleteCommunityAgentConversation,
  importCommunityPaper,
  listCommunityAgentConversations,
  streamCommunityAgentRun,
  upsertCommunityAgentConversation,
} from "../services/community-conversation-api"
import {
  buildConversationHistory,
  createSeedConversationRecord,
  deriveConversationTitle,
} from "../utils/conversation-records"
import {
  applyStreamEventToRun,
  buildRunningProgressSteps,
  createAssistantTurnFromRun,
  createConversationId,
  createRunningAssistantTurn,
  createUserTurn,
  getConversationScopedPaperId,
  getIntentBadgeLabel,
  getModeBadgeLabel,
} from "../utils/conversation-runtime"

interface LocationState {
  seedInput?: string
  seedSkillToggles?: CommunityAgentSkillToggles
}

export function CommunityConversationWorkspace() {
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
  }, [
    authLoading,
    conversationId,
    conversations,
    conversationsHydrated,
    conversationsLoading,
    isAuthenticated,
    locationState?.seedInput,
    t,
  ])

  const currentConversation = useMemo(
    () => conversations.find((entry) => entry.id === conversationId) ?? null,
    [conversationId, conversations],
  )

  const mergeConversationRecord = useCallback((record: CommunityConversationRecord) => {
    setConversations((current) =>
      [record, ...current.filter((entry) => entry.id !== record.id)].sort((left, right) =>
        right.updated_at.localeCompare(left.updated_at),
      ),
    )
  }, [])

  const updateConversationTurn = useCallback((
    targetConversationId: string,
    targetTurnId: string,
    updater: (turn: CommunityConversationTurn) => CommunityConversationTurn,
  ) => {
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
  }, [])

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

  const runConversationTurn = useCallback(async (
    record: CommunityConversationRecord,
    latestUserInput: string,
    skillTogglesOverride?: CommunityAgentSkillToggles,
    modeOverride?: CommunityAgentMode,
  ) => {
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
              error: nextRun.status === "failed"
                ? (nextRun.message ?? nextRun.summary ?? t("community.agent.error"))
                : null,
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
  }, [agentMode, externalSearchEnabled, mergeConversationRecord, t, updateConversationTurn])

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
  }, [
    agentBusy,
    agentMode,
    currentConversation,
    externalSearchEnabled,
    isAuthenticated,
    locationState?.seedSkillToggles,
    runConversationTurn,
  ])

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
      <div className="min-h-[60vh] bg-[color:var(--px-shell-bg)] px-3 py-8 text-[color:var(--px-shell-ink)] sm:px-4 lg:px-6">
        <PanelShell className="mx-auto max-w-[960px] px-8 py-8">
          <div className="flex items-center gap-3 text-sm text-[color:color-mix(in_srgb,var(--px-shell-muted)_86%,black_14%)]">
            <Loader2 className="h-4 w-4 animate-spin text-[color:var(--px-shell-accent)]" />
            <span>{t("common.status.loading")}</span>
          </div>
        </PanelShell>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-[60vh] bg-[color:var(--px-shell-bg)] px-3 py-8 text-[color:var(--px-shell-ink)] sm:px-4 lg:px-6">
        <div className="mx-auto max-w-[980px]">
          <LoginPrompt
            messageKey="auth.loginRequiredForThisFeature"
            descriptionKey="community.conversation.loginRequiredDescription"
            className="min-h-[360px] rounded-[32px] border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)]"
          />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-full bg-[color:var(--px-shell-bg)] px-3 py-4 text-[color:var(--px-shell-ink)] sm:px-4 lg:px-6">
      <div className="mx-auto grid w-full max-w-[1920px] gap-4 xl:grid-cols-[248px_minmax(0,1fr)]">
        <ConversationRail
          userEmail={user?.email ?? undefined}
          conversations={conversations}
          activeConversationId={conversationId}
          conversationsLoading={conversationsLoading}
          deletingConversationId={deletingConversationId}
          onNewChat={handleNewChat}
          onOpenConversation={(targetConversationId) => navigate(`/agent/${targetConversationId}`)}
          onDeleteConversation={(targetConversationId) => {
            void handleDeleteConversation(targetConversationId)
          }}
        />

        <PanelShell
          as="section"
          tone="panel"
          padding="none"
          className="relative flex max-h-[calc(100vh-6.8rem)] flex-col overflow-hidden rounded-[32px] bg-[color:var(--px-shell-surface)]"
        >
          <header className="z-20 flex flex-none items-center justify-between border-b border-[color:var(--px-shell-line)] bg-[color:color-mix(in_srgb,var(--px-shell-panel)_82%,transparent)] px-6 py-4 backdrop-blur-xl">
            <div className="min-w-0 flex items-center gap-4">
              <div className="min-w-0 flex flex-col pr-4">
                <h1 className="truncate text-lg font-bold leading-tight tracking-[-0.01em] text-[color:var(--px-shell-ink)]">
                  {currentConversation?.title || t("community.agent.newChat")}
                </h1>
                <p className="truncate text-sm font-medium text-[color:var(--px-shell-muted)]">
                  {t("community.conversation.title")} <span aria-hidden="true">|</span> {t("community.conversation.historyBadge")}
                </p>
              </div>
            </div>
            <div className="hidden shrink-0 flex-wrap items-center justify-end gap-3 sm:flex">
              <Pill className="text-[11px]">
                {getIntentBadgeLabel(t, lastAssistantTurn?.run)}
              </Pill>
              <Pill tone="accent" className="text-[11px]">
                {getModeBadgeLabel(t, lastAssistantTurn?.run?.mode ?? agentMode)}
              </Pill>
            </div>
          </header>

          <ConversationThread
            messageListRef={messageListRef}
            currentConversation={currentConversation}
            agentBusy={agentBusy}
            agentError={agentError}
            runningProgressSteps={runningProgressSteps}
            runningStageIndex={runningStageIndex}
            onCitationOpen={(citation) => {
              void handleCitationOpen(citation)
            }}
            onOpenPaper={(paperId) => navigate(`/paper/${paperId}`)}
          />

          <ConversationComposer
            input={input}
            agentBusy={agentBusy}
            agentMode={agentMode}
            externalSearchEnabled={externalSearchEnabled}
            onInputChange={setInput}
            onSubmit={handleSubmit}
            onModeChange={setAgentMode}
            onExternalSearchChange={setExternalSearchEnabled}
          />
        </PanelShell>
      </div>
    </div>
  )
}
