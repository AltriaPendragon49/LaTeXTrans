import { AlertTriangle, CheckCircle2, Code, Download, LogIn, RotateCw } from "lucide-react"
import { useEffect } from "react"
import { useTranslation } from "react-i18next"
import { useNavigate, useSearchParams } from "react-router-dom"

import { API_BASE_URL } from "@/api-base"
import { useAuth } from "@/contexts/AuthContext"
import { getTaskCopy } from "@/i18n/task-copy"
import { Button } from "@/ui/button/Button"
import { CardDescription, CardTitle } from "@/ui/card/Card"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { PanelShell } from "@/ui/panel-shell/PanelShell"
import { Pill } from "@/ui/pill/Pill"
import { StatusBadge } from "@/ui/status-badge/StatusBadge"
import { WorkflowStepper, type WorkflowStepState } from "@/ui/workflow-stepper/WorkflowStepper"
import { useTranslationTask } from "../hooks/useTranslationTask"
import { ProcessingLogViewer } from "./ProcessingLogViewer"

/** 处理步骤的顺序定义 */
const stepOrder = ["downloading", "translating", "validating", "compiling"] as const

/**
 * 处理工作区组件
 * 展示翻译任务的处理进度，包括步骤引导、实时日志和结果操作按钮。
 * 支持通过 URL 参数 taskId 恢复任务状态，对未登录用户显示提示横幅
 */
export function ProcessingWorkspace() {
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
  } = useTranslationTask()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const { t } = useTranslation()

  const urlTaskId = searchParams.get("taskId")
  const effectiveTaskId = urlTaskId || storeTaskId
  const isGuest = !user

  // 从 URL 参数恢复任务 ID
  useEffect(() => {
    if (urlTaskId && urlTaskId !== storeTaskId) {
      setTaskId(urlTaskId)
    }
  }, [urlTaskId, storeTaskId, setTaskId])

  // 启动/停止任务状态轮询
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

  /** 计算当前所处的步骤索引 */
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
  const summaryAccent = canPreview
    ? "text-[color:var(--px-shell-success)]"
    : isFailed
      ? "text-[color:var(--px-shell-danger)]"
      : "text-[color:var(--px-shell-accent)]"
  const summaryTone = canPreview ? "success" : isFailed ? "danger" : "accent"

  /** 根据当前进度构建步骤引导项状态列表 */
  const stepperItems = steps.map((step, index) => {
    const state: WorkflowStepState = index < currentStepIndex || canPreview
      ? "complete"
      : isFailed && index === currentStepIndex
        ? "error"
        : !canPreview && !isFailed && index === currentStepIndex
          ? "current"
          : "upcoming"

    return {
      id: step.id,
      label: step.label,
      description:
        !canPreview && !isFailed && index === currentStepIndex
          ? currentDetail
          : isFailed && index === currentStepIndex
            ? failureText
            : null,
      state,
    }
  })

  return (
    <div
      data-testid="processing-shell"
      className="mx-auto flex h-full min-h-0 w-full max-w-[1480px] flex-1 flex-col gap-4 overflow-hidden px-4 py-4 sm:px-6 lg:px-8 xl:px-10 xl:py-6"
    >
      {isGuest ? (
        <NoticeBanner
          tone="warning"
          icon={<AlertTriangle className="h-4 w-4" />}
          title={t("processing.guest_mode")}
          description={t("processing.you_won_t_be_able_to_access_the_translation_results_again_after_leaving_this_page")}
          action={(
            <Button type="button" variant="ghost" size="sm" onClick={() => navigate("/login")}>
              <LogIn className="h-3 w-3" />
              {t("processing.sign_in_to_save_to_history")}
            </Button>
          )}
        />
      ) : null}

      {taskWarnings ? (
        <NoticeBanner
          tone="warning"
          icon={<AlertTriangle className="h-4 w-4" />}
          title={t("processing.formatting_note")}
          description={t("task.detail.formattingWarning", { warningText: taskWarnings })}
        />
      ) : null}

      <PanelShell
        data-testid="processing-hero-panel"
        tone="hero"
        className="flex shrink-0 flex-col gap-4 lg:flex-row lg:items-center lg:justify-between lg:px-6"
      >
        <div className="max-w-2xl">
          <h1 className="text-2xl font-bold tracking-tight text-[color:var(--px-shell-ink)] lg:text-3xl">
            {canPreview ? t("task.result.completed") : t("task.result.inProgress")}
          </h1>
          <p className="mt-1.5 text-sm text-[color:var(--px-shell-muted)] lg:text-base">
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
            <Button onClick={() => navigate("/preview")}>
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
      </PanelShell>

      <div
        data-testid="processing-workbench"
        className="grid min-h-0 flex-1 grid-cols-1 gap-4 xl:grid-cols-[minmax(380px,0.92fr)_minmax(480px,1.08fr)]"
      >
        <div
          data-testid="processing-summary-panel"
          className="grid min-h-0 content-start gap-4 xl:grid-rows-[minmax(0,1.2fr)_minmax(176px,0.8fr)]"
        >
          <PanelShell
            data-testid="processing-status-card"
            padding="none"
            className="flex min-h-0 flex-col overflow-hidden"
          >
            <div className="flex flex-col gap-1.5 border-b border-[color:var(--px-shell-line)] px-6 py-5">
              <CardTitle>{t("processing.task_status")}</CardTitle>
              <CardDescription>{currentDetail}</CardDescription>
            </div>
            <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-5 pb-4 pt-4">
              <WorkflowStepper items={stepperItems} />
            </div>
          </PanelShell>

          <PanelShell
            data-testid="processing-summary-card"
            tone={summaryTone}
            className="overflow-hidden"
          >
            <div className="flex h-full min-h-[176px] flex-col justify-between p-5">
              <div className="flex items-start justify-between gap-3">
                <PanelShell
                  tone="panel"
                  padding="compact"
                  className="rounded-2xl bg-[color:color-mix(in_srgb,var(--px-shell-panel-strong)_88%,white)]"
                >
                  {canPreview ? (
                    <CheckCircle2 className="h-12 w-12 text-[color:var(--px-shell-success)]" />
                  ) : isFailed ? (
                    <AlertTriangle className="h-12 w-12 text-[color:var(--px-shell-danger-strong)]" />
                  ) : (
                    <RotateCw className="h-12 w-12 animate-spin text-[color:var(--px-shell-accent)]" />
                  )}
                </PanelShell>
                <Pill tone="muted" className="px-3 py-1 text-sm font-semibold tracking-normal">
                  {summaryStepCount}/{steps.length}
                </Pill>
              </div>

              {canPreview ? (
                <div className="space-y-2">
                  <p className={`text-sm font-medium ${summaryAccent}`}>{copy.statusLabel}</p>
                  <div className="space-y-1">
                    <p className="text-[1.75rem] font-semibold tracking-tight text-[color:var(--px-shell-ink)]">
                      {t("task.result.completed")}
                    </p>
                    <p className="text-sm text-[color:var(--px-shell-muted)]">{currentDetail}</p>
                  </div>
                </div>
              ) : isFailed ? (
                <div className="space-y-2">
                  <p className={`text-sm font-medium ${summaryAccent}`}>{copy.statusLabel}</p>
                  <div className="space-y-1">
                    <p className="text-[1.75rem] font-semibold tracking-tight text-[color:var(--px-shell-ink)]">
                      {t("task.result.failed")}
                    </p>
                    <p className="text-sm text-[color:var(--px-shell-muted)]">{failureText}</p>
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  <p className={`text-sm font-medium ${summaryAccent}`}>
                    {copy.stageLabel || copy.statusLabel}
                  </p>
                  <div className="space-y-1">
                    <p className="text-[1.75rem] font-semibold tracking-tight text-[color:var(--px-shell-ink)]">
                      {currentDetail}
                    </p>
                    <p className="text-sm text-[color:var(--px-shell-muted)]">{copy.statusLabel}</p>
                  </div>
                  {copy.isRateLimited ? (
                    <div className="flex animate-pulse items-center gap-2 rounded-lg border border-[color:var(--px-shell-warning-line)] bg-[color:var(--px-shell-warning-soft)] px-3 py-2">
                      <AlertTriangle className="h-4 w-4 shrink-0 text-[color:var(--px-shell-warning)]" />
                      <p className="text-left text-xs text-[color:var(--px-shell-warning)]">
                        {copy.detailLabel}
                      </p>
                    </div>
                  ) : null}
                </div>
              )}
            </div>
          </PanelShell>
        </div>

        <div data-testid="processing-log-panel" className="min-h-0 min-w-0">
          <PanelShell padding="none" className="flex h-full min-h-0 flex-col overflow-hidden">
            <div className="flex shrink-0 flex-col gap-3 border-b border-[color:var(--px-shell-line)] px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
              <div className="space-y-2">
                <CardTitle>{t("processing.live_logs")}</CardTitle>
                <CardDescription>{currentDetail}</CardDescription>
              </div>
              <div className="flex gap-2 self-start sm:self-auto">
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                  <Code className="h-4 w-4" />
                </Button>
                <StatusBadge tone={canPreview ? "success" : isFailed ? "danger" : "accent"} size="md">
                  {copy.statusLabel}
                </StatusBadge>
              </div>
            </div>
            <div className="flex min-h-0 flex-1 px-6 pb-6 pt-5">
              <ProcessingLogViewer
                data-testid="processing-log-scroll-region"
                logs={logs}
                className="h-full min-h-0 w-full flex-1 rounded-2xl px-4 py-4 text-[13px] leading-6"
              />
            </div>
          </PanelShell>
        </div>
      </div>
    </div>
  )
}
