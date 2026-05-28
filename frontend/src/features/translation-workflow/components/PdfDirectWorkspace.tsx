import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Download, FileText, Info, Loader2, Upload, X, ExternalLink, List } from "lucide-react"

import { Button } from "@/ui/button/Button"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { PanelShell } from "@/ui/panel-shell/PanelShell"
import { useAuth } from "@/contexts/AuthContext"
import { LoginPrompt } from "@/features/auth-shell/components/LoginPrompt"
import { API_BASE_URL } from "@/api-base"

interface PdfDirectTask {
  task_id: string
  file_name?: string
  page_num?: number | null
  progress?: number | null
  trans_status?: number
  trans_failure_cause?: string | null
  status?: string
  has_artifact?: boolean
  created_at?: string
  completed_at?: string
}

interface TaskListResponse {
  tasks: PdfDirectTask[]
  quota_snapshot?: Record<string, unknown>
}

const POLL_INTERVAL_MS = 2000

async function apiPost(path: string, body?: FormData | object): Promise<Response> {
  const token = getAccessToken()
  const headers: Record<string, string> = {}
  if (token) headers["Authorization"] = `Bearer ${token}`

  if (body instanceof FormData) {
    return fetch(`${API_BASE_URL}${path}`, { method: "POST", headers, body })
  }
  headers["Content-Type"] = "application/json"
  return fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })
}

async function apiGet(path: string): Promise<Response> {
  const token = getAccessToken()
  const headers: Record<string, string> = {}
  if (token) headers["Authorization"] = `Bearer ${token}`
  return fetch(`${API_BASE_URL}${path}`, { headers })
}

function getAccessToken(): string | null {
  try {
    const raw = localStorage.getItem("latextrans.localAuth.session")
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return parsed?.access_token ?? null
  } catch {
    return null
  }
}

function statusLabel(transStatus: number | undefined, t: (key: string) => string): string {
  switch (transStatus) {
    case 101: return t("pdfDirect.status.ready")
    case 103: return t("pdfDirect.status.processing")
    case 104: return t("pdfDirect.status.canceled")
    case 105: return t("pdfDirect.status.completed")
    case 106: return t("pdfDirect.status.failed")
    default: return t("pdfDirect.status.ready")
  }
}

export function PdfDirectWorkspace() {
  const { t } = useTranslation()
  const { user, refreshQuotaSnapshot } = useAuth()
  const isAuthenticated = !!user

  const [uploadedTask, setUploadedTask] = useState<PdfDirectTask | null>(null)
  const [taskList, setTaskList] = useState<PdfDirectTask[]>([])
  const [isLoadingList, setIsLoadingList] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [isStarting, setIsStarting] = useState(false)
  const [isDownloading, setIsDownloading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [errorCode, setErrorCode] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const fetchTaskList = useCallback(async () => {
    setIsLoadingList(true)
    try {
      const response = await apiGet("/api/pdf-direct")
      if (response.ok) {
        const data: TaskListResponse = await response.json()
        setTaskList(data.tasks ?? [])
      }
    } catch {
      /* ignore list fetch errors */
    } finally {
      setIsLoadingList(false)
    }
  }, [])

  useEffect(() => {
    if (isAuthenticated) {
      void fetchTaskList()
    }
  }, [isAuthenticated, fetchTaskList])

  useEffect(() => {
    return () => {
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current)
    }
  }, [])

  function clearError() {
    setError(null)
    setErrorCode(null)
  }

  function stopPolling() {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current)
      pollTimerRef.current = null
    }
  }

  function selectTask(task: PdfDirectTask) {
    stopPolling()
    clearError()
    setUploadedTask(task)
    // Auto-resume polling for processing tasks
    if (task.trans_status === 103) {
      startPolling(task.task_id)
    }
  }

  async function handleFileSelect(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    clearError()

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError(t("pdfDirect.errors.onlyPdf"))
      return
    }

    setIsUploading(true)
    try {
      const formData = new FormData()
      formData.append("file", file)

      const response = await apiPost("/api/pdf-direct/upload", formData)
      const data = await response.json()

      if (!response.ok) {
        handleApiError(data, response.status)
        return
      }

      setUploadedTask(data)
      void refreshQuotaSnapshot()
      void fetchTaskList()
      toast.success(t("pdfDirect.uploadSuccess"))
    } catch {
      setError(t("pdfDirect.errors.network"))
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  async function handleStart(taskOverride?: PdfDirectTask) {
    const task = taskOverride ?? uploadedTask
    if (!task) return
    clearError()
    setIsStarting(true)

    try {
      const response = await apiPost(`/api/pdf-direct/${task.task_id}/start`)
      const data = await response.json()

      if (!response.ok) {
        handleApiError(data, response.status)
        return
      }

      setUploadedTask(data)
      void refreshQuotaSnapshot()
      void fetchTaskList()
      startPolling(task.task_id)
    } catch {
      setError(t("pdfDirect.errors.network"))
    } finally {
      setIsStarting(false)
    }
  }

  function startPolling(taskId: string) {
    stopPolling()

    async function poll() {
      try {
        const response = await apiPost(`/api/pdf-direct/${taskId}/poll`)
        const data = await response.json()

        if (!response.ok) {
          stopPolling()
          handleApiError(data, response.status)
          void fetchTaskList()
          return
        }

        setUploadedTask(data)

        const terminalStatuses = [104, 105, 106]
        if (terminalStatuses.includes(data.trans_status)) {
          stopPolling()
          void refreshQuotaSnapshot()
          void fetchTaskList()
          if (data.trans_status === 105) {
            toast.success(t("pdfDirect.translationComplete"))
          }
        } else {
          pollTimerRef.current = setTimeout(poll, POLL_INTERVAL_MS)
        }
      } catch {
        stopPolling()
        void fetchTaskList()
      }
    }

    pollTimerRef.current = setTimeout(poll, POLL_INTERVAL_MS)
  }

  async function handleCancel() {
    if (!uploadedTask) return
    stopPolling()
    clearError()

    try {
      const response = await apiPost(`/api/pdf-direct/${uploadedTask.task_id}/cancel`)
      const data = await response.json()

      if (!response.ok) {
        handleApiError(data, response.status)
        return
      }

      setUploadedTask(data)
      void refreshQuotaSnapshot()
      void fetchTaskList()
      toast.info(t("pdfDirect.canceled"))
    } catch {
      setError(t("pdfDirect.errors.network"))
    }
  }

  async function handleDownload() {
    if (!uploadedTask) return
    setIsDownloading(true)
    clearError()

    try {
      const response = await apiGet(`/api/pdf-direct/${uploadedTask.task_id}/download`)

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        handleApiError(data, response.status)
        return
      }

      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `translated_${uploadedTask.file_name ?? uploadedTask.task_id}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      setError(t("pdfDirect.errors.downloadFailed"))
    } finally {
      setIsDownloading(false)
    }
  }

  function handleApiError(data: Record<string, unknown>, status: number) {
    const code = typeof data.code === "string" ? data.code : null
    const message = typeof data.message === "string" ? data.message : null
    setErrorCode(code)

    if (code === "PDF_DIRECT_CREDIT_INSUFFICIENT") {
      setError(t("pdfDirect.errors.insufficientCredits"))
    } else if (code === "PDF_DIRECT_CREDENTIAL_UNAVAILABLE") {
      setError(t("pdfDirect.errors.credentialUnavailable"))
    } else if (code === "PDF_DIRECT_VALIDATION_ERROR") {
      setError(message ?? t("pdfDirect.errors.validationFailed"))
    } else if (code === "PDF_DIRECT_LIMIT_ERROR") {
      setError(message ?? t("pdfDirect.errors.limitExceeded"))
    } else if (code === "PDF_DIRECT_RETRYABLE_ERROR") {
      setError(t("pdfDirect.errors.serviceBusy"))
    } else if (code === "PDF_DIRECT_NOT_READY") {
      setError(t("pdfDirect.errors.notReady"))
    } else if (status === 401) {
      setError(t("pdfDirect.errors.loginRequired"))
    } else {
      setError(message ?? t("pdfDirect.errors.unknown"))
    }
  }

  function resetWorkspace() {
    stopPolling()
    setUploadedTask(null)
    clearError()
  }

  const isTerminal = uploadedTask && [104, 105, 106].includes(uploadedTask.trans_status ?? 0)
  const isProcessing = uploadedTask?.trans_status === 103
  const isReady = uploadedTask?.trans_status === 101
  const progressPercent = uploadedTask?.progress != null ? Math.round(uploadedTask.progress * 100) : 0

  if (!isAuthenticated) {
    return (
      <LoginPrompt
        messageKey="pdfDirect.loginRequired"
        descriptionKey="pdfDirect.loginRequiredDescription"
      />
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <FileText className="h-5 w-5 text-[color:var(--px-shell-accent)]" />
        <h3 className="text-lg font-bold text-[color:var(--px-shell-ink)]">{t("pdfDirect.title")}</h3>
      </div>
      <p className="text-sm text-[color:var(--px-shell-muted)]">
        {t("pdfDirect.description")}
      </p>

      {/* Upload area + current task workspace */}
      <div className="rounded-lg border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] p-6">
        {!uploadedTask ? (
          <div className="space-y-4">
            <div className="flex flex-col items-center gap-4 rounded-lg border-2 border-dashed border-[color:var(--px-shell-line)] p-8 text-center">
              <Upload className="h-10 w-10 text-[color:var(--px-shell-muted)]" />
              <p className="text-sm text-[color:var(--px-shell-muted)]">
                {t("pdfDirect.uploadPrompt")}
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                onChange={handleFileSelect}
                className="hidden"
              />
              <Button
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                className="gap-2"
              >
                {isUploading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="h-4 w-4" />
                )}
                {isUploading ? t("pdfDirect.uploading") : t("pdfDirect.selectPdf")}
              </Button>
            </div>
            <p className="text-center text-xs text-[color:var(--px-shell-muted)]">
              {t("pdfDirect.supportedNote")}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <span className="font-bold text-[color:var(--px-shell-ink)]">
                  {uploadedTask.file_name}
                </span>
                {uploadedTask.page_num != null && (
                  <span className="ml-3 text-sm text-[color:var(--px-shell-muted)]">
                    {t("pdfDirect.pageCount", { count: uploadedTask.page_num })}
                  </span>
                )}
              </div>
              {!isProcessing && (
                <Button variant="ghost" size="sm" onClick={resetWorkspace}>
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>

            {isReady && (
              <Button onClick={() => handleStart()} disabled={isStarting} className="w-full gap-2" size="lg">
                {isStarting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Download className="h-4 w-4" />
                )}
                {isStarting ? t("pdfDirect.starting") : t("pdfDirect.startTranslation")}
              </Button>
            )}

            {isProcessing && (
              <PanelShell tone="glass" className="space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-bold text-[color:var(--px-shell-ink)]">
                    {t("pdfDirect.status.processing")}
                  </span>
                  <span className="font-mono text-[color:var(--px-shell-muted)]">{progressPercent}%</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-[color:var(--px-shell-line)]">
                  <div
                    className="h-full rounded-full bg-[color:var(--px-shell-accent)] transition-all duration-300 ease-out"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
                <div className="flex justify-end">
                  <Button variant="ghost" size="sm" onClick={handleCancel} className="text-red-500">
                    {t("pdfDirect.cancel")}
                  </Button>
                </div>
              </PanelShell>
            )}

            {isTerminal && uploadedTask.trans_status === 105 && (
              <div className="space-y-3">
                <PanelShell tone="success" className="space-y-2">
                  <p className="font-bold text-green-600">{t("pdfDirect.status.completed")}</p>
                </PanelShell>
                <Button onClick={handleDownload} disabled={isDownloading} className="w-full gap-2" size="lg">
                  {isDownloading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Download className="h-4 w-4" />
                  )}
                  {isDownloading ? t("pdfDirect.downloading") : t("pdfDirect.download")}
                </Button>
              </div>
            )}

            {isTerminal && uploadedTask.trans_status === 106 && (
              <PanelShell tone="danger" className="space-y-2">
                <p className="font-bold text-red-500">{t("pdfDirect.status.failed")}</p>
                {uploadedTask.trans_failure_cause && (
                  <p className="text-sm text-[color:var(--px-shell-muted)]">
                    {uploadedTask.trans_failure_cause}
                  </p>
                )}
              </PanelShell>
            )}

            {isTerminal && uploadedTask.trans_status === 104 && (
              <PanelShell tone="glass" className="space-y-2">
                <p className="font-bold text-[color:var(--px-shell-muted)]">{t("pdfDirect.status.canceled")}</p>
              </PanelShell>
            )}
          </div>
        )}
      </div>

      {error && (
        <NoticeBanner
          tone={errorCode === "PDF_DIRECT_CREDIT_INSUFFICIENT" ? "warning" : "danger"}
          icon={<Info className="h-4 w-4" />}
          description={error}
          className="animate-in fade-in"
          action={
            errorCode === "PDF_DIRECT_CREDIT_INSUFFICIENT" ? (
              <a
                href="https://niutrans.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm font-medium underline"
              >
                {t("pdfDirect.recharge")}
                <ExternalLink className="h-3 w-3" />
              </a>
            ) : errorCode === "PDF_DIRECT_CREDENTIAL_UNAVAILABLE" ? (
              <Button variant="ghost" size="sm" onClick={() => window.location.reload()}>
                {t("pdfDirect.reLogin")}
              </Button>
            ) : (
              <X className="h-4 w-4 opacity-50 cursor-pointer" onClick={clearError} />
            )
          }
        />
      )}

      {/* Task list */}
      <div className="rounded-lg border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] p-6">
        <div className="mb-4 flex items-center gap-2">
          <List className="h-4 w-4 text-[color:var(--px-shell-muted)]" />
          <h4 className="text-sm font-bold text-[color:var(--px-shell-ink)]">{t("pdfDirect.taskList")}</h4>
        </div>

        {isLoadingList && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-[color:var(--px-shell-muted)]" />
          </div>
        )}

        {!isLoadingList && taskList.length === 0 && (
          <p className="py-6 text-center text-sm text-[color:var(--px-shell-muted)]">
            {t("pdfDirect.taskList.empty")}
          </p>
        )}

        {!isLoadingList && taskList.length > 0 && (
          <div className="divide-y divide-[color:var(--px-shell-line)]">
            {taskList.map((task) => (
              <div
                key={task.task_id}
                className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-[color:var(--px-shell-ink)]">
                    {task.file_name ?? task.task_id}
                  </p>
                  <p className="text-xs text-[color:var(--px-shell-muted)]">
                    <span className={task.trans_status === 105 ? "text-green-600" : task.trans_status === 106 ? "text-red-500" : ""}>
                      {statusLabel(task.trans_status, t)}
                    </span>
                    {task.page_num != null && (
                      <span className="ml-3">{t("pdfDirect.pageCount", { count: task.page_num })}</span>
                    )}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {task.trans_status === 101 && (
                    <Button
                      size="sm"
                      className="gap-1"
                      onClick={() => {
                        selectTask(task)
                        handleStart(task)
                      }}
                    >
                      <Download className="h-3.5 w-3.5" />
                      {t("pdfDirect.startTranslation")}
                    </Button>
                  )}
                  {task.trans_status === 105 && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="gap-1"
                      onClick={() => {
                        selectTask(task)
                      }}
                    >
                      <Download className="h-3.5 w-3.5" />
                      {t("pdfDirect.download")}
                    </Button>
                  )}
                  {task.trans_status !== 101 && task.trans_status !== 105 && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => selectTask(task)}
                    >
                      {t("pdfDirect.taskList.view")}
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
