import { useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { ChevronDown, Download, FileText, Info, Loader2, RefreshCw, X, Zap, FileCheck } from "lucide-react"

import { Button } from "@/ui/button/Button"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/ui/primitives/collapsible"

import { InfoTile } from "@/ui/info-tile/InfoTile"
import { Input } from "@/ui/input/Input"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { PanelShell } from "@/ui/panel-shell/PanelShell"
import { TabsContent } from "@/ui/primitives/tabs"
import { EditorialTabs, EditorialTabsList, EditorialTabsTrigger } from "@/ui/tabs/EditorialTabs"
import { useAuth } from "@/contexts/AuthContext"
import { AdvancedConfig } from "@/features/translation-workflow/components/AdvancedConfig"
import {
  BatchTranslation,
  type BatchTranslationHandle,
  type BatchTranslationState,
} from "@/features/translation-workflow/components/BatchTranslation"
import { DropZone } from "@/features/translation-workflow/components/DropZone"
import { PdfDirectWorkspace } from "@/features/translation-workflow/components/PdfDirectWorkspace"
import { useTranslationConfig } from "@/features/translation-workflow/hooks/useTranslationConfig"
import { useTranslationTask } from "@/features/translation-workflow/hooks/useTranslationTask"
import { LoginPrompt } from "@/features/auth-shell/components/LoginPrompt"
import { getDailyLatexQuotaExceededDetail } from "@/lib/api"
import { cn } from "@/lib/utils"

/** 工作区模式在 localStorage 中的 key */
const WORKSPACE_MODE_KEY = "latextrans.translation.workspaceMode"

/**
 * 翻译工作区组件（主入口）
 * 提供三种翻译方式：
 * 1. LaTeX 翻译：支持 arXiv ID 下载、本地上传和批量翻译三个子标签页
 * 2. PDF 直接翻译：上传 PDF 文件通过小牛翻译 API 直接翻译
 *
 * 包含高级配置面板（折叠），支持开始翻译、下载源文件和批量提交等操作
 */
export function TranslationWorkspace() {
  const navigate = useNavigate()
  const { refreshQuotaSnapshot, user } = useAuth()
  const { t } = useTranslation()
  const isAuthenticated = !!user
  const { config, loadUserSettings } = useTranslationConfig()
  const {
    taskId,
    status,
    downloadProgress,
    downloadStage,
    isDownloading,
    startArxivDownload,
    startTranslation,
  } = useTranslationTask()
  const canStartSingleTranslation = Boolean(taskId && status === "ready")

  const [workspaceMode, setWorkspaceMode] = useState<string>(() => {
    try { return localStorage.getItem(WORKSPACE_MODE_KEY) ?? "latex" } catch { return "latex" }
  })
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

  /** 切换工作区模式（LaTeX / PDF 直接翻译），持久化到 localStorage */
  function handleWorkspaceModeChange(mode: string) {
    setWorkspaceMode(mode)
    try { localStorage.setItem(WORKSPACE_MODE_KEY, mode) } catch { /* noop */ }
  }

  /** arXiv 下载各阶段的中文描述映射 */
  const stageMap: Record<string, string> = {
    downloading: t("dashboard.downloading_source_files_from_arxiv"),
    extracting: t("dashboard.extracting_source_files_2"),
    downloading_pdf: t("dashboard.downloading_the_original_pdf"),
    validating: t("dashboard.validating_latex_structure_2"),
  }

  /** arXiv 下载各阶段的标题映射 */
  const stageTitleMap: Record<string, string> = {
    downloading: t("task.steps.downloadSource"),
    extracting: t("dashboard.extracting_source_files"),
    downloading_pdf: t("dashboard.downloading_original_pdf"),
    validating: t("dashboard.validating_latex_structure"),
  }

  // 组件挂载时加载用户设置
  useEffect(() => {
    loadUserSettings()
  }, [loadUserSettings])

  /**
   * 从 arXiv 下载源文件
   * 调用 startArxivDownload 触发下载流程，通过 store 反应下载进度
   */
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

  /**
   * 开始翻译
   * 调用 startTranslation 并传入当前语言和高级配置，
   * 成功后跳转到 /processing 页面查看进度
   */
  async function handleStart() {
    if (!taskId) {
      return
    }

    try {
      await startTranslation({
        source_language: config.source_language,
        target_language: config.target_language,
        advanced_config: config.advanced_config,
      })
      void refreshQuotaSnapshot()
      navigate("/processing")
    } catch (error: unknown) {
      if (getDailyLatexQuotaExceededDetail(error)) {
        void refreshQuotaSnapshot()
      }
    }
  }

  return (
    <div className="mx-auto w-full max-w-[1400px] px-6 py-6 md:px-8 md:py-8 lg:px-10 lg:py-10">
      <div className="space-y-8 animate-in fade-in duration-500">
        {/* 一级工作区模式选择器：LaTeX 翻译 / PDF 直接翻译 */}
        <EditorialTabs value={workspaceMode} onValueChange={handleWorkspaceModeChange} className="space-y-6">
        <div className="flex justify-start">
          <EditorialTabsList className="gap-1">
            <EditorialTabsTrigger value="latex">
              <FileText className="mr-2 h-4 w-4" />
              {t("workspace.latexTranslation")}
            </EditorialTabsTrigger>
            <EditorialTabsTrigger value="pdf">
              <FileCheck className="mr-2 h-4 w-4" />
              {t("workspace.pdfDirect")}
            </EditorialTabsTrigger>
          </EditorialTabsList>
        </div>

        {/* LaTeX 翻译内容区域 */}
        <TabsContent value="latex" className="mt-0">
          <EditorialTabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <div className="flex justify-start">
            <EditorialTabsList className="gap-1">
              <EditorialTabsTrigger value="arxiv">
                {t("dashboard.arxiv_id")}
              </EditorialTabsTrigger>
              <EditorialTabsTrigger value="upload">
                {t("dashboard.local_upload")}
              </EditorialTabsTrigger>
              <EditorialTabsTrigger value="batch">
                {t("dashboard.batch_translation")}
              </EditorialTabsTrigger>
            </EditorialTabsList>
          </div>

        <div className="overflow-visible">
          <div className="py-6 sm:py-8">
            {/* arXiv ID 标签页 */}
            <TabsContent value="arxiv" className="mt-0 space-y-6">
              <div className="max-w-2xl">
                <div className="mb-2 flex items-center gap-3">
                  <FileText className="h-5 w-5 text-[color:var(--px-shell-accent)]" />
                  <h3 className="text-lg font-bold text-[color:var(--px-shell-ink)]">{t("dashboard.arxiv_paper")}</h3>
                </div>
                <p className="mb-6 text-sm text-[color:var(--px-shell-muted)]">
                  {t("dashboard.enter_an_arxiv_id_for_example_2310_xxxxx_to_download_source_files")}
                </p>

                <div className="flex flex-col gap-4 sm:flex-row">
                  <Input
                    placeholder={t("dashboard.enter_an_arxiv_id_for_example_2301_12345")}
                    value={localArxivId}
                    onChange={(event) => setLocalArxivId(event.target.value)}
                    className="rounded-[22px] bg-[color:var(--px-shell-panel-strong)] px-4 py-6 font-mono text-base"
                  />
                  <Button
                    onClick={handleLoadArxiv}
                    disabled={!localArxivId || isLoadingSource || isDownloading || status === "processing"}
                    className="h-auto rounded-[22px] px-8 font-medium"
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
                    className="mt-4 animate-in fade-in zoom-in-95 duration-200"
                    onClick={() => setShowArxivTip(false)}
                  >
                    <NoticeBanner
                      tone="neutral"
                      icon={<Info className="h-4 w-4 text-[color:var(--px-shell-accent)]" />}
                      title={t("dashboard.tip")}
                      description={t("dashboard.large_papers_can_take_longer_to_download_through_the_official_arxiv_channel_please_be_patient")}
                      className="relative cursor-pointer transition-colors hover:bg-[color:var(--px-shell-panel-strong)]"
                      action={<X className="h-4 w-4 opacity-50 transition-opacity hover:opacity-100" />}
                    />
                  </div>
                ) : null}

                {/* 下载进度条 */}
                {isLoadingSource || isDownloading ? (
                  <PanelShell
                    tone="glass"
                    className="mt-4 animate-in fade-in space-y-3 duration-200"
                  >
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-bold text-[color:var(--px-shell-ink)]">
                        {stageTitleMap[downloadStage] ?? t("dashboard.preparing")}
                      </span>
                      <span className="font-mono text-[color:var(--px-shell-muted)]">{Math.round(downloadProgress)}%</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-[color:var(--px-shell-line)]">
                      <div
                        className="h-full rounded-full bg-[color:var(--px-shell-accent)] transition-all duration-300 ease-out"
                        style={{ width: `${Math.round(downloadProgress)}%` }}
                      />
                    </div>
                    <p className="text-xs text-[color:var(--px-shell-muted)]">
                      {stageMap[downloadStage] ?? t("dashboard.preparing_download")}
                    </p>
                  </PanelShell>
                ) : null}
              </div>
            </TabsContent>

            {/* 本地上传标签页 */}
            <TabsContent value="upload" className="mt-0">
              <DropZone />
            </TabsContent>

            {/* 批量翻译标签页 */}
            <TabsContent value="batch" className="mt-0">
              {isAuthenticated ? (
                <BatchTranslation
                  ref={batchRef}
                  advancedConfig={config.advanced_config}
                  targetLanguage={config.target_language}
                  sourceLanguage={config.source_language}
                  onStateChange={setBatchState}
                  onQuotaChanged={() => void refreshQuotaSnapshot()}
                />
              ) : (
                <LoginPrompt
                  messageKey="dashboard.batch.loginRequired"
                  descriptionKey="dashboard.batch.loginRequiredDescription"
                />
              )}
            </TabsContent>

            {/* 源文件就绪提示 */}
            {taskId && status === "ready" && activeTab !== "batch" ? (
              <NoticeBanner
                tone="success"
                icon={<FileText className="h-5 w-5" />}
                title={t("dashboard.source_document_ready")}
                description={
                  <span className="font-mono text-sm">
                    {t("dashboard.task_id", { taskId })}
                  </span>
                }
                className="mt-6 animate-in fade-in slide-in-from-top-2"
              />
            ) : null}
          </div>
        </div>
      </EditorialTabs>

      <div className="overflow-hidden">
        <div className="py-6 sm:py-8 mt-2 border-t border-[color:var(--px-shell-line)]/50">
            <div className="flex flex-col justify-between gap-6 md:flex-row md:items-center">
              <div className="flex flex-1 items-center gap-6 opacity-70 cursor-not-allowed">
                <div className="flex-1">
                  <InfoTile
                    title={t("dashboard.summary.sourceLanguage")}
                    description={t("dashboard.summary.detectAutomatically")}
                    tone="panel"
                    valueClassName="text-[color:var(--px-shell-muted)]"
                  />
                </div>
                <div className="flex-1">
                  <InfoTile
                    title={t("dashboard.summary.targetLanguage")}
                    description={t("dashboard.summary.followGlobalSettings")}
                    tone="panel"
                    valueClassName="text-[color:var(--px-shell-muted)]"
                  />
                </div>
              </div>
            {activeTab === "batch" ? (
              <Button
                size="lg"
                onClick={() => batchRef.current?.submitCurrent()}
                disabled={!batchState.canSubmit}
                className="w-full gap-3 px-10 py-6 text-base font-bold md:w-auto"
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
                className="w-full gap-3 px-10 py-6 text-base font-bold md:w-auto disabled:scale-100 disabled:shadow-none disabled:opacity-50"
              >
                {t("dashboard.start_translation")}
                <Zap className="h-5 w-5 fill-current" />
              </Button>
            )}
          </div>
        </div>

        {/* 高级配置折叠面板 */}
        <Collapsible open={isConfigOpen} onOpenChange={setIsConfigOpen} className="group border-t border-[color:var(--px-shell-line)]">
          <CollapsibleTrigger asChild>
            <div className="flex cursor-pointer select-none items-center justify-center gap-2 py-4 text-sm font-bold text-[color:var(--px-shell-muted)] transition-colors hover:bg-[color:var(--px-shell-panel-strong)] hover:text-[color:var(--px-shell-ink)]">
              <span>{t("dashboard.advancedConfig")}</span>
              <ChevronDown className={cn("h-4 w-4 transition-transform duration-200", isConfigOpen ? "rotate-180" : "")} />
            </div>
          </CollapsibleTrigger>

          <CollapsibleContent className="p-6 pt-2 sm:p-8">
            {showApiWarning ? (
              <div className="mb-6 animate-in fade-in zoom-in-95 duration-200" onClick={() => setShowApiWarning(false)}>
                <NoticeBanner
                  tone="warning"
                  icon={<Info className="h-4 w-4" />}
                  description={t("dashboard.the_default_api_uses_a_free_tier_and_may_affect_quality_and_speed_a_custom_api_is_recommended")}
                  className="group cursor-pointer transition-opacity hover:opacity-95"
                  action={<X className="h-4 w-4 opacity-50 transition-opacity group-hover:opacity-100" />}
                />
              </div>
            ) : null}
            <AdvancedConfig />
          </CollapsibleContent>
        </Collapsible>
      </div>
        </TabsContent>

        {/* PDF 直接翻译内容区域 */}
        <TabsContent value="pdf" className="mt-0">
          <PdfDirectWorkspace />
        </TabsContent>

        <div className="pb-12" />
      </EditorialTabs>
      </div>
    </div>
  )
}
