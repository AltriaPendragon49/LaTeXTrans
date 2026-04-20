import { ArrowUpRight, Bot, Loader2, User } from "lucide-react"
import type { RefObject } from "react"
import { useTranslation } from "react-i18next"

import { Button } from "@/ui/button/Button"
import { Card } from "@/ui/card/Card"
import { ChatBubble } from "@/ui/chat-bubble/ChatBubble"
import { InteractiveCard } from "@/ui/interactive-card/InteractiveCard"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { Pill } from "@/ui/pill/Pill"
import { StatePanel } from "@/ui/state-panel/StatePanel"
import { cn } from "@/lib/utils"
import type {
  CommunityAgentCitation,
  CommunityConversationRecord,
  CommunityConversationTurn,
} from "@/types/community"

interface ConversationThreadProps {
  messageListRef: RefObject<HTMLDivElement | null>
  currentConversation: CommunityConversationRecord | null
  agentBusy: boolean
  agentError: string | null
  runningProgressSteps: string[]
  runningStageIndex: number
  onCitationOpen: (citation: CommunityAgentCitation) => void
  onOpenPaper: (paperId: string) => void
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

function ConversationTurnCard({
  turn,
  onCitationOpen,
  onOpenPaper,
}: {
  turn: CommunityConversationTurn
  onCitationOpen: (citation: CommunityAgentCitation) => void
  onOpenPaper: (paperId: string) => void
}) {
  const { t } = useTranslation()
  const assistantRun = turn.role === "assistant" ? turn.run : null
  const assistantAction = assistantRun?.action ?? null
  const assistantActionPaperId = assistantAction?.paper_id ?? null
  const primaryCitation = assistantRun?.citations?.[0] ?? null
  const secondaryCitations = assistantRun?.citations?.slice(1) ?? []
  const deepResearchReport = assistantRun?.mode === "deep_research" ? assistantRun.report : null
  const renderedContent = deepResearchReport?.body_markdown ?? turn.content

  return (
    <div
      className={cn(
        "flex w-full items-end gap-4",
        turn.role === "user" ? "justify-end" : "justify-start",
      )}
    >
      {turn.role === "assistant" ? (
        <div className="mt-6 hidden size-10 shrink-0 items-center justify-center rounded-full border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] shadow-sm sm:flex">
          <Bot className="h-5 w-5 text-[color:var(--px-shell-accent)]" />
        </div>
      ) : null}

      <div
        className={cn(
          "flex w-full flex-col gap-1.5",
          turn.role === "user" ? "max-w-[85%] items-end md:max-w-[70%]" : "max-w-[85%] md:max-w-[70%]",
        )}
      >
        <div className={cn("flex items-center gap-2", turn.role === "user" ? "pr-2" : "pl-2")}>
          {turn.role === "user" ? (
            <>
              <span className="text-xs text-[color:var(--px-shell-muted)]">
                {formatConversationTimestamp(turn.created_at)}
              </span>
              <span className="text-sm font-semibold text-[color:var(--px-shell-ink)]">
                {t("community.conversation.userLabel", "You")}
              </span>
            </>
          ) : (
            <>
              <span className="text-sm font-semibold text-[color:var(--px-shell-ink)]">
                {t("community.conversation.agentLabel", "Paper Agent")}
              </span>
              <span className="text-xs text-[color:var(--px-shell-muted)]">
                {formatConversationTimestamp(turn.created_at)}
              </span>
            </>
          )}
        </div>

        {turn.role === "assistant" && primaryCitation ? (
          <div className="mt-4 space-y-3" data-testid="community-conversation-primary-paper">
            <InteractiveCard
              onClick={() => onCitationOpen(primaryCitation)}
              tone="strong"
              size="lg"
            >
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="max-w-3xl space-y-3.5">
                  <div className="flex flex-wrap items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-[color:var(--px-shell-muted)]">
                    <Pill>{primaryCitation.source}</Pill>
                    {primaryCitation.arxiv_id ? <span>{`arXiv:${primaryCitation.arxiv_id}`}</span> : null}
                    <span aria-hidden="true">|</span>
                    <span>{t("community.conversation.openPaperTitle")}</span>
                  </div>
                  <p className="text-[1.45rem] font-semibold tracking-[-0.035em] text-[color:var(--px-shell-ink)]">
                    {primaryCitation.title}
                  </p>
                  {primaryCitation.snippet ? (
                    <p className="line-clamp-4 max-w-3xl text-[15px] leading-7 text-[color:color-mix(in_srgb,var(--px-shell-muted)_86%,black_14%)]">
                      {primaryCitation.snippet}
                    </p>
                  ) : null}
                </div>

                <span className="inline-flex min-h-10 items-center gap-2 rounded-full border border-[color:var(--px-shell-ink)] bg-[color:var(--px-shell-ink)] px-4 py-2 text-sm font-semibold text-[color:var(--px-shell-surface)] shadow-[0_12px_30px_rgba(15,23,42,0.12)]">
                  {t("community.conversation.openPaperAction")}
                  <ArrowUpRight className="h-4 w-4" />
                </span>
              </div>
            </InteractiveCard>

            {secondaryCitations.length ? (
              <div className="grid gap-3 lg:grid-cols-2">
                {secondaryCitations.map((citation) => (
                  <InteractiveCard
                    key={citation.id}
                    onClick={() => onCitationOpen(citation)}
                    tone="panel"
                    size="md"
                  >
                    <p className="text-sm font-semibold text-[color:var(--px-shell-ink)]">{citation.title}</p>
                    <p className="mt-2 text-xs uppercase tracking-[0.16em] text-[color:var(--px-shell-muted)]">
                      {citation.source}
                      {citation.arxiv_id ? ` | arXiv:${citation.arxiv_id}` : ""}
                    </p>
                    {citation.snippet ? (
                      <p className="mt-3 line-clamp-3 text-sm leading-6 text-[color:color-mix(in_srgb,var(--px-shell-muted)_86%,black_14%)]">
                        {citation.snippet}
                      </p>
                    ) : null}
                  </InteractiveCard>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        {deepResearchReport ? (
          <Card
            data-testid="community-deep-research-report"
            className="mt-4 rounded-[24px] bg-[color:var(--px-shell-surface)] px-5 py-4 shadow-none"
          >
            <p className="text-sm font-semibold text-[color:var(--px-shell-ink)]">
              {t("community.conversation.deepResearchReportTitle")}
            </p>
            <p className="mt-1 text-sm text-[color:color-mix(in_srgb,var(--px-shell-muted)_86%,black_14%)]">
              {deepResearchReport.coverage_note}
            </p>
          </Card>
        ) : null}

        <ChatBubble speaker={turn.role === "assistant" ? "assistant" : "user"}>
          {renderedContent}
        </ChatBubble>

        {assistantAction?.type === "navigate_paper" && assistantActionPaperId ? (
          <Card className="mt-5 rounded-[24px] bg-[color:var(--px-shell-panel)] p-4 shadow-[0_12px_30px_rgba(15,23,42,0.04)]">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="space-y-1">
                <p className="text-sm font-semibold text-[color:var(--px-shell-ink)]">
                  {t("community.conversation.openPaperTitle")}
                </p>
                <p className="text-sm text-[color:color-mix(in_srgb,var(--px-shell-muted)_86%,black_14%)]">
                  {assistantAction.auto_started_translation
                    ? t("community.conversation.openPaperDescriptionTranslating")
                    : t("community.conversation.openPaperDescription")}
                </p>
              </div>

              <Button
                type="button"
                onClick={() => onOpenPaper(assistantActionPaperId)}
                className="h-11 bg-[color:var(--px-shell-accent)] px-4 text-white hover:bg-[color:var(--px-shell-accent-strong)]"
              >
                {t("community.conversation.openPaperAction")}
                <ArrowUpRight className="h-4 w-4" />
              </Button>
            </div>
          </Card>
        ) : null}
      </div>

      {turn.role === "user" ? (
        <div className="mt-6 hidden size-10 shrink-0 items-center justify-center rounded-full border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] shadow-sm sm:flex">
          <User className="h-5 w-5 text-[color:var(--px-shell-muted)]" />
        </div>
      ) : null}
    </div>
  )
}

export function ConversationThread({
  messageListRef,
  currentConversation,
  agentBusy,
  agentError,
  runningProgressSteps,
  runningStageIndex,
  onCitationOpen,
  onOpenPaper,
}: ConversationThreadProps) {
  const { t } = useTranslation()

  return (
    <div ref={messageListRef} className="flex-1 overflow-y-auto px-4 py-6 pb-48 md:px-8 lg:px-24">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-8">
        {!currentConversation?.turns.length ? (
          <StatePanel
            className="rounded-[28px] border-dashed bg-[color:var(--px-shell-panel)] py-10 shadow-none"
            title={t("community.conversation.emptyState")}
          />
        ) : null}

        {currentConversation?.turns.map((turn) => (
          <ConversationTurnCard
            key={turn.id}
            turn={turn}
            onCitationOpen={onCitationOpen}
            onOpenPaper={onOpenPaper}
          />
        ))}

        {agentBusy ? (
          <NoticeBanner
            icon={<Loader2 className="h-4 w-4 animate-spin" />}
            title={t("community.conversation.running")}
            description={runningProgressSteps[runningStageIndex]}
            className="rounded-[24px]"
          />
        ) : null}

        {agentError ? (
          <NoticeBanner
            tone="danger"
            title={t("community.detail.errorTitle")}
            description={agentError}
            className="rounded-[24px]"
          />
        ) : null}
      </div>
    </div>
  )
}
