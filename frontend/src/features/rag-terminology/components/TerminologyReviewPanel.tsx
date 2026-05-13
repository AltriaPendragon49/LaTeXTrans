import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import {
  CheckCircle2,
  FileText,
  Loader2,
  Search,
  Upload,
  XCircle,
} from "lucide-react"

import { Button } from "@/ui/button/Button"
import { Input } from "@/ui/input/Input"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { PanelShell } from "@/ui/panel-shell/PanelShell"
import { StatusBadge } from "@/ui/status-badge/StatusBadge"
import { TabsContent } from "@/ui/primitives/tabs"
import { EditorialTabs, EditorialTabsList, EditorialTabsTrigger } from "@/ui/tabs/EditorialTabs"
import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHeader,
  DataTableHeaderCell,
  DataTableHeaderRow,
  DataTableRow,
} from "@/ui/data-table/DataTable"
import { Label } from "@/ui/primitives/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/ui/primitives/select"

import type { TerminologyTerm } from "@/features/rag-terminology/types"
import {
  approveTerm,
  listPendingTerms,
  rejectTerm,
  uploadTerminologyFile,
} from "@/features/rag-terminology/services/rag-terminology-api"

const PAGE_SIZE = 20

const SOURCE_TYPE_LABELS: Record<string, { tone: "muted" | "accent" | "info" | "success" | "warning" | "danger"; label: string }> = {
  system: { tone: "accent", label: "System" },
  user: { tone: "info", label: "User" },
  imported: { tone: "warning", label: "Imported" },
  auto_extracted: { tone: "muted", label: "Auto" },
}

const STATUS_LABELS: Record<string, { tone: "muted" | "accent" | "info" | "success" | "warning" | "danger"; label: string }> = {
  pending_review: { tone: "warning", label: "Pending" },
  approved: { tone: "success", label: "Approved" },
  rejected: { tone: "danger", label: "Rejected" },
}

function formatDate(dateString: string): string {
  try {
    const date = new Date(dateString)
    return date.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    })
  } catch {
    return dateString
  }
}

export function TerminologyReviewPanel() {
  const { t } = useTranslation()

  const [activeTab, setActiveTab] = useState("terms")
  const [terms, setTerms] = useState<TerminologyTerm[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [isLoading, setIsLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null)

  // Upload state
  const [isUploading, setIsUploading] = useState(false)
  const [isDragActive, setIsDragActive] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const loadTerms = useCallback(async () => {
    setIsLoading(true)
    setLoadError(null)
    try {
      const response = await listPendingTerms({
        page,
        page_size: PAGE_SIZE,
      })
      setTerms(response.terms)
      setTotal(response.total)
    } catch {
      setLoadError(t("ragTerminology.reviewPanel.error"))
    } finally {
      setIsLoading(false)
    }
  }, [page, t])

  useEffect(() => {
    loadTerms()
  }, [loadTerms])

  async function handleApprove(termId: string) {
    setActionLoadingId(termId)
    try {
      await approveTerm(termId)
      toast.success(t("ragTerminology.reviewPanel.approveSuccess"))
      setTerms((prev) => prev.filter((term) => term.id !== termId))
      setTotal((prev) => prev - 1)
    } catch {
      toast.error(t("ragTerminology.reviewPanel.approveError"))
    } finally {
      setActionLoadingId(null)
    }
  }

  async function handleReject(termId: string) {
    setActionLoadingId(termId)
    try {
      await rejectTerm(termId)
      toast.success(t("ragTerminology.reviewPanel.rejectSuccess"))
      setTerms((prev) => prev.filter((term) => term.id !== termId))
      setTotal((prev) => prev - 1)
    } catch {
      toast.error(t("ragTerminology.reviewPanel.rejectError"))
    } finally {
      setActionLoadingId(null)
    }
  }

  function handleDrag(event: React.DragEvent) {
    event.preventDefault()
    event.stopPropagation()
    if (event.type === "dragenter" || event.type === "dragover") {
      setIsDragActive(true)
    } else if (event.type === "dragleave") {
      setIsDragActive(false)
    }
  }

  async function handleUploadFile(file: File) {
    const validExtensions = [".csv", ".bib"]
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase()

    if (!validExtensions.includes(ext)) {
      toast.error(t("ragTerminology.upload.supportedFormats"))
      return
    }

    setIsUploading(true)
    try {
      const result = await uploadTerminologyFile(file)
      toast.success(
        t("ragTerminology.upload.success", {
          accepted: result.accepted,
          rejected: result.rejected,
        }),
      )
      // Refresh pending terms after upload
      loadTerms()
    } catch {
      toast.error(t("ragTerminology.upload.error"))
    } finally {
      setIsUploading(false)
    }
  }

  function handleDrop(event: React.DragEvent) {
    event.preventDefault()
    event.stopPropagation()
    setIsDragActive(false)

    const file = event.dataTransfer.files[0]
    if (file) {
      handleUploadFile(file)
    }
  }

  function handleFileSelect(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (file) {
      handleUploadFile(file)
    }
    // Reset input value so the same file can be uploaded again
    event.target.value = ""
  }

  return (
    <PanelShell className="space-y-6 p-4 sm:p-6">
      <EditorialTabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <div className="flex justify-start">
          <EditorialTabsList className="gap-1">
            <EditorialTabsTrigger value="terms">
              {t("ragTerminology.reviewPanel.termsTab")}
            </EditorialTabsTrigger>
            <EditorialTabsTrigger value="upload">
              {t("ragTerminology.reviewPanel.uploadTab")}
            </EditorialTabsTrigger>
          </EditorialTabsList>
        </div>

        <TabsContent value="terms" className="mt-0 space-y-4">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-14 text-[color:var(--px-shell-muted)]">
              <Loader2 className="h-6 w-6 animate-spin" />
              <p className="mt-3 text-sm">{t("ragTerminology.reviewPanel.loading")}</p>
            </div>
          ) : loadError ? (
            <NoticeBanner
              tone="danger"
              icon={<XCircle className="h-4 w-4" />}
              description={loadError}
              action={
                <Button variant="ghost" size="sm" onClick={loadTerms}>
                  {t("common.actions.retry")}
                </Button>
              }
            />
          ) : terms.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-14 text-[color:var(--px-shell-muted)]">
              <Search className="h-7 w-7" />
              <p className="mt-3 text-sm">{t("ragTerminology.reviewPanel.empty")}</p>
            </div>
          ) : (
            <>
              <DataTable>
                <DataTableHeader>
                  <DataTableHeaderRow className="grid-cols-[1fr_1fr_100px_100px_100px_120px_140px]">
                    <DataTableHeaderCell>
                      {t("ragTerminology.reviewPanel.table.sourceTerm")}
                    </DataTableHeaderCell>
                    <DataTableHeaderCell>
                      {t("ragTerminology.reviewPanel.table.targetTerm")}
                    </DataTableHeaderCell>
                    <DataTableHeaderCell>
                      {t("ragTerminology.reviewPanel.table.sourceType")}
                    </DataTableHeaderCell>
                    <DataTableHeaderCell>
                      {t("ragTerminology.reviewPanel.table.domain")}
                    </DataTableHeaderCell>
                    <DataTableHeaderCell>
                      {t("ragTerminology.reviewPanel.table.status")}
                    </DataTableHeaderCell>
                    <DataTableHeaderCell>
                      {t("ragTerminology.reviewPanel.table.createdAt")}
                    </DataTableHeaderCell>
                    <DataTableHeaderCell className="text-right">
                      {t("ragTerminology.reviewPanel.table.actions")}
                    </DataTableHeaderCell>
                  </DataTableHeaderRow>
                </DataTableHeader>

                <DataTableBody>
                  {terms.map((term) => {
                    const sourceTypeStyle = SOURCE_TYPE_LABELS[term.source_type] ?? { tone: "muted" as const, label: term.source_type }
                    const statusStyle = STATUS_LABELS[term.status] ?? { tone: "muted" as const, label: term.status }
                    const isActionLoading = actionLoadingId === term.id

                    return (
                      <DataTableRow
                        key={term.id}
                        className="grid-cols-[1fr_1fr_100px_100px_100px_120px_140px] items-center"
                      >
                        <DataTableCell className="truncate font-medium text-[color:var(--px-shell-ink)]">
                          {term.source_term}
                        </DataTableCell>
                        <DataTableCell className="truncate text-[color:var(--px-shell-muted)]">
                          {term.target_term}
                        </DataTableCell>
                        <DataTableCell>
                          <StatusBadge tone={sourceTypeStyle.tone} size="sm">
                            {sourceTypeStyle.label}
                          </StatusBadge>
                        </DataTableCell>
                        <DataTableCell className="truncate text-sm text-[color:var(--px-shell-muted)]">
                          {term.domain || "-"}
                        </DataTableCell>
                        <DataTableCell>
                          <StatusBadge tone={statusStyle.tone} size="sm">
                            {statusStyle.label}
                          </StatusBadge>
                        </DataTableCell>
                        <DataTableCell className="text-xs text-[color:var(--px-shell-muted)]">
                          {formatDate(term.created_at)}
                        </DataTableCell>
                        <DataTableCell className="flex justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleApprove(term.id)}
                            disabled={isActionLoading}
                          >
                            {isActionLoading ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <CheckCircle2 className="h-3.5 w-3.5 text-[color:var(--px-shell-success)]" />
                            )}
                            <span className="ml-1">{t("ragTerminology.reviewPanel.approve")}</span>
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleReject(term.id)}
                            disabled={isActionLoading}
                          >
                            <XCircle className="h-3.5 w-3.5 text-[color:var(--px-shell-danger)]" />
                            <span className="ml-1">{t("ragTerminology.reviewPanel.reject")}</span>
                          </Button>
                        </DataTableCell>
                      </DataTableRow>
                    )
                  })}
                </DataTableBody>
              </DataTable>

              {/* Pagination */}
              {totalPages > 1 ? (
                <div className="flex items-center justify-between pt-2">
                  <p className="text-xs text-[color:var(--px-shell-muted)]">
                    {t("ragTerminology.pagination.pageInfo", {
                      current: page,
                      total: totalPages,
                    })}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page <= 1}
                    >
                      {t("ragTerminology.pagination.previous")}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      disabled={page >= totalPages}
                    >
                      {t("ragTerminology.pagination.next")}
                    </Button>
                  </div>
                </div>
              ) : null}
            </>
          )}
        </TabsContent>

        <TabsContent value="upload" className="mt-0 space-y-4">
          <div className="space-y-2">
            <Label>{t("ragTerminology.upload.title")}</Label>
            <p className="text-sm text-[color:var(--px-shell-muted)]">
              {t("ragTerminology.upload.description")}
            </p>
          </div>

          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={`flex cursor-pointer flex-col items-center justify-center rounded-[24px] border-2 border-dashed p-10 transition-colors ${
              isDragActive
                ? "border-[color:var(--px-shell-accent)] bg-[color:var(--px-shell-accent-soft)]"
                : "border-[color:var(--px-shell-line)] hover:border-[color:var(--px-shell-accent)]/30 hover:bg-[color:var(--px-shell-panel-strong)]"
            }`}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".csv,.bib"
              className="hidden"
              onChange={handleFileSelect}
            />
            {isUploading ? (
              <>
                <Loader2 className="h-8 w-8 animate-spin text-[color:var(--px-shell-accent)]" />
                <p className="mt-4 text-sm font-medium text-[color:var(--px-shell-ink)]">
                  {t("ragTerminology.upload.uploading")}
                </p>
              </>
            ) : (
              <>
                <Upload className="h-8 w-8 text-[color:var(--px-shell-muted)]" />
                <p className="mt-4 text-sm font-medium text-[color:var(--px-shell-ink)]">
                  {t("ragTerminology.upload.dragAndDrop")}
                </p>
                <p className="mt-2 text-xs text-[color:var(--px-shell-muted)]">
                  {t("ragTerminology.upload.supportedFormats")}
                </p>
              </>
            )}
          </div>
        </TabsContent>
      </EditorialTabs>
    </PanelShell>
  )
}
