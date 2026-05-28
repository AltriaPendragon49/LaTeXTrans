import { create } from "zustand"
import { toast } from "sonner"

import { API_BASE_URL } from "@/api-base"
import i18n from "@/i18n"
import { downloadArxiv, getDailyLatexQuotaExceededMessage, getTaskStatus, startTranslation } from "@/lib/api"
import { getAccessToken, isLocalAuthConfigured } from "@/lib/local-auth"
import { DEFAULT_CONFIG, getDefaultTranslationModel } from "@/types/config"
import type { AdvancedConfig, LatexValidation, TranslationConfig } from "@/types/config"
import type { TranslateRequest } from "@/lib/api"

/** 任务详情参数类型 */
type TaskDetailParams = Record<string, string | number | boolean | null> | null

/** 翻译工作流全局状态接口 */
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

/** 全局轮询和下载轮询的定时器引用 */
let pollingInterval: ReturnType<typeof setInterval> | null = null
let downloadPollingInterval: ReturnType<typeof setInterval> | null = null

/**
 * 翻译工作流全局状态管理 (Zustand Store)
 * 管理翻译任务的全生命周期状态：上传、下载、轮询、翻译、编译。
 * 包含用户设置加载、LaTeX 验证、批量操作等功能
 */
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

  /** 设置当前翻译任务 ID */
  setTaskId: (id) => set({ taskId: id }),
  /** 设置当前 arXiv ID */
  setArxivId: (id) => set({ arxivId: id }),

  /** 完全重置——清理轮询定时器并重置所有状态 */
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

  /** 只重置翻译状态（保留配置和用户设置）——用于发起新翻译 */
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

  /** 合并更新翻译配置 */
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

  /** 合并更新高级配置 */
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

  /** 重置配置为默认值 */
  resetConfig: () =>
    set({
      config: { ...DEFAULT_CONFIG },
    }),

  /** 设置 LaTeX 校验结果 */
  setLatexValidation: (validation) => set({ latexValidation: validation }),

  /**
   * 从后端 GET /api/settings 加载用户设置
   * 将服务端保存的默认语言、翻译模式、API key 状态等合并到本地配置中
   */
  loadUserSettings: async (forceReload = false) => {
    // 如果已经加载过且不强制重载，则跳过
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

  /** 标记用户设置为未加载，下次访问时会重新拉取 */
  invalidateUserSettings: () => {
    set({ userSettingsLoaded: false })
  },

  /**
   * 从 arXiv 下载源文件
   * 调用 POST /api/download/arxiv 接口，然后启动 SSE/轮询监听下载进度
   */
  startArxivDownload: async (arxivId) => {
    get().resetTranslationState()

    // 确保用户设置已加载
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

  /**
   * 轮询 arXiv 下载进度
   * 优先使用 SSE (GET /api/task/{taskId}/stream) 获取实时进度，
   * 失败时回退到 HTTP 轮询 (GET /api/status/{taskId})
   */
  pollDownloadProgress: () => {
    const { taskId } = get()
    if (!taskId) return

    let eventSource: EventSource | null = null
    let sseRetryCount = 0
    const maxSseRetries = 3

    /** 标记下载失败 */
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

    /** HTTP 轮询回退方案 */
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

    /** 建立 SSE 连接监听下载进度 */
    const connectSSE = () => {
      if (downloadPollingInterval) return

      try {
        eventSource = new EventSource(`${API_BASE_URL}/api/task/${taskId}/stream`)

        eventSource.onopen = () => {
          sseRetryCount = 0
        }

        // 处理 update 事件：增量进度更新
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

        // 处理 complete 事件
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

        // 处理 error 事件
        eventSource.addEventListener("error", (event) => {
          try {
            const data = JSON.parse((event as MessageEvent).data)
            markDownloadFailed(data.error || data.message)
            eventSource?.close()
            eventSource = null
          } catch {
            // 连接错误会传递到下面的 onerror 共享处理器
          }
        })

        // SSE 连接错误处理，支持最多 3 次重试后回退到 HTTP 轮询
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

  /**
   * 开始翻译
   * 调用 POST /api/translate/{taskId} 提交翻译请求，启动任务状态轮询
   */
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

  /**
   * 轮询翻译任务状态
   * 每 2 秒调用 GET /api/status/{taskId} 获取最新状态，
   * 任务完成或失败后自动停止轮询
   */
  pollStatus: () => {
    // 已经在轮询中，避免重复启动
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

        // 终端状态：停止轮询并显示对应 toast
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

  /** 停止任务状态轮询 */
  stopPolling: () => {
    if (pollingInterval) clearInterval(pollingInterval)
    pollingInterval = null
    set({ isPolling: false })
  },
}))
