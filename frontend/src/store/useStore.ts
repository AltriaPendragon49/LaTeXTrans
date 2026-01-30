import { create } from 'zustand'
import { toast } from "sonner"
import { downloadArxiv, startTranslation, getTaskStatus } from '@/lib/api'
import type { TranslateRequest } from '@/lib/api'

interface TranslationState {
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

    // Actions
    setTaskId: (id: string) => void
    setArxivId: (id: string) => void
    reset: () => void

    // Async Actions
    startArxivDownload: (arxivId: string) => Promise<void>
    startTranslation: (config: TranslateRequest) => Promise<void>
    pollStatus: () => void
    stopPolling: () => void
}

let pollingInterval: any = null

export const useStore = create<TranslationState>((set, get) => ({
    taskId: null,
    arxivId: null,
    status: 'idle',
    progress: 0,
    message: '',
    logs: [],
    error: null,
    isPolling: false,
    outputMetrics: {},

    setTaskId: (id) => set({ taskId: id }),
    setArxivId: (id) => set({ arxivId: id }),

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
            outputMetrics: {}
        })
    },

    startArxivDownload: async (arxivId) => {
        try {
            set({ status: 'downloading', message: 'Downloading ArXiv paper...', error: null, logs: ['Starting ArXiv download...'], arxivId: arxivId })
            const response = await downloadArxiv(arxivId)
            set({ taskId: response.task_id, message: response.message, logs: [...get().logs, `Task created: ${response.task_id}`, response.message] })
            toast.success("ArXiv source downloaded successfully")
        } catch (error: any) {
            const msg = error.message || 'Failed to download ArXiv paper'
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
        } catch (error: any) {
            const msg = error.message || 'Failed to start translation'
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
