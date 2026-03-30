import { useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { ChevronDown, ChevronRight, Download, FileText, Info, Loader2, Play, RefreshCw, X, Zap } from "lucide-react"

import { AdvancedConfig } from "@/components/AdvancedConfig"
import { BatchTranslation, type BatchTranslationHandle, type BatchTranslationState } from "@/components/BatchTranslation"
import { DropZone } from "@/components/DropZone"
import { LoginPrompt } from "@/components/LoginPrompt"
import { Button } from "@/components/ui/button"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useAuth } from "@/contexts/AuthContext"
import { useStore } from "@/store/useStore"
import { cn } from "@/lib/utils"

export default function Dashboard() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { t } = useTranslation()
  const isAuthenticated = !!user
  const {
    taskId,
    status,
    config,
    downloadProgress,
    downloadStage,
    isDownloading,
    startArxivDownload,
    startTranslation,
    loadUserSettings,
  } = useStore()
  const canStartSingleTranslation = Boolean(taskId && status === "ready")

  const [activeTab, setActiveTab] = useState("arxiv")
  const [isConfigOpen, setIsConfigOpen] = useState(false)
  const [localArxivId, setLocalArxivId] = useState("")
  const [isLoadingSource, setIsLoadingSource] = useState(false)
  const [showArxivTip, setShowArxivTip] = useState(true)
  const [showApiWarning, setShowApiWarning] = useState(true)
  const batchRef = useRef<BatchTranslationHandle>(null)
  const [batchState, setBatchState] = useState<BatchTranslationState>({
    isSubmitting: false,
    activeTab: "arxiv",
    canSubmit: false,
  })

  const stageMap: Record<string, string> = {
    downloading: t("dashboard.downloading_source_files_from_arxiv"),
    extracting: t("dashboard.extracting_source_files_2"),
    downloading_pdf: t("dashboard.downloading_the_original_pdf"),
    validating: t("dashboard.validating_latex_structure_2"),
  }

  const stageTitleMap: Record<string, string> = {
    downloading: t("task.steps.downloadSource"),
    extracting: t("dashboard.extracting_source_files"),
    downloading_pdf: t("dashboard.downloading_original_pdf"),
    validating: t("dashboard.validating_latex_structure"),
  }

  useEffect(() => {
    loadUserSettings()
  }, [loadUserSettings])

  async function handleLoadArxiv() {
    if (!localArxivId.trim()) {
      return
    }

    setIsLoadingSource(true)
    toast.info(t("dashboard.loading_source_document_please_wait"))
    try {
      await startArxivDownload(localArxivId)
    } finally {
      setIsLoadingSource(false)
    }
  }

  async function handleStart() {
    if (!taskId) {
      return
    }

    await startTranslation({
      source_language: config.source_language,
      target_language: config.target_language,
      advanced_config: config.advanced_config,
    })
    navigate("/processing")
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <div className="flex justify-start">
          <TabsList className="bg-surface-container-low border border-outline-variant/10 rounded-xl p-1 h-auto">
            <TabsTrigger 
              value="arxiv" 
              className="rounded-lg data-[state=active]:bg-surface-container-lowest data-[state=active]:shadow-sm px-6 py-2.5 text-sm font-medium transition-all"
            >
              {t("dashboard.arxiv_id")}
            </TabsTrigger>
            <TabsTrigger 
              value="upload" 
              className="rounded-lg data-[state=active]:bg-surface-container-lowest data-[state=active]:shadow-sm px-6 py-2.5 text-sm font-medium transition-all"
            >
              {t("dashboard.local_upload")}
            </TabsTrigger>
            <TabsTrigger 
              value="batch" 
              className="rounded-lg data-[state=active]:bg-surface-container-lowest data-[state=active]:shadow-sm px-6 py-2.5 text-sm font-medium transition-all"
            >
              {t("dashboard.batch_translation")}
            </TabsTrigger>
          </TabsList>
        </div>

        <div className="bg-surface-container-lowest rounded-2xl border border-outline-variant/10 shadow-sm p-6 sm:p-8">
          <TabsContent value="arxiv" className="mt-0 space-y-6">
            <div className="max-w-2xl">
              <div className="flex items-center gap-3 mb-2">
                <FileText className="text-primary w-5 h-5" />
                <h3 className="text-lg font-bold text-on-surface">{t("dashboard.arxiv_paper")}</h3>
              </div>
              <p className="text-sm text-tertiary mb-6">
                {t("dashboard.enter_an_arxiv_id_for_example_2310_xxxxx_to_download_source_files")}
              </p>

              <div className="flex flex-col sm:flex-row gap-4">
                <Input
                  placeholder={t("dashboard.enter_an_arxiv_id_for_example_2301_12345")}
                  value={localArxivId}
                  onChange={(event) => setLocalArxivId(event.target.value)}
                  className="bg-surface-container-low border-outline-variant/20 rounded-xl px-4 py-6 font-mono text-base focus-visible:ring-primary/20"
                />
                <Button
                  onClick={handleLoadArxiv}
                  disabled={!localArxivId || isLoadingSource || isDownloading || status === "processing"}
                  className="rounded-xl px-8 h-auto font-medium transition-all hover:bg-primary/90"
                >
                  {isLoadingSource || isDownloading ? (
                    <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Download className="mr-2 h-4 w-4" />
                  )}
                  {t("dashboard.load_source")}
                </Button>
              </div>

              {showArxivTip ? (
                <div
                  className="mt-4 relative flex cursor-pointer items-start gap-3 rounded-xl border border-outline-variant/20 bg-surface-container-low p-4 text-sm text-tertiary transition-colors hover:bg-surface-container animate-in fade-in zoom-in-95 duration-200"
                  onClick={() => setShowArxivTip(false)}
                >
                  <Info className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                  <div className="leading-relaxed">
                    <span className="font-bold text-on-surface mr-1">{t("dashboard.tip")}</span>
                    {t("dashboard.large_papers_can_take_longer_to_download_through_the_official_arxiv_channel_please_be_patient")}
                  </div>
                  <X className="absolute right-3 top-3 h-4 w-4 shrink-0 opacity-50 transition-opacity hover:opacity-100" />
                </div>
              ) : null}

              {isLoadingSource || isDownloading ? (
                <div className="mt-4 space-y-3 rounded-xl border border-outline-variant/20 bg-surface-container-low p-5 animate-in fade-in duration-200">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-bold text-on-surface">{stageTitleMap[downloadStage] ?? t("dashboard.preparing")}</span>
                    <span className="text-tertiary font-mono">{Math.round(downloadProgress)}%</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-outline-variant/20">
                    <div
                      className="h-full rounded-full bg-primary transition-all duration-300 ease-out"
                      style={{ width: `${Math.round(downloadProgress)}%` }}
                    />
                  </div>
                  <p className="text-xs text-tertiary">
                    {stageMap[downloadStage] ?? t("dashboard.preparing_download")}
                  </p>
                </div>
              ) : null}
            </div>
          </TabsContent>

          <TabsContent value="upload" className="mt-0">
            <DropZone />
          </TabsContent>

          <TabsContent value="batch" className="mt-0">
            {isAuthenticated ? (
              <BatchTranslation
                ref={batchRef}
                advancedConfig={config.advanced_config}
                targetLanguage={config.target_language}
                sourceLanguage={config.source_language}
                onStateChange={setBatchState}
              />
            ) : (
              <LoginPrompt
                messageKey="dashboard.batch.loginRequired"
                descriptionKey="dashboard.batch.loginRequiredDescription"
              />
            )}
          </TabsContent>

          {taskId && status === "ready" && activeTab !== "batch" ? (
            <div className="mt-6 flex items-center gap-4 rounded-xl border border-green-500/20 bg-green-50/50 dark:bg-green-950/20 p-5 animate-in fade-in slide-in-from-top-2">
              <div className="rounded-full bg-green-100 dark:bg-green-900/50 p-2.5 text-green-600 dark:text-green-400">
                <FileText className="h-5 w-5" />
              </div>
              <div className="flex-1">
                <p className="font-bold text-green-800 dark:text-green-300">{t("dashboard.source_document_ready")}</p>
                <p className="font-mono text-sm text-green-600/80 dark:text-green-400/80 mt-0.5">
                  {t("dashboard.task_id", { taskId })}
                </p>
              </div>
            </div>
          ) : null}
        </div>
      </Tabs>

      <div className="bg-surface-container-lowest rounded-2xl border border-outline-variant/10 shadow-sm overflow-hidden">
        <div className="p-6 sm:p-8">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="flex items-center gap-6 flex-1 opacity-70 cursor-not-allowed">
               <div className="flex-1">
                 <label className="block text-[10px] font-bold uppercase tracking-widest text-tertiary mb-1.5 px-1">Source Language</label>
                 <div className="w-full bg-surface-container-low rounded-lg px-4 py-3 text-sm font-medium text-on-surface-variant">
                   Detect Automatically
                 </div>
               </div>
               <div className="flex-1">
                 <label className="block text-[10px] font-bold uppercase tracking-widest text-tertiary mb-1.5 px-1">Target Language</label>
                 <div className="w-full bg-surface-container-low rounded-lg px-4 py-3 text-sm font-medium text-on-surface-variant">
                   Follow Global Settings
                 </div>
               </div>
            </div>
            {activeTab === "batch" ? (
              <Button
                size="lg"
                onClick={() => batchRef.current?.submitCurrent()}
                disabled={!batchState.canSubmit}
                className="px-10 py-6 bg-primary text-on-primary rounded-full font-bold flex items-center justify-center gap-3 transition-all hover:scale-[1.02] shadow-[0_10px_20px_rgba(239,68,68,0.2)] md:w-auto w-full text-base"
              >
                {batchState.isSubmitting ? t("dashboard.submitting") : t("dashboard.start_batch_translation")}
                {batchState.isSubmitting ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Zap className="h-5 w-5 fill-current" />
                )}
              </Button>
            ) : (
              <Button
                size="lg"
                onClick={handleStart}
                disabled={!canStartSingleTranslation}
                className="px-10 py-6 bg-primary text-on-primary rounded-full font-bold flex items-center justify-center gap-3 transition-all hover:scale-[1.02] shadow-[0_10px_20px_rgba(239,68,68,0.2)] md:w-auto w-full text-base disabled:scale-100 disabled:shadow-none disabled:opacity-50"
              >
                {t("dashboard.start_translation")}
                <Zap className="h-5 w-5 fill-current" />
              </Button>
            )}
          </div>
        </div>

        <Collapsible open={isConfigOpen} onOpenChange={setIsConfigOpen} className="border-t border-outline-variant/10 group">
          <CollapsibleTrigger asChild>
            <div className="flex items-center justify-center gap-2 py-4 cursor-pointer text-sm font-bold text-tertiary hover:bg-surface-container-lowest hover:text-on-surface transition-colors select-none">
              <span>{t("dashboard.advancedConfig")}</span>
              <ChevronDown className={cn("h-4 w-4 transition-transform duration-200", isConfigOpen ? "rotate-180" : "")} />
            </div>
          </CollapsibleTrigger>

          <CollapsibleContent className="p-6 sm:p-8 pt-2">
            {showApiWarning ? (
              <div
                className="mb-6 group flex cursor-pointer items-start gap-2 rounded-xl border border-amber-500/20 bg-amber-500/10 p-3 text-sm text-amber-700 transition-colors hover:bg-amber-500/20 animate-in fade-in zoom-in-95 duration-200 dark:text-amber-400"
                onClick={() => setShowApiWarning(false)}
              >
                <Info className="mt-0.5 h-4 w-4 shrink-0" />
                <span className="mr-1 leading-relaxed">
                  {t("dashboard.the_default_api_uses_a_free_tier_and_may_affect_quality_and_speed_a_custom_api_is_recommended")}
                </span>
                <X className="h-4 w-4 shrink-0 opacity-50 transition-opacity group-hover:opacity-100 ml-auto" />
              </div>
            ) : null}
            <AdvancedConfig />
          </CollapsibleContent>
        </Collapsible>
      </div>
      
      <div className="pb-12" />
    </div>
  )
}
