import { create } from 'zustand'
import { toast } from "sonner"
import { downloadArxiv, startTranslation, getTaskStatus } from '@/lib/api'
import { API_BASE_URL } from '@/api-base'
import i18n from '@/i18n'
import type { TranslateRequest } from '@/lib/api'
import type { TranslationConfig, AdvancedConfig, LatexValidation } from '@/types/config'
import { DEFAULT_CONFIG } from '@/types/config'
import { getAccessToken, isLocalAuthConfigured } from '@/lib/local-auth'

type TaskDetailParams = Record<string, string | number | boolean | null> | null

interface TranslationState {
    // Task state
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
    taskWarnings: string | null  // Font-size auto-downgrade and other formatting notices
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
    userSettingsLoaded: boolean  // Track if user settings have been loaded
    hasSystemApiKey: boolean  // Track if user has custom API key in system settings

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
    loadUserSettings: (forceReload?: boolean) => Promise<void>  // Load user settings from API
    invalidateUserSettings: () => void  // Mark settings as stale to force reload

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
    stage: 'idle',
    progress: 0,
    message: '',
    detailCode: null,
    detailParams: null,
    failureReasonCode: null,
    logs: [],
    error: null,
    isPolling: false,
    taskWarnings: null,
    outputMetrics: {},

    // Download Progress State
    downloadProgress: 0,
    downloadStage: '',
    isDownloading: false,

    // Configuration state - reset on page refresh
    config: { ...DEFAULT_CONFIG },
    latexValidation: null,
    userSettingsLoaded: false,
    hasSystemApiKey: false,

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
            stage: 'idle',
            progress: 0,
            message: '',
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
            downloadStage: '',
            userSettingsLoaded: false,
            hasSystemApiKey: false
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
            stage: 'idle',
            progress: 0,
            message: '',
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

    // Load user settings from API and apply to config
    loadUserSettings: async (forceReload = false) => {
        // Skip if already loaded (unless force reload)
        if (get().userSettingsLoaded && !forceReload) return

        try {
            // Skip if not configured or not authenticated
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
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            })

            if (!response.ok) {
                console.warn('[Settings] Failed to load user settings:', response.status)
                set({ userSettingsLoaded: true })
                return
            }

            const settings = await response.json()
            console.log('[Settings] Loaded user settings:', settings)

            // Save system API key configuration status
            const hasSystemApiKey = settings.has_custom_api_key || false
            console.log('[Settings] Has system API key:', hasSystemApiKey)

            // Map API settings to config format
            const newConfig: Partial<TranslationConfig> = {
                source_language: settings.default_source_language || 'en',
                target_language: settings.default_target_language || 'zh',
                advanced_config: {
                    translation_mode: settings.translation_mode || 'full',
                    compile_strategy: settings.compile_strategy || 'auto',
                    generate_terminology_table: settings.generate_glossary ?? true,
                    translation_model: settings.translation_model || 'deepseek-ai/deepseek-v3.2',
                    use_author_api: settings.use_author_api ?? true,
                    custom_base_url: settings.custom_base_url || undefined,
                    // Note: API key is not returned for security
                    formatting: settings.default_formatting || undefined,
                }
            }

            set((state) => ({
                config: {
                    ...state.config,
                    ...newConfig,
                    advanced_config: {
                        ...state.config.advanced_config,
                        ...newConfig.advanced_config,
                    }
                },
                userSettingsLoaded: true,
                hasSystemApiKey: hasSystemApiKey
            }))

            console.log('[Settings] Applied user settings to config')
        } catch (error) {
            console.error('[Settings] Error loading user settings:', error)
            set({ userSettingsLoaded: true })
        }
    },

    // Invalidate user settings to force reload on next loadUserSettings call
    invalidateUserSettings: () => {
        set({ userSettingsLoaded: false })
        console.log('[Settings] User settings invalidated, will reload on next access')
    },

    startArxivDownload: async (arxivId) => {
        // Reset previous task state only, preserve user configuration
        get().resetTranslationState()

        // Force reload user settings to ensure latest config
        set({ userSettingsLoaded: false })
        await get().loadUserSettings()

        try {
            set({
                status: 'downloading',
                stage: 'downloading',
                message: i18n.t('task.detail.downloadSourceStarting'),
                detailCode: 'download_source_starting',
                detailParams: null,
                error: null,
                logs: [i18n.t('task.detail.downloadSourceStarting')],
                arxivId: arxivId,
                isDownloading: true,
                downloadProgress: 0,
                downloadStage: 'downloading'
            })

            const response = await downloadArxiv(arxivId)

            // Set task_id and start SSE-based download progress tracking.
            set({
                taskId: response.task_id,
                logs: [...get().logs, response.message].filter((value, index, values) => values.indexOf(value) === index)
            })

            // Use SSE instead of polling for download progress.
            get().pollDownloadProgress()

        } catch (error: unknown) {
            const msg = error instanceof Error ? error.message : i18n.t('dashboard.arxivDownloadFailed')
            set({
                error: msg,
                status: 'failed',
                stage: 'downloading',
                isDownloading: false,
                downloadProgress: 0
            })
            toast.error(i18n.t('dashboard.arxivDownloadFailed'))
            throw error
        }
    },

    pollDownloadProgress: () => {
        const { taskId } = get()
        if (!taskId) return

        // Try establishing SSE connection.
        let eventSource: EventSource | null = null
        let sseRetryCount = 0
        const MAX_SSE_RETRIES = 3
        const markDownloadFailed = (msg?: string) => {
            const errorMsg = msg || i18n.t('dashboard.arxivDownloadFailed')
            set({
                status: 'failed',
                stage: get().downloadStage || 'downloading',
                isDownloading: false,
                error: errorMsg,
                message: errorMsg
            })
            toast.error(i18n.t('dashboard.arxivDownloadFailed'))
        }

        const connectSSE = () => {
            if (downloadPollingInterval) return // already downgraded to polling

            try {
                const url = `${API_BASE_URL}/api/task/${taskId}/stream`
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
                        const currentStatus = String(data.status || '').toLowerCase()

                        set({
                            downloadProgress: data.progress,
                            downloadStage: data.stage || 'downloading',
                            stage: data.stage || get().stage,
                            detailCode: data.detail_code ?? null,
                            detailParams: data.detail_params ?? null,
                            message: data.message
                        })

                        // Check whether source download is complete.
                        if (data.status?.toLowerCase() === 'pending' && data.progress === 100) {
                            if (get().status !== 'ready') {
                                set({
                                    status: 'ready',
                                    stage: data.stage || 'done',
                                    isDownloading: false,
                                    downloadProgress: 100,
                                    detailCode: 'download_source_complete',
                                    detailParams: null,
                                    message: data.message,
                                    logs: [...get().logs, data.message].filter((value, index, values) => values.indexOf(value) === index)
                                })
                                toast.success(i18n.t('dashboard.sourceDocumentReady'))
                            }
                            eventSource?.close()
                            eventSource = null
                        } else if (currentStatus === 'failed') {
                            markDownloadFailed(data.error || data.message)
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
                        const currentStatus = String(data.status || '').toLowerCase()

                        if (currentStatus === 'failed' || currentStatus === 'failed_compilation' || currentStatus === 'structure_invalid') {
                            markDownloadFailed(data.error || data.message)
                        } else if (get().status !== 'ready') {
                            set({
                                status: 'ready',
                                stage: data.stage || 'done',
                                isDownloading: false,
                                downloadProgress: 100,
                                detailCode: 'download_source_complete',
                                detailParams: null,
                                message: data.message,
                                logs: [...get().logs, data.message].filter((value, index, values) => values.indexOf(value) === index)
                            })
                            toast.success(i18n.t('dashboard.sourceDocumentReady'))
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
                        markDownloadFailed(data.error || data.message)
                        eventSource?.close()
                        eventSource = null
                    } catch {
                        // Connection errors are handled by onerror.
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
                        // Downgrade to polling.
                        console.log('[Download SSE] Falling back to polling')
                        startPollingFallback()
                    }
                }
            } catch (err) {
                console.error('[Download SSE] Setup error:', err)
                startPollingFallback()
            }
        }

        // Polling fallback strategy.
        const startPollingFallback = () => {
            if (downloadPollingInterval) return // avoid duplicate intervals

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
                        stage: statusData.stage || get().stage,
                        detailCode: statusData.detail_code ?? null,
                        detailParams: statusData.detail_params ?? null,
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
                                stage: statusData.stage || 'done',
                                isDownloading: false,
                                downloadProgress: 100,
                                detailCode: 'download_source_complete',
                                detailParams: null,
                                message: statusData.message,
                                logs: [...get().logs, statusData.message].filter((value, index, values) => values.indexOf(value) === index)
                            })
                            toast.success(i18n.t('dashboard.sourceDocumentReady'))
                        }
                        return
                    } else if (statusData.status.toLowerCase() === 'failed') {
                        if (downloadPollingInterval) clearInterval(downloadPollingInterval)
                        downloadPollingInterval = null

                        markDownloadFailed(statusData.error || statusData.message)
                    }

                } catch (error) {
                    console.error("Download polling error", error)
                }
            }, 2000) // fallback polling interval: 2s
        }

        // Start SSE connection.
        connectSSE()
    },

    startTranslation: async (config) => {
        const { taskId } = get()
        if (!taskId) {
            toast.error(i18n.t('task.error.missingTaskId'))
            throw new Error(i18n.t('task.error.missingTaskId'))
        }

        try {
            set({
                status: 'processing',
                stage: 'parsing',
                message: i18n.t('task.detail.translationStarting'),
                detailCode: 'translation_starting',
                detailParams: null,
                failureReasonCode: null,
                error: null,
            })
            const response = await startTranslation(taskId, config)
            set({
                message: response.message,
                logs: [...get().logs, response.message].filter((value, index, values) => values.indexOf(value) === index),
            })
            toast.success(i18n.t('task.toast.translationStarted'))
            get().pollStatus()
        } catch (error: unknown) {
            const msg = error instanceof Error ? error.message : i18n.t('task.error.startFailed')
            set({ error: msg, status: 'failed' })
            toast.error(i18n.t('task.error.startFailed'))
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
                    logs: statusData.logs ? statusData.logs : [...state.logs, statusData.message].filter((v, i, a) => a.indexOf(v) === i)
                }))

                if (['completed', 'failed', 'completed_with_warnings', 'failed_compilation'].includes(statusData.status.toLowerCase())) {
                    const wasPolling = get().isPolling
                    stopPolling()
                    if (wasPolling) {
                        if (statusData.status.toLowerCase() === 'completed') {
                            toast.success(i18n.t('task.toast.completed'), { id: `task-completed-${taskId}` })
                        } else if (statusData.status.toLowerCase() === 'failed') {
                            toast.error(i18n.t('task.toast.failed'), { id: `task-failed-${taskId}` })
                        } else if (statusData.status.toLowerCase() === 'failed_compilation') {
                            toast.error(i18n.t('task.toast.failedCompilation'), { id: `task-failed-compilation-${taskId}` })
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
    }
}))

