import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import {
  BookOpenText,
  FileEdit,
  Loader2,
  Plus,
  Search,
  Trash2,
  XCircle,
} from "lucide-react"

import { Button } from "@/ui/button/Button"
import { PanelShell } from "@/ui/panel-shell/PanelShell"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { StatusBadge } from "@/ui/status-badge/StatusBadge"
import { Label } from "@/ui/primitives/label"
import { Input } from "@/ui/input/Input"
import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHeader,
  DataTableHeaderCell,
  DataTableHeaderRow,
  DataTableRow,
} from "@/ui/data-table/DataTable"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
  SelectGroup,
  SelectLabel,
} from "@/ui/primitives/select"

import type { TerminologyTerm } from "@/features/rag-terminology/types"
import {
  listTerms,
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

const LANGUAGE_OPTIONS = [
  { value: "en", label: "English" },
  { value: "zh", label: "中文" },
  { value: "ja", label: "日本語" },
  { value: "ko", label: "한국어" },
  { value: "fr", label: "Français" },
  { value: "de", label: "Deutsch" },
  { value: "ru", label: "Русский" },
  { value: "es", label: "Español" },
]

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

export function TerminologyBrowserPage() {
  const { t } = useTranslation()

  // Domain data
  const { domains, groups, isLoading: isDomainsLoading, error: domainsError } = useDomains()

  // Data state
  const [terms, setTerms] = useState<TerminologyTerm[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [isLoading, setIsLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  // Filters
  const [statusFilter, setStatusFilter] = useState("")
  const [domainFilter, setDomainFilter] = useState("")
  const [sourceLangFilter, setSourceLangFilter] = useState("")
  const [searchQuery, setSearchQuery] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")

  // Dialog state
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [editingTerm, setEditingTerm] = useState<TerminologyTerm | null>(null)
  const [editDialogOpen, setEditDialogOpen] = useState(false)

  // Action loading
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null)

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery)
      setPage(1)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery])

  // Load terms
  const loadTerms = useCallback(async () => {
    setIsLoading(true)
    setLoadError(null)
    try {
      const params: ListTermsParams = { page, page_size: PAGE_SIZE }
      if (statusFilter) params.status = statusFilter
      if (domainFilter) params.domain = domainFilter
      if (sourceLangFilter) params.source_lang = sourceLangFilter
      if (debouncedSearch) params.query = debouncedSearch
      const response = await listTerms(params)
      setTerms(response.terms)
      setTotal(response.total)
    } catch {
      setLoadError(t("ragTerminology.browser.loadError"))
    } finally {
      setIsLoading(false)
    }
  }, [page, statusFilter, domainFilter, sourceLangFilter, debouncedSearch, t])

  useEffect(() => {
    loadTerms()
  }, [loadTerms])

  // Reset page when filters change
  function handleFilterChange(setter: (v: string) => void, value: string) {
    setter(value)
    setPage(1)
  }

  // Create term
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
      loadTerms()
    } catch {
      toast.error(t("ragTerminology.createError"))
    }
  }

  // Edit term
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
      loadTerms()
    } catch {
      toast.error(t("ragTerminology.editError"))
    }
  }

  // Delete term
  async function handleDelete(termId: string) {
    if (!window.confirm(t("ragTerminology.deleteConfirm"))) return
    setActionLoadingId(termId)
    try {
      await deleteTerm(termId)
      toast.success(t("ragTerminology.deleteSuccess"))
      setTerms((prev) => prev.filter((term) => term.id !== termId))
      setTotal((prev) => prev - 1)
    } catch {
      toast.error(t("ragTerminology.deleteError"))
    } finally {
      setActionLoadingId(null)
    }
  }

  // Render domain filter options grouped
  function renderDomainFilterOptions() {
    if (isDomainsLoading || domainsError || groups == null || Object.keys(groups).length === 0) {
      return domains.map((d) => (
        <SelectItem key={d.value} value={d.value}>{d.label_zh || d.value}</SelectItem>
      ))
    }

    const ungrouped = domains.filter((d) => d.group == null)
    const groupedByGroup: Record<string, typeof domains> = {}
    for (const d of domains) {
      if (d.group) {
        if (!groupedByGroup[d.group]) groupedByGroup[d.group] = []
        groupedByGroup[d.group].push(d)
      }
    }

    return (
      <>
        {ungrouped.map((d) => (
          <SelectItem key={d.value} value={d.value}>{d.label_zh || d.value}</SelectItem>
        ))}
        {Object.entries(groupedByGroup).map(([groupKey, items]) => (
          <SelectGroup key={groupKey}>
            <SelectLabel>{groupKey}</SelectLabel>
            {items.map((d) => (
              <SelectItem key={d.value} value={d.value}>{d.label_zh || d.value}</SelectItem>
            ))}
          </SelectGroup>
        ))}
      </>
    )
  }

  return (
    <PanelShell className="space-y-6 p-4 sm:p-6">
      {/* Create dialog */}
      <TermFormModal
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        onSave={handleCreate}
        title={t("ragTerminology.dialog.createTitle")}
        showLanguageFields={true}
        domainOptions={domains}
        domainGroups={groups}
      />

      {/* Edit dialog */}
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
        showLanguageFields={true}
        domainOptions={domains}
        domainGroups={groups}
      />

      {/* Filters bar */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[color:var(--px-shell-muted)]" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t("ragTerminology.browser.searchPlaceholder")}
            className="pl-9"
          />
        </div>

        {/* Status filter */}
        <div className="flex items-center gap-2">
          <Label className="text-sm whitespace-nowrap">{t("ragTerminology.filters.status")}</Label>
          <Select value={statusFilter || "__all__"} onValueChange={(v) => handleFilterChange(setStatusFilter, v === "__all__" ? "" : v)}>
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

        {/* Domain filter */}
        <div className="flex items-center gap-2">
          <Label className="text-sm whitespace-nowrap">{t("ragTerminology.filters.domain")}</Label>
          <Select value={domainFilter || "__all__"} onValueChange={(v) => handleFilterChange(setDomainFilter, v === "__all__" ? "" : v)}>
            <SelectTrigger className="w-44">
              <SelectValue placeholder={t("ragTerminology.filters.all")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">{t("ragTerminology.filters.all")}</SelectItem>
              {isDomainsLoading ? (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="h-4 w-4 animate-spin text-[color:var(--px-shell-muted)]" />
                </div>
              ) : (
                renderDomainFilterOptions()
              )}
            </SelectContent>
          </Select>
        </div>

        {/* Source lang filter */}
        <div className="flex items-center gap-2">
          <Label className="text-sm whitespace-nowrap">{t("ragTerminology.filters.sourceLang")}</Label>
          <Select value={sourceLangFilter || "__all__"} onValueChange={(v) => handleFilterChange(setSourceLangFilter, v === "__all__" ? "" : v)}>
            <SelectTrigger className="w-28">
              <SelectValue placeholder={t("ragTerminology.filters.all")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">{t("ragTerminology.filters.all")}</SelectItem>
              {LANGUAGE_OPTIONS.map((l) => (
                <SelectItem key={l.value} value={l.value}>{l.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Clear filters */}
        <Button variant="outline" size="sm" onClick={() => {
          setStatusFilter("")
          setDomainFilter("")
          setSourceLangFilter("")
          setSearchQuery("")
          setDebouncedSearch("")
          setPage(1)
        }}>
          {t("ragTerminology.filters.clear")}
        </Button>

        <div className="flex-1" />

        {/* Create button */}
        <Button size="sm" onClick={() => setCreateDialogOpen(true)}>
          <Plus className="h-4 w-4 mr-1" />
          {t("ragTerminology.create")}
        </Button>
      </div>

      {/* Results count */}
      {!isLoading && !loadError && terms.length > 0 && (
        <p className="text-xs text-[color:var(--px-shell-muted)]">
          {t("ragTerminology.browser.resultsCount", { count: total })}
        </p>
      )}

      {/* Content area */}
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
          <BookOpenText className="h-7 w-7" />
          <p className="mt-3 text-sm">{searchQuery || statusFilter || domainFilter || sourceLangFilter
            ? t("ragTerminology.browser.noResults")
            : t("ragTerminology.browser.empty")}</p>
        </div>
      ) : (
        <>
          <DataTable>
            <DataTableHeader>
              <DataTableHeaderRow className="grid-cols-[1fr_1fr_100px_90px_90px_100px_100px]">
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
              {terms.map((term) => {
                const sourceTypeStyle = SOURCE_TYPE_LABELS[term.source_type] ?? { tone: "muted" as const, label: term.source_type }
                const statusStyle = STATUS_LABELS[term.status] ?? { tone: "muted" as const, label: term.status }
                const isActionLoading = actionLoadingId === term.id
                const allowEditDelete = ["manual", "system"].includes(term.source_type) || term.status === "pending_review"
                return (
                  <DataTableRow key={term.id} className="grid-cols-[1fr_1fr_100px_90px_90px_100px_100px] items-center">
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
                    </DataTableCell>
                  </DataTableRow>
                )
              })}
            </DataTableBody>
          </DataTable>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-2">
              <p className="text-xs text-[color:var(--px-shell-muted)]">
                {t("ragTerminology.pagination.pageInfo", { current: page, total: totalPages })}
              </p>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
                  {t("ragTerminology.pagination.previous")}
                </Button>
                <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages}>
                  {t("ragTerminology.pagination.next")}
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </PanelShell>
  )
}
