import { History, Loader2, RefreshCw, Search, ShieldAlert, Trash2 } from "lucide-react"
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"

import { LoginPrompt } from "@/components/LoginPrompt"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { useAuth } from "@/contexts/AuthContext"
import { deleteAdminCurationJob, listAdminCurationJobs } from "@/lib/community-api"
import type { AdminCurationJobHistoryItem } from "@/types/community"

const ADMIN_ROLES = new Set(["admin", "super_admin", "community_admin", "curation_admin"])

function hasAdminRole(roles: string[] | null | undefined): boolean {
  if (!roles?.length) {
    return false
  }
  return roles.some((role) => ADMIN_ROLES.has(String(role).trim().toLowerCase()))
}

const STATUS_OPTIONS = [
  { value: "all", labelKey: "community.admin.tasks.filters.all", fallback: "All" },
  { value: "queued", labelKey: "community.admin.tasks.filters.queued", fallback: "Queued" },
  { value: "processing", labelKey: "community.admin.tasks.filters.processing", fallback: "Processing" },
  { value: "completed", labelKey: "community.admin.tasks.filters.completed", fallback: "Completed" },
  { value: "failed", labelKey: "community.admin.tasks.filters.failed", fallback: "Failed" },
]

export default function CommunityAdminCurationTasksPage() {
  const { t } = useTranslation()
  const { user, isAuthenticated } = useAuth()
  const [statusFilter, setStatusFilter] = useState("all")
  const [searchValue, setSearchValue] = useState("")
  const [jobs, setJobs] = useState<AdminCurationJobHistoryItem[]>([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [isDeleting, setIsDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [jobPendingDelete, setJobPendingDelete] = useState<AdminCurationJobHistoryItem | null>(null)

  const isAdmin = hasAdminRole(user?.roles)

  async function loadJobs(params?: { status?: string, q?: string }) {
    const status = params?.status ?? statusFilter
    const q = params?.q ?? searchValue
    try {
      setIsLoading(true)
      const payload = await listAdminCurationJobs({ status, q })
      setJobs(payload.items)
      setTotal(payload.total)
      setError(null)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : t("community.submit.errorFallback"))
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (!isAuthenticated || !isAdmin) {
      return
    }
    void loadJobs({ status: statusFilter, q: searchValue })
  }, [isAuthenticated, isAdmin, statusFilter])

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
        <Card className="border-destructive/20 bg-destructive/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <ShieldAlert className="h-5 w-5" />
              {t("community.admin.accessDenied", "Admin access required")}
            </CardTitle>
            <CardDescription>
              {t(
                "community.admin.accessDeniedDescription",
                "You do not have permission to access the community curation console.",
              )}
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-8">
      <header className="space-y-2">
        <div className="flex items-center gap-3">
          <div className="rounded-2xl border border-border/60 bg-muted/40 p-3">
            <History className="h-5 w-5 text-foreground" />
          </div>
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">
              {t("community.admin.tasks.title", "Admin curation task history")}
            </h1>
            <p className="text-sm text-muted-foreground">
              {t(
                "community.admin.tasks.description",
                "Review queued, processing, completed, and failed admin curation jobs. Deletes are permanent hard deletes.",
              )}
            </p>
          </div>
        </div>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>{t("community.admin.tasks.filtersTitle", "Filters")}</CardTitle>
          <CardDescription>
            {t("community.admin.tasks.filtersDescription", "Search by arXiv ID or batch ID, then manage task history.")}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 md:flex-row md:items-center">
          <label className="flex min-w-44 flex-col gap-2 text-sm">
            <span>{t("community.admin.tasks.statusLabel", "Status")}</span>
            <select
              className="h-10 rounded-md border border-input bg-background px-3 text-sm"
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {t(option.labelKey, option.fallback)}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-1 flex-col gap-2 text-sm">
            <span>{t("community.admin.tasks.searchLabel", "Search")}</span>
            <Input
              value={searchValue}
              onChange={(event) => setSearchValue(event.target.value)}
              placeholder={t("community.admin.tasks.searchPlaceholder", "Search arXiv ID or batch ID")}
            />
          </label>
          <div className="flex gap-2 pt-6">
            <Button type="button" variant="outline" onClick={() => void loadJobs({ status: statusFilter, q: searchValue })}>
              <Search className="mr-2 h-4 w-4" />
              {t("community.admin.tasks.searchAction", "Search")}
            </Button>
            <Button type="button" variant="outline" onClick={() => void loadJobs({ status: statusFilter, q: searchValue })}>
              <RefreshCw className="mr-2 h-4 w-4" />
              {t("common.actions.refresh", "Refresh")}
            </Button>
          </div>
        </CardContent>
      </Card>

      {error ? (
        <Card className="border-destructive/30 bg-destructive/10">
          <CardContent className="py-4 text-sm text-destructive">{error}</CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>{t("community.admin.tasks.resultsTitle", "Task records")}</CardTitle>
          <CardDescription>
            {t("community.admin.tasks.totalLabel", "Total tasks")}: {total}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center gap-3 py-8 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              {t("common.status.loading")}
            </div>
          ) : jobs.length === 0 ? (
            <p className="py-8 text-sm text-muted-foreground">
              {t("community.admin.tasks.empty", "No admin curation tasks match the current filters.")}
            </p>
          ) : (
            <div className="space-y-3">
              {jobs.map((job) => (
                <div key={job.job_id} className="rounded-2xl border border-border/60 bg-muted/15 p-4">
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div className="space-y-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="secondary">{job.status}</Badge>
                        {job.terminal_task_status ? <Badge variant="outline">{job.terminal_task_status}</Badge> : null}
                        <span className="font-medium">{job.arxiv_id || job.original_filename || job.job_id}</span>
                      </div>
                      <div className="grid gap-1 text-sm text-muted-foreground">
                        <p>job: {job.job_id}</p>
                        <p>batch: {job.batch_id}</p>
                        {job.task_id ? <p>task: {job.task_id}</p> : null}
                        {job.paper_id ? <p>paper: {job.paper_id}</p> : null}
                        {job.published_paper_id ? <p>published: {job.published_paper_id}</p> : null}
                        {job.failed_artifact_path ? <p>{job.failed_artifact_path}</p> : null}
                        {job.updated_at ? <p>{t("community.admin.tasks.updatedAt", "Updated")}: {job.updated_at}</p> : null}
                      </div>
                      {job.error ? <p className="text-sm text-destructive">{job.error}</p> : null}
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        type="button"
                        variant="destructive"
                        onClick={() => setJobPendingDelete(job)}
                        aria-label={`Delete ${job.job_id}`}
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        {t("community.admin.tasks.deleteAction", "Delete")}
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
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
        <AlertDialogContent className="rounded-2xl">
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
            <AlertDialogCancel className="rounded-full">
              {t("common.actions.cancel", "Cancel")}
            </AlertDialogCancel>
            <AlertDialogAction
              className="rounded-full bg-destructive text-destructive-foreground hover:bg-destructive/90"
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
    </div>
  )
}
