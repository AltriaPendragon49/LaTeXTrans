import { ArrowUpRight, Loader2, MessageSquarePlus, Sparkles } from "lucide-react"
import type { CSSProperties, FormEvent } from "react"
import { useTranslation } from "react-i18next"

import { Button } from "@/ui/button/Button"
import { ComposerShell } from "@/ui/composer-shell/ComposerShell"
import { Textarea } from "@/ui/input/Textarea"
import { SegmentedControl } from "@/ui/segmented-control/SegmentedControl"
import { ToggleSwitch } from "@/ui/toggle-switch/ToggleSwitch"
import type { CommunityAgentMode } from "@/types/community"

/** 对话输入框组件 Props */
interface ConversationComposerProps {
  /** 当前输入文本 */
  input: string
  /** Agent 是否忙碌中 */
  agentBusy: boolean
  /** Agent 模式（chat / deep_research） */
  agentMode: CommunityAgentMode
  /** 是否启用外部搜索 */
  externalSearchEnabled: boolean
  onInputChange: (value: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  onModeChange: (mode: CommunityAgentMode) => void
  onExternalSearchChange: (enabled: boolean) => void
}

/**
 * 对话输入框组件
 * 提供文本输入区域、Agent 模式切换（chat / deep_research）、
 * 外部搜索开关和发送按钮。支持 Enter 快捷发送
 */
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
    <div className="absolute bottom-0 left-0 w-full bg-gradient-to-t from-[color:var(--px-shell-surface)] via-[color:color-mix(in_srgb,var(--px-shell-surface)_94%,white_6%)] to-transparent px-4 pb-6 pt-12 md:px-8">
      <div className="mx-auto flex max-w-4xl flex-col gap-3">
        <div className="rounded-[30px] border border-[color:color-mix(in_srgb,var(--px-shell-line)_74%,white_26%)] bg-[linear-gradient(180deg,color-mix(in_srgb,var(--px-shell-panel)_92%,white_8%),color-mix(in_srgb,var(--px-shell-surface)_96%,white_4%))] p-2 shadow-[0_30px_70px_-48px_rgba(15,23,42,0.52)] backdrop-blur-xl">
          <ComposerShell
            onSubmit={onSubmit}
            className="rounded-[24px] border border-transparent bg-transparent shadow-none"
            toolbar={(
              <div className="flex flex-wrap items-center gap-3">
                <SegmentedControl
                  value={agentMode}
                  onValueChange={onModeChange}
                  className="bg-[color:color-mix(in_srgb,var(--px-shell-panel)_88%,white_12%)]"
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

                <label className="flex items-center gap-2 rounded-full border border-[color:var(--px-shell-line)] bg-[color:color-mix(in_srgb,var(--px-shell-panel)_88%,white_12%)] px-4 py-2 shadow-sm">
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
                className="h-11 w-11 rounded-full bg-[linear-gradient(135deg,var(--px-shell-accent),var(--px-shell-accent-strong))] text-white shadow-[0_18px_36px_-22px_rgba(0,55,176,0.56)] hover:brightness-110"
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
    </div>
  )
}
