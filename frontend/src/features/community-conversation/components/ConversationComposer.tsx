import { ArrowUpRight, Loader2, MessageSquarePlus, Sparkles } from "lucide-react"
import type { CSSProperties, FormEvent } from "react"
import { useTranslation } from "react-i18next"

import { Button } from "@/ui/button/Button"
import { ComposerShell } from "@/ui/composer-shell/ComposerShell"
import { Textarea } from "@/ui/input/Textarea"
import { SegmentedControl } from "@/ui/segmented-control/SegmentedControl"
import { ToggleSwitch } from "@/ui/toggle-switch/ToggleSwitch"
import type { CommunityAgentMode } from "@/types/community"

interface ConversationComposerProps {
  input: string
  agentBusy: boolean
  agentMode: CommunityAgentMode
  externalSearchEnabled: boolean
  onInputChange: (value: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  onModeChange: (mode: CommunityAgentMode) => void
  onExternalSearchChange: (enabled: boolean) => void
}

export function ConversationComposer({
  input,
  agentBusy,
  agentMode,
  externalSearchEnabled,
  onInputChange,
  onSubmit,
  onModeChange,
  onExternalSearchChange,
}: ConversationComposerProps) {
  const { t } = useTranslation()

  return (
    <div className="absolute bottom-0 left-0 w-full bg-gradient-to-t from-[color:var(--px-shell-surface)] via-[color:var(--px-shell-surface)] to-transparent px-4 pb-6 pt-10 md:px-8">
      <div className="mx-auto flex max-w-4xl flex-col gap-3">
        <ComposerShell
          onSubmit={onSubmit}
          toolbar={(
            <div className="flex flex-wrap items-center gap-3">
              <SegmentedControl
                value={agentMode}
                onValueChange={onModeChange}
                className="bg-[color:var(--px-shell-panel)]"
                items={[
                  {
                    value: "chat",
                    label: t("community.agent.mode.chat"),
                    icon: <MessageSquarePlus className="h-4 w-4" />,
                  },
                  {
                    value: "deep_research",
                    label: t("community.agent.mode.deepResearch"),
                    icon: <Sparkles className="h-4 w-4" />,
                  },
                ]}
              />

              <label className="flex items-center gap-2 rounded-full border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] px-4 py-2 shadow-sm">
                <ToggleSwitch
                  checked={externalSearchEnabled}
                  onCheckedChange={onExternalSearchChange}
                  aria-label={t("community.agent.externalSearch.label")}
                />
                <span className="text-xs font-bold uppercase tracking-[0.16em] text-[color:var(--px-shell-muted)]">
                  {t("community.agent.externalSearch.label")}
                </span>
              </label>
            </div>
          )}
          actionSlot={(
            <Button
              type="submit"
              size="icon"
              disabled={agentBusy}
              aria-label={t("community.agent.send")}
              className="h-10 w-10 bg-[color:var(--px-shell-accent)] text-white hover:bg-[color:var(--px-shell-accent-strong)]"
            >
              {agentBusy ? <Loader2 className="h-5 w-5 animate-spin" /> : <ArrowUpRight className="h-5 w-5" />}
            </Button>
          )}
          footer={(
            <div className="text-center">
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[color:var(--px-shell-muted)]">
                {t("community.agent.markdownSupported", "Supports Markdown")}
              </p>
            </div>
          )}
        >
          <div className="min-h-[44px] max-h-32 overflow-y-auto">
            <Textarea
              id="conversation-agent-input"
              aria-label={t("community.agent.aria")}
              value={input}
              onChange={(event) => onInputChange(event.target.value)}
              placeholder={t("community.agent.placeholder")}
              rows={1}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault()
                  if (!agentBusy && input.trim()) {
                    onSubmit(event as unknown as FormEvent<HTMLFormElement>)
                  }
                }
              }}
              className="min-h-[44px] border-0 bg-transparent px-3 py-2.5 text-[15px] leading-relaxed shadow-none focus-visible:ring-0"
              style={{ fieldSizing: "content" } as CSSProperties}
            />
          </div>
        </ComposerShell>
      </div>
    </div>
  )
}
