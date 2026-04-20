import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Columns, Download, FileText, Plus, Smartphone } from "lucide-react"
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
import { Button } from "@/ui/button/Button"
import { Card, CardContent } from "@/ui/card/Card"
import { PageIntro } from "@/ui/page-intro/PageIntro"
import { StatePanel } from "@/ui/state-panel/StatePanel"

type ViewMode = "split" | "single"

interface PdfViewerProps {
  emptyMessage: string
  title: string
  url: string | null
}

function PdfViewer({ emptyMessage, title, url }: PdfViewerProps) {
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

  return (
    <div className="flex h-full min-h-0 flex-col bg-[color:var(--px-shell-panel-strong)]">
      <div className="border-b border-[color:var(--px-shell-line)] px-4 py-3 text-center text-xs font-semibold uppercase tracking-[0.18em] text-[color:var(--px-shell-muted)]">
        {title}
      </div>
      <iframe src={url} className="h-full w-full border-0" title={title} />
    </div>
  )
}

export function ComparisonWorkbench() {
  const [viewMode, setViewMode] = useState<ViewMode>("split")
  const { taskId, arxivId, resetTranslationState } = useTranslationTask()
  const navigate = useNavigate()
  const { t } = useTranslation()

  const sourceUrl = taskId
    ? `${API_BASE_URL}/api/preview/${taskId}/source-pdf`
    : (arxivId ? `https://arxiv.org/pdf/${arxivId}.pdf` : null)
  const previewUrl = taskId ? `${API_BASE_URL}/api/preview/${taskId}/pdf` : null
  const downloadUrl = taskId ? `${API_BASE_URL}/api/download/${taskId}/pdf` : null

  const handleDownload = () => {
    if (downloadUrl) {
      window.open(downloadUrl, "_blank")
    }
  }

  const handleNewTranslation = () => {
    resetTranslationState()
    navigate("/")
  }

  const handleViewModeChange = (value: string) => {
    if (value === "split" || value === "single") {
      setViewMode(value)
    }
  }

  const emptyMessage = t("comparison.no_documents_available")
  const sourceTitle = t("comparison.original_pdf_source_document")
  const translatedTitle = t("comparison.translated_pdf_translation_result")

  return (
    <div className="flex h-full min-h-0 flex-col gap-6">
      <PageIntro
        title={t("comparison.title")}
        description={t("comparison.description")}
        actions={(
          <>
            <TerminologyTable taskId={taskId} />
            <Button variant="outline" size="sm" onClick={handleNewTranslation}>
              <Plus className="mr-2 h-4 w-4" />
              {t("common.new_translation")}
            </Button>
            <Button size="sm" onClick={handleDownload} disabled={!downloadUrl}>
              <Download className="mr-2 h-4 w-4" />
              {t("comparison.download_pdf")}
            </Button>
          </>
        )}
      />

      <Card className="overflow-hidden rounded-[28px] shadow-none">
        <CardContent className="flex flex-col gap-4 p-4 sm:p-5">
          <div className="flex flex-col gap-4 border-b border-[color:var(--px-shell-line)] pb-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-1">
              <p className="text-[10px] font-black uppercase tracking-[0.22em] text-[color:var(--px-shell-muted)]">
                {t("comparison.layoutLabel")}
              </p>
              <p className="text-sm text-[color:var(--px-shell-muted)]">
                {t("comparison.layoutDescription")}
              </p>
            </div>

            <ToggleGroup type="single" value={viewMode} onValueChange={handleViewModeChange} className="justify-start">
              <ToggleGroupItem value="split" aria-label={t("comparison.split_view")} className="gap-2">
                <Columns className="h-4 w-4" />
                <span>{t("comparison.split_view")}</span>
              </ToggleGroupItem>
              <ToggleGroupItem value="single" aria-label={t("comparison.single_view")} className="gap-2">
                <Smartphone className="h-4 w-4" />
                <span>{t("comparison.single_view")}</span>
              </ToggleGroupItem>
            </ToggleGroup>
          </div>

          <div className="min-h-0 flex-1 overflow-hidden rounded-[24px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-surface)]">
            {viewMode === "split" ? (
              <ResizablePanelGroup orientation="horizontal">
                <ResizablePanel defaultSize={50} minSize={30}>
                  <div className="h-full min-h-0 overflow-hidden">
                    <PdfViewer emptyMessage={emptyMessage} title={sourceTitle} url={sourceUrl} />
                  </div>
                </ResizablePanel>
                <ResizableHandle withHandle />
                <ResizablePanel defaultSize={50} minSize={30}>
                  <div className="h-full min-h-0 overflow-hidden">
                    <PdfViewer emptyMessage={emptyMessage} title={translatedTitle} url={previewUrl} />
                  </div>
                </ResizablePanel>
              </ResizablePanelGroup>
            ) : (
              <div className="h-full min-h-0 overflow-hidden">
                <PdfViewer emptyMessage={emptyMessage} title={translatedTitle} url={previewUrl} />
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
