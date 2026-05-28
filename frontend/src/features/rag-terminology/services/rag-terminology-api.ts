import api from "@/lib/api"
import type {
  TerminologyTerm,
  TerminologyUploadResult,
  MatchLogEntry,
  CreateTermPayload,
  UpdateTermPayload,
  BatchOperationPayload,
  DomainsResponse,
} from "@/features/rag-terminology/types"

/** 术语列表查询参数 */
export interface ListTermsParams {
  page: number
  page_size: number
  status?: string
  source_lang?: string
  domain?: string
  source_type?: string
  query?: string
}

/** 术语列表响应 */
export interface ListTermsResponse {
  terms: TerminologyTerm[]
  total: number
  page: number
  page_size: number
}

/**
 * 上传术语文件（CSV 或 BibTeX）用于 RAG 注入
 * POST /terminology/upload (multipart/form-data)
 */
export async function uploadTerminologyFile(file: File): Promise<TerminologyUploadResult> {
  const formData = new FormData()
  formData.append("file", file)

  const response = await api.post<TerminologyUploadResult>("/terminology/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  })
  return response.data
}

/**
 * 列出术语条目（支持筛选）
 * GET /terminology/terms
 */
export async function listTerms(params: ListTermsParams): Promise<ListTermsResponse> {
  const response = await api.get<ListTermsResponse>("/terminology/terms", { params })
  return response.data
}

/**
 * 列出待审核的术语条目
 * GET /terminology/pending
 */
export async function listPendingTerms(params: ListTermsParams): Promise<ListTermsResponse> {
  const response = await api.get<ListTermsResponse>("/terminology/pending", { params })
  return response.data
}

/**
 * 批准待审核术语
 * POST /terminology/{termId}/approve
 */
export async function approveTerm(termId: string): Promise<void> {
  await api.post(`/terminology/${termId}/approve`)
}

/**
 * 拒绝待审核术语
 * POST /terminology/{termId}/reject
 */
export async function rejectTerm(termId: string, reason?: string): Promise<void> {
  await api.post(`/terminology/${termId}/reject`, { reason })
}

/**
 * 创建新术语（管理员）
 * POST /terminology/terms
 */
export async function createTerm(data: CreateTermPayload): Promise<TerminologyTerm> {
  const response = await api.post<TerminologyTerm>("/terminology/terms", data)
  return response.data
}

/**
 * 更新已有术语（管理员）
 * PUT /terminology/terms/{termId}
 */
export async function updateTerm(termId: string, data: UpdateTermPayload): Promise<void> {
  await api.put(`/terminology/terms/${termId}`, data)
}

/**
 * 删除术语（管理员）
 * DELETE /terminology/terms/{termId}
 */
export async function deleteTerm(termId: string): Promise<void> {
  await api.delete(`/terminology/terms/${termId}`)
}

/**
 * 批量审批/拒绝/删除术语（管理员）
 * POST /terminology/terms/batch
 */
export async function batchOperateTerms(payload: BatchOperationPayload): Promise<{ succeeded: number; failed: number }> {
  const response = await api.post("/terminology/terms/batch", payload)
  return response.data
}

/**
 * 获取翻译任务的匹配日志
 * GET /terminology/tasks/{taskId}/matches
 */
export async function getMatchLogs(taskId: string): Promise<MatchLogEntry[]> {
  const response = await api.get<MatchLogEntry[]>(`/terminology/tasks/${taskId}/matches`)
  return response.data
}

/**
 * 列出当前用户自己的术语条目
 * GET /terminology/my-terms
 */
export async function listMyTerms(params: ListTermsParams): Promise<ListTermsResponse> {
  const response = await api.get<ListTermsResponse>("/terminology/my-terms", { params })
  return response.data
}

/**
 * 列出所有可用的术语领域
 * GET /terminology/domains
 */
export async function listDomains(): Promise<DomainsResponse> {
  const response = await api.get<DomainsResponse>("/terminology/domains")
  return response.data
}

/**
 * 将个人术语共享给管理员审核
 * POST /terminology/terms/{termId}/share
 */
export async function shareTerm(termId: string): Promise<{ shared_term_id: string }> {
  const response = await api.post<{ shared_term_id: string }>(`/terminology/terms/${termId}/share`)
  return response.data
}
