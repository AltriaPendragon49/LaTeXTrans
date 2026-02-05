import { create } from 'zustand'
import { toast } from "sonner"
import { downloadArxiv, startTranslation, getTaskStatus } from '@/lib/api'
import type { TranslateRequest } from '@/lib/api'
import type { TranslationConfig, AdvancedConfig, LatexValidation } from '@/types/config'
import { DEFAULT_CONFIG } from '@/types/config'

interface TranslationState {
    // Task state
    taskId: string | null
    arxivId: string | null
    status: string
    progress: number
    message: string
    logs: string[]
    error: string | null
    isPolling: boolean
    outputMetrics: {
        pdfPath?: string
        translationQuality?: number
    }

    // Download Progress State
    downloadProgress: number
    downloadStage: string
    isDownloading: boolean

    // Configuration state
    config: TranslationConfig
    latexValidation: LatexValidation | null

    // Basic Actions
    setTaskId: (id: string) => void
    setArxivId: (id: string | null) => void
    reset: () => void

    // Configuration Actions
    setConfig: (config: Partial<TranslationConfig>) => void
    setAdvancedConfig: (config: Partial<AdvancedConfig>) => void
    resetConfig: () => void
    setLatexValidation: (validation: LatexValidation | null) => void

    // Async Actions
    startArxivDownload: (arxivId: string) => Promise<void>
    pollDownloadProgress: () => void
    startTranslation: (config: TranslateRequest) => Promise<void>
    pollStatus: () => void
    stopPolling: () => void
}

let pollingInterval: ReturnType<typeof setInterval> | null = null
let downloadPollingInterval: ReturnType<typeof setInterval> | null = null

export const useStore = create<TranslationState>((set, get) => ({
    // Task state
    taskId: null,
    arxivId: null,
    status: 'idle',
    progress: 0,
    message: '',
    logs: [],
    error: null,
    isPolling: false,
    outputMetrics: {},

    // Download Progress State
    downloadProgress: 0,
    downloadStage: '',
    isDownloading: false,

    // Configuration state - reset on page refresh
    config: { ...DEFAULT_CONFIG },
    latexValidation: null,

    setTaskId: (id) => set({ taskId: id }),
    setArxivId: (id) => set({ arxivId: id }),

    // Reset all state including configuration
    reset: () => {
        if (pollingInterval) clearInterval(pollingInterval)
        if (downloadPollingInterval) clearInterval(downloadPollingInterval)
        pollingInterval = null
        downloadPollingInterval = null
        set({
            taskId: null,
            arxivId: null,
            status: 'idle',
            progress: 0,
            message: '',
            logs: [],
            error: null,
            isPolling: false,
            outputMetrics: {},
            config: { ...DEFAULT_CONFIG },
            latexValidation: null,
            isDownloading: false,
            downloadProgress: 0,
            downloadStage: ''
        })
    },

    // Update configuration (partial update)
    setConfig: (newConfig) => set((state) => ({
        config: {
            ...state.config,
            ...newConfig,
            // Deep merge advanced_config if provided
            advanced_config: newConfig.advanced_config
                ? { ...state.config.advanced_config, ...newConfig.advanced_config }
                : state.config.advanced_config
        }
    })),

    // Update advanced configuration only
    setAdvancedConfig: (advancedConfig) => set((state) => ({
        config: {
            ...state.config,
            advanced_config: {
                ...state.config.advanced_config,
                ...advancedConfig
            }
        }
    })),

    // Reset configuration to defaults
    resetConfig: () => set({
        config: { ...DEFAULT_CONFIG }
    }),

    // Set LaTeX validation result (from upload)
    setLatexValidation: (validation) => set({ latexValidation: validation }),

    startArxivDownload: async (arxivId) => {
        // Reset previous task state first
        get().reset()

        try {
            set({
                status: 'downloading',
                message: 'Starting ArXiv download...',
                error: null,
                logs: ['Starting ArXiv download...'],
                arxivId: arxivId,
                isDownloading: true,
                downloadProgress: 0,
                downloadStage: 'downloading'
            })

            const response = await downloadArxiv(arxivId)

            //设置 task_id 并开始轮询下载进度
            set({
                taskId: response.task_id,
                logs: [...get().logs, `Task created: ${response.task_id}`, response.message]
            })

            // 启动专门的下载进度轮询
            get().pollDownloadProgress()

        } catch (error: unknown) {
            const msg = error instanceof Error ? error.message : 'Failed to download ArXiv paper'
            set({
                error: msg,
                status: 'failed',
                isDownloading: false,
                downloadProgress: 0
            })
            toast.error(msg)
            throw error
        }
    },

    pollDownloadProgress: () => {
        if (downloadPollingInterval) return // 避免重复轮询

        downloadPollingInterval = setInterval(async () => {
            const { taskId } = get()
            if (!taskId) {
                if (downloadPollingInterval) clearInterval(downloadPollingInterval)
                downloadPollingInterval = null
                return
            }

            try {
                const statusData = await getTaskStatus(taskId)

                // 更新下载进度和状态
                set({
                    downloadProgress: statusData.progress,
                    downloadStage: statusData.stage || 'downloading',
                    message: statusData.message
                })

                // 检查是否下载完成（status 为 pending 表示准备好翻译）
                if (statusData.status.toLowerCase() === 'pending' && statusData.progress === 100) {
                    // 下载完成 - 先清除轮询，避免重复
                    if (downloadPollingInterval) {
                        clearInterval(downloadPollingInterval)
                        downloadPollingInterval = null
                    }

                    // 只在当前状态不是 ready 时更新状态，避免重复更新
                    if (get().status !== 'ready') {
                        set({
                            status: 'ready',
                            isDownloading: false,
                            downloadProgress: 100,
                            message: 'ArXiv source downloaded successfully',
                            logs: [...get().logs, 'Download completed']
                        })
                        toast.success("ArXiv source downloaded successfully")
                    }
                    return // 退出本次轮询回调
                } else if (statusData.status.toLowerCase() === 'failed') {
                    // 下载失败
                    if (downloadPollingInterval) clearInterval(downloadPollingInterval)
                    downloadPollingInterval = null

                    set({
                        status: 'failed',
                        isDownloading: false,
                        error: statusData.error || 'Download failed',
                        message: statusData.message
                    })
                    toast.error(statusData.error || 'Download failed')
                }

            } catch (error) {
                console.error("Download polling error", error)
            }
        }, 200) // 每200ms轮询一次，确保能捕获到中间进度
    },

    startTranslation: async (config) => {
        const { taskId } = get()
        if (!taskId) {
            toast.error("No active task ID")
            throw new Error("No active task ID")
        }

        try {
            set({ status: 'starting_translation', message: 'Initiating translation...', error: null })
            const response = await startTranslation(taskId, config)
            set({ message: response.message, logs: [...get().logs, 'Translation started'] })
            toast.success("Translation started")
            get().pollStatus()
        } catch (error: unknown) {
            const msg = error instanceof Error ? error.message : 'Failed to start translation'
            set({ error: msg, status: 'failed' })
            toast.error(msg)
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
                    progress: statusData.progress,
                    message: statusData.message,
                    error: statusData.error || null,
                    logs: statusData.logs ? statusData.logs : [...state.logs, statusData.message].filter((v, i, a) => a.indexOf(v) === i)
                }))

                if (['completed', 'failed', 'completed_with_warnings'].includes(statusData.status.toLowerCase())) {
                    stopPolling()
                    if (statusData.status.toLowerCase() === 'completed') {
                        toast.success("Task completed successfully")
                    } else if (statusData.status.toLowerCase() === 'failed') {
                        toast.error("Task failed")
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
    }
}))
