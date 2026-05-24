import { create } from "zustand"
import { toast } from "sonner"

import { API_BASE_URL } from "@/api-base"
import i18n from "@/i18n"
import { downloadArxiv, getDailyLatexQuotaExceededMessage, getTaskStatus, startTranslation } from "@/lib/api"
import { getAccessToken, isLocalAuthConfigured } from "@/lib/local-auth"
import { DEFAULT_CONFIG, getDefaultTranslationModel } from "@/types/config"
import type { AdvancedConfig, LatexValidation, TranslationConfig } from "@/types/config"
import type { TranslateRequest } from "@/lib/api"

type TaskDetailParams = Record<string, string | number | boolean | null> | null

interface TranslationWorkflowState {
  taskId: string | null
  arxivId: string | null
  status: string
  stage: string
  progress: number
  message: string
  detailCode: string | null
  detailParams: TaskDetailParams
  failureReasonCode: string | null
  logs: string[]
  error: string | null
  isPolling: boolean
  taskWarnings: string | null
  outputMetrics: {
    pdfPath?: string
    translationQuality?: number
  }
  downloadProgress: number
  downloadStage: string
  isDownloading: boolean
  config: TranslationConfig
  latexValidation: LatexValidation | null
  userSettingsLoaded: boolean
  hasSystemApiKey: boolean
  setTaskId: (id: string) => void
  setArxivId: (id: string | null) => void
  reset: () => void
  resetTranslationState: () => void
  setConfig: (config: Partial<TranslationConfig>) => void
  setAdvancedConfig: (config: Partial<AdvancedConfig>) => void
  resetConfig: () => void
  setLatexValidation: (validation: LatexValidation | null) => void
  loadUserSettings: (forceReload?: boolean) => Promise<void>
  invalidateUserSettings: () => void
  startArxivDownload: (arxivId: string) => Promise<void>
  pollDownloadProgress: () => void
  startTranslation: (config: TranslateRequest) => Promise<void>
  pollStatus: () => void
  stopPolling: () => void
}

let pollingInterval: ReturnType<typeof setInterval> | null = null
let downloadPollingInterval: ReturnType<typeof setInterval> | null = null

export const useTranslationStore = create<TranslationWorkflowState>((set, get) => ({
  taskId: null,
  arxivId: null,
  status: "idle",
  stage: "idle",
  progress: 0,
  message: "",
  detailCode: null,
  detailParams: null,
  failureReasonCode: null,
  logs: [],
  error: null,
  isPolling: false,
  taskWarnings: null,
  outputMetrics: {},
  downloadProgress: 0,
  downloadStage: "",
  isDownloading: false,
  config: { ...DEFAULT_CONFIG },
  latexValidation: null,
  userSettingsLoaded: false,
  hasSystemApiKey: false,

  setTaskId: (id) => set({ taskId: id }),
  setArxivId: (id) => set({ arxivId: id }),

  reset: () => {
    if (pollingInterval) clearInterval(pollingInterval)
    if (downloadPollingInterval) clearInterval(downloadPollingInterval)
    pollingInterval = null
    downloadPollingInterval = null
    set({
      taskId: null,
      arxivId: null,
      status: "idle",
      stage: "idle",
      progress: 0,
      message: "",
      detailCode: null,
      detailParams: null,
      failureReasonCode: null,
      logs: [],
      error: null,
      isPolling: false,
      outputMetrics: {},
      config: { ...DEFAULT_CONFIG },
      latexValidation: null,
      isDownloading: false,
      downloadProgress: 0,
      downloadStage: "",
      userSettingsLoaded: false,
      hasSystemApiKey: false,
    })
  },

  resetTranslationState: () => {
    if (pollingInterval) clearInterval(pollingInterval)
    if (downloadPollingInterval) clearInterval(downloadPollingInterval)
    pollingInterval = null
    downloadPollingInterval = null
    set({
      taskId: null,
      arxivId: null,
      status: "idle",
      stage: "idle",
      progress: 0,
      message: "",
      detailCode: null,
      detailParams: null,
      failureReasonCode: null,
      logs: [],
      error: null,
      isPolling: false,
      taskWarnings: null,
      outputMetrics: {},
      latexValidation: null,
      isDownloading: false,
      downloadProgress: 0,
      downloadStage: "",
    })
  },

  setConfig: (newConfig) =>
    set((state) => ({
      config: {
        ...state.config,
        ...newConfig,
        advanced_config: newConfig.advanced_config
          ? { ...state.config.advanced_config, ...newConfig.advanced_config }
          : state.config.advanced_config,
      },
    })),

  setAdvancedConfig: (advancedConfig) =>
    set((state) => ({
      config: {
        ...state.config,
        advanced_config: {
          ...state.config.advanced_config,
          ...advancedConfig,
        },
      },
    })),

  resetConfig: () =>
    set({
      config: { ...DEFAULT_CONFIG },
    }),

  setLatexValidation: (validation) => set({ latexValidation: validation }),

  loadUserSettings: async (forceReload = false) => {
    if (get().userSettingsLoaded && !forceReload) return

    try {
      if (!isLocalAuthConfigured()) {
        set({ userSettingsLoaded: true })
        return
      }

      const token = await getAccessToken()
      if (!token) {
        set({ userSettingsLoaded: true })
        return
      }

      const response = await fetch(`${API_BASE_URL}/api/settings`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      })

      if (!response.ok) {
        console.warn("[Settings] Failed to load user settings:", response.status)
        set({ userSettingsLoaded: true })
        return
      }

      const settings = await response.json()

      const hasSystemApiKey = settings.has_custom_api_key || false
      const newConfig: Partial<TranslationConfig> = {
        source_language: settings.default_source_language || "en",
        target_language: settings.default_target_language || "zh",
        advanced_config: {
          translation_mode: settings.translation_mode || "full",
          compile_strategy: settings.compile_strategy || "auto",
          generate_terminology_table: settings.generate_glossary ?? true,
          translation_model: settings.translation_model || getDefaultTranslationModel(),
          use_author_api: settings.use_author_api ?? true,
          custom_base_url: settings.custom_base_url || undefined,
          formatting: settings.default_formatting || undefined,
        },
      }

      set((state) => ({
        config: {
          ...state.config,
          ...newConfig,
          advanced_config: {
            ...state.config.advanced_config,
            ...newConfig.advanced_config,
          },
        },
        userSettingsLoaded: true,
        hasSystemApiKey,
      }))
    } catch (error) {
      console.error("[Settings] Error loading user settings:", error)
      set({ userSettingsLoaded: true })
    }
  },

  invalidateUserSettings: () => {
    set({ userSettingsLoaded: false })
  },

  startArxivDownload: async (arxivId) => {
    get().resetTranslationState()

    set({ userSettingsLoaded: false })
    await get().loadUserSettings()

    try {
      set({
        status: "downloading",
        stage: "downloading",
        message: i18n.t("task.detail.downloadSourceStarting"),
        detailCode: "download_source_starting",
        detailParams: null,
        error: null,
        logs: [i18n.t("task.detail.downloadSourceStarting")],
        arxivId,
        isDownloading: true,
        downloadProgress: 0,
        downloadStage: "downloading",
      })

      const response = await downloadArxiv(arxivId)

      set({
        taskId: response.task_id,
        logs: [...get().logs, response.message].filter(
          (value, index, values) => values.indexOf(value) === index,
        ),
      })

      get().pollDownloadProgress()
    } catch (error: unknown) {
      const message =
        error instanceof Error ? error.message : i18n.t("dashboard.arxivDownloadFailed")
      set({
        error: message,
        status: "failed",
        stage: "downloading",
        isDownloading: false,
        downloadProgress: 0,
      })
      toast.error(i18n.t("dashboard.arxivDownloadFailed"))
      throw error
    }
  },

  pollDownloadProgress: () => {
    const { taskId } = get()
    if (!taskId) return

    let eventSource: EventSource | null = null
    let sseRetryCount = 0
    const maxSseRetries = 3

    const markDownloadFailed = (message?: string) => {
      const errorMessage = message || i18n.t("dashboard.arxivDownloadFailed")
      set({
        status: "failed",
        stage: get().downloadStage || "downloading",
        isDownloading: false,
        error: errorMessage,
        message: errorMessage,
      })
      toast.error(i18n.t("dashboard.arxivDownloadFailed"))
    }

    const startPollingFallback = () => {
      if (downloadPollingInterval) return

      downloadPollingInterval = setInterval(async () => {
        const currentTaskId = get().taskId
        if (!currentTaskId) {
          if (downloadPollingInterval) clearInterval(downloadPollingInterval)
          downloadPollingInterval = null
          return
        }

        try {
          const statusData = await getTaskStatus(currentTaskId)

          set({
            downloadProgress: statusData.progress,
            downloadStage: statusData.stage || "downloading",
            stage: statusData.stage || get().stage,
            detailCode: statusData.detail_code ?? null,
            detailParams: statusData.detail_params ?? null,
            message: statusData.message,
          })

          if (statusData.status.toLowerCase() === "pending" && statusData.progress === 100) {
            if (downloadPollingInterval) {
              clearInterval(downloadPollingInterval)
              downloadPollingInterval = null
            }

            if (get().status !== "ready") {
              set({
                status: "ready",
                stage: statusData.stage || "done",
                isDownloading: false,
                downloadProgress: 100,
                detailCode: "download_source_complete",
                detailParams: null,
                message: statusData.message,
                logs: [...get().logs, statusData.message].filter(
                  (value, index, values) => values.indexOf(value) === index,
                ),
              })
              toast.success(i18n.t("dashboard.sourceDocumentReady"))
            }
            return
          }

          if (statusData.status.toLowerCase() === "failed") {
            if (downloadPollingInterval) clearInterval(downloadPollingInterval)
            downloadPollingInterval = null
            markDownloadFailed(statusData.error || statusData.message)
          }
        } catch (error) {
          console.error("Download polling error", error)
        }
      }, 2000)
    }

    const connectSSE = () => {
      if (downloadPollingInterval) return

      try {
        eventSource = new EventSource(`${API_BASE_URL}/api/task/${taskId}/stream`)

        eventSource.onopen = () => {
          sseRetryCount = 0
        }

        eventSource.addEventListener("update", (event) => {
          try {
            const data = JSON.parse(event.data)
            const currentStatus = String(data.status || "").toLowerCase()

            set({
              downloadProgress: data.progress,
              downloadStage: data.stage || "downloading",
              stage: data.stage || get().stage,
              detailCode: data.detail_code ?? null,
              detailParams: data.detail_params ?? null,
              message: data.message,
            })

            if (data.status?.toLowerCase() === "pending" && data.progress === 100) {
              if (get().status !== "ready") {
                set({
                  status: "ready",
                  stage: data.stage || "done",
                  isDownloading: false,
                  downloadProgress: 100,
                  detailCode: "download_source_complete",
                  detailParams: null,
                  message: data.message,
                  logs: [...get().logs, data.message].filter(
                    (value, index, values) => values.indexOf(value) === index,
                  ),
                })
                toast.success(i18n.t("dashboard.sourceDocumentReady"))
              }
              eventSource?.close()
              eventSource = null
            } else if (currentStatus === "failed") {
              markDownloadFailed(data.error || data.message)
              eventSource?.close()
              eventSource = null
            }
          } catch (error) {
            console.error("[Download SSE] Parse error:", error)
          }
        })

        eventSource.addEventListener("complete", (event) => {
          try {
            const data = JSON.parse(event.data)
            const currentStatus = String(data.status || "").toLowerCase()

            if (
              currentStatus === "failed" ||
              currentStatus === "failed_compilation" ||
              currentStatus === "structure_invalid"
            ) {
              markDownloadFailed(data.error || data.message)
            } else if (get().status !== "ready") {
              set({
                status: "ready",
                stage: data.stage || "done",
                isDownloading: false,
                downloadProgress: 100,
                detailCode: "download_source_complete",
                detailParams: null,
                message: data.message,
                logs: [...get().logs, data.message].filter(
                  (value, index, values) => values.indexOf(value) === index,
                ),
              })
              toast.success(i18n.t("dashboard.sourceDocumentReady"))
            }
            eventSource?.close()
            eventSource = null
          } catch (error) {
            console.error("[Download SSE] Parse error:", error)
          }
        })

        eventSource.addEventListener("error", (event) => {
          try {
            const data = JSON.parse((event as MessageEvent).data)
            markDownloadFailed(data.error || data.message)
            eventSource?.close()
            eventSource = null
          } catch {
            // Connection errors fall through to the shared handler below.
          }
        })

        eventSource.onerror = () => {
          eventSource?.close()
          eventSource = null

          if (sseRetryCount < maxSseRetries) {
            sseRetryCount += 1
            setTimeout(connectSSE, 1000 * sseRetryCount)
          } else {
            startPollingFallback()
          }
        }
      } catch (error) {
        console.error("[Download SSE] Setup error:", error)
        startPollingFallback()
      }
    }

    connectSSE()
  },

  startTranslation: async (config) => {
    const { taskId } = get()
    if (!taskId) {
      toast.error(i18n.t("task.error.missingTaskId"))
      throw new Error(i18n.t("task.error.missingTaskId"))
    }

    try {
      set({
        status: "processing",
        stage: "parsing",
        message: i18n.t("task.detail.translationStarting"),
        detailCode: "translation_starting",
        detailParams: null,
        failureReasonCode: null,
        error: null,
      })
      const response = await startTranslation(taskId, config)
      set({
        message: response.message,
        logs: [...get().logs, response.message].filter(
          (value, index, values) => values.indexOf(value) === index,
        ),
      })
      toast.success(i18n.t("task.toast.translationStarted"))
      get().pollStatus()
    } catch (error: unknown) {
      const quotaMessage = getDailyLatexQuotaExceededMessage(error, i18n.t.bind(i18n))
      const message = quotaMessage ?? (error instanceof Error ? error.message : i18n.t("task.error.startFailed"))
      set({ error: message, status: "failed" })
      toast.error(quotaMessage ?? i18n.t("task.error.startFailed"))
      throw error
    }
  },

  pollStatus: () => {
    if (get().isPolling) return
    set({ isPolling: true })

    pollingInterval = setInterval(async () => {
      const { taskId, isPolling, stopPolling } = get()
      if (!taskId || !isPolling) {
        stopPolling()
        return
      }

      try {
        const statusData = await getTaskStatus(taskId)

        set((state) => ({
          status: statusData.status,
          stage: statusData.stage || state.stage,
          progress: statusData.progress,
          message: statusData.message,
          detailCode: statusData.detail_code ?? state.detailCode,
          detailParams: statusData.detail_params ?? state.detailParams,
          failureReasonCode: statusData.failure_reason_code ?? state.failureReasonCode,
          error: statusData.error || null,
          taskWarnings: statusData.warnings ?? state.taskWarnings,
          logs: statusData.logs
            ? statusData.logs
            : [...state.logs, statusData.message].filter((value, index, values) => values.indexOf(value) === index),
        }))

        if (
          ["completed", "failed", "completed_with_warnings", "failed_compilation"].includes(
            statusData.status.toLowerCase(),
          )
        ) {
          const wasPolling = get().isPolling
          stopPolling()
          if (wasPolling) {
            if (statusData.status.toLowerCase() === "completed") {
              toast.success(i18n.t("task.toast.completed"), { id: `task-completed-${taskId}` })
            } else if (statusData.status.toLowerCase() === "failed") {
              toast.error(i18n.t("task.toast.failed"), { id: `task-failed-${taskId}` })
            } else if (statusData.status.toLowerCase() === "failed_compilation") {
              toast.error(i18n.t("task.toast.failedCompilation"), {
                id: `task-failed-compilation-${taskId}`,
              })
            }
          }
        }
      } catch (error) {
        console.error("Polling error", error)
      }
    }, 2000)
  },

  stopPolling: () => {
    if (pollingInterval) clearInterval(pollingInterval)
    pollingInterval = null
    set({ isPolling: false })
  },
}))
