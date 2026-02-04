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
    startTranslation: (config: TranslateRequest) => Promise<void>
    pollStatus: () => void
    stopPolling: () => void
}

let pollingInterval: ReturnType<typeof setInterval> | null = null

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

    // Configuration state - reset on page refresh
    config: { ...DEFAULT_CONFIG },
    latexValidation: null,

    setTaskId: (id) => set({ taskId: id }),
    setArxivId: (id) => set({ arxivId: id }),

    // Reset all state including configuration
    reset: () => {
        if (pollingInterval) clearInterval(pollingInterval)
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
            latexValidation: null
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
        // Reset previous task state first (clears logs, previous taskId, etc.)
        get().reset()

        try {
            set({ status: 'downloading', message: 'Downloading ArXiv paper...', error: null, logs: ['Starting ArXiv download...'], arxivId: arxivId })
            const response = await downloadArxiv(arxivId)
            set({
                taskId: response.task_id,
                status: 'ready',  // <-- Update status to 'ready' so Start button is enabled
                message: response.message,
                logs: [...get().logs, `Task created: ${response.task_id}`, response.message]
            })
            toast.success("ArXiv source downloaded successfully")
        } catch (error: unknown) {
            const msg = error instanceof Error ? error.message : 'Failed to download ArXiv paper'
            set({ error: msg, status: 'failed' })
            toast.error(msg)
            throw error
        }
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
