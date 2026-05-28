import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { Columns, Download, FileText, Languages, Plus, Smartphone } from "lucide-react"
import { useTranslation } from "react-i18next"

import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/ui/primitives/resizable"
import { ToggleGroup, ToggleGroupItem } from "@/ui/primitives/toggle-group"
import { API_BASE_URL } from "@/api-base"
import { TerminologyTable } from "@/features/translation-workflow/components/TerminologyTable"
import { useTranslationTask } from "@/features/translation-workflow/hooks/useTranslationTask"
import { useIsMobile } from "@/hooks/use-mobile"
import { Button } from "@/ui/button/Button"
import { StatePanel } from "@/ui/state-panel/StatePanel"

/** 桌面端 PDF 查看模式 */
type ViewMode = "split" | "single"
/** PDF 查看器模式 */
type PdfViewerMode = "split" | "single"
/** 移动端文档切换模式 */
type MobileDocumentMode = "translated" | "source"

/** PDF 查看器子组件的 Props */
interface PdfViewerProps {
  /** 无 PDF 时的空状态提示文案 */
  emptyMessage: string
  /** 查看模式 */
  mode: PdfViewerMode
  /** 查看器标题 */
  title: string
  /** PDF 文件 URL，为 null 时显示空状态 */
  url: string | null
}

/**
 * 构建带查看参数的 PDF.js 查看器 URL
 * 添加 page=1&view=FitH&pagemode=none 等参数以优化嵌入显示效果
 */
function buildPdfViewerUrl(url: string) {
  const viewerParams = `page=1&view=FitH&pagemode=none&toolbar=0&navpanes=0&scrollbar=0`
  return url.includes("#") ? `${url}&${viewerParams}` : `${url}#${viewerParams}`
}

/**
 * PDF 查看器子组件
 * 在 iframe 中嵌入 PDF 预览，无 URL 时显示空状态面板
 */
function PdfViewer({ emptyMessage, mode, title, url }: PdfViewerProps) {
  const { t } = useTranslation()

  if (!url) {
    return (
      <div className="h-full p-4">
        <StatePanel
          className="h-full min-h-[520px] justify-center rounded-[24px] border-dashed bg-[color:var(--px-shell-panel-strong)] shadow-none"
          icon={<FileText className="h-7 w-7" />}
          title={title}
          description={emptyMessage}
          meta={t("comparison.no_documents_available")}
        />
      </div>
    )
  }

  const viewerUrl = buildPdfViewerUrl(url)

  return (
    <div className="flex h-full min-h-0 flex-col bg-[color:var(--px-shell-panel-strong)]">
      <div className="bg-[color:color-mix(in_srgb,var(--px-shell-panel)_72%,white)] px-3 py-2 text-center text-[11px] font-semibold uppercase tracking-[0.16em] text-[color:var(--px-shell-muted)]">
        {title}
      </div>
      <iframe src={viewerUrl} className={`h-full border-0 mx-auto ${mode === "single" ? "w-[60%]" : "w-full"}`} title={title} />
    </div>
  )
}

/**
 * 对比工作台组件
 * 左右分栏展示源 PDF 和翻译后的 PDF，支持分栏/单栏切换、
 * 术语表查看、PDF 下载和新翻译操作。移动端自动切换为单栏模式
 */
export function ComparisonWorkbench() {
  const isMobile = useIsMobile()
  const [viewMode, setViewMode] = useState<ViewMode>(() =>
    typeof window !== "undefined" && window.innerWidth < 768 ? "single" : "split",
  )
  const [mobileDocumentMode, setMobileDocumentMode] = useState<MobileDocumentMode>("translated")
  const { taskId, arxivId, resetTranslationState } = useTranslationTask()
  const navigate = useNavigate()
  const { t } = useTranslation()

  // 构建源 PDF 和翻译后 PDF 的 URL
  const sourceUrl = taskId
    ? `${API_BASE_URL}/api/preview/${taskId}/source-pdf`
    : (arxivId ? `https://arxiv.org/pdf/${arxivId}.pdf` : null)
  const previewUrl = taskId ? `${API_BASE_URL}/api/preview/${taskId}/pdf` : null
  const downloadUrl = taskId ? `${API_BASE_URL}/api/download/${taskId}/pdf` : null

  /** 下载翻译后的 PDF */
  const handleDownload = () => {
    if (downloadUrl) {
      window.open(downloadUrl, "_blank")
    }
  }

  /** 发起新翻译，重置状态并跳转到翻译页面 */
  const handleNewTranslation = () => {
    resetTranslationState()
    navigate("/translate")
  }

  const handleViewModeChange = (value: string) => {
    if (value === "split" || value === "single") {
      setViewMode(value)
    }
  }

  const handleMobileDocumentChange = (value: string) => {
    if (value === "translated" || value === "source") {
      setMobileDocumentMode(value)
    }
  }

  const emptyMessage = t("comparison.no_documents_available")
  const sourceTitle = t("comparison.original_pdf_source_document")
  const translatedTitle = t("comparison.translated_pdf_translation_result")
  const mobileViewerTitle = mobileDocumentMode === "source" ? sourceTitle : translatedTitle
  const mobileViewerUrl = mobileDocumentMode === "source" ? sourceUrl : previewUrl

  // 移动端强制使用单栏模式
  useEffect(() => {
    if (isMobile && viewMode !== "single") {
      setViewMode("single")
    }
  }, [isMobile, viewMode])

  return (
    <div
      data-testid="comparison-workbench"
      className="flex h-full min-h-0 w-full min-w-0 flex-1 flex-col gap-3 overflow-hidden px-4 py-3 md:px-5 md:py-3"
    >
      <div
        data-testid="comparison-header"
        className="grid gap-2 md:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] md:items-center"
      >
        <div className="min-w-0">
          <h1 className="truncate text-xl font-semibold leading-none tracking-tight text-[color:var(--px-shell-ink)] md:text-[1.7rem]">
            {t("comparison.title")}
          </h1>
        </div>

        <div data-testid="comparison-view-toggle" className="justify-self-center">
          {isMobile ? (
            <ToggleGroup
              type="single"
              value={mobileDocumentMode}
              onValueChange={handleMobileDocumentChange}
              className="justify-start rounded-full bg-[color:color-mix(in_srgb,var(--px-shell-panel)_78%,white)] p-0.5 shadow-[0_10px_24px_-20px_rgba(15,23,42,0.55)]"
            >
              <ToggleGroupItem value="translated" aria-label={translatedTitle} className="h-8 gap-1.5 px-3 text-[11px]">
                <Smartphone className="h-4 w-4" />
                <span>{t("community.detail.mode.translatedPdf")}</span>
              </ToggleGroupItem>
              <ToggleGroupItem value="source" aria-label={sourceTitle} className="h-8 gap-1.5 px-3 text-[11px]">
                <Languages className="h-4 w-4" />
                <span>{t("community.detail.mode.source")}</span>
              </ToggleGroupItem>
            </ToggleGroup>
          ) : (
            <ToggleGroup
              type="single"
              value={viewMode}
              onValueChange={handleViewModeChange}
              className="justify-start rounded-full bg-[color:color-mix(in_srgb,var(--px-shell-panel)_78%,white)] p-0.5 shadow-[0_10px_24px_-20px_rgba(15,23,42,0.55)]"
            >
              <ToggleGroupItem value="split" aria-label={t("comparison.split_view")} className="h-8 gap-1.5 px-3 text-[11px]">
                <Columns className="h-4 w-4" />
                <span>{t("comparison.split_view")}</span>
              </ToggleGroupItem>
              <ToggleGroupItem value="single" aria-label={t("comparison.single_view")} className="h-8 gap-1.5 px-3 text-[11px]">
                <Smartphone className="h-4 w-4" />
                <span>{t("comparison.single_view")}</span>
              </ToggleGroupItem>
            </ToggleGroup>
          )}
        </div>

        <div className="flex flex-wrap items-center justify-start gap-2 md:justify-end">
          <TerminologyTable taskId={taskId} />
          <Button variant="outline" size="sm" onClick={handleNewTranslation} className="min-h-8 px-3">
            <Plus className="mr-2 h-4 w-4" />
            {t("common.new_translation")}
          </Button>
          <Button size="sm" onClick={handleDownload} disabled={!downloadUrl} className="min-h-8 px-3">
            <Download className="mr-2 h-4 w-4" />
            {t("comparison.download_pdf")}
          </Button>
        </div>
      </div>

      <div
        data-testid="comparison-preview-region"
        className="min-h-[560px] min-w-0 flex-1 overflow-hidden rounded-[22px] bg-transparent"
      >
        {!isMobile && viewMode === "split" ? (
          <ResizablePanelGroup orientation="horizontal">
            <ResizablePanel defaultSize={50} minSize={30}>
              <div className="h-full min-h-0 overflow-hidden rounded-[18px] bg-[color:var(--px-shell-panel-strong)]">
                <PdfViewer emptyMessage={emptyMessage} mode="split" title={sourceTitle} url={sourceUrl} />
              </div>
            </ResizablePanel>
            <ResizableHandle withHandle />
            <ResizablePanel defaultSize={50} minSize={30}>
              <div className="h-full min-h-0 overflow-hidden rounded-[18px] bg-[color:var(--px-shell-panel-strong)]">
                <PdfViewer emptyMessage={emptyMessage} mode="split" title={translatedTitle} url={previewUrl} />
              </div>
            </ResizablePanel>
          </ResizablePanelGroup>
        ) : (
          <div className="h-full min-h-0 overflow-hidden rounded-[18px] bg-[color:var(--px-shell-panel-strong)]">
            <PdfViewer
              emptyMessage={emptyMessage}
              mode="single"
              title={isMobile ? mobileViewerTitle : translatedTitle}
              url={isMobile ? mobileViewerUrl : previewUrl}
            />
          </div>
        )}
      </div>
    </div>
  )
}
