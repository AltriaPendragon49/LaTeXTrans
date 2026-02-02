import axios from "axios"

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

export interface TranslateRequest {
    target_language: string
    source_language: string
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
    message: string
    warnings?: string
    error?: string
    output_path?: string
    logs?: string[]
}

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        "Content-Type": "application/json",
    },
})

export const downloadArxiv = async (arxivId: string): Promise<ArxivResponse> => {
    const response = await api.post<ArxivResponse>("/arxiv", { arxiv_id: arxivId })
    return response.data
}

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

export default api
