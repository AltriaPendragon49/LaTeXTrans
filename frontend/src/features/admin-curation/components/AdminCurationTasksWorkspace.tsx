import { History, Loader2, RefreshCw, Search, ShieldAlert, Trash2 } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"

import { LoginPrompt } from "@/features/auth-shell/components/LoginPrompt"
import { useAuth } from "@/contexts/AuthContext"
import { useIsMobile } from "@/hooks/use-mobile"
import {
  batchDeleteAdminCurationJobs,
  deleteAdminCurationJob,
  listAdminCurationJobs,
} from "@/features/admin-curation/services/admin-curation-api"
import { hasAdminRole } from "@/features/admin-curation/utils/admin-access"
import type { AdminCurationJobHistoryItem } from "@/types/community"
import { Button } from "@/ui/button/Button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/ui/card/Card"
import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHeader,
  DataTableHeaderCell,
  DataTableHeaderRow,
  DataTableRow,
} from "@/ui/data-table/DataTable"
import { FormFieldShell } from "@/ui/form-field-shell/FormFieldShell"
import { LoadingState } from "@/ui/loading-state/LoadingState"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { PageIntro } from "@/ui/page-intro/PageIntro"
import { Checkbox } from "@/ui/primitives/checkbox"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/ui/primitives/alert-dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/ui/primitives/select"
import { SearchBar } from "@/ui/search-bar/SearchBar"
import { StatePanel } from "@/ui/state-panel/StatePanel"
import { StatusBadge } from "@/ui/status-badge/StatusBadge"

const STATUS_OPTIONS = [
  { value: "all", labelKey: "community.admin.tasks.filters.all", fallback: "All" },
  { value: "queued", labelKey: "community.admin.tasks.filters.queued", fallback: "Queued" },
  { value: "processing", labelKey: "community.admin.tasks.filters.processing", fallback: "Processing" },
  { value: "completed", labelKey: "community.admin.tasks.filters.completed", fallback: "Completed" },
  { value: "failed", labelKey: "community.admin.tasks.filters.failed", fallback: "Failed" },
]

function getJobStatusTone(status: string): "accent" | "success" | "danger" | "warning" | "muted" {
  switch (status.toLowerCase()) {
    case "completed":
      return "success"
    case "failed":
      return "danger"
    case "processing":
      return "accent"
    case "queued":
      return "warning"
    default:
      return "muted"
  }
}

export function AdminCurationTasksWorkspace() {
  const { t } = useTranslation()
  const { user, isAuthenticated } = useAuth()
  const isMobile = useIsMobile()
  const [statusFilter, setStatusFilter] = useState("all")
  const [searchValue, setSearchValue] = useState("")
  const [jobs, setJobs] = useState<AdminCurationJobHistoryItem[]>([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [isDeleting, setIsDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [jobPendingDelete, setJobPendingDelete] = useState<AdminCurationJobHistoryItem | null>(null)
  const [isBatchDeleteDialogOpen, setIsBatchDeleteDialogOpen] = useState(false)
  const [selectedJobIds, setSelectedJobIds] = useState<string[]>([])

  const isAdmin = hasAdminRole(user?.roles)

  const loadJobs = useCallback(async (params?: { status?: string, q?: string }) => {
    const status = params?.status ?? statusFilter
    const q = params?.q ?? searchValue
    try {
      setIsLoading(true)
      const payload = await listAdminCurationJobs({ status, q })
      setJobs(payload.items)
      setTotal(payload.total)
      setSelectedJobIds((current) => current.filter((jobId) => payload.items.some((job) => job.job_id === jobId)))
      setError(null)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : t("community.submit.errorFallback"))
    } finally {
      setIsLoading(false)
    }
  }, [searchValue, statusFilter, t])

  useEffect(() => {
    if (!isAuthenticated || !isAdmin) {
      return
    }
    void loadJobs({ status: statusFilter, q: searchValue })
  }, [isAuthenticated, isAdmin, loadJobs, searchValue, statusFilter])

  async function handleDeleteJob() {
    if (!jobPendingDelete) {
      return
    }

    try {
      setIsDeleting(true)
      await deleteAdminCurationJob(jobPendingDelete.job_id)
      toast.success(t("community.admin.tasks.deleteSuccess", "Task deleted permanently."))
      setJobPendingDelete(null)
      await loadJobs({ status: statusFilter, q: searchValue })
    } catch (deleteError) {
      toast.error(deleteError instanceof Error ? deleteError.message : t("community.submit.errorFallback"))
    } finally {
      setIsDeleting(false)
    }
  }

  const visibleJobIds = jobs.map((job) => job.job_id)
  const allVisibleSelected = visibleJobIds.length > 0 && visibleJobIds.every((jobId) => selectedJobIds.includes(jobId))
  const selectedVisibleCount = selectedJobIds.filter((jobId) => visibleJobIds.includes(jobId)).length

  function toggleJobSelection(jobId: string, checked: boolean | "indeterminate") {
    const shouldSelect = checked === true
    setSelectedJobIds((current) => {
      if (shouldSelect) {
        return current.includes(jobId) ? current : [...current, jobId]
      }
      return current.filter((candidate) => candidate !== jobId)
    })
  }

  function toggleSelectAllVisible() {
    setSelectedJobIds((current) => {
      if (allVisibleSelected) {
        return current.filter((jobId) => !visibleJobIds.includes(jobId))
      }
      return Array.from(new Set([...current, ...visibleJobIds]))
    })
  }

  async function handleBatchDeleteJobs() {
    const visibleSelectedJobIds = selectedJobIds.filter((jobId) => visibleJobIds.includes(jobId))
    if (!visibleSelectedJobIds.length) {
      return
    }

    try {
      setIsDeleting(true)
      const payload = await batchDeleteAdminCurationJobs(visibleSelectedJobIds)
      const failedIds = payload.failed.map((item) => item.job_id)
      setIsBatchDeleteDialogOpen(false)
      await loadJobs({ status: statusFilter, q: searchValue })
      setSelectedJobIds(failedIds)

      if (payload.deleted_count > 0) {
        toast.success(
          t("community.admin.tasks.batchDeleteSuccess", {
            count: payload.deleted_count,
            defaultValue: "Deleted {{count}} tasks permanently.",
          }),
        )
      }

      if (payload.failed_count > 0) {
        toast.error(
          t("community.admin.tasks.batchDeletePartialFailure", {
            count: payload.failed_count,
            defaultValue: "{{count}} tasks could not be deleted. They remain selected.",
          }),
        )
      }
    } catch (deleteError) {
      toast.error(deleteError instanceof Error ? deleteError.message : t("community.submit.errorFallback"))
    } finally {
      setIsDeleting(false)
    }
  }

  if (!isAuthenticated) {
    return (
      <LoginPrompt
        messageKey="community.submit.loginRequiredTitle"
        descriptionKey="community.submit.loginRequiredDescription"
      />
    )
  }

  if (!isAdmin) {
    return (
      <div className="mx-auto w-full max-w-3xl px-6 py-8">
        <StatePanel
          tone="danger"
          className="py-10"
          icon={<ShieldAlert className="h-7 w-7" />}
          title={t("community.admin.accessDenied", "Admin access required")}
          description={t(
            "community.admin.accessDeniedDescription",
            "You do not have permission to access the community curation console.",
          )}
        />
      </div>
    )
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-8">
      <PageIntro
        icon={<History className="h-5 w-5" />}
        title={t("community.admin.tasks.title", "Admin curation task history")}
        description={t(
          "community.admin.tasks.description",
          "Review queued, processing, completed, and failed admin curation jobs. Deletes are permanent hard deletes.",
        )}
      />

      <Card>
        <CardHeader>
          <CardTitle>{t("community.admin.tasks.filtersTitle", "Filters")}</CardTitle>
          <CardDescription>
            {t("community.admin.tasks.filtersDescription", "Search by arXiv ID or batch ID, then manage task history.")}
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-[minmax(220px,260px)_minmax(0,1fr)] md:items-start">
          <FormFieldShell
            label={t("community.admin.tasks.statusLabel", "Status")}
            description={t("community.admin.tasks.filtersTitle", "Filters")}
            size="compact"
          >
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger aria-label={t("community.admin.tasks.statusLabel", "Status")} className="bg-[color:var(--px-shell-panel-strong)]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {t(option.labelKey, option.fallback)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormFieldShell>
          <div className="min-w-0 flex-1">
            <SearchBar
              value={searchValue}
              onValueChange={setSearchValue}
              onSubmit={(nextValue) => void loadJobs({ status: statusFilter, q: nextValue })}
              ariaLabel={t("community.admin.tasks.searchLabel", "Search")}
              placeholder={t("community.admin.tasks.searchPlaceholder", "Search arXiv ID or batch ID")}
              actionLabel={t("community.admin.tasks.searchAction", "Search")}
              actionIcon={<Search className="h-4 w-4" />}
              auxiliaryAction={(
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => void loadJobs({ status: statusFilter, q: searchValue })}
                >
                  <RefreshCw className="h-4 w-4" />
                  {t("common.actions.refresh", "Refresh")}
                </Button>
              )}
              inputClassName="min-h-10"
            />
          </div>
        </CardContent>
      </Card>

      {error ? (
        <NoticeBanner tone="danger" description={error} />
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>{t("community.admin.tasks.resultsTitle", "Task records")}</CardTitle>
          <CardDescription>
            {t("community.admin.tasks.totalLabel", "Total tasks")}: {total}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-4 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <p className="text-sm text-[color:var(--px-shell-muted)]">
              {t("community.admin.tasks.selectedCount", {
                count: selectedVisibleCount,
                defaultValue: "{{count}} selected",
              })}
            </p>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={toggleSelectAllVisible}
                disabled={jobs.length === 0}
              >
                {t("community.admin.tasks.selectAllVisible", "Select all visible")}
              </Button>
              <Button
                type="button"
                variant="destructive"
                onClick={() => setIsBatchDeleteDialogOpen(true)}
                disabled={selectedVisibleCount === 0}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                {t("community.admin.tasks.batchDeleteAction", "Delete selected")}
              </Button>
            </div>
          </div>
          {isLoading ? (
            <LoadingState className="py-8" label={t("common.status.loading")} />
          ) : jobs.length === 0 ? (
            <StatePanel
              className="py-10 shadow-none"
              title={t("community.admin.tasks.empty", "No admin curation tasks match the current filters.")}
              description={t(
                "community.admin.tasks.filtersDescription",
                "Search by arXiv ID or batch ID, then manage task history.",
              )}
            />
          ) : (
            <DataTable
              data-testid="admin-curation-task-records"
              data-layout={isMobile ? "cards" : "table"}
              className="shadow-none"
            >
              <DataTableHeader className="hidden lg:block">
                <DataTableHeaderRow className="grid-cols-[40px_minmax(0,2.3fr)_minmax(180px,1fr)_minmax(180px,1fr)_auto]">
                  <DataTableHeaderCell />
                  <DataTableHeaderCell>{t("community.admin.tasks.resultsTitle", "Task records")}</DataTableHeaderCell>
                  <DataTableHeaderCell>{t("community.admin.tasks.statusLabel", "Status")}</DataTableHeaderCell>
                  <DataTableHeaderCell>{t("community.admin.tasks.updatedAt", "Updated")}</DataTableHeaderCell>
                  <DataTableHeaderCell className="text-right">{t("common.actions.delete", "Delete")}</DataTableHeaderCell>
                </DataTableHeaderRow>
              </DataTableHeader>
              <DataTableBody>
                {jobs.map((job) => (
                  <DataTableRow
                    key={job.job_id}
                    className={`grid-cols-1 gap-4 lg:grid-cols-[40px_minmax(0,2.3fr)_minmax(180px,1fr)_minmax(180px,1fr)_auto] lg:items-start ${isMobile ? "rounded-[24px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] shadow-[0_18px_38px_-34px_rgba(15,23,42,0.18)]" : ""}`}
                  >
                    <DataTableCell className="pt-1 lg:pt-2">
                      <Checkbox
                        checked={selectedJobIds.includes(job.job_id)}
                        onCheckedChange={(checked) => toggleJobSelection(job.job_id, checked)}
                        aria-label={t("community.admin.tasks.selectJobAriaLabel", {
                          jobId: job.job_id,
                          defaultValue: "Select {{jobId}}",
                        })}
                      />
                    </DataTableCell>

                    <DataTableCell className="space-y-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <StatusBadge tone={getJobStatusTone(job.status)}>{job.status}</StatusBadge>
                        {job.terminal_task_status ? (
                          <StatusBadge tone="muted">{job.terminal_task_status}</StatusBadge>
                        ) : null}
                      </div>
                      <div className="space-y-2">
                        <p className="text-sm font-semibold text-[color:var(--px-shell-ink)]">
                          {job.arxiv_id || job.original_filename || job.job_id}
                        </p>
                        <div className="grid gap-1 text-xs text-[color:var(--px-shell-muted)]">
                          <p>job: {job.job_id}</p>
                          <p>batch: {job.batch_id}</p>
                          {job.task_id ? <p>task: {job.task_id}</p> : null}
                          {job.paper_id ? <p>paper: {job.paper_id}</p> : null}
                          {job.published_paper_id ? <p>published: {job.published_paper_id}</p> : null}
                          {job.failed_artifact_path ? <p>{job.failed_artifact_path}</p> : null}
                        </div>
                        {job.error ? (
                          <p className="text-sm text-[color:var(--px-shell-danger)]">{job.error}</p>
                        ) : null}
                      </div>
                    </DataTableCell>

                    <DataTableCell className="space-y-2 text-sm text-[color:var(--px-shell-muted)]">
                      <p className="font-medium text-[color:var(--px-shell-ink)]">{job.source_type}</p>
                      <p>{job.arxiv_id ? `arXiv:${job.arxiv_id}` : job.original_filename || t("common.labels.none", "None")}</p>
                    </DataTableCell>

                    <DataTableCell className="space-y-2 text-sm text-[color:var(--px-shell-muted)]">
                      <p>{job.updated_at ? `${t("community.admin.tasks.updatedAt", "Updated")}: ${job.updated_at}` : t("common.labels.none", "None")}</p>
                      <p>{job.created_at}</p>
                    </DataTableCell>

                    <DataTableCell className="flex items-center justify-start lg:justify-end">
                      <Button
                        type="button"
                        variant="destructive"
                        size="sm"
                        onClick={() => setJobPendingDelete(job)}
                        aria-label={`Delete ${job.job_id}`}
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        {t("community.admin.tasks.deleteAction", "Delete")}
                      </Button>
                    </DataTableCell>
                  </DataTableRow>
                ))}
              </DataTableBody>
            </DataTable>
          )}
        </CardContent>
      </Card>

      <AlertDialog
        open={jobPendingDelete !== null}
        onOpenChange={(open) => {
          if (!open) {
            setJobPendingDelete(null)
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t("community.admin.tasks.deleteDialogTitle", "Permanently delete this task?")}
            </AlertDialogTitle>
            <AlertDialogDescription className="text-sm">
              {jobPendingDelete
                ? t(
                    "community.admin.tasks.deleteDialogDescription",
                    "This permanently deletes the task record and all retained artifacts. This action cannot be undone.",
                  )
                : ""}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="mt-4 gap-2 sm:gap-0">
            <AlertDialogCancel>
              {t("common.actions.cancel", "Cancel")}
            </AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={(event) => {
                event.preventDefault()
                void handleDeleteJob()
              }}
            >
              {isDeleting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              {t("community.admin.tasks.deleteConfirm", "Permanently delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog
        open={isBatchDeleteDialogOpen}
        onOpenChange={(open) => {
          setIsBatchDeleteDialogOpen(open)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t("community.admin.tasks.batchDeleteDialogTitle", "Permanently delete selected tasks?")}
            </AlertDialogTitle>
            <AlertDialogDescription className="text-sm">
              {t("community.admin.tasks.batchDeleteDialogDescription", {
                count: selectedVisibleCount,
                defaultValue:
                  "This permanently deletes {{count}} selected task records and their retained artifacts. This action cannot be undone.",
              })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="mt-4 gap-2 sm:gap-0">
            <AlertDialogCancel>
              {t("common.actions.cancel", "Cancel")}
            </AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={(event) => {
                event.preventDefault()
                void handleBatchDeleteJobs()
              }}
            >
              {isDeleting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              {t("community.admin.tasks.deleteConfirm", "Permanently delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
