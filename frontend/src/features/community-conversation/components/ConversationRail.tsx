import { Bot, Loader2, MessageSquarePlus, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/ui/button/Button"
import { InteractiveCard } from "@/ui/interactive-card/InteractiveCard"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { PanelShell } from "@/ui/panel-shell/PanelShell"
import { cn } from "@/lib/utils"
import type { CommunityConversationRecord } from "@/types/community"

interface ConversationRailProps {
  userEmail?: string
  conversations: CommunityConversationRecord[]
  activeConversationId: string
  conversationsLoading: boolean
  deletingConversationId: string | null
  onNewChat: () => void
  onOpenConversation: (conversationId: string) => void
  onDeleteConversation: (conversationId: string) => void
}

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
      className="flex min-h-[calc(100vh-6.8rem)] flex-col overflow-hidden"
    >
      <div className="border-b border-[color:var(--px-shell-line)] px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[color:var(--px-shell-accent-soft)]">
            <Bot className="h-5 w-5 text-[color:var(--px-shell-muted)]" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-[color:var(--px-shell-ink)]">
              {t("community.conversation.savedTitle")}
            </p>
            <p className="truncate text-xs text-[color:var(--px-shell-muted)]">{userEmail ?? ""}</p>
          </div>
        </div>

        <Button
          type="button"
          onClick={onNewChat}
          className="mt-4 h-11 w-full justify-start rounded-2xl bg-[color:var(--px-shell-accent)] px-4 text-white hover:bg-[color:var(--px-shell-accent-strong)]"
        >
          <MessageSquarePlus className="h-4 w-4" />
          {t("community.agent.newChat")}
        </Button>
      </div>

      <div className="flex-1 space-y-2 overflow-y-auto px-3 py-3">
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
              "flex items-start gap-2",
              conversation.id === activeConversationId ? "" : "hover:shadow-none",
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
              <p className="line-clamp-2 text-sm font-semibold text-[color:var(--px-shell-ink)]">
                {conversation.title || t("community.agent.newChat")}
              </p>
              <p className="mt-1 text-xs text-[color:var(--px-shell-muted)]">
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
              className="h-9 w-9 text-[color:var(--px-shell-muted)] hover:bg-[color:var(--px-shell-accent-soft)] hover:text-[color:var(--px-shell-ink)]"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </InteractiveCard>
        ))}
      </div>
    </PanelShell>
  )
}
