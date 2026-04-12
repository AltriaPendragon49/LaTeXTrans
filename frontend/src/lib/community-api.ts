import { API_BASE_URL, PAPER_PREVIEW_API_BASE_URL } from "@/api-base"
import api from "@/lib/api"
import { getAccessToken } from "@/lib/local-auth"
import { retryOnTransientNetworkError } from "@/lib/network-retry"
import type {
  AdminCurationBatchResponse,
  AdminDeletePaperResponse,
  CommunityAgentAcceptedRun,
  CommunityAgentMode,
  CommunityAgentRun,
  CommunityAgentStreamEvent,
  CommunityAgentSkillToggles,
  CommunityConversationRecord,
  CommunityFeedSort,
  CommunityPaperDetailResponse,
  CommunityPaperDownloadSessionResponse,
  CommunityPaperImportRequest,
  CommunityPaperImportResponse,
  CommunityPaperListResponse,
  CommunityPaperPreviewResponse,
  CommunityPaperSimilarResponse,
  CommunityPaperSubmitResponse,
  CommunityPaperTranslateResponse,
} from "@/types/community"
import type { TranslateRequest } from "@/lib/api"

const communityPaperDetailCache = new Map<string, CommunityPaperDetailResponse>()
const communityPaperDetailInflight = new Map<string, Promise<CommunityPaperDetailResponse>>()

export async function getCommunityPapers(params: {
  sort: CommunityFeedSort
  q?: string
  limit?: number
}): Promise<CommunityPaperListResponse> {
  const response = await retryOnTransientNetworkError(
    () =>
      api.get<CommunityPaperListResponse>("/papers", {
        params: {
          sort: params.sort,
          ...(params.q ? { q: params.q } : {}),
          ...(params.limit ? { limit: params.limit } : {}),
        },
      }),
    { attempts: 3, baseDelayMs: 150 },
  )
  return response.data
}

export async function createCommunityAgentRun(payload: {
  input: string
  paper_id?: string
  context?: Record<string, unknown>
  skill_toggles?: CommunityAgentSkillToggles
  mode?: CommunityAgentMode
}): Promise<CommunityAgentRun> {
  const response = await api.post<CommunityAgentRun>("/community-agent/runs", payload)
  return response.data
}

function parseSseFrame(frame: string): CommunityAgentStreamEvent | null {
  const lines = frame
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)

  if (!lines.length) {
    return null
  }

  let eventType = ""
  const dataLines: string[] = []
  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventType = line.slice("event:".length).trim()
      continue
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trim())
    }
  }

  if (!dataLines.length) {
    return null
  }

  const payload = JSON.parse(dataLines.join("\n")) as CommunityAgentStreamEvent
  if (!payload.type && eventType) {
    payload.type = eventType as CommunityAgentStreamEvent["type"]
  }
  return payload
}

async function fetchCommunityAgentRunResult(resultUrl: string): Promise<CommunityAgentRun> {
  const token = await getAccessToken()
  const response = await retryOnTransientNetworkError(
    () =>
      fetch(`${API_BASE_URL}${resultUrl}`, {
        headers: token
          ? {
              Authorization: `Bearer ${token}`,
            }
          : undefined,
      }),
    { attempts: 3, baseDelayMs: 150 },
  )

  if (!response.ok) {
    throw new Error(`Failed to fetch run result: ${response.status}`)
  }
  return (await response.json()) as CommunityAgentRun
}

export async function streamCommunityAgentRun(
  payload: {
    input: string
    paper_id?: string
    context?: Record<string, unknown>
    skill_toggles?: CommunityAgentSkillToggles
    mode?: CommunityAgentMode
  },
  options: {
    onEvent?: (event: CommunityAgentStreamEvent) => void
  } = {},
): Promise<CommunityAgentRun> {
  const acceptedResponse = await api.post<CommunityAgentAcceptedRun>("/community-agent/runs", {
    ...payload,
    execution_mode: "async",
  })
  const acceptedRun = acceptedResponse.data
  const token = await getAccessToken()

  const response = await fetch(`${API_BASE_URL}${acceptedRun.stream_url}`, {
    headers: token
      ? {
          Authorization: `Bearer ${token}`,
        }
      : undefined,
  })

  if (!response.ok || !response.body) {
    return fetchCommunityAgentRunResult(acceptedRun.result_url)
  }

  const decoder = new TextDecoder()
  let buffer = ""
  let completedRun: CommunityAgentRun | null = null

  const notify = (event: CommunityAgentStreamEvent) => {
    options.onEvent?.(event)
    if (event.type === "complete") {
      const snapshot = event.data.snapshot
      if (snapshot && typeof snapshot === "object") {
        completedRun = snapshot as CommunityAgentRun
      }
    }
  }

  const reader = response.body.getReader()
  while (true) {
    const { value, done } = await reader.read()
    if (done) {
      break
    }

    buffer += decoder.decode(value, { stream: true })
    const frames = buffer.split(/\r?\n\r?\n/)
    buffer = frames.pop() ?? ""

    for (const frame of frames) {
      const event = parseSseFrame(frame)
      if (!event) {
        continue
      }
      notify(event)
    }
  }

  if (buffer.trim()) {
    const trailingEvent = parseSseFrame(buffer)
    if (trailingEvent) {
      notify(trailingEvent)
    }
  }

  if (completedRun) {
    return completedRun
  }

  return fetchCommunityAgentRunResult(acceptedRun.result_url)
}

export async function listCommunityAgentConversations(): Promise<CommunityConversationRecord[]> {
  const response = await api.get<CommunityConversationRecord[]>("/community-agent/conversations")
  return response.data
}

export async function upsertCommunityAgentConversation(
  record: CommunityConversationRecord,
): Promise<CommunityConversationRecord> {
  const response = await api.put<CommunityConversationRecord>(
    `/community-agent/conversations/${record.id}`,
    record,
  )
  return response.data
}

export async function deleteCommunityAgentConversation(conversationId: string): Promise<{ deleted: boolean }> {
  const response = await api.delete<{ deleted: boolean }>(`/community-agent/conversations/${conversationId}`)
  return response.data
}

export async function importCommunityPaper(
  payload: CommunityPaperImportRequest,
): Promise<CommunityPaperImportResponse> {
  const response = await api.post<CommunityPaperImportResponse>("/papers/import", payload)
  return response.data
}

export async function getCommunityPaperDetail(
  paperId: string,
): Promise<CommunityPaperDetailResponse> {
  const response = await retryOnTransientNetworkError(
    () => api.get<CommunityPaperDetailResponse>(`/papers/${paperId}`),
    { attempts: 3, baseDelayMs: 150 },
  )
  communityPaperDetailCache.set(paperId, response.data)
  return response.data
}

export async function getCommunityPaperSimilar(
  paperId: string,
): Promise<CommunityPaperSimilarResponse> {
  const response = await retryOnTransientNetworkError(
    () => api.get<CommunityPaperSimilarResponse>(`/papers/${paperId}/similar`),
    { attempts: 3, baseDelayMs: 150 },
  )
  return response.data
}

export async function submitAdminArxivCurationBatch(
  payload: {
    arxiv_ids: string[]
    source_language: string
    target_language: string
  },
): Promise<AdminCurationBatchResponse> {
  const response = await api.post<AdminCurationBatchResponse>("/papers/admin/curation/arxiv", payload)
  return response.data
}

export async function submitAdminUploadCurationBatch(params: {
  files: File[]
  source_language: string
  target_language: string
}): Promise<AdminCurationBatchResponse> {
  const formData = new FormData()
  params.files.forEach((file) => {
    formData.append("files", file)
  })
  formData.append("source_language", params.source_language)
  formData.append("target_language", params.target_language)

  const response = await api.post<AdminCurationBatchResponse>("/papers/admin/curation/uploads", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  })
  return response.data
}

export async function getAdminCurationBatch(
  batchId: string,
): Promise<AdminCurationBatchResponse> {
  const response = await retryOnTransientNetworkError(
    () => api.get<AdminCurationBatchResponse>(`/papers/admin/curation/batches/${batchId}`),
    { attempts: 3, baseDelayMs: 150 },
  )
  return response.data
}

export function getCachedCommunityPaperDetail(paperId: string): CommunityPaperDetailResponse | null {
  return communityPaperDetailCache.get(paperId) ?? null
}

export function primeCommunityPaperDetailCache(
  paperId: string,
  payload: CommunityPaperDetailResponse,
): void {
  communityPaperDetailCache.set(paperId, payload)
}

export function clearCommunityPaperDetailCache(): void {
  communityPaperDetailCache.clear()
  communityPaperDetailInflight.clear()
}

export function preloadPaperDetailRoute(): Promise<unknown> {
  return import("@/pages/PaperDetail")
}

export async function prefetchCommunityPaperDetail(
  paperId: string,
): Promise<CommunityPaperDetailResponse> {
  const cached = communityPaperDetailCache.get(paperId)
  if (cached) {
    return cached
  }

  const inflight = communityPaperDetailInflight.get(paperId)
  if (inflight) {
    return inflight
  }

  const request = getCommunityPaperDetail(paperId).finally(() => {
    communityPaperDetailInflight.delete(paperId)
  })
  communityPaperDetailInflight.set(paperId, request)
  return request
}

export async function recordCommunityPaperView(paperId: string): Promise<void> {
  await api.post(`/papers/${paperId}/view`)
}

export async function submitCommunityPaperFromArxiv(payload: {
  arxiv_id: string
  source_language: string
  target_language: string
}): Promise<CommunityPaperSubmitResponse> {
  const response = await api.post<CommunityPaperSubmitResponse>("/papers/submit", payload)
  return response.data
}

export async function submitCommunityPaperFromUpload(
  file: File,
  payload: {
    source_language: string
    target_language: string
  },
): Promise<CommunityPaperSubmitResponse> {
  const formData = new FormData()
  formData.append("file", file)
  formData.append("source_language", payload.source_language)
  formData.append("target_language", payload.target_language)

  const response = await api.post<CommunityPaperSubmitResponse>("/papers/submit", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  })
  return response.data
}

export async function translateCommunityPaper(
  paperId: string,
  config: TranslateRequest,
): Promise<CommunityPaperTranslateResponse> {
  const response = await api.post<CommunityPaperTranslateResponse>(`/papers/${paperId}/translate`, config)
  return response.data
}

export async function getCommunityPaperPreview(
  paperId: string,
): Promise<CommunityPaperPreviewResponse> {
  const relativePath = `/api/papers/${paperId}/preview`
  const preferredUrl = `${PAPER_PREVIEW_API_BASE_URL}${relativePath}`
  const fallbackUrl = `${API_BASE_URL}${relativePath}`

  const fetchPreview = async (url: string): Promise<CommunityPaperPreviewResponse> => {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch paper preview: ${response.status}`)
    }

    return (await response.json()) as CommunityPaperPreviewResponse
  }

  try {
    return await retryOnTransientNetworkError(
      () => fetchPreview(preferredUrl),
      { attempts: 3, baseDelayMs: 150 },
    )
  } catch (error) {
    if (preferredUrl === fallbackUrl) {
      throw error
    }

    return await retryOnTransientNetworkError(
      () => fetchPreview(fallbackUrl),
      { attempts: 3, baseDelayMs: 150 },
    )
  }
}

export async function createCommunityPaperDownloadSession(
  paperId: string,
): Promise<CommunityPaperDownloadSessionResponse> {
  const response = await retryOnTransientNetworkError(
    () => api.post<CommunityPaperDownloadSessionResponse>(`/papers/${paperId}/download-session`),
    { attempts: 3, baseDelayMs: 150 },
  )
  return response.data
}

export async function deleteCommunityPaper(
  paperId: string,
): Promise<AdminDeletePaperResponse> {
  const response = await api.delete<AdminDeletePaperResponse>(`/papers/admin/${paperId}`)
  return response.data
}
