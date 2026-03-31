import { Search, Sparkles } from "lucide-react"
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
      {/* FEED CANVAS */}
      <div className="max-w-6xl mx-auto px-8 py-8">
        
        {/* Agent Search Section */}
        <section className="mb-10">
          <div className="bg-surface-container-lowest rounded-2xl p-6 border border-outline-variant/20 shadow-sm">
            <form onSubmit={handleSubmit} className="relative">
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
                className="w-full bg-surface-container-low border-none rounded-xl p-5 text-on-surface-variant focus:ring-2 focus:ring-primary/10 min-h-[120px] resize-none text-lg font-light tracking-tight placeholder:text-slate-400" 
                placeholder={t("community.agent.placeholder", "Ask the Digital Curator to find specific research papers...")}
              />
              <div className="absolute bottom-4 right-4 flex gap-3">
                <button 
                  type="button" 
                  onClick={() => setExternalSearchEnabled(v => !v)}
                  className={`px-6 py-2.5 rounded-full font-semibold text-sm transition-all border ${externalSearchEnabled ? "bg-primary text-on-primary border-primary" : "bg-slate-100 text-slate-600 dark:bg-surface-container-highest dark:text-on-surface-variant border-transparent"}`}
                >
                  <Search className="w-4 h-4 inline-block mr-1 mb-0.5" /> Web Search
                </button>
                <button type="submit" aria-label={t("community.agent.run")} className="px-8 py-2.5 bg-primary text-on-primary rounded-full font-semibold text-sm flex items-center gap-2 transition-all hover:opacity-90 shadow-lg shadow-primary/20">
                  <Sparkles className="text-lg w-4 h-4" />
                  {t("community.agent.intent.search", "Search")}
                </button>
              </div>
            </form>
          </div>
        </section>

        {/* Sorting Tabs & Actions */}
        <div className="flex justify-between items-center mb-8 border-b border-outline-variant/10">
          <div className="flex items-center gap-10">
            <button 
              onClick={() => setActiveTab("hot")}
              className={`font-bold pb-4 flex items-center gap-2 transition-colors ${activeTab === 'hot' ? 'text-primary border-b-2 border-primary' : 'text-tertiary hover:text-primary'}`}
            >
              <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>local_fire_department</span>
              Hot
            </button>
            <button 
              onClick={() => setActiveTab("latest")}
              className={`font-bold pb-4 flex items-center gap-2 transition-colors ${activeTab === 'latest' ? 'text-primary border-b-2 border-primary' : 'text-tertiary hover:text-primary'}`}
            >
              <span className="material-symbols-outlined text-sm">schedule</span>
              Latest
            </button>
          </div>
          <div className="flex gap-4 pb-4">
            <button className="flex items-center gap-2 px-4 py-1.5 text-tertiary hover:text-primary transition-colors text-sm font-medium">
              <span className="material-symbols-outlined text-xl">filter_list</span>
              Filter
            </button>
          </div>
        </div>

        {/* PAPER FEED (Single Column) */}
        <div className="flex flex-col gap-6 relative">
          {error ? <PaperFeedErrorState onRetry={refetch} /> : null}

          {!error && loading ? (
            <div className="flex flex-col gap-6">
              {Array.from({ length: 4 }).map((_, index) => (
                <div key={index} className="h-48">
                  <PaperCardSkeleton />
                </div>
              ))}
              <div className="flex justify-center py-8">
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
            <>
              {items.map((paper) => (
                <PaperCard key={paper.id} paper={paper} />
              ))}
            </>
          ) : null}
        </div>
      </div>
    </div>
  )
}
