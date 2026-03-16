import { useCallback, useEffect, useState } from "react"
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
import { useTranslation } from "react-i18next"

interface TermPair {
    source: string
    target: string
}

interface TerminologyTableProps {
    taskId: string | null
}

const parseCSV = (text: string): TermPair[] => {
    const lines = text.split("\n")
    const pairs: TermPair[] = []
    const startIndex = lines[0]?.toLowerCase().includes("source term") ? 1 : 0

    for (let index = startIndex; index < lines.length; index += 1) {
        const line = lines[index].trim()
        if (!line) continue

        const parts = line.split(",")
        if (parts.length < 2) continue

        const matches = line.match(/(".*?"|[^",\s]+)(?=\s*,|\s*$)/g)

        let source = ""
        let target = ""

        if (matches && matches.length >= 2) {
            source = matches[0]
            target = matches.slice(1).join(",")
        } else {
            source = parts[0]
            target = parts.slice(1).join(",")
        }

        source = source.replace(/^"|"$/g, "").trim()
        target = target.replace(/^"|"$/g, "").trim()

        if (source && target) {
            pairs.push({ source, target })
        }
    }

    return pairs
}

export function TerminologyTable({ taskId }: TerminologyTableProps) {
    const { t } = useTranslation()
    const [data, setData] = useState<TermPair[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [isOpen, setIsOpen] = useState(false)

    const downloadUrl = taskId ? `${API_BASE_URL}/api/download/${taskId}/terminology` : null

    const fetchTerminology = useCallback(async () => {
        if (!taskId || !downloadUrl) return

        setLoading(true)
        setError(null)

        try {
            const response = await fetch(downloadUrl)

            if (!response.ok) {
                if (response.status === 404) {
                    setError(t("glossary.no_glossary_was_found_for_this_task"))
                } else {
                    setError(t("glossary.failed_to_load_glossary"))
                }
                setData([])
                return
            }

            const text = await response.text()
            setData(parseCSV(text))
        } catch {
            setError(t("glossary.a_network_error_occurred_while_loading_the_glossary"))
            setData([])
        } finally {
            setLoading(false)
        }
    }, [downloadUrl, taskId, t])

    useEffect(() => {
        if (isOpen && taskId) {
            void fetchTerminology()
        }
    }, [fetchTerminology, isOpen, taskId])

    const handleDownload = () => {
        if (downloadUrl) {
            window.open(downloadUrl, "_blank")
        }
    }

    return (
        <Sheet open={isOpen} onOpenChange={setIsOpen}>
            <SheetTrigger asChild>
                <Button variant="outline" size="sm" disabled={!taskId}>
                    <BookText className="mr-2 h-4 w-4" />
                    {t("glossary.glossary")}
                </Button>
            </SheetTrigger>
            <SheetContent className="w-[400px] sm:w-[540px] flex flex-col h-full bg-white dark:bg-slate-950">
                <SheetHeader>
                    <SheetTitle className="flex items-center gap-2">
                        <BookText className="h-5 w-5" />
                        {t("glossary.glossary_2")}
                    </SheetTitle>
                    <SheetDescription>
                        {t("glossary.technical_terms_extracted_from_and_used_in_this_document")}
                    </SheetDescription>
                </SheetHeader>

                <div className="flex-1 overflow-hidden mt-6 border rounded-md">
                    {loading ? (
                        <div className="p-4 space-y-4">
                            {[1, 2, 3, 4, 5].map((item) => (
                                <div key={item} className="flex gap-4">
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
                            <p>{t("glossary.no_glossary_data_found")}</p>
                            <p className="text-xs mt-1 opacity-70">{t("glossary.make_sure_generate_glossary_was_enabled_during_translation")}</p>
                        </div>
                    ) : (
                        <ScrollArea className="h-full">
                            <div className="w-full text-sm">
                                <div className="sticky top-0 bg-slate-100 dark:bg-slate-900 border-b flex font-medium text-muted-foreground z-10">
                                    <div className="flex-1 p-3 border-r">{t("glossary.source")}</div>
                                    <div className="flex-1 p-3">{t("glossary.translation")}</div>
                                </div>
                                <div className="divide-y">
                                    {data.map((pair, index) => (
                                        <div
                                            key={`${pair.source}-${pair.target}-${index}`}
                                            className="flex hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors"
                                        >
                                            <div className="flex-1 p-3 border-r wrap-break-words font-medium text-slate-700 dark:text-slate-300">
                                                {pair.source}
                                            </div>
                                            <div className="flex-1 p-3 wrap-break-words text-slate-600 dark:text-slate-400">
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
                        {t("glossary.download_glossary_csv")}
                    </Button>
                </div>
            </SheetContent>
        </Sheet>
    )
}
