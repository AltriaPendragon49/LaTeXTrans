import { useCallback, useEffect, useState } from "react"
import { AlertCircle, BookText, Download } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/ui/button/Button"
import { API_BASE_URL } from "@/api-base"
import { ScrollArea } from "@/ui/primitives/scroll-area"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/ui/primitives/sheet"
import { Skeleton } from "@/ui/primitives/skeleton"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHeader,
  DataTableHeaderCell,
  DataTableHeaderRow,
  DataTableRow,
} from "@/ui/data-table/DataTable"

interface TermPair {
  source: string
  target: string
}

interface TerminologyTableProps {
  taskId: string | null
}

function parseCSV(text: string): TermPair[] {
  const lines = text.split("\n")
  const pairs: TermPair[] = []
  const startIndex = lines[0]?.toLowerCase().includes("source term") ? 1 : 0

  for (let index = startIndex; index < lines.length; index += 1) {
    const line = lines[index].trim()
    if (!line) {
      continue
    }

    const parts = line.split(",")
    if (parts.length < 2) {
      continue
    }

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
    if (!taskId || !downloadUrl) {
      return
    }

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

  function handleDownload() {
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
      <SheetContent className="flex h-full w-[400px] flex-col bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-ink)] sm:w-[540px]">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <BookText className="h-5 w-5" />
            {t("glossary.glossary_2")}
          </SheetTitle>
          <SheetDescription>
            {t("glossary.technical_terms_extracted_from_and_used_in_this_document")}
          </SheetDescription>
        </SheetHeader>

        <DataTable className="mt-6 flex-1 rounded-[20px] shadow-none">
          {loading ? (
            <div className="space-y-4 p-4">
              {[1, 2, 3, 4, 5].map((item) => (
                <div key={item} className="flex gap-4">
                  <Skeleton className="h-4 w-1/3" />
                  <Skeleton className="h-4 w-2/3" />
                </div>
              ))}
            </div>
          ) : error ? (
            <div className="p-4">
              <NoticeBanner
                tone="danger"
                icon={<AlertCircle className="h-4 w-4" />}
                title={t("glossary.failed_to_load_glossary")}
                description={error}
                className="rounded-[18px]"
              />
            </div>
          ) : data.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center p-6 text-center text-[color:var(--px-shell-muted)]">
              <BookText className="mb-2 h-10 w-10 opacity-25" />
              <p>{t("glossary.no_glossary_data_found")}</p>
              <p className="mt-1 text-xs opacity-70">
                {t("glossary.make_sure_generate_glossary_was_enabled_during_translation")}
              </p>
            </div>
          ) : (
            <ScrollArea className="h-full">
              <div className="w-full text-sm">
                <DataTableHeader className="sticky top-0 z-10">
                  <DataTableHeaderRow className="grid-cols-2 gap-0 px-0 py-0">
                    <DataTableHeaderCell className="border-r border-[color:var(--px-shell-line)] p-3 text-left normal-case tracking-normal">
                      {t("glossary.source")}
                    </DataTableHeaderCell>
                    <DataTableHeaderCell className="p-3 text-left normal-case tracking-normal">
                      {t("glossary.translation")}
                    </DataTableHeaderCell>
                  </DataTableHeaderRow>
                </DataTableHeader>
                <DataTableBody className="divide-y divide-[color:var(--px-shell-line)]">
                  {data.map((pair, index) => (
                    <DataTableRow
                      key={`${pair.source}-${pair.target}-${index}`}
                      className="grid-cols-2 gap-0 px-0 py-0 transition-colors hover:bg-[color:var(--px-shell-panel-strong)]"
                    >
                      <DataTableCell className="wrap-break-words border-r border-[color:var(--px-shell-line)] p-3 font-medium text-[color:var(--px-shell-ink)]">
                        {pair.source}
                      </DataTableCell>
                      <DataTableCell className="wrap-break-words p-3 text-[color:var(--px-shell-muted)]">
                        {pair.target}
                      </DataTableCell>
                    </DataTableRow>
                  ))}
                </DataTableBody>
              </div>
            </ScrollArea>
          )}
        </DataTable>

        <div className="mt-6 flex justify-end">
          <Button onClick={handleDownload} disabled={!downloadUrl || loading || data.length === 0} className="w-full sm:w-auto">
            <Download className="mr-2 h-4 w-4" />
            {t("glossary.download_glossary_csv")}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}
