/**
 * API 客户端
 * 基于 Axios 封装的后端 API 调用模块，包含认证拦截器和所有业务接口
 */
import axios from "axios"
import type { AdvancedConfig, LatexValidation } from "@/types/config"
import { API_BASE_URL } from "@/api-base"
import { getAccessToken } from "./local-auth"

const DAILY_LATEX_QUOTA_EXCEEDED_CODE = "DAILY_LATEX_QUOTA_EXCEEDED"

/** 每日 LaTeX 配额超出错误详情 */
export interface DailyLatexQuotaExceededDetail {
    code: typeof DAILY_LATEX_QUOTA_EXCEEDED_CODE
    requested_count: number
    limit: number
    used: number
    remaining: number
    quota_date: string
    reset_timezone: string
}

/** arXiv 下载接口响应 */
export interface ArxivResponse {
    task_id: string
    arxiv_id: string
    status: string
    message: string
    source_path?: string
}

/** 翻译请求，包含完整的高级配置 */
export interface TranslateRequest {
    target_language: string
    source_language: string
    advanced_config?: AdvancedConfig
}

/** 翻译接口响应 */
export interface TranslateResponse {
    task_id: string
    status: string
    message: string
}

/** 任务状态查询响应 */
export interface TaskStatusResponse {
    task_id: string
    status: string
    progress: number
    stage?: string
    message: string
    detail_code?: string | null
    detail_params?: Record<string, string | number | boolean | null> | null
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
    persist_failed?: boolean
}

/** 上传响应，包含 LaTeX 验证结果 */
export interface UploadResponse {
    task_id: string
    status: string
    message: string
    source_path: string
    latex_validation?: LatexValidation
}

/** 判断输入是否为 Record 类型 */
function isRecord(input: unknown): input is Record<string, unknown> {
    return Boolean(input && typeof input === "object")
}

/** 标准化数值：非有限数值返回 null */
function normalizeNumber(input: unknown): number | null {
    return typeof input === "number" && Number.isFinite(input) ? input : null
}

/**
 * 从 Axios 错误对象中提取每日 LaTeX 配额超出详情
 * @param error - Axios 错误对象
 * @returns 配额详情，若非配额错误则返回 null
 */
export function getDailyLatexQuotaExceededDetail(error: unknown): DailyLatexQuotaExceededDetail | null {
    if (!isRecord(error) || !isRecord(error.response)) {
        return null
    }

    const response = error.response
    if (!isRecord(response.data) || !isRecord(response.data.detail)) {
        return null
    }

    const detail = response.data.detail
    if (detail.code !== DAILY_LATEX_QUOTA_EXCEEDED_CODE) {
        return null
    }

    const requestedCount = normalizeNumber(detail.requested_count)
    const limit = normalizeNumber(detail.limit)
    const used = normalizeNumber(detail.used)
    const remaining = normalizeNumber(detail.remaining)

    if (requestedCount === null || limit === null || used === null || remaining === null) {
        return null
    }

    return {
        code: DAILY_LATEX_QUOTA_EXCEEDED_CODE,
        requested_count: requestedCount,
        limit,
        used,
        remaining,
        quota_date: typeof detail.quota_date === "string" ? detail.quota_date : "",
        reset_timezone: typeof detail.reset_timezone === "string" ? detail.reset_timezone : "",
    }
}

/**
 * 从错误对象生成每日配额超出的国际化消息
 * @param error - Axios 错误对象
 * @param translate - i18n 翻译函数
 * @returns 翻译后的消息，若非配额错误则返回 null
 */
export function getDailyLatexQuotaExceededMessage(
    error: unknown,
    translate: (key: string, values?: Record<string, unknown>) => string,
): string | null {
    const detail = getDailyLatexQuotaExceededDetail(error)
    if (!detail) {
        return null
    }

    return translate("task.error.dailyLatexQuotaExceeded", {
        requested: detail.requested_count,
        remaining: detail.remaining,
        limit: detail.limit,
        used: detail.used,
        quotaDate: detail.quota_date,
        resetTimezone: detail.reset_timezone,
    })
}

/** 创建 Axios 实例 */
const api = axios.create({
    baseURL: `${API_BASE_URL}/api`,
    headers: {
        "Content-Type": "application/json",
    },
})

/** 请求拦截器：自动附加 Bearer Token */
api.interceptors.request.use(async (config) => {
    const token = await getAccessToken()

    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }

    return config
})

/**
 * 通过 arXiv ID 下载论文
 * @param arxivId - arXiv 论文 ID
 */
export const downloadArxiv = async (arxivId: string): Promise<ArxivResponse> => {
    const response = await api.post<ArxivResponse>("/arxiv", { arxiv_id: arxivId })
    return response.data
}

/**
 * 发起翻译任务
 * @param taskId - 上传或 arXiv 下载返回的任务 ID
 * @param config - 翻译配置（含高级选项）
 */
export const startTranslation = async (taskId: string, config: TranslateRequest): Promise<TranslateResponse> => {
    const response = await api.post<TranslateResponse>(`/translate/${taskId}`, config)
    return response.data
}

/**
 * 查询单个任务状态
 * @param taskId - 任务 ID
 */
export const getTaskStatus = async (taskId: string): Promise<TaskStatusResponse> => {
    const response = await api.get<TaskStatusResponse>(`/task/${taskId}`)
    return response.data
}

/**
 * 获取任务日志
 * @param taskId - 任务 ID
 */
export const getTaskLogs = async (taskId: string): Promise<string[]> => {
    try {
        const response = await api.get<{ logs: string[] }>(`/task/${taskId}/logs`)
        return response.data.logs
    } catch {
        return []
    }
}

/**
 * 上传文件（ZIP、TAR.GZ、RAR 或 .tex）
 * @param file - 待上传文件
 * @returns 上传响应，包含任务 ID 和 LaTeX 验证结果
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
 * 获取翻译后 PDF 的下载地址
 * @param taskId - 任务 ID
 * @returns PDF 下载 URL
 */
export const getDownloadUrl = (taskId: string): string => {
    return `${API_BASE_URL}/api/download/${taskId}`
}

/**
 * 获取翻译后 PDF 的预览地址（内联显示）
 * @param taskId - 任务 ID
 * @returns PDF 预览 URL
 */
export const getPreviewUrl = (taskId: string): string => {
    return `${API_BASE_URL}/api/preview/${taskId}`
}

/**
 * 删除单条历史任务
 * @param taskId - 待删除的任务 ID
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
 * 批量删除历史任务
 * @param taskIds - 待删除的任务 ID 数组
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

/** 批量 arXiv 翻译请求 */
export interface BatchTranslateRequest {
    arxiv_ids: string[]
    target_language: string
    source_language: string
    advanced_config?: AdvancedConfig
}

/** 批量翻译响应 */
export interface BatchTranslateResponse {
    batch_id: string
    task_ids: string[]
    message: string
    queued_count: number
}

/** 批量上传翻译请求 */
export interface BatchUploadTranslateRequest {
    files: File[]
    target_language: string
    source_language: string
    advanced_config?: AdvancedConfig
}

/** 队列状态响应 */
export interface QueueStatusResponse {
    active_count: number
    queue_size: number
    max_concurrent: number
    total_pending: number
    user_quota_used: number
    user_quota_max: number
}

/**
 * 发起批量 arXiv 翻译（仅限已认证用户）
 */
export const startBatchTranslation = async (
    request: BatchTranslateRequest
): Promise<BatchTranslateResponse> => {
    const response = await api.post<BatchTranslateResponse>('/batch-translate', request)
    return response.data
}

/**
 * 发起批量上传文件翻译（仅限已认证用户）
 */
export const startBatchUploadTranslation = async (
    request: BatchUploadTranslateRequest
): Promise<BatchTranslateResponse> => {
    const formData = new FormData()
    for (const file of request.files) {
        formData.append("files", file)
    }
    formData.append("source_language", request.source_language)
    formData.append("target_language", request.target_language)
    if (request.advanced_config) {
        formData.append("advanced_config", JSON.stringify(request.advanced_config))
    }

    const response = await api.post<BatchTranslateResponse>('/upload/batch-translate', formData, {
        headers: {
            "Content-Type": "multipart/form-data",
        },
    })
    return response.data
}

/**
 * 获取当前任务队列状态
 */
export const getQueueStatus = async (): Promise<QueueStatusResponse> => {
    const response = await api.get<QueueStatusResponse>('/queue/status')
    return response.data
}

export default api
