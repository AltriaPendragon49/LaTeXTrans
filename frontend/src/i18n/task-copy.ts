type Translate = (key: string, options?: Record<string, unknown>) => string

export type TaskDetailParams = Record<string, string | number | boolean | null> | null | undefined

export interface TaskCopyInput {
  status?: string | null
  stage?: string | null
  detailCode?: string | null
  detailParams?: TaskDetailParams
  failureReasonCode?: string | null
  warnings?: string | null
}

const statusKeyMap: Record<string, string> = {
  pending: "task.status.pending",
  queued: "task.status.queued",
  processing: "task.status.processing",
  completed: "task.status.completed",
  completed_with_warnings: "task.status.completedWithWarnings",
  failed: "task.status.failed",
  failed_compilation: "task.status.failedCompilation",
  structure_invalid: "task.status.structureInvalid",
}

const stageKeyMap: Record<string, string> = {
  idle: "task.stage.idle",
  downloading: "task.stage.downloading",
  downloading_pdf: "task.stage.downloadingPdf",
  validating: "task.stage.validating",
  parsing: "task.stage.parsing",
  translating: "task.stage.translating",
  compiling: "task.stage.compiling",
  compilation_failed: "task.stage.compilationFailed",
  done: "task.stage.done",
}

const detailKeyMap: Record<string, string> = {
  task_queued: "task.detail.taskQueued",
  task_waiting: "task.detail.taskWaiting",
  download_source_starting: "task.detail.downloadSourceStarting",
  download_source_progress: "task.detail.downloadSourceProgress",
  download_source_complete: "task.detail.downloadSourceComplete",
  download_pdf_starting: "task.detail.downloadPdfStarting",
  download_pdf_progress: "task.detail.downloadPdfProgress",
  download_pdf_complete: "task.detail.downloadPdfComplete",
  validate_source_starting: "task.detail.validateSourceStarting",
  validate_source_complete: "task.detail.validateSourceComplete",
  translation_starting: "task.detail.translationStarting",
  translation_running: "task.detail.translationRunning",
  translation_retry_failed_chunks: "task.detail.translationRetryFailedChunks",
  translation_restore_structure: "task.detail.translationRestoreStructure",
  translation_restore_environment: "task.detail.translationRestoreEnvironment",
  translation_apply_fallback: "task.detail.translationApplyFallback",
  translation_validate_results: "task.detail.translationValidateResults",
  formatting_apply_config: "task.detail.formattingApplyConfig",
  formatting_warning: "task.detail.formattingWarning",
  compile_prepare_pdf: "task.detail.compilePreparePdf",
  compile_running: "task.detail.compileRunning",
  compile_complete: "task.detail.compileComplete",
  task_rate_limited_retrying: "task.detail.rateLimitedRetrying",
}

const failureKeyMap: Record<string, string> = {
  structure_env_stack_mismatch: "task.failure.structureEnvStackMismatch",
  structure_latexwalker_unexpected_closing_env: "task.failure.structureUnexpectedClosingEnv",
}

const valueDetailCodes = new Set([
  "translation_running",
  "translation_retry_failed_chunks",
  "translation_restore_structure",
  "translation_restore_environment",
  "translation_apply_fallback",
])

const percentDetailCodes = new Set([
  "download_source_progress",
  "download_pdf_progress",
])

const warningDetailCodes = new Set([
  "formatting_warning",
])

function normalizeStatus(status?: string | null) {
  return status?.toLowerCase() ?? ""
}

function normalizeStage(stage?: string | null) {
  if (!stage) {
    return ""
  }
  return stage === "extracting" ? "downloading" : stage.toLowerCase()
}

function getDetailValues(detailCode?: string | null, detailParams?: TaskDetailParams) {
  if (!detailParams) {
    return undefined
  }

  const params = { ...detailParams }
  const current = params.current
  const total = params.total

  if (
    (detailCode === "translation_running" ||
      detailCode === "translation_retry_failed_chunks" ||
      detailCode === "translation_restore_structure" ||
      detailCode === "translation_restore_environment" ||
      detailCode === "translation_apply_fallback") &&
    current != null &&
    total != null
  ) {
    return {
      ...params,
      value: `${current}/${total}`,
    }
  }

  if (typeof params.warning_text === "string") {
    return {
      ...params,
      warningText: params.warning_text,
    }
  }

  if (typeof params.retry_in_seconds === "number") {
    return {
      ...params,
      retryInSeconds: params.retry_in_seconds,
    }
  }

  return params
}

function hasRequiredDetailValues(
  detailCode?: string | null,
  detailValues?: Record<string, string | number | boolean | null>,
) {
  if (!detailCode) {
    return true
  }

  if (valueDetailCodes.has(detailCode)) {
    return typeof detailValues?.value === "string" && detailValues.value.length > 0
  }

  if (percentDetailCodes.has(detailCode)) {
    return detailValues?.percent != null
  }

  if (warningDetailCodes.has(detailCode)) {
    return typeof detailValues?.warningText === "string" && detailValues.warningText.length > 0
  }

  return true
}

export function getTaskStatusLabel(
  translate: Translate,
  status?: string | null,
  stage?: string | null,
) {
  const normalizedStatus = normalizeStatus(status)
  const normalizedStage = normalizeStage(stage)

  if (normalizedStatus === "processing") {
    if (normalizedStage === "downloading" || normalizedStage === "downloading_pdf") {
      return translate("task.status.downloading")
    }
    if (normalizedStage === "translating" || normalizedStage === "parsing") {
      return translate("task.status.translating")
    }
  }

  const key = statusKeyMap[normalizedStatus]
  return key ? translate(key) : (status ?? "")
}

export function getTaskStageLabel(translate: Translate, stage?: string | null) {
  const normalizedStage = normalizeStage(stage)
  const key = stageKeyMap[normalizedStage]
  return key ? translate(key) : (stage ?? "")
}

export function getTaskFailureLabel(
  translate: Translate,
  failureReasonCode?: string | null,
) {
  const key = failureReasonCode ? failureKeyMap[failureReasonCode] : undefined
  return key ? translate(key) : translate("task.failure.generic")
}

export function getTaskDetailLabel(
  translate: Translate,
  detailCode?: string | null,
  detailParams?: TaskDetailParams,
  stage?: string | null,
) {
  if (!detailCode) {
    return getTaskStageLabel(translate, stage)
  }

  const key = detailKeyMap[detailCode]
  if (!key) {
    return getTaskStageLabel(translate, stage)
  }

  const detailValues = getDetailValues(detailCode, detailParams)
  if (!hasRequiredDetailValues(detailCode, detailValues)) {
    return getTaskStageLabel(translate, stage)
  }

  return translate(key, detailValues)
}

export function getTaskCopy(
  translate: Translate,
  {
    status,
    stage,
    detailCode,
    detailParams,
    failureReasonCode,
  }: TaskCopyInput,
) {
  const normalizedStatus = normalizeStatus(status)
  const detailLabel = getTaskDetailLabel(translate, detailCode, detailParams, stage)
  const stageLabel = getTaskStageLabel(translate, stage)
  const statusLabel = getTaskStatusLabel(translate, status, stage)
  const failureLabel =
    normalizedStatus === "failed" ||
    normalizedStatus === "failed_compilation" ||
    normalizedStatus === "structure_invalid"
      ? getTaskFailureLabel(translate, failureReasonCode)
      : null

  return {
    statusLabel,
    stageLabel,
    detailLabel,
    failureLabel,
    isRateLimited: detailCode === "task_rate_limited_retrying",
  }
}
