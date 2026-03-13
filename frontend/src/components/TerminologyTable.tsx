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
import { API_BASE_URL } from "@/api-base"

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

    const downloadUrl = taskId ? `${API_BASE_URL}/api/download/${taskId}/terminology` : null

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
                    鏈琛?
                </Button>
            </SheetTrigger>
            <SheetContent className="w-[400px] sm:w-[540px] flex flex-col h-full bg-white dark:bg-slate-950">
                <SheetHeader>
                    <SheetTitle className="flex items-center gap-2">
                        <BookText className="h-5 w-5" />
                        鏈瀵圭収琛?
                    </SheetTitle>
                    <SheetDescription>
                        鏈枃妗ｄ腑鎻愬彇鍜屼娇鐢ㄧ殑涓撲笟鏈瀵圭収銆?
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
                            <p>娌℃湁鎵惧埌鏈鏁版嵁</p>
                            <p className="text-xs mt-1 opacity-70">璇风‘淇濆湪缈昏瘧鏃跺紑鍚簡"鐢熸垚鏈琛?閫夐」</p>
                        </div>
                    ) : (
                        <ScrollArea className="h-full">
                            <div className="w-full text-sm">
                                <div className="sticky top-0 bg-slate-100 dark:bg-slate-900 border-b flex font-medium text-muted-foreground z-10">
                                    <div className="flex-1 p-3 border-r">鍘熸枃 (Source)</div>
                                    <div className="flex-1 p-3">璇戞枃 (Target)</div>
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
                        涓嬭浇 CSV
                    </Button>
                </div>
            </SheetContent>
        </Sheet>
    )
}

