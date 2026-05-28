import { useTranslationStore } from "@/features/translation-workflow/store/useTranslationStore"

/**
 * 翻译任务 Hook
 * 从全局 Zustand store 中选取与当前翻译任务相关的状态和操作方法
 * @returns 包含 taskId、status、stage、logs、轮询控制、下载进度等任务相关数据和方法
 */
export function useTranslationTask() {
  const taskId = useTranslationStore((state) => state.taskId)
  const arxivId = useTranslationStore((state) => state.arxivId)
  const status = useTranslationStore((state) => state.status)
  const stage = useTranslationStore((state) => state.stage)
  const progress = useTranslationStore((state) => state.progress)
  const message = useTranslationStore((state) => state.message)
  const detailCode = useTranslationStore((state) => state.detailCode)
  const detailParams = useTranslationStore((state) => state.detailParams)
  const failureReasonCode = useTranslationStore((state) => state.failureReasonCode)
  const logs = useTranslationStore((state) => state.logs)
  const error = useTranslationStore((state) => state.error)
  const isPolling = useTranslationStore((state) => state.isPolling)
  const taskWarnings = useTranslationStore((state) => state.taskWarnings)
  const outputMetrics = useTranslationStore((state) => state.outputMetrics)
  const downloadProgress = useTranslationStore((state) => state.downloadProgress)
  const downloadStage = useTranslationStore((state) => state.downloadStage)
  const isDownloading = useTranslationStore((state) => state.isDownloading)
  const setTaskId = useTranslationStore((state) => state.setTaskId)
  const setArxivId = useTranslationStore((state) => state.setArxivId)
  const reset = useTranslationStore((state) => state.reset)
  const resetTranslationState = useTranslationStore((state) => state.resetTranslationState)
  const startArxivDownload = useTranslationStore((state) => state.startArxivDownload)
  const pollDownloadProgress = useTranslationStore((state) => state.pollDownloadProgress)
  const startTranslation = useTranslationStore((state) => state.startTranslation)
  const pollStatus = useTranslationStore((state) => state.pollStatus)
  const stopPolling = useTranslationStore((state) => state.stopPolling)

  return {
    taskId,
    arxivId,
    status,
    stage,
    progress,
    message,
    detailCode,
    detailParams,
    failureReasonCode,
    logs,
    error,
    isPolling,
    taskWarnings,
    outputMetrics,
    downloadProgress,
    downloadStage,
    isDownloading,
    setTaskId,
    setArxivId,
    reset,
    resetTranslationState,
    startArxivDownload,
    pollDownloadProgress,
    startTranslation,
    pollStatus,
    stopPolling,
  }
}
