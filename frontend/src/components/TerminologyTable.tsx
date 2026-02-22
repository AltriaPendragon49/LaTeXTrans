import { useEffect, useState } from "react"
import { Download, BookText, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
    SheetTrigger,
} from "@/components/ui/sheet"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"

interface TermPair {
    source: string
    target: string
}

interface TerminologyTableProps {
    taskId: string | null
}

export function TerminologyTable({ taskId }: TerminologyTableProps) {
    const [data, setData] = useState<TermPair[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [isOpen, setIsOpen] = useState(false)

    const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
    const downloadUrl = taskId ? `${API_BASE_URL}/download/${taskId}/terminology` : null

    useEffect(() => {
        if (isOpen && taskId) {
            fetchTerminology()
        }
    }, [isOpen, taskId])

    const fetchTerminology = async () => {
        if (!taskId || !downloadUrl) return

        setLoading(true)
        setError(null)

        try {
            const response = await fetch(downloadUrl)

            if (!response.ok) {
                if (response.status === 404) {
                    setError("No terminology table found for this task.")
                } else {
                    setError("Failed to load terminology table.")
                }
                setData([])
                return
            }

            const text = await response.text()
            const pairs = parseCSV(text)
            setData(pairs)
        } catch (err) {
            setError("Network error occurred while fetching terminology.")
            setData([])
        } finally {
            setLoading(false)
        }
    }

    const parseCSV = (text: string): TermPair[] => {
        const lines = text.split('\n')
        const pairs: TermPair[] = []

        // Skip header row if exists (usually "Source Term,Translation")
        const startIndex = lines[0]?.toLowerCase().includes('source term') ? 1 : 0

        for (let i = startIndex; i < lines.length; i++) {
            const line = lines[i].trim()
            if (!line) continue

            // Simple CSV parse handling comma
            // Note: This is a basic parser. For complex CSVs with quotes, a library is better.
            // Assuming the backend generates simple CSVs without internal commas/quotes for now.
            const parts = line.split(',')
            if (parts.length >= 2) {
                // Rejoin in case of extra commas, though our backend should handle this ideally
                // ideally backend uses csv.writer which quotes fields if they contain commas
                // Here we assume standard CSV format

                // Dealing with potential quoted strings from backend csv.writer
                // This is a naive implementation, but sufficient for simple term pairs
                // If complex parsing is needed, we'd need a proper parser logic

                // Let's use a slightly better regex for CSV split that handles quotes
                // matches: "value", value, "val,ue"
                const matches = line.match(/(".*?"|[^",\s]+)(?=\s*,|\s*$)/g)

                let source = ""
                let target = ""

                if (matches && matches.length >= 2) {
                    source = matches[0]
                    target = matches.slice(1).join(',')
                } else {
                    // Fallback to simple split
                    source = parts[0]
                    target = parts.slice(1).join(',')
                }

                // Clean quotes
                source = source.replace(/^"|"$/g, '').trim()
                target = target.replace(/^"|"$/g, '').trim()

                if (source && target) {
                    pairs.push({ source, target })
                }
            }
        }
        return pairs
    }

    const handleDownload = () => {
        if (downloadUrl) {
            window.open(downloadUrl, '_blank')
        }
    }

    return (
        <Sheet open={isOpen} onOpenChange={setIsOpen}>
            <SheetTrigger asChild>
                <Button variant="outline" size="sm" disabled={!taskId}>
                    <BookText className="mr-2 h-4 w-4" />
                    术语表
                </Button>
            </SheetTrigger>
            <SheetContent className="w-[400px] sm:w-[540px] flex flex-col h-full bg-white dark:bg-slate-950">
                <SheetHeader>
                    <SheetTitle className="flex items-center gap-2">
                        <BookText className="h-5 w-5" />
                        术语对照表
                    </SheetTitle>
                    <SheetDescription>
                        本文档中提取和使用的专业术语对照。
                    </SheetDescription>
                </SheetHeader>

                <div className="flex-1 overflow-hidden mt-6 border rounded-md">
                    {loading ? (
                        <div className="p-4 space-y-4">
                            {[1, 2, 3, 4, 5].map((i) => (
                                <div key={i} className="flex gap-4">
                                    <Skeleton className="h-4 w-1/3" />
                                    <Skeleton className="h-4 w-2/3" />
                                </div>
                            ))}
                        </div>
                    ) : error ? (
                        <div className="h-full flex flex-col items-center justify-center text-muted-foreground p-6 text-center">
                            <AlertCircle className="h-10 w-10 mb-2 opacity-20" />
                            <p>{error}</p>
                        </div>
                    ) : data.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center text-muted-foreground p-6 text-center">
                            <BookText className="h-10 w-10 mb-2 opacity-20" />
                            <p>没有找到术语数据</p>
                            <p className="text-xs mt-1 opacity-70">请确保在翻译时开启了"生成术语表"选项</p>
                        </div>
                    ) : (
                        <ScrollArea className="h-full">
                            <div className="w-full text-sm">
                                <div className="sticky top-0 bg-slate-100 dark:bg-slate-900 border-b flex font-medium text-muted-foreground z-10">
                                    <div className="flex-1 p-3 border-r">原文 (Source)</div>
                                    <div className="flex-1 p-3">译文 (Target)</div>
                                </div>
                                <div className="divide-y">
                                    {data.map((pair, idx) => (
                                        <div
                                            key={idx}
                                            className="flex hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors"
                                        >
                                            <div className="flex-1 p-3 border-r break-words font-medium text-slate-700 dark:text-slate-300">
                                                {pair.source}
                                            </div>
                                            <div className="flex-1 p-3 break-words text-slate-600 dark:text-slate-400">
                                                {pair.target}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </ScrollArea>
                    )}
                </div>

                <div className="mt-6 flex justify-end">
                    <Button
                        onClick={handleDownload}
                        disabled={!downloadUrl || loading || data.length === 0}
                        className="w-full sm:w-auto"
                    >
                        <Download className="mr-2 h-4 w-4" />
                        下载 CSV
                    </Button>
                </div>
            </SheetContent>
        </Sheet>
    )
}
