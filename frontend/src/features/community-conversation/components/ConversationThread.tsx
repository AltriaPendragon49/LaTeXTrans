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

/** 对话线程组件 Props */
interface ConversationThreadProps {
  /** 消息列表容器的 ref */
  messageListRef: RefObject<HTMLDivElement | null>
  /** 当前活跃的对话记录 */
  currentConversation: CommunityConversationRecord | null
  /** Agent 是否忙碌中 */
  agentBusy: boolean
  /** Agent 错误信息 */
  agentError: string | null
  /** 运行中进度步骤 */
  runningProgressSteps: string[]
  /** 当前进度步骤索引 */
  runningStageIndex: number
  /** 打开引文的回调 */
  onCitationOpen: (citation: CommunityAgentCitation) => void
  /** 打开论文回调 */
  onOpenPaper: (paperId: string) => void
}

/** 格式化对话时间戳为 HH:mm:ss */
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

/**
 * 对话轮次卡片子组件
 * 渲染单条对话轮次，包括用户消息气泡、Agent 回复气泡、
 * 主要引文卡片、次要引文列表和深度研究报告卡片
 */
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
        <div className="mt-6 hidden size-11 shrink-0 items-center justify-center rounded-[18px] border border-[color:var(--px-shell-line)]/70 bg-[linear-gradient(135deg,color-mix(in_srgb,var(--px-shell-accent-soft)_74%,white_26%),white)] shadow-[0_20px_34px_-30px_rgba(0,55,176,0.38)] sm:flex">
          <Bot className="h-5 w-5 text-[color:var(--px-shell-accent)]" />
        </div>
      ) : null}

      <div
        className={cn(
          "flex w-full flex-col gap-1.5",
          turn.role === "user" ? "max-w-[88%] items-end md:max-w-[72%]" : "max-w-[88%] md:max-w-[74%]",
        )}
      >
        <div className={cn("flex items-center gap-2", turn.role === "user" ? "pr-2" : "pl-2")}>
          {turn.role === "user" ? (
            <>
              <span className="text-sm font-semibold text-[color:var(--px-shell-ink)]">
                {t("community.conversation.userLabel", "You")}
              </span>
              <span className="text-xs uppercase tracking-[0.16em] text-[color:var(--px-shell-muted)]">
                {formatConversationTimestamp(turn.created_at)}
              </span>
            </>
          ) : (
            <>
              <span className="text-sm font-semibold text-[color:var(--px-shell-ink)]">
                {t("community.conversation.agentLabel", "Paper Agent")}
              </span>
              <span className="text-xs uppercase tracking-[0.16em] text-[color:var(--px-shell-muted)]">
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
            className="mt-4 rounded-[24px] border border-[color:var(--px-shell-line)]/70 bg-[linear-gradient(180deg,color-mix(in_srgb,var(--px-shell-surface)_92%,white_8%),color-mix(in_srgb,var(--px-shell-panel)_96%,white_4%))] px-5 py-4 shadow-none"
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
          <Card className="mt-5 rounded-[24px] border border-[color:var(--px-shell-line)]/70 bg-[linear-gradient(180deg,color-mix(in_srgb,var(--px-shell-panel)_90%,white_10%),color-mix(in_srgb,var(--px-shell-panel-strong)_92%,white_8%))] p-4 shadow-[0_18px_34px_-32px_rgba(15,23,42,0.32)]">
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
        <div className="mt-6 hidden size-11 shrink-0 items-center justify-center rounded-[18px] border border-[color:var(--px-shell-accent)]/18 bg-[linear-gradient(135deg,color-mix(in_srgb,var(--px-shell-accent-soft)_38%,white_62%),white)] shadow-[0_20px_34px_-30px_rgba(15,23,42,0.25)] sm:flex">
          <User className="h-5 w-5 text-[color:var(--px-shell-muted)]" />
        </div>
      ) : null}
    </div>
  )
}

/**
 * 对话线程组件
 * 渲染对话消息列表，包含所有用户和 Agent 的对话轮次、
 * 运行中进度指示器、错误提示和空状态
 */
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
    <div
      ref={messageListRef}
      className="flex-1 overflow-y-auto bg-[radial-gradient(circle_at_top,rgba(0,55,176,0.08),transparent_34%)] px-4 py-6 pb-52 md:px-8 lg:px-24"
    >
      <div className="mx-auto flex w-full max-w-[56rem] flex-col gap-9">
        {!currentConversation?.turns.length ? (
          <StatePanel
            className="rounded-[30px] border-dashed border-[color:var(--px-shell-line)]/80 bg-[linear-gradient(180deg,color-mix(in_srgb,var(--px-shell-panel)_90%,white_10%),color-mix(in_srgb,var(--px-shell-panel-strong)_92%,white_8%))] py-10 shadow-none"
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
            className="rounded-[24px] border border-[color:var(--px-shell-line)]/70 bg-[linear-gradient(180deg,color-mix(in_srgb,var(--px-shell-panel)_90%,white_10%),color-mix(in_srgb,var(--px-shell-panel-strong)_94%,white_6%))]"
          />
        ) : null}

        {agentError ? (
          <NoticeBanner
            tone="danger"
            title={t("community.detail.errorTitle")}
            description={agentError}
            className="rounded-[24px] border border-red-200/70"
          />
        ) : null}
      </div>
    </div>
  )
}
