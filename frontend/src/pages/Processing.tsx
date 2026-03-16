import { useEffect } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { AlertTriangle, CheckCircle2, Code, Download, LogIn, RotateCw } from "lucide-react"

import { API_BASE_URL } from "@/api-base"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
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

  return (
    <div className="mx-auto max-w-5xl space-y-6">
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

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {canPreview ? t("task.result.completed") : t("task.result.inProgress")}
          </h1>
          <p className="text-muted-foreground">
            {t("processing.track_translation_task_status_in_real_time")}
          </p>
        </div>

        {canPreview ? (
          <div className="flex gap-2">
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

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="col-span-1 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>{t("processing.task_status")}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="relative ml-3 space-y-8 border-l-2 border-slate-200 py-2 pl-6 dark:border-slate-800">
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

          <Card>
            <CardContent className="flex min-h-[200px] items-center justify-center pt-6">
              {canPreview ? (
                <div className="space-y-2 text-center">
                  <CheckCircle2 className="mx-auto h-16 w-16 text-emerald-500" />
                  <p className="font-medium text-emerald-600">{t("task.result.completed")}</p>
                </div>
              ) : isFailed ? (
                <div className="space-y-2 text-center">
                  <AlertTriangle className="mx-auto h-16 w-16 text-red-500" />
                  <p className="font-medium text-red-600">{t("task.result.failed")}</p>
                  <p className="text-xs text-slate-500">{failureText}</p>
                </div>
              ) : (
                <div className="space-y-2 text-center">
                  <RotateCw className="mx-auto h-16 w-16 animate-spin text-indigo-500" />
                  <p className="text-sm font-medium text-foreground">{currentDetail}</p>
                  <p className="text-xs capitalize text-slate-400">{copy.stageLabel || copy.statusLabel}</p>
                  {copy.isRateLimited && (
                    <div className="mt-3 flex animate-pulse items-center gap-2 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2">
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

        <div className="lg:col-span-2">
          <Card className="flex h-full flex-col">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>{t("processing.live_logs")}</CardTitle>
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                  <Code className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="flex-1">
              <LogViewer logs={logs} />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
