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
    resetTranslationState: () => void  // Reset task state only, preserve config

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

    // Reset translation/task state only, preserve configuration
    resetTranslationState: () => {
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
            latexValidation: null,
            isDownloading: false,
            downloadProgress: 0,
            downloadStage: ''
            // Note: config is preserved, not reset
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

            //设置 task_id 并开始 SSE 监听下载进度
            set({
                taskId: response.task_id,
                logs: [...get().logs, `Task created: ${response.task_id}`, response.message]
            })

            // 使用 SSE 替代轮询监听下载进度
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
        const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
        const { taskId } = get()
        if (!taskId) return

        // 尝试建立 SSE 连接
        let eventSource: EventSource | null = null
        let sseRetryCount = 0
        const MAX_SSE_RETRIES = 3

        const connectSSE = () => {
            if (downloadPollingInterval) return // 已降级为轮询

            try {
                const url = `${API_BASE_URL}/task/${taskId}/stream`
                console.log('[Download SSE] Connecting to:', url)

                eventSource = new EventSource(url)

                eventSource.onopen = () => {
                    console.log('[Download SSE] Connection opened')
                    sseRetryCount = 0
                }

                eventSource.addEventListener('update', (event) => {
                    try {
                        const data = JSON.parse(event.data)
                        console.log('[Download SSE] Update:', data)

                        set({
                            downloadProgress: data.progress,
                            downloadStage: data.stage || 'downloading',
                            message: data.message
                        })

                        // 检查下载完成
                        if (data.status?.toLowerCase() === 'pending' && data.progress === 100) {
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
                            eventSource?.close()
                            eventSource = null
                        }
                    } catch (err) {
                        console.error('[Download SSE] Parse error:', err)
                    }
                })

                eventSource.addEventListener('complete', (event) => {
                    try {
                        const data = JSON.parse(event.data)
                        console.log('[Download SSE] Complete:', data)

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
                        eventSource?.close()
                        eventSource = null
                    } catch (err) {
                        console.error('[Download SSE] Parse error:', err)
                    }
                })

                eventSource.addEventListener('error', (event) => {
                    try {
                        const data = JSON.parse((event as MessageEvent).data)
                        console.error('[Download SSE] Server error:', data)
                        set({
                            status: 'failed',
                            isDownloading: false,
                            error: data.message || 'Download failed',
                            message: data.message
                        })
                        toast.error(data.message || 'Download failed')
                        eventSource?.close()
                        eventSource = null
                    } catch {
                        // 连接错误由 onerror 处理
                    }
                })

                eventSource.onerror = () => {
                    console.error('[Download SSE] Connection error')
                    eventSource?.close()
                    eventSource = null

                    if (sseRetryCount < MAX_SSE_RETRIES) {
                        sseRetryCount++
                        console.log(`[Download SSE] Retry ${sseRetryCount}/${MAX_SSE_RETRIES}`)
                        setTimeout(connectSSE, 1000 * sseRetryCount)
                    } else {
                        // 降级为轮询
                        console.log('[Download SSE] Falling back to polling')
                        startPollingFallback()
                    }
                }
            } catch (err) {
                console.error('[Download SSE] Setup error:', err)
                startPollingFallback()
            }
        }

        // 轮询降级策略
        const startPollingFallback = () => {
            if (downloadPollingInterval) return // 避免重复

            console.log('[Download] Starting polling fallback (2s interval)')

            downloadPollingInterval = setInterval(async () => {
                const { taskId } = get()
                if (!taskId) {
                    if (downloadPollingInterval) clearInterval(downloadPollingInterval)
                    downloadPollingInterval = null
                    return
                }

                try {
                    const statusData = await getTaskStatus(taskId)

                    set({
                        downloadProgress: statusData.progress,
                        downloadStage: statusData.stage || 'downloading',
                        message: statusData.message
                    })

                    if (statusData.status.toLowerCase() === 'pending' && statusData.progress === 100) {
                        if (downloadPollingInterval) {
                            clearInterval(downloadPollingInterval)
                            downloadPollingInterval = null
                        }

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
                        return
                    } else if (statusData.status.toLowerCase() === 'failed') {
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
            }, 2000) // 降级为 2s 轮询
        }

        // 启动 SSE 连接
        connectSSE()
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
