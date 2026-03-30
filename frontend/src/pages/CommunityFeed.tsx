import { Search, Paperclip, ChevronDown, Sparkles, ArrowUp } from "lucide-react"
import { useState, type FormEvent } from "react"
import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router-dom"

import { PaperCard } from "@/components/community/PaperCard"
import { PaperCardSkeleton } from "@/components/community/PaperCardSkeleton"
import { PaperFeedEmptyState } from "@/components/community/PaperFeedEmptyState"
import { PaperFeedErrorState } from "@/components/community/PaperFeedErrorState"
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
  const [activeTab, setActiveTab] = useState<"latest" | "hot">("latest")
  
  const { items, loading, error, refetch } = useCommunityPapers(activeTab, "")

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const normalized = agentInput.trim()
    if (!normalized) return

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
    <div className="flex-1 w-full bg-surface text-on-surface">
      {/* TOP NAVIGATION / AGENT INPUT AREA */}
      <header className="px-8 md:px-12 pt-8 pb-4 border-b border-outline-variant/10">
        <div className="max-w-5xl mx-auto flex flex-col gap-8">
          <div className="flex items-center justify-between">
            <h1 className="text-3xl font-extrabold tracking-tight text-on-surface">{t("community.feed.launchTitle", "Community Feed")}</h1>

          </div>

          {/* Agent Input (Prominent & Centered) */}
          <div className="max-w-3xl mx-auto w-full">
            <form onSubmit={handleSubmit} className="bg-surface-container-lowest border border-outline-variant/30 rounded-2xl p-4 shadow-xl focus-within:border-primary/50 transition-all">
              <textarea 
                aria-label={t("community.agent.aria")}
                value={agentInput}
                onChange={(e) => setAgentInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    if (agentInput.trim() !== '') handleSubmit(e as unknown as FormEvent<HTMLFormElement>);
                  }
                }}
                className="w-full bg-transparent border-none outline-none focus:ring-0 text-on-surface placeholder:text-tertiary resize-none h-20 text-base" 
                placeholder={t("community.agent.placeholder", "Ask or search anything...")}
              />
              <div className="flex items-center justify-between mt-2 pt-2 border-t border-outline-variant/10">
                <div className="flex gap-2">
                  <button type="button" className="p-2 text-tertiary hover:text-primary transition-colors">
                    <Paperclip className="w-5 h-5" />
                  </button>
                  <button
                    type="button"
                    aria-pressed={externalSearchEnabled}
                    aria-label={t("community.agent.externalSearch.label")}
                    onClick={() => setExternalSearchEnabled((current) => !current)}
                    className={`flex items-center gap-2 px-3 py-1 text-xs font-bold rounded-lg border transition-colors uppercase tracking-wider ${
                      externalSearchEnabled
                        ? "bg-primary text-on-primary border-primary shadow-sm"
                        : "bg-surface-container-high hover:bg-surface-container-highest border-outline-variant/20 text-on-surface"
                    }`}
                  >
                    <Search className="w-4 h-4" /> {t("community.agent.intent.search", "Search")}
                  </button>
                  <button type="button" className="flex items-center gap-2 px-3 py-1 bg-surface-container-high hover:bg-surface-container-highest text-xs font-bold rounded-lg border border-outline-variant/20 transition-colors uppercase tracking-wider text-on-surface">
                    <Sparkles className="w-4 h-4" /> Balanced <ChevronDown className="w-4 h-4" />
                  </button>
                </div>
                
                <div className="flex flex-col sm:flex-row items-center gap-4">
                  <span className="text-[10px] font-bold text-tertiary uppercase tracking-widest hidden sm:block">Enter to search</span>
                  <button type="submit" aria-label={t("community.agent.run")} className="w-9 h-9 bg-primary text-on-primary rounded-lg flex items-center justify-center hover:bg-primary/90 transition-colors shadow-md border-none">
                    <ArrowUp className="w-5 h-5 font-bold" />
                  </button>
                </div>
              </div>
            </form>
          </div>

          {/* Sorting Tabs */}
          <div className="flex gap-8 items-center mt-4">
            <button 
              onClick={() => setActiveTab("hot")}
              className={`pb-3 border-b-2 font-bold text-xs uppercase tracking-[0.2em] transition-colors ${activeTab === 'hot' ? 'border-primary text-primary' : 'border-transparent text-tertiary hover:text-on-surface'}`}
            >
              Hot
            </button>
            <button 
              onClick={() => setActiveTab("latest")}
              className={`pb-3 border-b-2 font-bold text-xs uppercase tracking-[0.2em] transition-colors ${activeTab === 'latest' ? 'border-primary text-primary' : 'border-transparent text-tertiary hover:text-on-surface'}`}
            >
              Latest
            </button>
            <button className="pb-3 border-b-2 border-transparent text-tertiary hover:text-on-surface transition-colors font-bold text-xs uppercase tracking-[0.2em] ml-auto">
              Filters
            </button>
          </div>
        </div>
      </header>

      {/* FEED LIST */}
      <section className="max-w-5xl mx-auto px-8 md:px-12 py-8 relative">
        {error ? <PaperFeedErrorState onRetry={refetch} /> : null}

        {!error && loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="h-48">
                <PaperCardSkeleton />
              </div>
            ))}
            <div className="md:col-span-2 flex justify-center py-8">
              <div className="flex items-center gap-3 text-tertiary">
                <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce"></div>
                <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:-0.15s]"></div>
                <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:-0.3s]"></div>
                <span className="text-[10px] font-black uppercase tracking-[0.3em] ml-2">Exploring more papers</span>
              </div>
            </div>
          </div>
        ) : null}

        {!error && !loading && !items.length ? <PaperFeedEmptyState /> : null}

        {!error && !loading && items.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {items.map((paper) => (
              <PaperCard key={paper.id} paper={paper} />
            ))}
          </div>
        ) : null}
      </section>
    </div>
  )
}
