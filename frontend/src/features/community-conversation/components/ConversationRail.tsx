import { Bot, Loader2, MessageSquarePlus, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/ui/button/Button"
import { InteractiveCard } from "@/ui/interactive-card/InteractiveCard"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { PanelShell } from "@/ui/panel-shell/PanelShell"
import { Pill } from "@/ui/pill/Pill"
import { cn } from "@/lib/utils"
import type { CommunityConversationRecord } from "@/types/community"

/** 对话侧栏 Props */
interface ConversationRailProps {
  /** 用户邮箱 */
  userEmail?: string
  /** 对话列表 */
  conversations: CommunityConversationRecord[]
  /** 当前活跃对话 ID */
  activeConversationId: string
  /** 是否正在加载对话列表 */
  conversationsLoading: boolean
  /** 正在删除的对话 ID */
  deletingConversationId: string | null
  /** 新建对话回调 */
  onNewChat: () => void
  /** 打开对话回调 */
  onOpenConversation: (conversationId: string) => void
  /** 删除对话回调 */
  onDeleteConversation: (conversationId: string) => void
}

/**
 * 对话侧栏组件
 * 展示已保存的 Agent 对话列表，支持新建对话、切换对话和删除操作。
 * 活跃对话高亮显示
 */
export function ConversationRail({
  userEmail,
  conversations,
  activeConversationId,
  conversationsLoading,
  deletingConversationId,
  onNewChat,
  onOpenConversation,
  onDeleteConversation,
}: ConversationRailProps) {
  const { t } = useTranslation()

  return (
    <PanelShell
      as="aside"
      tone="glass"
      padding="none"
      className="flex min-h-[calc(100vh-6.8rem)] flex-col overflow-hidden rounded-[30px] border border-[color:color-mix(in_srgb,var(--px-shell-line)_78%,white_22%)] bg-[linear-gradient(180deg,color-mix(in_srgb,var(--px-shell-panel)_92%,white_8%),color-mix(in_srgb,var(--px-shell-surface)_94%,white_6%))] shadow-[0_28px_60px_-48px_rgba(15,23,42,0.48)]"
    >
      <div className="border-b border-[color:color-mix(in_srgb,var(--px-shell-line)_76%,white_24%)] px-4 py-4">
        <div className="rounded-[24px] border border-[color:var(--px-shell-line)]/70 bg-[linear-gradient(180deg,color-mix(in_srgb,var(--px-shell-panel-strong)_90%,white_10%),color-mix(in_srgb,var(--px-shell-panel)_96%,white_4%))] px-4 py-4 shadow-[0_24px_40px_-36px_rgba(15,23,42,0.4)]">
          <div className="flex items-start gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-[18px] border border-[color:var(--px-shell-line)]/70 bg-[linear-gradient(135deg,color-mix(in_srgb,var(--px-shell-accent-soft)_78%,white_22%),white)] shadow-sm">
              <Bot className="h-5 w-5 text-[color:var(--px-shell-accent)]" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm font-semibold text-[color:var(--px-shell-ink)]">
                  {t("community.conversation.savedTitle")}
                </p>
                <Pill tone="accent" className="text-[10px] uppercase tracking-[0.18em]">
                  {t("community.conversation.title")}
                </Pill>
              </div>
              <p className="mt-1 truncate text-xs text-[color:var(--px-shell-muted)]">{userEmail ?? ""}</p>
            </div>
          </div>

          <Button
            type="button"
            onClick={onNewChat}
            className="mt-4 h-11 w-full justify-start rounded-[18px] bg-[linear-gradient(135deg,var(--px-shell-accent),var(--px-shell-accent-strong))] px-4 text-white shadow-[0_18px_38px_-26px_rgba(0,55,176,0.58)] hover:brightness-110"
          >
            <MessageSquarePlus className="h-4 w-4" />
            {t("community.agent.newChat")}
          </Button>
        </div>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto px-3 py-3">
        {conversationsLoading ? (
          <NoticeBanner
            tone="info"
            icon={<Loader2 className="h-4 w-4 animate-spin" />}
            description={t("common.status.loading")}
            className="rounded-[22px]"
          />
        ) : null}

        {!conversationsLoading && !conversations.length ? (
          <NoticeBanner
            tone="neutral"
            description={t("community.conversation.savedEmpty")}
            className="rounded-[22px] border-dashed"
          />
        ) : null}

        {conversations.map((conversation) => (
          <InteractiveCard
            key={conversation.id}
            element="div"
            tone={conversation.id === activeConversationId ? "selected" : "ghost"}
            size="sm"
            className={cn(
              "flex items-start gap-2 rounded-[22px] border border-transparent bg-[color:color-mix(in_srgb,var(--px-shell-panel)_82%,transparent)] px-1 shadow-none transition-all duration-200",
              conversation.id === activeConversationId
                ? "border-[color:var(--px-shell-accent)]/20 bg-[linear-gradient(180deg,color-mix(in_srgb,var(--px-shell-accent-soft)_62%,white_38%),color-mix(in_srgb,var(--px-shell-panel)_94%,white_6%))] shadow-[0_18px_34px_-34px_rgba(0,55,176,0.48)]"
                : "hover:border-[color:var(--px-shell-line)]/80 hover:bg-[color:color-mix(in_srgb,var(--px-shell-panel-strong)_74%,white_26%)] hover:shadow-none",
            )}
          >
            <div
              role="button"
              tabIndex={0}
              onClick={() => onOpenConversation(conversation.id)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault()
                  onOpenConversation(conversation.id)
                }
              }}
              className="min-w-0 flex-1 text-left"
            >
              <p className="line-clamp-2 text-sm font-semibold leading-6 text-[color:var(--px-shell-ink)]">
                {conversation.title || t("community.agent.newChat")}
              </p>
              <p className="mt-1 text-xs uppercase tracking-[0.16em] text-[color:var(--px-shell-muted)]">
                {new Date(conversation.updated_at).toLocaleString()}
              </p>
            </div>

            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label={t("community.conversation.deleteConversationAria", { title: conversation.title })}
              disabled={deletingConversationId === conversation.id}
              onClick={() => onDeleteConversation(conversation.id)}
              className="h-9 w-9 rounded-full text-[color:var(--px-shell-muted)] hover:bg-[color:var(--px-shell-accent-soft)] hover:text-[color:var(--px-shell-ink)]"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </InteractiveCard>
        ))}
      </div>
    </PanelShell>
  )
}
