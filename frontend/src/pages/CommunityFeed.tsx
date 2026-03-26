import { ArrowUpRight, Bot } from "lucide-react"
import { useMemo, useState, type FormEvent } from "react"
import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router-dom"

import { PaperCard } from "@/components/community/PaperCard"
import { PaperCardSkeleton } from "@/components/community/PaperCardSkeleton"
import { PaperFeedEmptyState } from "@/components/community/PaperFeedEmptyState"
import { PaperFeedErrorState } from "@/components/community/PaperFeedErrorState"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { useCommunityPapers } from "@/hooks/use-community-papers"

function createConversationId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID()
  }
  return `conversation-${Date.now()}`
}

export default function CommunityFeedPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [agentInput, setAgentInput] = useState("")
  const [externalSearchEnabled, setExternalSearchEnabled] = useState(false)
  const { items, loading, error, refetch } = useCommunityPapers("latest", "")

  const capabilityChips = useMemo(
    () => [
      t("community.agent.intent.search"),
      t("community.agent.intent.answer"),
      t("community.agent.intent.translate"),
    ],
    [t],
  )

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const normalized = agentInput.trim()
    if (!normalized) {
      return
    }

    navigate(`/agent/${createConversationId()}`, {
      state: {
        seedInput: normalized,
        seedSkillToggles: {
          external_search: externalSearchEnabled,
        },
      },
    })
  }

  return (
    <div className="min-h-full bg-[var(--shell-bg)] px-4 py-4 text-[var(--shell-text)] sm:px-6 lg:px-8">
      <div className="mx-auto flex w-full max-w-[1560px] flex-col gap-6">
        <section className="overflow-hidden rounded-[32px] border border-[color:var(--shell-border)] bg-[linear-gradient(180deg,color-mix(in_srgb,var(--shell-surface)_98%,white_2%),color-mix(in_srgb,var(--shell-surface)_94%,transparent))] shadow-[var(--shell-panel-shadow)]">
          <div className="px-5 py-6 sm:px-6 lg:px-8 lg:py-7">
            <div className="mx-auto max-w-[1120px] space-y-5 text-center">
              <div className="inline-flex items-center gap-2 rounded-full border border-[color:var(--shell-border)] bg-[var(--shell-pill)] px-3.5 py-1.5 text-[11px] font-medium uppercase tracking-[0.22em] text-[var(--shell-text-muted)]">
                <Bot className="h-3.5 w-3.5 text-[var(--shell-icon)]" />
                {t("community.agent.entryLabel")}
              </div>

              <div className="mx-auto max-w-[920px] space-y-3">
                <h1 className="text-balance text-[2.45rem] font-semibold tracking-[-0.05em] text-[var(--shell-heading)] sm:text-[3.55rem]">
                  {t("community.feed.launchTitle")}
                </h1>
                <p className="mx-auto max-w-[760px] text-sm leading-7 text-[var(--shell-text-soft)] sm:text-base">
                  {t("community.feed.launchDescription")}
                </p>
              </div>

              <form
                onSubmit={handleSubmit}
                className="mx-auto max-w-[1060px] space-y-3 rounded-[30px] border border-[color:var(--shell-border)] bg-[color:color-mix(in_srgb,var(--shell-surface)_96%,transparent)] p-4 text-left shadow-[0_18px_56px_rgba(15,23,42,0.08)] sm:p-5"
              >
                <label htmlFor="community-agent-input" className="sr-only">
                  {t("community.agent.aria")}
                </label>
                <textarea
                  id="community-agent-input"
                  aria-label={t("community.agent.aria")}
                  value={agentInput}
                  onChange={(event) => setAgentInput(event.target.value)}
                  placeholder={t("community.agent.placeholder")}
                  rows={3}
                  className="min-h-[104px] w-full resize-none border-0 bg-transparent px-1 text-[1.08rem] leading-8 text-[var(--shell-heading)] outline-none placeholder:text-[var(--shell-text-muted)]"
                />
                <div className="flex flex-col gap-3 border-t border-[color:var(--shell-border)] pt-3.5 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex flex-col gap-3">
                    <div className="flex flex-wrap gap-2">
                      {capabilityChips.map((chip) => (
                        <Badge
                          key={chip}
                          variant="outline"
                          className="rounded-full border-[color:var(--shell-border)] bg-[var(--shell-pill)] px-3 py-1 text-[10px] uppercase tracking-[0.16em] text-[var(--shell-text-soft)]"
                        >
                          {chip}
                        </Badge>
                      ))}
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
                    className="h-11 rounded-full bg-[var(--shell-accent)] px-5 text-[var(--shell-accent-foreground)] hover:bg-[var(--shell-accent-hover)]"
                  >
                    {t("community.agent.run")}
                    <ArrowUpRight className="h-4 w-4" />
                  </Button>
                </div>
              </form>
            </div>
          </div>
        </section>

        <section className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold tracking-[-0.03em] text-[var(--shell-heading)]">
                {t("community.feed.recentTitle")}
              </h2>
              <p className="text-sm text-[var(--shell-text-soft)]">{t("community.feed.recentDescription")}</p>
            </div>
          </div>

          {error ? <PaperFeedErrorState onRetry={refetch} /> : null}

          {!error && loading ? (
            <div data-testid="community-feed-loading" className="grid gap-4 xl:grid-cols-2 2xl:grid-cols-3">
              {Array.from({ length: 3 }).map((_, index) => (
                <PaperCardSkeleton key={index} />
              ))}
            </div>
          ) : null}

          {!error && !loading && !items.length ? <PaperFeedEmptyState /> : null}

          {!error && !loading && items.length ? (
            <div className="grid gap-4 xl:grid-cols-2 2xl:grid-cols-3">
              {items.slice(0, 6).map((paper) => (
                <PaperCard key={paper.id} paper={paper} />
              ))}
            </div>
          ) : null}
        </section>
      </div>
    </div>
  )
}
