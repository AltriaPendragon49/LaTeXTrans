import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Download, Columns, Smartphone, Plus } from "lucide-react"

import {
    ResizableHandle,
    ResizablePanel,
    ResizablePanelGroup,
} from "@/components/ui/resizable"
import { Button } from "@/components/ui/button"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { useStore } from "@/store/useStore"
import { TerminologyTable } from "@/components/TerminologyTable"
import { API_BASE_URL } from "@/api-base"
import { useTranslation } from "react-i18next"

type ViewMode = "split" | "single"

interface PDFViewerProps {
    emptyMessage: string
    title: string
    url: string | null
}

function PDFViewer({ emptyMessage, title, url }: PDFViewerProps) {
    if (!url) {
        return (
            <div className="flex flex-col items-center justify-center h-full bg-slate-100 dark:bg-slate-900 border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-lg m-4 min-h-[600px]">
                <p className="text-muted-foreground font-medium mb-2">{title}</p>
                <p className="text-slate-400 text-sm">{emptyMessage}</p>
            </div>
        )
    }

    return (
        <div className="w-full h-full bg-slate-200 dark:bg-slate-900 flex flex-col">
            <div className="bg-slate-100 dark:bg-slate-800 p-2 text-xs text-center border-b font-medium text-muted-foreground">
                {title}
            </div>
            <iframe src={url} className="w-full h-full border-none" title={title} />
        </div>
    )
}

export default function ComparisonsPage() {
    const [viewMode, setViewMode] = useState<ViewMode>("split")
    const { taskId, arxivId, resetTranslationState } = useStore()
    const navigate = useNavigate()
    const { t } = useTranslation()

    const handleNewTranslation = () => {
        resetTranslationState()
        navigate("/")
    }

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

    const handleViewModeChange = (value: string) => {
        if (value === "split" || value === "single") {
            setViewMode(value)
        }
    }

    const emptyMessage = t("comparison.no_documents_available")
    const sourceTitle = t("comparison.original_pdf_source_document")
    const translatedTitle = t("comparison.translated_pdf_translation_result")

    return (
        <div className="h-full flex flex-col space-y-4">
            <div className="flex items-center justify-between bg-white dark:bg-slate-900 p-2 rounded-md shadow-sm border">
                <div className="flex items-center space-x-2">
                    <ToggleGroup type="single" value={viewMode} onValueChange={handleViewModeChange}>
                        <ToggleGroupItem value="split" aria-label={t("comparison.split_view")}>
                            <Columns className="h-4 w-4" />
                        </ToggleGroupItem>
                        <ToggleGroupItem value="single" aria-label={t("comparison.single_view")}>
                            <Smartphone className="h-4 w-4" />
                        </ToggleGroupItem>
                    </ToggleGroup>

                    <div className="h-6 w-px bg-slate-200 dark:bg-slate-800 mx-2" />
                </div>

                <div className="flex items-center space-x-2">
                    <TerminologyTable taskId={taskId} />
                    <Button variant="default" size="sm" className="ml-2" onClick={handleDownload} disabled={!downloadUrl}>
                        <Download className="mr-2 h-4 w-4" /> {t("comparison.download_pdf")}
                    </Button>
                    <Button variant="outline" size="sm" onClick={handleNewTranslation}>
                        <Plus className="mr-2 h-4 w-4" /> {t("common.new_translation")}
                    </Button>
                </div>
            </div>

            <div className="flex-1 border rounded-md overflow-hidden bg-slate-50 dark:bg-slate-950 relative">
                {viewMode === "split" ? (
                    <ResizablePanelGroup orientation="horizontal">
                        <ResizablePanel defaultSize={50} minSize={30}>
                            <div className="h-full overflow-hidden flex justify-center">
                                <PDFViewer emptyMessage={emptyMessage} title={sourceTitle} url={sourceUrl} />
                            </div>
                        </ResizablePanel>
                        <ResizableHandle withHandle />
                        <ResizablePanel defaultSize={50} minSize={30}>
                            <div className="h-full overflow-hidden flex justify-center bg-white dark:bg-zinc-900">
                                <PDFViewer emptyMessage={emptyMessage} title={translatedTitle} url={previewUrl} />
                            </div>
                        </ResizablePanel>
                    </ResizablePanelGroup>
                ) : (
                    <div className="h-full overflow-hidden flex justify-center bg-white dark:bg-zinc-900">
                        <PDFViewer emptyMessage={emptyMessage} title={translatedTitle} url={previewUrl} />
                    </div>
                )}
            </div>
        </div>
    )
}
