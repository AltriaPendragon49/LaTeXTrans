import { useState } from "react"
import { Download, Columns, Smartphone } from "lucide-react"

import {
    ResizableHandle,
    ResizablePanel,
    ResizablePanelGroup,
} from "@/components/ui/resizable"
import { Button } from "@/components/ui/button"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { useStore } from "@/store/useStore"

export default function ComparisonsPage() {
    // const [scale, setScale] = useState<number>(1.0) // Scale not needed for iframe
    const [viewMode, setViewMode] = useState<"split" | "single">("split")
    const { taskId, arxivId } = useStore()

    // Source PDF: 优先使用后端接口，ArXiv 论文可直接用 arxiv.org 链接
    // 后端接口会找到原始 PDF（排除 zh_前缀和翻译版）
    const sourceUrl = taskId
        ? `http://localhost:8000/api/preview/${taskId}/source-pdf`
        : (arxivId ? `https://arxiv.org/pdf/${arxivId}.pdf` : null)
    // 使用 preview 端点显示 PDF（inline），download 端点用于实际下载
    const previewUrl = taskId ? `http://localhost:8000/api/preview/${taskId}/pdf` : null
    const downloadUrl = taskId ? `http://localhost:8000/api/download/${taskId}/pdf` : null

    const handleDownload = () => {
        if (downloadUrl) {
            window.open(downloadUrl, '_blank')
        }
    }

    const PDFViewer = ({ url, title }: { url: string | null, title: string }) => {
        if (!url) {
            return (
                <div className="flex flex-col items-center justify-center h-full bg-slate-100 dark:bg-slate-900 border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-lg m-4 min-h-[600px]">
                    <p className="text-muted-foreground font-medium mb-2">{title}</p>
                    <p className="text-slate-400 text-sm">No Document Available</p>
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

    return (
        <div className="h-full flex flex-col space-y-4">
            {/* Toolbar */}
            <div className="flex items-center justify-between bg-white dark:bg-slate-900 p-2 rounded-md shadow-sm border">
                <div className="flex items-center space-x-2">
                    <ToggleGroup type="single" value={viewMode} onValueChange={(v) => v && setViewMode(v as any)}>
                        <ToggleGroupItem value="split" aria-label="Split View">
                            <Columns className="h-4 w-4" />
                        </ToggleGroupItem>
                        <ToggleGroupItem value="single" aria-label="Single View">
                            <Smartphone className="h-4 w-4" />
                        </ToggleGroupItem>
                    </ToggleGroup>

                    <div className="h-6 w-px bg-slate-200 dark:bg-slate-800 mx-2" />
                </div>

                <div className="flex items-center space-x-2">
                    <Button variant="default" size="sm" className="ml-4" onClick={handleDownload} disabled={!downloadUrl}>
                        <Download className="mr-2 h-4 w-4" /> Download PDF
                    </Button>
                </div>
            </div>

            {/* Viewer Area */}
            <div className="flex-1 border rounded-md overflow-hidden bg-slate-50 dark:bg-slate-950 relative">
                {viewMode === "split" ? (
                    <ResizablePanelGroup orientation="horizontal">
                        <ResizablePanel defaultSize={50} minSize={30}>
                            <div className="h-full overflow-hidden flex justify-center">
                                <PDFViewer url={sourceUrl} title="Source PDF (Original)" />
                            </div>
                        </ResizablePanel>
                        <ResizableHandle withHandle />
                        <ResizablePanel defaultSize={50} minSize={30}>
                            <div className="h-full overflow-hidden flex justify-center bg-white dark:bg-zinc-900">
                                <PDFViewer url={previewUrl} title="Target PDF (Translated)" />
                            </div>
                        </ResizablePanel>
                    </ResizablePanelGroup>
                ) : (
                    <div className="h-full overflow-hidden flex justify-center bg-white dark:bg-zinc-900">
                        <PDFViewer url={previewUrl} title="Target PDF (Translated)" />
                    </div>
                )}
            </div>
        </div>
    )
}
