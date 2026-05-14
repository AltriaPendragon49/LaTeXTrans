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

export interface ListTermsParams {
  page: number
  page_size: number
  status?: string
  source_lang?: string
  domain?: string
  source_type?: string
}

export interface ListTermsResponse {
  terms: TerminologyTerm[]
  total: number
  page: number
  page_size: number
}

/**
 * Upload a terminology file (CSV or BibTeX) for RAG injection.
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
 * List terminology terms with optional filters.
 */
export async function listTerms(params: ListTermsParams): Promise<ListTermsResponse> {
  const response = await api.get<ListTermsResponse>("/terminology/terms", { params })
  return response.data
}

/**
 * List terminology terms pending review.
 */
export async function listPendingTerms(params: ListTermsParams): Promise<ListTermsResponse> {
  const response = await api.get<ListTermsResponse>("/terminology/pending", { params })
  return response.data
}

/**
 * Approve a pending terminology term.
 */
export async function approveTerm(termId: string): Promise<void> {
  await api.post(`/terminology/${termId}/approve`)
}

/**
 * Reject a pending terminology term.
 */
export async function rejectTerm(termId: string, reason?: string): Promise<void> {
  await api.post(`/terminology/${termId}/reject`, { reason })
}

/**
 * Create a new terminology term (admin).
 */
export async function createTerm(data: CreateTermPayload): Promise<TerminologyTerm> {
  const response = await api.post<TerminologyTerm>("/terminology/terms", data)
  return response.data
}

/**
 * Update an existing terminology term (admin).
 */
export async function updateTerm(termId: string, data: UpdateTermPayload): Promise<void> {
  await api.put(`/terminology/terms/${termId}`, data)
}

/**
 * Delete a terminology term (admin).
 */
export async function deleteTerm(termId: string): Promise<void> {
  await api.delete(`/terminology/terms/${termId}`)
}

/**
 * Batch approve/reject/delete terms (admin).
 */
export async function batchOperateTerms(payload: BatchOperationPayload): Promise<{ succeeded: number; failed: number }> {
  const response = await api.post("/terminology/terms/batch", payload)
  return response.data
}

/**
 * Get match logs for a completed translation task.
 */
export async function getMatchLogs(taskId: string): Promise<MatchLogEntry[]> {
  const response = await api.get<MatchLogEntry[]>(`/terminology/tasks/${taskId}/matches`)
  return response.data
}

/**
 * List the current user's own terminology terms.
 */
export async function listMyTerms(params: ListTermsParams): Promise<ListTermsResponse> {
  const response = await api.get<ListTermsResponse>("/terminology/my-terms", { params })
  return response.data
}

/**
 * List all available terminology domains.
 */
export async function listDomains(): Promise<DomainsResponse> {
  const response = await api.get<DomainsResponse>("/terminology/domains")
  return response.data
}

/**
 * Share a personal term to admin for review.
 */
export async function shareTerm(termId: string): Promise<{ shared_term_id: string }> {
  const response = await api.post<{ shared_term_id: string }>(`/terminology/terms/${termId}/share`)
  return response.data
}
