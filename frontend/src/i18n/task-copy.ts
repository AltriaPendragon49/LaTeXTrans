/**
 * 任务文案翻译工具
 * 根据任务状态、阶段、详情代码和失败原因生成对应的国际化文案
 */

type Translate = (key: string, options?: Record<string, unknown>) => string

/** 任务详情参数类型 */
export type TaskDetailParams = Record<string, string | number | boolean | null> | null | undefined

/** getTaskCopy 的输入参数 */
export interface TaskCopyInput {
  status?: string | null
  stage?: string | null
  detailCode?: string | null
  detailParams?: TaskDetailParams
  failureReasonCode?: string | null
  warnings?: string | null
}

/** 状态 -> 国际化 key 映射 */
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

/** 阶段 -> 国际化 key 映射 */
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

/** 详情代码 -> 国际化 key 映射 */
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

/** 失败原因 -> 国际化 key 映射 */
const failureKeyMap: Record<string, string> = {
  structure_env_stack_mismatch: "task.failure.structureEnvStackMismatch",
  structure_latexwalker_unexpected_closing_env: "task.failure.structureUnexpectedClosingEnv",
}

/** 需要显示 current/total 值的详情代码 */
const valueDetailCodes = new Set([
  "translation_running",
  "translation_retry_failed_chunks",
  "translation_restore_structure",
  "translation_restore_environment",
  "translation_apply_fallback",
])

/** 需要显示百分比的详情代码 */
const percentDetailCodes = new Set([
  "download_source_progress",
  "download_pdf_progress",
])

/** 需要显示警告文本的详情代码 */
const warningDetailCodes = new Set([
  "formatting_warning",
])

/** 标准化状态值为小写 */
function normalizeStatus(status?: string | null) {
  return status?.toLowerCase() ?? ""
}

/** 标准化阶段值，"extracting" 映射为 "downloading" */
function normalizeStage(stage?: string | null) {
  if (!stage) {
    return ""
  }
  return stage === "extracting" ? "downloading" : stage.toLowerCase()
}

/** 根据详情代码构建插值参数 */
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

/** 检查是否需要/具备特定详情代码所需的插值参数 */
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

/**
 * 根据任务状态和阶段获取状态标签
 * @param translate - i18n 翻译函数
 * @param status - 任务状态
 * @param stage - 任务阶段
 */
export function getTaskStatusLabel(
  translate: Translate,
  status?: string | null,
  stage?: string | null,
) {
  const normalizedStatus = normalizeStatus(status)
  const normalizedStage = normalizeStage(stage)

  // processing 状态根据阶段给出更精细的描述
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

/**
 * 获取任务阶段标签
 * @param translate - i18n 翻译函数
 * @param stage - 阶段名
 */
export function getTaskStageLabel(translate: Translate, stage?: string | null) {
  const normalizedStage = normalizeStage(stage)
  const key = stageKeyMap[normalizedStage]
  return key ? translate(key) : (stage ?? "")
}

/**
 * 获取任务失败原因标签
 * @param translate - i18n 翻译函数
 * @param failureReasonCode - 失败原因代码
 */
export function getTaskFailureLabel(
  translate: Translate,
  failureReasonCode?: string | null,
) {
  const key = failureReasonCode ? failureKeyMap[failureReasonCode] : undefined
  return key ? translate(key) : translate("task.failure.generic")
}

/**
 * 获取任务详情标签
 * @param translate - i18n 翻译函数
 * @param detailCode - 详情代码
 * @param detailParams - 详情参数
 * @param stage - 当前阶段（detailCode 为空时回退到阶段标签）
 */
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

/**
 * 聚合获取任务的所有文案标签
 * @param translate - i18n 翻译函数
 * @param input - 任务状态、阶段、详情代码等信息
 * @returns 包含 statusLabel、stageLabel、detailLabel、failureLabel 的对象
 */
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
