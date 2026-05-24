import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import {
  CheckCircle2,
  FileEdit,
  Loader2,
  Plus,
  Search,
  Trash2,
  Upload,
  XCircle,
} from "lucide-react"

import { Button } from "@/ui/button/Button"
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
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/ui/primitives/select"

import type { TerminologyTerm } from "@/features/rag-terminology/types"
import {
  approveTerm,
  listPendingTerms,
  listTerms,
  rejectTerm,
  uploadTerminologyFile,
  createTerm,
  updateTerm,
  deleteTerm,
} from "@/features/rag-terminology/services/rag-terminology-api"
import type { ListTermsParams } from "@/features/rag-terminology/services/rag-terminology-api"
import { TermFormModal } from "@/features/rag-terminology/components/TermFormModal"
import type { TermFormData } from "@/features/rag-terminology/types"
import { useDomains } from "@/features/rag-terminology/hooks/useDomains"

const PAGE_SIZE = 20

const SOURCE_TYPE_LABELS: Record<string, { tone: "muted" | "accent" | "info" | "success" | "warning" | "danger"; label: string }> = {
  system: { tone: "accent", label: "System" },
  user: { tone: "info", label: "User" },
  imported: { tone: "warning", label: "Imported" },
  auto_extracted: { tone: "muted", label: "Auto" },
  manual: { tone: "info", label: "Manual" },
  bibtex_imported: { tone: "warning", label: "BibTeX" },
  shared_by_user: { tone: "info", label: "Shared" },
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

  // Tab state
  const [activeTab, setActiveTab] = useState("terms")

  // Pending terms tab
  const [pendingTerms, setPendingTerms] = useState<TerminologyTerm[]>([])
  const [pendingTotal, setPendingTotal] = useState(0)
  const [pendingPage, setPendingPage] = useState(1)
  const [isLoadingPending, setIsLoadingPending] = useState(false)
  const [pendingLoadError, setPendingLoadError] = useState<string | null>(null)

  // All terms tab
  const [allTerms, setAllTerms] = useState<TerminologyTerm[]>([])
  const [allTotal, setAllTotal] = useState(0)
  const [allPage, setAllPage] = useState(1)
  const [isLoadingAll, setIsLoadingAll] = useState(false)
  const [allLoadError, setAllLoadError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState("")
  const [domainFilter, setDomainFilter] = useState("")

  // Insert a state to track which term is being edited
  const [editingTerm, setEditingTerm] = useState<TerminologyTerm | null>(null)

  // Create/Edit dialog
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [editDialogOpen, setEditDialogOpen] = useState(false)

  // Upload state
  const [isUploading, setIsUploading] = useState(false)
  const [isDragActive, setIsDragActive] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  // Action loading
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null)

  // Dynamic domains from API
  const { domains, groups } = useDomains()

  // Pending terms filters
  const [pendingDomainFilter, setPendingDomainFilter] = useState("")

  const pendingTotalPages = Math.max(1, Math.ceil(pendingTotal / PAGE_SIZE))
  const allTotalPages = Math.max(1, Math.ceil(allTotal / PAGE_SIZE))

  // ---- Load pending terms ----
  const loadPendingTerms = useCallback(async () => {
    setIsLoadingPending(true)
    setPendingLoadError(null)
    try {
      const params: ListTermsParams = { page: pendingPage, page_size: PAGE_SIZE }
      if (pendingDomainFilter) params.domain = pendingDomainFilter
      const response = await listPendingTerms(params)
      setPendingTerms(response.terms)
      setPendingTotal(response.total)
    } catch {
      setPendingLoadError(t("ragTerminology.reviewPanel.error"))
    } finally {
      setIsLoadingPending(false)
    }
  }, [pendingPage, pendingDomainFilter, t])

  useEffect(() => {
    if (activeTab === "terms") loadPendingTerms()
  }, [loadPendingTerms, activeTab])

  // ---- Load all terms ----
  const loadAllTerms = useCallback(async () => {
    setIsLoadingAll(true)
    setAllLoadError(null)
    try {
      const params: ListTermsParams = { page: allPage, page_size: PAGE_SIZE }
      if (statusFilter) params.status = statusFilter
      if (domainFilter) params.domain = domainFilter
      const response = await listTerms(params)
      setAllTerms(response.terms)
      setAllTotal(response.total)
    } catch {
      setAllLoadError(t("ragTerminology.reviewPanel.error"))
    } finally {
      setIsLoadingAll(false)
    }
  }, [allPage, statusFilter, domainFilter, t])

  useEffect(() => {
    if (activeTab === "allTerms") loadAllTerms()
  }, [loadAllTerms, activeTab])

  // ---- Actions ----
  async function handleApprove(termId: string) {
    setActionLoadingId(termId)
    try {
      await approveTerm(termId)
      toast.success(t("ragTerminology.reviewPanel.approveSuccess"))
      setPendingTerms((prev) => prev.filter((term) => term.id !== termId))
      setPendingTotal((prev) => prev - 1)
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
      setPendingTerms((prev) => prev.filter((term) => term.id !== termId))
      setPendingTotal((prev) => prev - 1)
    } catch {
      toast.error(t("ragTerminology.reviewPanel.rejectError"))
    } finally {
      setActionLoadingId(null)
    }
  }

  async function handleCreate(data: TermFormData) {
    try {
      await createTerm({
        source_term: data.source_term,
        target_term: data.target_term,
        source_lang: data.source_lang,
        target_lang: data.target_lang,
        domain: data.domain,
        source_type: "manual",
        status: "approved",
      })
      toast.success(t("ragTerminology.createSuccess"))
      if (activeTab === "allTerms") loadAllTerms()
    } catch {
      toast.error(t("ragTerminology.createError"))
    }
  }

  async function handleEdit(data: TermFormData) {
    if (!editingTerm) return
    try {
      await updateTerm(editingTerm.id, {
        source_term: data.source_term,
        target_term: data.target_term,
        source_lang: data.source_lang,
        target_lang: data.target_lang,
        domain: data.domain,
      })
      toast.success(t("ragTerminology.editSuccess"))
      setEditingTerm(null)
      if (activeTab === "allTerms") loadAllTerms()
    } catch {
      toast.error(t("ragTerminology.editError"))
    }
  }

  async function handleDelete(termId: string) {
    if (!window.confirm(t("ragTerminology.deleteConfirm"))) return
    setActionLoadingId(termId)
    try {
      await deleteTerm(termId)
      toast.success(t("ragTerminology.deleteSuccess"))
      setAllTerms((prev) => prev.filter((term) => term.id !== termId))
      setAllTotal((prev) => prev - 1)
    } catch {
      toast.error(t("ragTerminology.deleteError"))
    } finally {
      setActionLoadingId(null)
    }
  }

  // ---- Upload ----
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
      toast.success(t("ragTerminology.upload.success", { accepted: result.accepted, rejected: result.rejected }))
      if (activeTab === "terms") loadPendingTerms()
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
    if (file) handleUploadFile(file)
  }

  function handleFileSelect(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (file) handleUploadFile(file)
    event.target.value = ""
  }

  // ---- Render pending terms table ----
  function renderPendingTable() {
    if (isLoadingPending) {
      return (
        <div className="flex flex-col items-center justify-center py-14 text-[color:var(--px-shell-muted)]">
          <Loader2 className="h-6 w-6 animate-spin" />
          <p className="mt-3 text-sm">{t("ragTerminology.reviewPanel.loading")}</p>
        </div>
      )
    }
    if (pendingLoadError) {
      return (
        <NoticeBanner
          tone="danger"
          icon={<XCircle className="h-4 w-4" />}
          description={pendingLoadError}
          action={
            <Button variant="ghost" size="sm" onClick={loadPendingTerms}>
              {t("common.actions.retry")}
            </Button>
          }
        />
      )
    }
    if (pendingTerms.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center py-14 text-[color:var(--px-shell-muted)]">
          <Search className="h-7 w-7" />
          <p className="mt-3 text-sm">{t("ragTerminology.reviewPanel.empty")}</p>
        </div>
      )
    }
    return (
      <>
        <DataTable>
          <DataTableHeader>
            <DataTableHeaderRow className="grid-cols-[1fr_1fr_100px_100px_100px_120px_140px]">
              <DataTableHeaderCell>{t("ragTerminology.reviewPanel.table.sourceTerm")}</DataTableHeaderCell>
              <DataTableHeaderCell>{t("ragTerminology.reviewPanel.table.targetTerm")}</DataTableHeaderCell>
              <DataTableHeaderCell>{t("ragTerminology.reviewPanel.table.sourceType")}</DataTableHeaderCell>
              <DataTableHeaderCell>{t("ragTerminology.reviewPanel.table.domain")}</DataTableHeaderCell>
              <DataTableHeaderCell>{t("ragTerminology.reviewPanel.table.status")}</DataTableHeaderCell>
              <DataTableHeaderCell>{t("ragTerminology.reviewPanel.table.createdAt")}</DataTableHeaderCell>
              <DataTableHeaderCell className="text-right">{t("ragTerminology.reviewPanel.table.actions")}</DataTableHeaderCell>
            </DataTableHeaderRow>
          </DataTableHeader>
          <DataTableBody>
            {pendingTerms.map((term) => {
              const sourceTypeStyle = SOURCE_TYPE_LABELS[term.source_type] ?? { tone: "muted" as const, label: term.source_type }
              const statusStyle = STATUS_LABELS[term.status] ?? { tone: "muted" as const, label: term.status }
              const isActionLoading = actionLoadingId === term.id
              return (
                <DataTableRow key={term.id} className="grid-cols-[1fr_1fr_100px_100px_100px_120px_140px] items-center">
                  <DataTableCell className="truncate font-medium text-[color:var(--px-shell-ink)]">{term.source_term}</DataTableCell>
                  <DataTableCell className="truncate text-[color:var(--px-shell-muted)]">{term.target_term}</DataTableCell>
                  <DataTableCell>
                    <StatusBadge tone={sourceTypeStyle.tone} size="sm">{sourceTypeStyle.label}</StatusBadge>
                  </DataTableCell>
                  <DataTableCell className="truncate text-sm text-[color:var(--px-shell-muted)]">{term.domain || "-"}</DataTableCell>
                  <DataTableCell>
                    <StatusBadge tone={statusStyle.tone} size="sm">{statusStyle.label}</StatusBadge>
                  </DataTableCell>
                  <DataTableCell className="text-xs text-[color:var(--px-shell-muted)]">{formatDate(term.created_at)}</DataTableCell>
                  <DataTableCell className="flex justify-end gap-2">
                    <Button variant="ghost" size="sm" onClick={() => handleApprove(term.id)} disabled={isActionLoading}>
                      {isActionLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5 text-[color:var(--px-shell-success)]" />}
                      <span className="ml-1">{t("ragTerminology.reviewPanel.approve")}</span>
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleReject(term.id)} disabled={isActionLoading}>
                      <XCircle className="h-3.5 w-3.5 text-[color:var(--px-shell-danger)]" />
                      <span className="ml-1">{t("ragTerminology.reviewPanel.reject")}</span>
                    </Button>
                  </DataTableCell>
                </DataTableRow>
              )
            })}
          </DataTableBody>
        </DataTable>
        {pendingTotalPages > 1 && (
          <div className="flex items-center justify-between pt-2">
            <p className="text-xs text-[color:var(--px-shell-muted)]">
              {t("ragTerminology.pagination.pageInfo", { current: pendingPage, total: pendingTotalPages })}
            </p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => setPendingPage((p) => Math.max(1, p - 1))} disabled={pendingPage <= 1}>
                {t("ragTerminology.pagination.previous")}
              </Button>
              <Button variant="outline" size="sm" onClick={() => setPendingPage((p) => Math.min(pendingTotalPages, p + 1))} disabled={pendingPage >= pendingTotalPages}>
                {t("ragTerminology.pagination.next")}
              </Button>
            </div>
          </div>
        )}
      </>
    )
  }

  // ---- Render all terms table ----
  function renderAllTermsTable() {
    return (
      <>
        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <Label className="text-sm whitespace-nowrap">{t("ragTerminology.filters.status")}</Label>
            <Select value={statusFilter || "__all__"} onValueChange={(v) => { setStatusFilter(v === "__all__" ? "" : v); setAllPage(1) }}>
              <SelectTrigger className="w-36">
                <SelectValue placeholder={t("ragTerminology.filters.all")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">{t("ragTerminology.filters.all")}</SelectItem>
                <SelectItem value="pending_review">Pending</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
                <SelectItem value="rejected">Rejected</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <Label className="text-sm whitespace-nowrap">{t("ragTerminology.filters.domain")}</Label>
            <Select value={domainFilter || "__all__"} onValueChange={(v) => { setDomainFilter(v === "__all__" ? "" : v); setAllPage(1) }}>
              <SelectTrigger className="w-44">
                <SelectValue placeholder={t("ragTerminology.filters.all")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">{t("ragTerminology.filters.all")}</SelectItem>
                {domains.map((d) => <SelectItem key={d.value} value={d.value}>{d.label_zh || d.value}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <Button variant="outline" size="sm" onClick={() => { setStatusFilter(""); setDomainFilter(""); setAllPage(1) }}>
            {t("ragTerminology.filters.clear")}
          </Button>
          <div className="flex-1" />
          <Button size="sm" onClick={() => setCreateDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-1" />
            {t("ragTerminology.create")}
          </Button>
        </div>

        {isLoadingAll ? (
          <div className="flex flex-col items-center justify-center py-14 text-[color:var(--px-shell-muted)]">
            <Loader2 className="h-6 w-6 animate-spin" />
            <p className="mt-3 text-sm">{t("ragTerminology.reviewPanel.loading")}</p>
          </div>
        ) : allLoadError ? (
          <NoticeBanner tone="danger" icon={<XCircle className="h-4 w-4" />} description={allLoadError}
            action={<Button variant="ghost" size="sm" onClick={loadAllTerms}>{t("common.actions.retry")}</Button>}
          />
        ) : allTerms.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-14 text-[color:var(--px-shell-muted)]">
            <Search className="h-7 w-7" />
            <p className="mt-3 text-sm">{t("ragTerminology.reviewPanel.empty")}</p>
          </div>
        ) : (
          <>
            <DataTable>
              <DataTableHeader>
                <DataTableHeaderRow className="grid-cols-[1fr_1fr_100px_100px_90px_100px_100px]">
                  <DataTableHeaderCell>{t("ragTerminology.reviewPanel.table.sourceTerm")}</DataTableHeaderCell>
                  <DataTableHeaderCell>{t("ragTerminology.reviewPanel.table.targetTerm")}</DataTableHeaderCell>
                  <DataTableHeaderCell>{t("ragTerminology.reviewPanel.table.sourceType")}</DataTableHeaderCell>
                  <DataTableHeaderCell>{t("ragTerminology.reviewPanel.table.domain")}</DataTableHeaderCell>
                  <DataTableHeaderCell>{t("ragTerminology.reviewPanel.table.status")}</DataTableHeaderCell>
                  <DataTableHeaderCell>{t("ragTerminology.reviewPanel.table.createdAt")}</DataTableHeaderCell>
                  <DataTableHeaderCell className="text-right">{t("ragTerminology.reviewPanel.table.actions")}</DataTableHeaderCell>
                </DataTableHeaderRow>
              </DataTableHeader>
              <DataTableBody>
                {allTerms.map((term) => {
                  const sourceTypeStyle = SOURCE_TYPE_LABELS[term.source_type] ?? { tone: "muted" as const, label: term.source_type }
                  const statusStyle = STATUS_LABELS[term.status] ?? { tone: "muted" as const, label: term.status }
                  const isActionLoading = actionLoadingId === term.id
                  const isApproved = term.status === "approved"
                  const allowEditDelete = ["manual", "system"].includes(term.source_type) || term.status === "pending_review"
                  return (
                    <DataTableRow key={term.id} className="grid-cols-[1fr_1fr_100px_100px_90px_100px_100px] items-center">
                      <DataTableCell className="truncate font-medium text-[color:var(--px-shell-ink)]">{term.source_term}</DataTableCell>
                      <DataTableCell className="truncate text-[color:var(--px-shell-muted)]">{term.target_term}</DataTableCell>
                      <DataTableCell>
                        <StatusBadge tone={sourceTypeStyle.tone} size="sm">{sourceTypeStyle.label}</StatusBadge>
                      </DataTableCell>
                      <DataTableCell className="truncate text-sm text-[color:var(--px-shell-muted)]">{term.domain || "-"}</DataTableCell>
                      <DataTableCell>
                        <StatusBadge tone={statusStyle.tone} size="sm">{statusStyle.label}</StatusBadge>
                      </DataTableCell>
                      <DataTableCell className="text-xs text-[color:var(--px-shell-muted)]">{formatDate(term.created_at)}</DataTableCell>
                      <DataTableCell className="flex justify-end gap-1">
                        {allowEditDelete && (
                          <>
                            <Button variant="ghost" size="sm" onClick={() => { setEditingTerm(term); setEditDialogOpen(true) }} title={t("common.actions.edit")}>
                              <FileEdit className="h-3.5 w-3.5" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleDelete(term.id)} disabled={isActionLoading} title={t("common.actions.delete")}>
                              <Trash2 className="h-3.5 w-3.5 text-[color:var(--px-shell-danger)]" />
                            </Button>
                          </>
                        )}
                        {!isApproved && term.status === "pending_review" && (
                          <>
                            <Button variant="ghost" size="sm" onClick={() => handleApprove(term.id)} disabled={isActionLoading}>
                              <CheckCircle2 className="h-3.5 w-3.5 text-[color:var(--px-shell-success)]" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleReject(term.id)} disabled={isActionLoading}>
                              <XCircle className="h-3.5 w-3.5 text-[color:var(--px-shell-danger)]" />
                            </Button>
                          </>
                        )}
                      </DataTableCell>
                    </DataTableRow>
                  )
                })}
              </DataTableBody>
            </DataTable>
            {allTotalPages > 1 && (
              <div className="flex items-center justify-between pt-2">
                <p className="text-xs text-[color:var(--px-shell-muted)]">
                  {t("ragTerminology.pagination.pageInfo", { current: allPage, total: allTotalPages })}
                </p>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setAllPage((p) => Math.max(1, p - 1))} disabled={allPage <= 1}>
                    {t("ragTerminology.pagination.previous")}
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => setAllPage((p) => Math.min(allTotalPages, p + 1))} disabled={allPage >= allTotalPages}>
                    {t("ragTerminology.pagination.next")}
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </>
    )
  }

  // ---- Render upload tab ----
  function renderUploadTab() {
    return (
      <div className="space-y-6">
        <div className="space-y-2">
          <Label>{t("ragTerminology.upload.title")}</Label>
          <p className="text-sm text-[color:var(--px-shell-muted)]">{t("ragTerminology.upload.description")}</p>
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
          <input ref={inputRef} type="file" accept=".csv,.bib" className="hidden" onChange={handleFileSelect} />
          {isUploading ? (
            <>
              <Loader2 className="h-8 w-8 animate-spin text-[color:var(--px-shell-accent)]" />
              <p className="mt-4 text-sm font-medium text-[color:var(--px-shell-ink)]">{t("ragTerminology.upload.uploading")}</p>
            </>
          ) : (
            <>
              <Upload className="h-8 w-8 text-[color:var(--px-shell-muted)]" />
              <p className="mt-4 text-sm font-medium text-[color:var(--px-shell-ink)]">{t("ragTerminology.upload.dragAndDrop")}</p>
              <p className="mt-2 text-xs text-[color:var(--px-shell-muted)]">{t("ragTerminology.upload.supportedFormats")}</p>
            </>
          )}
        </div>
      </div>
    )
  }

  return (
    <PanelShell className="space-y-6 p-4 sm:p-6">
      <TermFormModal
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        onSave={handleCreate}
        title={t("ragTerminology.dialog.createTitle")}
        domainOptions={domains}
        domainGroups={groups}
      />
      <TermFormModal
        open={editDialogOpen}
        onClose={() => { setEditDialogOpen(false); setEditingTerm(null) }}
        onSave={handleEdit}
        initial={editingTerm ? {
          source_term: editingTerm.source_term,
          target_term: editingTerm.target_term,
          source_lang: editingTerm.source_lang,
          target_lang: editingTerm.target_lang,
          domain: editingTerm.domain,
        } : undefined}
        title={t("ragTerminology.dialog.editTitle")}
        domainOptions={domains}
        domainGroups={groups}
      />

      <EditorialTabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <div className="flex justify-start">
          <EditorialTabsList className="gap-1">
            <EditorialTabsTrigger value="terms">
              {t("ragTerminology.reviewPanel.termsTab")}
            </EditorialTabsTrigger>
            <EditorialTabsTrigger value="allTerms">
              {t("ragTerminology.reviewPanel.allTermsTab")}
            </EditorialTabsTrigger>
            <EditorialTabsTrigger value="upload">
              {t("ragTerminology.reviewPanel.uploadTab")}
            </EditorialTabsTrigger>
          </EditorialTabsList>
        </div>

        <TabsContent value="terms" className="mt-0 space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <Label className="text-sm whitespace-nowrap">{t("ragTerminology.filters.domain")}</Label>
              <Select value={pendingDomainFilter || "__all__"} onValueChange={(v) => { setPendingDomainFilter(v === "__all__" ? "" : v); setPendingPage(1) }}>
                <SelectTrigger className="w-44">
                  <SelectValue placeholder={t("ragTerminology.filters.all")} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">{t("ragTerminology.filters.all")}</SelectItem>
                  {domains.map((d) => (
                    <SelectItem key={d.value} value={d.value}>{d.label_zh || d.value}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {pendingDomainFilter && (
              <Button variant="outline" size="sm" onClick={() => { setPendingDomainFilter(""); setPendingPage(1) }}>
                {t("ragTerminology.filters.clear")}
              </Button>
            )}
          </div>
          {renderPendingTable()}
        </TabsContent>

        <TabsContent value="allTerms" className="mt-0 space-y-4">
          {renderAllTermsTable()}
        </TabsContent>

        <TabsContent value="upload" className="mt-0 space-y-4">
          {renderUploadTab()}
        </TabsContent>
      </EditorialTabs>
    </PanelShell>
  )
}
