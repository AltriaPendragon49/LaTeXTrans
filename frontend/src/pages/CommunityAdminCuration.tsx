import { Loader2, RefreshCw, ShieldAlert, Upload } from "lucide-react"
import { useEffect, useMemo, useState, type ChangeEvent, type FormEvent } from "react"
import { useTranslation } from "react-i18next"

import { LoginPrompt } from "@/components/LoginPrompt"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { useAuth } from "@/contexts/AuthContext"
import {
  getAdminCurationBatch,
  submitAdminArxivCurationBatch,
  submitAdminUploadCurationBatch,
} from "@/lib/community-api"
import { useStore } from "@/store/useStore"
import type { AdminCurationBatchResponse } from "@/types/community"

const ADMIN_ROLES = new Set(["admin", "super_admin", "community_admin", "curation_admin"])
const ACTIVE_BATCH_STATUSES = new Set(["queued", "pending", "running"])
const ACTIVE_JOB_STATUSES = new Set(["queued", "pending", "running", "processing"])

function hasAdminRole(roles: string[] | null | undefined): boolean {
  if (!roles?.length) {
    return false
  }
  return roles.some((role) => ADMIN_ROLES.has(String(role).trim().toLowerCase()))
}

function parseArxivIds(rawValue: string): string[] {
  return Array.from(
    new Set(
      rawValue
        .split(/[\s,]+/)
        .map((value) => value.trim())
        .filter(Boolean),
    ),
  )
}

function isBatchActive(batch: AdminCurationBatchResponse | null): boolean {
  if (!batch) {
    return false
  }
  if (ACTIVE_BATCH_STATUSES.has(batch.status.toLowerCase())) {
    return true
  }
  return batch.items.some((item) => ACTIVE_JOB_STATUSES.has(item.status.toLowerCase()))
}

export default function CommunityAdminCurationPage() {
  const { t } = useTranslation()
  const { user, isAuthenticated } = useAuth()
  const { config, loadUserSettings } = useStore()

  const [arxivInput, setArxivInput] = useState("")
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [batch, setBatch] = useState<AdminCurationBatchResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isSubmittingArxiv, setIsSubmittingArxiv] = useState(false)
  const [isSubmittingUpload, setIsSubmittingUpload] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const isAdmin = hasAdminRole(user?.roles)
  const sourceLanguage = config.source_language || "en"
  const targetLanguage = config.target_language || "zh"
  const arxivIds = useMemo(() => parseArxivIds(arxivInput), [arxivInput])
  const hasActiveBatch = isBatchActive(batch)

  useEffect(() => {
    if (isAuthenticated) {
      void loadUserSettings()
    }
  }, [isAuthenticated, loadUserSettings])

  useEffect(() => {
    if (!batch?.batch_id || !hasActiveBatch) {
      return
    }

    const intervalId = window.setInterval(() => {
      void refreshBatch(batch.batch_id)
    }, 4000)

    return () => window.clearInterval(intervalId)
  }, [batch?.batch_id, hasActiveBatch])

  async function refreshBatch(batchId: string) {
    try {
      setIsRefreshing(true)
      const nextBatch = await getAdminCurationBatch(batchId)
      setBatch(nextBatch)
      setError(null)
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : t("community.submit.errorFallback"))
    } finally {
      setIsRefreshing(false)
    }
  }

  async function handleSubmitArxiv(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!arxivIds.length) {
      return
    }

    try {
      setIsSubmittingArxiv(true)
      const result = await submitAdminArxivCurationBatch({
        arxiv_ids: arxivIds,
        source_language: sourceLanguage,
        target_language: targetLanguage,
      })
      setBatch(result)
      setError(null)
      setArxivInput("")
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : t("community.submit.errorFallback"))
    } finally {
      setIsSubmittingArxiv(false)
    }
  }

  async function handleSubmitUploads() {
    if (!selectedFiles.length) {
      return
    }

    try {
      setIsSubmittingUpload(true)
      const result = await submitAdminUploadCurationBatch({
        files: selectedFiles,
        source_language: sourceLanguage,
        target_language: targetLanguage,
      })
      setBatch(result)
      setError(null)
      setSelectedFiles([])
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : t("community.submit.errorFallback"))
    } finally {
      setIsSubmittingUpload(false)
    }
  }

  function handleFileSelect(event: ChangeEvent<HTMLInputElement>) {
    setSelectedFiles(Array.from(event.target.files ?? []))
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
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-6 py-8">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">
          {t("community.admin.curation.title", "Community admin curation")}
        </h1>
        <p className="text-sm text-muted-foreground">
          {t(
            "community.admin.curation.description",
            "Submit arXiv IDs or upload archives for official community curation.",
          )}
        </p>
        <p className="text-xs text-muted-foreground">
          {t("community.admin.curation.languageHint", "Language pair")} {sourceLanguage} {"->"} {targetLanguage}
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>{t("community.admin.curation.arxivTitle", "Batch import from arXiv")}</CardTitle>
          <CardDescription>
            {t("community.admin.curation.arxivDescription", "Enter one or more arXiv IDs separated by commas or spaces.")}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-3" onSubmit={handleSubmitArxiv}>
            <textarea
              value={arxivInput}
              onChange={(event) => setArxivInput(event.target.value)}
              placeholder={t("community.submit.arxivPlaceholder")}
              className="min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              aria-label={t("community.submit.arxivLabel")}
            />
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                {t("community.admin.curation.pendingCount", "IDs ready")}: {arxivIds.length}
              </span>
              <Button type="submit" disabled={!arxivIds.length || isSubmittingArxiv}>
                {isSubmittingArxiv ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                {t("community.submit.submitArxiv")}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("community.admin.curation.uploadTitle", "Batch import from uploads")}</CardTitle>
          <CardDescription>
            {t("community.admin.curation.uploadDescription", "Upload one or more source packages for curation.")}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Input type="file" multiple onChange={handleFileSelect} aria-label={t("community.submit.uploadLabel")} />
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">
              {t("community.submit.fileSelected", { name: `${selectedFiles.length}` })}
            </span>
            <Button type="button" disabled={!selectedFiles.length || isSubmittingUpload} onClick={() => void handleSubmitUploads()}>
              {isSubmittingUpload ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
              {t("community.submit.submitUpload")}
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
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <div className="space-y-1">
            <CardTitle>{t("community.admin.curation.batchStatusTitle", "Batch status")}</CardTitle>
            <CardDescription>{batch ? batch.batch_id : t("community.admin.curation.batchStatusEmpty", "No batch submitted yet.")}</CardDescription>
          </div>
          {batch ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={isRefreshing}
              onClick={() => void refreshBatch(batch.batch_id)}
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
              {t("common.actions.refresh", "Refresh")}
            </Button>
          ) : null}
        </CardHeader>
        <CardContent>
          {!batch ? (
            <p className="text-sm text-muted-foreground">{t("community.submit.emptyDescription")}</p>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm">
                <span className="text-muted-foreground">{t("task.status", "Status")}:</span>
                <Badge variant="outline">{batch.status}</Badge>
              </div>
              <div className="grid gap-2">
                {batch.items.map((item) => (
                  <div
                    key={item.job_id}
                    className="rounded-md border border-border/60 bg-muted/20 p-3 text-sm"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="secondary">{item.status}</Badge>
                      <span className="font-medium">{item.source_type}</span>
                      {item.arxiv_id ? <span className="text-muted-foreground">arXiv:{item.arxiv_id}</span> : null}
                      {item.original_filename ? <span className="text-muted-foreground">{item.original_filename}</span> : null}
                      {item.paper_id ? <span className="text-muted-foreground">paper:{item.paper_id}</span> : null}
                    </div>
                    {item.error ? (
                      <p className="mt-2 text-xs text-destructive">{item.error}</p>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
