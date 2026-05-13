import api from "@/lib/api"
import type { TerminologyTerm, TerminologyUploadResult, MatchLogEntry } from "@/features/rag-terminology/types"

export interface ListTermsParams {
  page: number
  page_size: number
  status?: string
  source_lang?: string
  domain?: string
}

export interface ListTermsResponse {
  terms: TerminologyTerm[]
  total: number
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
 * Get match logs for a completed translation task.
 */
export async function getMatchLogs(taskId: string): Promise<MatchLogEntry[]> {
  const response = await api.get<MatchLogEntry[]>(`/terminology/tasks/${taskId}/matches`)
  return response.data
}
