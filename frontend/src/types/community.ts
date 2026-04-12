export type CommunityStatus = "official" | "user_fallback"

export type TranslationStatus =
  | "not_started"
  | "queued"
  | "processing"
  | "completed"
  | "failed"

export interface PaperAssetSummary {
  id: string
  task_id: string | null
  asset_type: string
  file_name: string
  mime_type: string
  created_at: string | null
}

export interface ViewerState {
  liked: boolean
  favorited: boolean
}

export interface CommunityPaper {
  id: string
  source: "upload" | "arxiv"
  arxiv_id: string | null
  title: string
  authors: unknown[]
  categories: string[]
  abstract_raw?: string | null
  abstract_translated?: string | null
  community_status: CommunityStatus
  trans_status: TranslationStatus
  created_at: string | null
  official_published_at: string | null
  community_selected_task_id: string | null
  community_selected_asset_id: string | null
  visibility?: string
  status?: string
  like_count?: number
  favorite_count?: number
  comment_count?: number
  view_count?: number
  download_count?: number
  latest_asset?: PaperAssetSummary | null
  assets?: Partial<Record<PaperAssetSummary["asset_type"], PaperAssetSummary>> | null
  viewer_state?: ViewerState | null
}

export interface CommunityPaperListResponse {
  items: CommunityPaper[]
  total: number
  source_mode?: "database" | "baseline_seed"
}

export type CommunityAgentIntent = "search" | "answer" | "translate"
export type CommunityAgentMode = "chat" | "deep_research"

export interface CommunityAgentSkillToggles {
  external_search: boolean
}

export interface CommunityAgentCitation {
  id: string
  title: string
  url?: string | null
  source: string
  arxiv_id?: string | null
  paper_id?: string | null
  anchor_id?: string | null
  snippet?: string | null
}

export interface CommunityAgentToolTrace {
  id: string
  kind: string
  label: string
  provider: string
  status: string
  detail?: string | null
}

export interface CommunityAgentProviderState {
  internal_search: string
  external_search: string
  reasoning: string
  translation_bridge: string
}

export interface CommunityAgentAction {
  type: "navigate_paper" | "open_url"
  paper_id?: string | null
  anchor_id?: string | null
  task_id?: string | null
  url?: string | null
  auto_started_translation?: boolean | null
  reused?: boolean | null
  imported?: boolean | null
}

export interface CommunityAgentReport {
  format: "markdown"
  body_markdown: string
  evidence_count: number
  target_min_evidence: number
  target_max_evidence: number
  context_pack_limit?: number
  timeout_seconds?: number
  partial_coverage: boolean
  coverage_note: string
}

export interface CommunityAgentAcceptedRun {
  run_id: string
  status: "accepted" | "queued" | "running"
  intent?: CommunityAgentIntent | null
  mode?: CommunityAgentMode | null
  message?: string | null
  summary?: string | null
  tool_trace?: CommunityAgentToolTrace[]
  citations?: CommunityAgentCitation[]
  provider_state?: CommunityAgentProviderState | null
  action?: CommunityAgentAction | null
  report?: CommunityAgentReport | null
  stream_url: string
  result_url: string
}

export interface CommunityAgentRun {
  run_id: string
  status: "accepted" | "queued" | "running" | "completed" | "failed"
  intent?: CommunityAgentIntent | null
  mode?: CommunityAgentMode | null
  message?: string | null
  summary?: string | null
  tool_trace?: CommunityAgentToolTrace[]
  citations?: CommunityAgentCitation[]
  provider_state?: CommunityAgentProviderState | null
  action?: CommunityAgentAction | null
  report?: CommunityAgentReport | null
  stream_url?: string | null
  result_url?: string | null
}

export type CommunityAgentStreamEventType =
  | "status"
  | "assistant_delta"
  | "tool_start"
  | "tool_result"
  | "citation"
  | "action"
  | "complete"
  | "error"
  | "heartbeat"

export interface CommunityAgentStreamEvent {
  type: CommunityAgentStreamEventType
  run_id?: string
  sequence?: number
  timestamp?: string
  data: Record<string, unknown>
}

export type CommunityConversationTurnRole = "user" | "assistant"

export interface CommunityConversationTurn {
  id: string
  role: CommunityConversationTurnRole
  content: string
  created_at: string
  run?: CommunityAgentRun | null
  status?: "running" | "completed" | "failed"
  error?: string | null
}

export interface CommunityConversationRecord {
  id: string
  title: string
  created_at: string
  updated_at: string
  turns: CommunityConversationTurn[]
}

export type CommunityPaperReaderMode =
  | "source"
  | "translated"
  | "translated_html"
  | "translated_pdf"
  | "bilingual_compare"
export type CommunityPaperReaderState =
  | "source_ready"
  | "translated_ready"
  | "warming"
  | "unavailable"
export type CommunityPaperFailureType =
  | "source_unavailable"
  | "queue_busy"
  | "translation_failed"
  | "external_search_unavailable"

export interface CommunityPaperReaderAnchor {
  anchor_id: string
  kind: "section" | "block" | "anchor" | string
  label?: string | null
}

export interface CommunityPaperExperience {
  stage_label: string
  can_leave_hint?: string | null
  failure_type?: CommunityPaperFailureType | null
}

export interface CommunityPaperReaderResource {
  kind: "source_html" | "source_pdf" | "external_arxiv_html" | "preview_html" | "translated_pdf"
  html_content?: string | null
  url?: string | null
  anchors?: CommunityPaperReaderAnchor[]
}

export interface CommunityPaperReader {
  preferred_mode: CommunityPaperReaderMode
  available_modes: CommunityPaperReaderMode[]
  source?: CommunityPaperReaderResource | null
  translated?: CommunityPaperReaderResource | null
  active_anchor_id?: string | null
  state: CommunityPaperReaderState
}

export interface ReaderSelectionContext {
  text: string
  anchor_id: string | null
  mode: CommunityPaperReaderMode
  position?: { x: number, y: number }
  range?: Range
  color?: string
  note?: string
}

export interface PaperAnnotation {
  id: string
  text: string
  range: Range
  anchor_id: string | null
  mode: CommunityPaperReaderMode
  color: string
  note: string
}

export interface PaperAnnotationOverlayRect {
  id: string
  color: string
  top: number
  left: number
  width: number
  height: number
}

export interface StructuredInsightSection {
  section_key: StructuredInsightSectionKey
  content?: string | null
  raw_content?: string | null
  summary?: string | null
  blocks?: StructuredInsightBlock[] | null
  status?: string | null
  updated_at?: string | null
}

export interface StructuredInsightBlock {
  heading: string
  content: string
}

export const STRUCTURED_INSIGHT_SECTION_KEYS = [
  "problem",
  "solution",
  "innovation",
  "experiment",
  "future",
] as const

export type StructuredInsightSectionKey = (typeof STRUCTURED_INSIGHT_SECTION_KEYS)[number]

export interface StructuredInsightsPayload {
  state: string
  sections: StructuredInsightSection[]
}

export interface CommunityPaperDetailResponse {
  paper: CommunityPaper
  preview?: CommunityPaperPreviewResponse | null
  reader_state?: "ready" | "warming" | "unavailable"
  reader?: CommunityPaperReader | null
  experience?: CommunityPaperExperience | null
  structured_insights?: StructuredInsightsPayload | null
}

export interface CommunityPaperSimilarItem {
  arxiv_id: string
  title: string
  abstract: string
  arxiv_url: string
  community_paper_id?: string | null
  link_type: "community" | "arxiv" | string
}

export interface CommunityPaperSimilarResponse {
  items: CommunityPaperSimilarItem[]
}

export interface CommunityPaperSubmitResponse {
  paper: CommunityPaper
  task: {
    task_id: string | null
    status: string | null
  }
  admission_result: string
}

export interface CommunityPaperTranslateResponse {
  paper_id: string
  task_id: string
  status: string
  reused_existing_task: boolean
  processing_url: string
}

export interface CommunityPaperPreviewResponse {
  paper_id: string
  task_id: string | null
  asset: PaperAssetSummary
  html_content?: string | null
  generated_at: string | null
  fetch_url?: string | null
}

export interface CommunityPaperDownloadSessionResponse {
  paper_id: string
  asset_id: string
  download_url: string
  expires_at: string
}

export interface AdminCurationBatchItem {
  job_id: string
  paper_id?: string | null
  source_type: string
  arxiv_id?: string | null
  original_filename?: string | null
  status: string
  error?: string | null
}

export interface AdminCurationBatchResponse {
  batch_id: string
  status: string
  items: AdminCurationBatchItem[]
}

export interface AdminDeletePaperResponse {
  job_id: string
  paper_id: string
  status: string
}

export interface CommunityPaperImportRequest {
  source: "arxiv"
  arxiv_id: string
}

export interface CommunityPaperImportResponse {
  paper_id: string
  reused: boolean
  imported: boolean
  reader_state: CommunityPaperReaderState
}

export type CommunityFeedSort = "latest" | "translated" | "hot"
