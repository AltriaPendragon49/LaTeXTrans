import axios from "axios"
import type { AdvancedConfig, LatexValidation } from "@/types/config"

// API base URL - configurable via environment variable for deployment flexibility
// Development: http://localhost:8000/api (default)
// Production: Set VITE_API_URL to your Cloudflare Tunnel URL
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api"

export interface ArxivResponse {
    task_id: string
    arxiv_id: string
    status: string
    message: string
    source_path?: string
}

/**
 * Translation request with full advanced configuration.
 */
export interface TranslateRequest {
    target_language: string
    source_language: string
    advanced_config?: AdvancedConfig
}

export interface TranslateResponse {
    task_id: string
    status: string
    message: string
}

export interface TaskStatusResponse {
    task_id: string
    status: string
    progress: number
    stage?: string  // 当前阶段 (downloading, extracting, downloading_pdf, validating 等)
    message: string
    warnings?: string
    error?: string
    failure_reason_code?: string
    failure_class?: string
    guard_phase?: string
    replay_bundle_ref?: string
    output_path?: string
    logs?: string[]
    advanced_config?: AdvancedConfig
    latex_validation?: LatexValidation
    persist_failed?: boolean  // 持久化失败标志：Supabase 写入全部重试失败时为 true
}

/**
 * Upload response with LaTeX validation result.
 */
export interface UploadResponse {
    task_id: string
    status: string
    message: string
    source_path: string
    latex_validation?: LatexValidation
}

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        "Content-Type": "application/json",
    },
})

// Request interceptor to add auth token
api.interceptors.request.use(async (config) => {
    // Dynamically import to avoid circular dependencies
    const { getAccessToken } = await import('./supabase')
    const token = await getAccessToken()

    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }

    return config
})

export const downloadArxiv = async (arxivId: string): Promise<ArxivResponse> => {
    const response = await api.post<ArxivResponse>("/arxiv", { arxiv_id: arxivId })
    return response.data
}

/**
 * Start translation with full configuration.
 * 
 * @param taskId - Task ID from upload or arxiv endpoint
 * @param config - Translation configuration including advanced options
 */
export const startTranslation = async (taskId: string, config: TranslateRequest): Promise<TranslateResponse> => {
    const response = await api.post<TranslateResponse>(`/translate/${taskId}`, config)
    return response.data
}

export const getTaskStatus = async (taskId: string): Promise<TaskStatusResponse> => {
    const response = await api.get<TaskStatusResponse>(`/task/${taskId}`)
    return response.data
}

export const getTaskLogs = async (taskId: string): Promise<string[]> => {
    // Assuming there is an endpoint for logs, or it comes with status
    // Based on previous reading, task endpoint might return logs or separate
    // Let's assume separate or part of status for now.
    // If not implemented in backend, we might need to rely on polling status message or adding a log endpoint.
    // For MVP, using message updates as logs is fine, or check if /task/{taskId}/logs exists
    try {
        const response = await api.get<{ logs: string[] }>(`/task/${taskId}/logs`)
        return response.data.logs
    } catch {
        return []
    }
}

/**
 * Upload a file (ZIP, TAR.GZ, RAR, or .tex) for translation.
 * 
 * @param file - File to upload
 * @returns Upload response with task ID and LaTeX validation
 */
export const uploadFile = async (file: File): Promise<UploadResponse> => {
    const formData = new FormData()
    formData.append("file", file)

    const response = await api.post<UploadResponse>("/upload", formData, {
        headers: {
            "Content-Type": "multipart/form-data",
        },
    })
    return response.data
}

/**
 * Get download URL for translated PDF.
 * 
 * @param taskId - Task ID
 * @returns URL to download the PDF
 */
export const getDownloadUrl = (taskId: string): string => {
    return `${API_BASE_URL}/download/${taskId}`
}

/**
 * Get preview URL for translated PDF (inline display).
 * 
 * @param taskId - Task ID
 * @returns URL to preview the PDF
 */
export const getPreviewUrl = (taskId: string): string => {
    return `${API_BASE_URL}/preview/${taskId}`
}

/**
 * Delete a single task from history.
 * 
 * @param taskId - Task ID to delete
 * @returns Deletion result with deleted directories and errors
 */
export const deleteTask = async (taskId: string): Promise<{
    message: string
    task_id: string
    deleted_dirs: string[]
    errors: string[]
}> => {
    const response = await api.delete(`/history/${taskId}`)
    return response.data
}

/**
 * Delete multiple tasks in batch.
 * 
 * @param taskIds - Array of task IDs to delete
 * @returns Batch deletion results
 */
export const deleteTasksBatch = async (taskIds: string[]): Promise<{
    message: string
    results: Array<{
        task_id: string
        success: boolean
        deleted_dirs?: string[]
        errors?: string[]
        error?: string
    }>
}> => {
    const response = await api.delete(`/history`, {
        data: { task_ids: taskIds }
    })
    return response.data
}

export interface BatchTranslateRequest {
    arxiv_ids: string[]
    target_language: string
    source_language: string
    advanced_config?: AdvancedConfig
}

export interface BatchTranslateResponse {
    batch_id: string
    task_ids: string[]
    message: string
    queued_count: number
}

export interface QueueStatusResponse {
    active_count: number
    queue_size: number
    max_concurrent: number
    total_pending: number
    user_quota_used: number
    user_quota_max: number
}

/**
 * Start batch translation for multiple arXiv IDs (authenticated users only).
 */
export const startBatchTranslation = async (
    request: BatchTranslateRequest
): Promise<BatchTranslateResponse> => {
    const response = await api.post<BatchTranslateResponse>('/batch-translate', request)
    return response.data
}

/**
 * Get current task queue status.
 */
export const getQueueStatus = async (): Promise<QueueStatusResponse> => {
    const response = await api.get<QueueStatusResponse>('/queue/status')
    return response.data
}

export default api

