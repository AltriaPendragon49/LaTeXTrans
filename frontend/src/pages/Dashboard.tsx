import { useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { ChevronDown, ChevronRight, Download, FileText, Info, Loader2, Play, RefreshCw, X } from "lucide-react"

import { AdvancedConfig } from "@/components/AdvancedConfig"
import { BatchTranslation, type BatchTranslationHandle, type BatchTranslationState } from "@/components/BatchTranslation"
import { DropZone } from "@/components/DropZone"
import { LoginPrompt } from "@/components/LoginPrompt"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useAuth } from "@/contexts/AuthContext"
import { useStore } from "@/store/useStore"

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
    <div className="container mx-auto max-w-4xl space-y-8 p-6 animate-in fade-in duration-500">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">{t("dashboard.start_translation")}</h1>
        <p className="text-muted-foreground">{t("dashboard.toolsDescription")}</p>
      </div>

      <div className="space-y-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-3 lg:w-[520px]">
            <TabsTrigger value="arxiv">{t("dashboard.arxiv_id")}</TabsTrigger>
            <TabsTrigger value="upload">{t("dashboard.local_upload")}</TabsTrigger>
            <TabsTrigger value="batch">{t("dashboard.batch_translation")}</TabsTrigger>
          </TabsList>

          <Card className="border-border/50 bg-card/50 shadow-sm backdrop-blur-sm">
            {activeTab !== "batch" ? (
              <CardHeader>
                <CardTitle>{activeTab === "arxiv" ? t("dashboard.arxiv_paper") : t("dashboard.file_upload")}</CardTitle>
                <CardDescription>
                  {activeTab === "arxiv"
                    ? t("dashboard.enter_an_arxiv_id_for_example_2310_xxxxx_to_download_source_files")
                    : t("dashboard.upload_a_latex_project_archive_zip_rar_tar_gz")}
                </CardDescription>
              </CardHeader>
            ) : null}

            <CardContent className="space-y-6">
              <TabsContent value="arxiv" className="mt-0 space-y-4">
                <div className="flex gap-4">
                  <Input
                    placeholder={t("dashboard.enter_an_arxiv_id_for_example_2301_12345")}
                    value={localArxivId}
                    onChange={(event) => setLocalArxivId(event.target.value)}
                    className="bg-background font-mono"
                  />
                  <Button
                    onClick={handleLoadArxiv}
                    disabled={!localArxivId || isLoadingSource || isDownloading || status === "processing"}
                    className="transition-all duration-150 active:scale-95"
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
                    className="relative flex cursor-pointer items-start gap-2 rounded-md border border-border/50 bg-muted/50 p-3 text-xs text-muted-foreground transition-colors hover:bg-muted/80 animate-in fade-in zoom-in-95 duration-200"
                    onClick={() => setShowArxivTip(false)}
                  >
                    <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                    <div className="leading-relaxed">
                      <span className="font-medium">{t("dashboard.tip")}</span>
                      {t("dashboard.large_papers_can_take_longer_to_download_through_the_official_arxiv_channel_please_be_patient")}
                    </div>
                    <X className="absolute right-3 top-3 h-3.5 w-3.5 shrink-0 opacity-50 transition-opacity group-hover:opacity-100" />
                  </div>
                ) : null}

                {isLoadingSource || isDownloading ? (
                  <div className="space-y-2 rounded-md border border-border/50 bg-muted/40 p-4 animate-in fade-in duration-200">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium">{stageTitleMap[downloadStage] ?? t("dashboard.preparing")}</span>
                      <span className="text-muted-foreground">{Math.round(downloadProgress)}%</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-border/60">
                      <div
                        className="h-full rounded-full bg-primary transition-all duration-300 ease-out"
                        style={{ width: `${Math.round(downloadProgress)}%` }}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {stageMap[downloadStage] ?? t("dashboard.preparing_download")}
                    </p>
                  </div>
                ) : null}
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

              {taskId && status === "ready" ? (
                <div className="flex items-center gap-3 rounded-lg border border-green-500/20 bg-green-500/10 p-4 animate-in fade-in slide-in-from-top-2">
                  <div className="rounded-full bg-green-500/20 p-2 text-green-600 dark:text-green-400">
                    <FileText className="h-5 w-5" />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-green-700 dark:text-green-300">{t("dashboard.source_document_ready")}</p>
                    <p className="font-mono text-xs text-green-600/80 dark:text-green-400/80">
                      {t("dashboard.task_id", { taskId })}
                    </p>
                  </div>
                </div>
              ) : null}
            </CardContent>
          </Card>
        </Tabs>

        <div className="flex justify-end pt-2">
          {activeTab === "batch" ? (
            <Button
              size="lg"
              onClick={() => batchRef.current?.submitCurrent()}
              disabled={!batchState.canSubmit}
              className="min-w-[200px] w-full py-6 text-lg shadow-lg shadow-primary/20 md:w-auto"
            >
              {batchState.isSubmitting ? (
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              ) : (
                <Play className="mr-2 h-5 w-5 fill-current" />
              )}
              {batchState.isSubmitting ? t("dashboard.submitting") : t("dashboard.start_batch_translation")}
            </Button>
          ) : (
            <Button
              size="lg"
              onClick={handleStart}
              disabled={!taskId || status === "downloading" || status === "starting_translation"}
              className="min-w-[200px] w-full py-6 text-lg shadow-lg shadow-primary/20 md:w-auto"
            >
              <Play className="mr-2 h-5 w-5 fill-current" />
              {t("dashboard.start_translation")}
            </Button>
          )}
        </div>
      </div>

      <Collapsible open={isConfigOpen} onOpenChange={setIsConfigOpen} className="space-y-2">
        <div className="flex w-full flex-col justify-between gap-3 md:flex-row md:items-center">
          <CollapsibleTrigger asChild>
            <Button
              variant="ghost"
              className="group w-fit justify-start gap-2 p-0 hover:bg-transparent hover:text-primary"
            >
              {isConfigOpen ? (
                <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground group-hover:text-primary" />
              ) : (
                <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground group-hover:text-primary" />
              )}
              <span className="whitespace-nowrap text-lg font-medium">{t("dashboard.advancedConfig")}</span>
              <span className="ml-1 whitespace-nowrap text-sm font-normal text-muted-foreground">
                {t("dashboard.optional")}
              </span>
            </Button>
          </CollapsibleTrigger>

          {showApiWarning ? (
            <div
              className="group flex cursor-pointer items-center gap-1.5 rounded-md border border-amber-500/20 bg-amber-500/10 px-2.5 py-1.5 text-[11px] text-amber-600 transition-colors hover:bg-amber-500/20 animate-in fade-in zoom-in-95 duration-200 sm:w-fit sm:text-xs dark:text-amber-400"
              onClick={() => setShowApiWarning(false)}
            >
              <Info className="h-3.5 w-3.5 shrink-0" />
              <span className="mr-1 leading-tight">
                {t("dashboard.the_default_api_uses_a_free_tier_and_may_affect_quality_and_speed_a_custom_api_is_recommended")}
              </span>
              <X className="h-3.5 w-3.5 shrink-0 opacity-50 transition-opacity group-hover:opacity-100" />
            </div>
          ) : null}
        </div>

        <CollapsibleContent className="space-y-4 pt-2 animate-in slide-in-from-top-2 fade-in duration-200">
          <AdvancedConfig />
        </CollapsibleContent>
      </Collapsible>

      <div className="pb-12" />
    </div>
  )
}
