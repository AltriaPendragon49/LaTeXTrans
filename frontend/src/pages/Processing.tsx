import { useEffect } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { AlertTriangle, CheckCircle2, Code, Download, LogIn, RotateCw } from "lucide-react"

import { API_BASE_URL } from "@/api-base"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { LogViewer } from "@/components/log-viewer"
import { useAuth } from "@/contexts/AuthContext"
import { getTaskCopy } from "@/i18n/task-copy"
import { useStore } from "@/store/useStore"
import { useTranslation } from "react-i18next"

const stepOrder = ["downloading", "translating", "validating", "compiling"] as const

export default function ProcessingPage() {
  const {
    taskId: storeTaskId,
    status,
    stage,
    detailCode,
    detailParams,
    failureReasonCode,
    logs,
    pollStatus,
    stopPolling,
    setTaskId,
    taskWarnings,
  } = useStore()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const { t } = useTranslation()

  const urlTaskId = searchParams.get("taskId")
  const effectiveTaskId = urlTaskId || storeTaskId
  const isGuest = !user

  useEffect(() => {
    if (urlTaskId && urlTaskId !== storeTaskId) {
      setTaskId(urlTaskId)
    }
  }, [urlTaskId, storeTaskId, setTaskId])

  useEffect(() => {
    if (effectiveTaskId) {
      pollStatus()
    }
    return () => stopPolling()
  }, [effectiveTaskId, pollStatus, stopPolling])

  const normalizedStatus = (status || "").toLowerCase()
  const normalizedStage = ((stage === "extracting" ? "downloading" : stage) || "").toLowerCase()
  const canPreview =
    normalizedStatus === "completed" || normalizedStatus === "completed_with_warnings"
  const isFailed = ["failed", "failed_compilation", "structure_invalid"].includes(normalizedStatus)

  const copy = getTaskCopy(t, {
    status,
    stage: normalizedStage,
    detailCode,
    detailParams,
    failureReasonCode,
    warnings: taskWarnings,
  })

  const steps = [
    { id: "downloading", label: t("task.stage.downloading") },
    { id: "translating", label: t("task.stage.translating") },
    { id: "validating", label: t("task.stage.validating") },
    { id: "compiling", label: t("task.stage.compiling") },
  ]

  const currentStepIndex = (() => {
    if (canPreview) {
      return stepOrder.length
    }

    if (normalizedStage === "downloading" || normalizedStage === "downloading_pdf") {
      return 0
    }
    if (normalizedStage === "parsing" || normalizedStage === "translating") {
      return 1
    }
    if (normalizedStage === "validating") {
      return 2
    }
    if (normalizedStage === "compiling" || normalizedStage === "compilation_failed") {
      return 3
    }
    if (isFailed) {
      return Math.max(0, stepOrder.indexOf("translating"))
    }

    return 0
  })()

  const activeTaskId = effectiveTaskId
  const currentDetail = copy.detailLabel || copy.stageLabel || copy.statusLabel
  const failureText = copy.failureLabel || copy.statusLabel
  const summaryStepCount = canPreview ? steps.length : Math.min(currentStepIndex + 1, steps.length)
  const summaryTone = canPreview
    ? "border-emerald-500/20 bg-emerald-500/10"
    : isFailed
      ? "border-red-500/20 bg-red-500/10"
      : "border-indigo-500/20 bg-indigo-500/10"
  const summaryAccent = canPreview
    ? "text-emerald-600"
    : isFailed
      ? "text-red-600"
      : "text-indigo-600"

  return (
    <div className="mx-auto flex w-full max-w-[1380px] flex-1 flex-col gap-6 px-6 py-8 xl:px-10">
      {isGuest && (
        <div className="flex items-center gap-3 rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3">
          <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400" />
          <p className="flex-1 text-sm text-amber-300">
            <span className="font-semibold">{t("processing.guest_mode")}</span>
            {t("processing.you_won_t_be_able_to_access_the_translation_results_again_after_leaving_this_page")}
            <button
              onClick={() => navigate("/login")}
              className="ml-2 inline-flex items-center gap-1 underline underline-offset-2 hover:text-amber-200"
            >
              <LogIn className="h-3 w-3" />
              {t("processing.sign_in_to_save_to_history")}
            </button>
          </p>
        </div>
      )}

      {taskWarnings && (
        <div className="flex items-start gap-3 rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
          <p className="flex-1 text-sm text-amber-300">
            <span className="font-semibold">{t("processing.formatting_note")}</span>
            {t("task.detail.formattingWarning", { warningText: taskWarnings })}
          </p>
        </div>
      )}

      <div className="flex flex-col gap-4 rounded-[28px] border border-border/60 bg-gradient-to-br from-background via-background to-muted/20 px-6 py-6 shadow-[0_18px_45px_rgba(15,23,42,0.06)] lg:flex-row lg:items-center lg:justify-between">
        <div className="max-w-2xl">
          <h1 className="text-3xl font-bold tracking-tight">
            {canPreview ? t("task.result.completed") : t("task.result.inProgress")}
          </h1>
          <p className="mt-2 text-muted-foreground">
            {t("processing.track_translation_task_status_in_real_time")}
          </p>
        </div>

        {canPreview ? (
          <div className="flex flex-wrap gap-2 lg:justify-end">
            <Button
              variant="outline"
              onClick={() => window.open(`${API_BASE_URL}/api/download/${activeTaskId}/source`, "_blank")}
            >
              <Download className="mr-2 h-4 w-4" />
              {t("task.steps.downloadSource")}
            </Button>
            <Button
              className="bg-emerald-600 hover:bg-emerald-700"
              onClick={() => navigate("/preview")}
            >
              {t("common.actions.viewResult")}
            </Button>
          </div>
        ) : isFailed ? (
          <Button variant="outline" onClick={() => navigate("/")}>
            {t("common.actions.backToHome")}
          </Button>
        ) : (
          <Button variant="destructive" onClick={() => navigate("/")}>
            {t("processing.cancel_task")}
          </Button>
        )}
      </div>

      <div
        data-testid="processing-workbench"
        className="grid flex-1 grid-cols-1 gap-6 xl:grid-cols-[minmax(380px,0.95fr)_minmax(0,1.25fr)]"
      >
        <div data-testid="processing-summary-panel" className="grid content-start gap-6">
          <Card className="overflow-hidden border-border/60 bg-card/95 shadow-[0_18px_45px_rgba(15,23,42,0.06)]">
            <CardHeader className="gap-2 border-b border-border/60 pb-5">
              <CardTitle>{t("processing.task_status")}</CardTitle>
              <CardDescription>{currentDetail}</CardDescription>
            </CardHeader>
            <CardContent className="px-6 pb-6 pt-5">
              <div className="relative ml-3 space-y-7 border-l-2 border-slate-200 py-1 pl-6 dark:border-slate-800">
                {steps.map((step, index) => {
                  const isActive = !canPreview && !isFailed && index === currentStepIndex
                  const isFailedStep = isFailed && index === currentStepIndex
                  const isCompleted = index < currentStepIndex || canPreview

                  return (
                    <div key={step.id} className="relative">
                      <span
                        className={`absolute -left-[31px] flex h-6 w-6 items-center justify-center rounded-full border-2 bg-background ${
                          isCompleted
                            ? "border-emerald-500 bg-emerald-500 text-white"
                            : isFailedStep
                              ? "border-red-500 bg-red-500 text-white"
                              : isActive
                                ? "animate-pulse border-2 border-indigo-500"
                                : "border-slate-300"
                        }`}
                      >
                        {isCompleted && <CheckCircle2 className="h-3 w-3" />}
                        {isFailedStep && <AlertTriangle className="h-3 w-3" />}
                        {isActive && <RotateCw className="h-3 w-3 animate-spin text-indigo-500" />}
                      </span>
                      <div className="flex flex-col">
                        <span
                          className={`text-sm font-medium ${
                            isActive
                              ? "text-indigo-600"
                              : isCompleted
                                ? "text-emerald-600"
                                : isFailedStep
                                  ? "text-red-600"
                                  : "text-slate-500"
                          }`}
                        >
                          {step.label}
                        </span>
                        {isActive && (
                          <span className="animate-pulse text-xs text-muted-foreground">
                            {currentDetail}
                          </span>
                        )}
                        {isFailedStep && (
                          <span className="text-xs text-red-600">{failureText}</span>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>

          <Card
            className={`overflow-hidden border-border/60 shadow-[0_18px_45px_rgba(15,23,42,0.06)] ${summaryTone}`}
          >
            <CardContent className="flex min-h-[220px] flex-col justify-between p-6">
              <div className="flex items-start justify-between gap-4">
                <div className="rounded-2xl border border-background/70 bg-background/80 p-4 shadow-sm">
                  {canPreview ? (
                    <CheckCircle2 className="h-14 w-14 text-emerald-500" />
                  ) : isFailed ? (
                    <AlertTriangle className="h-14 w-14 text-red-500" />
                  ) : (
                    <RotateCw className="h-14 w-14 animate-spin text-indigo-500" />
                  )}
                </div>
                <div className="rounded-full border border-border/70 bg-background/80 px-3 py-1 text-sm font-semibold text-foreground shadow-sm">
                  {summaryStepCount}/{steps.length}
                </div>
              </div>

              {canPreview ? (
                <div className="space-y-3">
                  <p className={`text-sm font-medium ${summaryAccent}`}>{copy.statusLabel}</p>
                  <div className="space-y-1">
                    <p className="text-2xl font-semibold tracking-tight text-foreground">
                      {t("task.result.completed")}
                    </p>
                    <p className="text-sm text-muted-foreground">{currentDetail}</p>
                  </div>
                </div>
              ) : isFailed ? (
                <div className="space-y-3">
                  <p className={`text-sm font-medium ${summaryAccent}`}>{copy.statusLabel}</p>
                  <div className="space-y-1">
                    <p className="text-2xl font-semibold tracking-tight text-foreground">
                      {t("task.result.failed")}
                    </p>
                    <p className="text-sm text-muted-foreground">{failureText}</p>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  <p className={`text-sm font-medium ${summaryAccent}`}>
                    {copy.stageLabel || copy.statusLabel}
                  </p>
                  <div className="space-y-1">
                    <p className="text-2xl font-semibold tracking-tight text-foreground">
                      {currentDetail}
                    </p>
                    <p className="text-sm text-muted-foreground">{copy.statusLabel}</p>
                  </div>
                  {copy.isRateLimited && (
                    <div className="flex animate-pulse items-center gap-2 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2">
                      <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400" />
                      <p className="text-left text-xs text-amber-500 dark:text-amber-400">
                        {copy.detailLabel}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div data-testid="processing-log-panel" className="min-w-0">
          <Card className="flex h-full min-h-[440px] flex-col overflow-hidden border-border/60 bg-card/95 shadow-[0_24px_55px_rgba(15,23,42,0.08)] lg:min-h-[620px]">
            <CardHeader className="flex flex-col gap-3 border-b border-border/60 pb-5 sm:flex-row sm:items-center sm:justify-between">
              <div className="space-y-2">
                <CardTitle>{t("processing.live_logs")}</CardTitle>
                <CardDescription>{currentDetail}</CardDescription>
              </div>
              <div className="flex gap-2 self-start sm:self-auto">
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                  <Code className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="flex flex-1 px-6 pb-6 pt-5">
              <LogViewer
                logs={logs}
                className="h-full min-h-[360px] w-full rounded-2xl border-slate-900/80 bg-slate-950/95 px-4 py-4 text-[13px] leading-6 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] lg:min-h-[520px]"
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
