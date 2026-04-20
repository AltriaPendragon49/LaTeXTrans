import { Loader2, RefreshCw, ShieldAlert, Upload } from "lucide-react"
import { useCallback, useEffect, useMemo, useRef, useState, type ChangeEvent, type FormEvent } from "react"
import { useTranslation } from "react-i18next"

import { LoginPrompt } from "@/features/auth-shell/components/LoginPrompt"
import { useAuth } from "@/contexts/AuthContext"
import { useTranslationConfig } from "@/features/translation-workflow/hooks/useTranslationConfig"
import {
  getAdminCurationBatch,
  submitAdminArxivCurationBatch,
  submitAdminUploadCurationBatch,
} from "@/features/admin-curation/services/admin-curation-api"
import { hasAdminRole } from "@/features/admin-curation/utils/admin-access"
import type { AdminCurationBatchResponse } from "@/types/community"
import { Button } from "@/ui/button/Button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/ui/card/Card"
import { FormFieldShell } from "@/ui/form-field-shell/FormFieldShell"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { PageIntro } from "@/ui/page-intro/PageIntro"
import { Textarea } from "@/ui/input/Textarea"
import { Pill } from "@/ui/pill/Pill"
import { RecordRow } from "@/ui/record-row/RecordRow"
import { StatePanel } from "@/ui/state-panel/StatePanel"
import { UploadDropSurface } from "@/ui/upload-card/UploadDropSurface"

const ACTIVE_BATCH_STATUSES = new Set(["queued", "pending", "running"])
const ACTIVE_JOB_STATUSES = new Set(["queued", "pending", "running", "processing"])

function parseArxivIds(rawValue: string): string[] {
  return Array.from(
    new Set(
      rawValue
        .split(/\r?\n/)
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

export function AdminCurationWorkspace() {
  const { t } = useTranslation()
  const { user, isAuthenticated } = useAuth()
  const { config, loadUserSettings } = useTranslationConfig()

  const [arxivInput, setArxivInput] = useState("")
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [batch, setBatch] = useState<AdminCurationBatchResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isSubmittingArxiv, setIsSubmittingArxiv] = useState(false)
  const [isSubmittingUpload, setIsSubmittingUpload] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const uploadInputRef = useRef<HTMLInputElement>(null)

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

  const refreshBatch = useCallback(async (batchId: string) => {
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
  }, [t])

  useEffect(() => {
    if (!batch?.batch_id || !hasActiveBatch) {
      return
    }

    const intervalId = window.setInterval(() => {
      void refreshBatch(batch.batch_id)
    }, 4000)

    return () => window.clearInterval(intervalId)
  }, [batch?.batch_id, hasActiveBatch, refreshBatch])

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
    event.target.value = ""
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
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-6 py-8">
      <PageIntro
        title={t("community.admin.curation.title", "Community admin curation")}
        description={t(
          "community.admin.curation.description",
          "Submit arXiv IDs or upload archives for official community curation.",
        )}
        meta={
          <>
            {t("community.admin.curation.languageHint", "Language pair")} {sourceLanguage} {"->"} {targetLanguage}
          </>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle>{t("community.admin.curation.arxivTitle", "Batch import from arXiv")}</CardTitle>
          <CardDescription>
            {t("community.admin.curation.arxivDescription", "Enter one arXiv ID per line.")}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-3" onSubmit={handleSubmitArxiv}>
            <FormFieldShell
              label={t("community.submit.arxivLabel")}
              description={t("community.admin.curation.arxivDescription", "Enter one arXiv ID per line.")}
              headerAside={<Pill tone="accent">{arxivIds.length}</Pill>}
            >
              <Textarea
                value={arxivInput}
                onChange={(event) => setArxivInput(event.target.value)}
                placeholder={t("community.submit.arxivPlaceholder")}
                className="min-h-24"
                aria-label={t("community.submit.arxivLabel")}
              />
            </FormFieldShell>
            <div className="flex items-center justify-between">
              <span className="text-xs text-[color:var(--px-shell-muted)]">
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
          <input
            ref={uploadInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={handleFileSelect}
            aria-label={t("community.submit.uploadLabel")}
          />
          <FormFieldShell
            label={t("community.submit.uploadLabel")}
            description={t("community.admin.curation.uploadDescription", "Upload one or more source packages for curation.")}
            headerAside={selectedFiles.length ? <Pill tone="accent">{selectedFiles.length}</Pill> : null}
          >
            <UploadDropSurface
              heading={t("community.submit.uploadLabel")}
              body={t("community.admin.curation.uploadDescription", "Upload one or more source packages for curation.")}
              onClick={() => uploadInputRef.current?.click()}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault()
                  uploadInputRef.current?.click()
                }
              }}
              role="button"
              tabIndex={0}
              className="cursor-pointer"
            />
          </FormFieldShell>
          {selectedFiles.length ? (
            <div className="grid gap-2">
              {selectedFiles.map((file) => (
                <RecordRow
                  key={`${file.name}-${file.size}-${file.lastModified}`}
                  icon={<Upload className="h-4 w-4 text-[color:var(--px-shell-accent)]" />}
                  title={file.name}
                  meta={`${(file.size / 1024 / 1024).toFixed(1)} MB`}
                  className="bg-[color:var(--px-shell-panel-strong)]"
                />
              ))}
            </div>
          ) : null}
          <div className="flex items-center justify-between">
            <span className="text-xs text-[color:var(--px-shell-muted)]">
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
        <NoticeBanner tone="danger" description={error} />
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
            <p className="text-sm text-[color:var(--px-shell-muted)]">{t("community.submit.emptyDescription")}</p>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm">
                <span className="text-[color:var(--px-shell-muted)]">{t("task.status", "Status")}:</span>
                <Pill>{batch.status}</Pill>
              </div>
              <div className="grid gap-2">
                {batch.items.map((item) => (
                  <RecordRow
                    key={item.job_id}
                    title={item.arxiv_id ? `arXiv:${item.arxiv_id}` : item.original_filename || item.job_id}
                    badge={<Pill tone="accent">{item.status}</Pill>}
                    meta={
                      <div className="flex flex-wrap gap-x-3 gap-y-1">
                        <span>{item.source_type}</span>
                        {item.paper_id ? <span>paper:{item.paper_id}</span> : null}
                        <span>job:{item.job_id}</span>
                      </div>
                    }
                    alert={item.error ? <p className="text-xs text-[color:var(--px-shell-danger)]">{item.error}</p> : null}
                    className="bg-[color:var(--px-shell-panel-strong)]"
                  />
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
