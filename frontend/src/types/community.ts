/**
 * 社区模块类型定义
 *
 * 定义社区（Community）功能所需的所有 TypeScript 类型，包括：
 * - 论文数据模型、状态枚举
 * - Agent 对话/流式事件类型
 * - 收藏夹、点赞、阅读器、管理后台等接口类型
 */

/** 社区来源状态 */
export type CommunityStatus = "official" | "user_fallback"

/** 翻译任务状态 */
export type TranslationStatus =
  | "not_started"
  | "queued"
  | "processing"
  | "completed"
  | "failed"

/** 论文资源摘要 */
export interface PaperAssetSummary {
  id: string
  task_id: string | null
  asset_type: string
  file_name: string
  mime_type: string
  created_at: string | null
}

/** 用户对论文的交互状态（点赞、收藏） */
export interface ViewerState {
  liked: boolean
  favorited: boolean
  favorite_folder_count?: number
}

/** 收藏夹 */
export interface FavoriteFolder {
  id: string
  name: string
  paper_count: number
  created_at: string | null
  updated_at: string | null
}

/** 收藏夹列表响应 */
export interface FavoriteFolderListResponse {
  items: FavoriteFolder[]
}

/** 收藏夹变更响应 */
export interface FavoriteFolderMutationResponse {
  folder: FavoriteFolder
}

/** 收藏夹删除响应 */
export interface FavoriteFolderDeleteResponse {
  folder_id: string
  deleted: boolean
}

/** 论文收藏夹状态查询响应 */
export interface PaperFavoriteFolderStateResponse {
  paper_id: string
  items: FavoriteFolder[]
  selected_folder_ids: string[]
  favorited: boolean
  favorite_folder_count: number
}

/** 论文收藏夹更新响应 */
export interface PaperFavoriteFolderUpdateResponse {
  paper_id: string
  favorited: boolean
  favorite_folder_count: number
  favorite_count: number
  selected_folder_ids: string[]
}

/** 论文点赞响应 */
export interface PaperLikeResponse {
  paper_id: string
  liked: boolean
  like_count: number
}

/** 收藏夹内的论文列表响应 */
export interface FavoriteFolderPapersResponse {
  folder: FavoriteFolder
  items: CommunityPaper[]
  total: number
}

/** 社区论文 */
export interface CommunityPaper {
  id: string
  source: "upload" | "arxiv"
  arxiv_id: string | null
  arxiv_url?: string | null
  github_url?: string | null
  title: string
  authors: unknown[]
  categories: string[]
  abstract_raw?: string | null
  abstract_translated?: string | null
  community_status?: CommunityStatus | null
  trans_status: TranslationStatus
  created_at: string | null
  arxiv_published_at?: string | null
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

/** 社区论文列表响应 */
export interface CommunityPaperListResponse {
  items: CommunityPaper[]
  total: number
  offset?: number
  limit?: number | null
  has_more?: boolean
  next_offset?: number | null
  source_mode?: "database" | "baseline_seed"
}

/** Agent 意图类型 */
export type CommunityAgentIntent = "search" | "answer" | "translate"

/** Agent 运行模式 */
export type CommunityAgentMode = "chat" | "deep_research"

/** Agent 技能开关 */
export interface CommunityAgentSkillToggles {
  external_search: boolean
}

/** Agent 引用 */
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

/** Agent 工具调用追踪 */
export interface CommunityAgentToolTrace {
  id: string
  kind: string
  label: string
  provider: string
  status: string
  detail?: string | null
}

/** Agent 各 Provider 状态 */
export interface CommunityAgentProviderState {
  internal_search: string
  external_search: string
  reasoning: string
  translation_bridge: string
}

/** Agent 操作动作 */
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

/** Agent 深度研究报告 */
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

/** Agent 运行已接受的响应 */
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

/** Agent 完整运行记录 */
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

/** SSE 流事件类型 */
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

/** SSE 流事件 */
export interface CommunityAgentStreamEvent {
  type: CommunityAgentStreamEventType
  run_id?: string
  sequence?: number
  timestamp?: string
  data: Record<string, unknown>
}

/** 对话轮次角色 */
export type CommunityConversationTurnRole = "user" | "assistant"

/** 对话轮次 */
export interface CommunityConversationTurn {
  id: string
  role: CommunityConversationTurnRole
  content: string
  created_at: string
  run?: CommunityAgentRun | null
  status?: "running" | "completed" | "failed"
  error?: string | null
}

/** 对话记录 */
export interface CommunityConversationRecord {
  id: string
  title: string
  created_at: string
  updated_at: string
  turns: CommunityConversationTurn[]
}

/** 论文阅读模式 */
export type CommunityPaperReaderMode =
  | "source"
  | "translated"
  | "translated_html"
  | "translated_pdf"
  | "bilingual_compare"

/** 论文阅读器可用状态 */
export type CommunityPaperReaderState =
  | "source_ready"
  | "translated_ready"
  | "warming"
  | "unavailable"

/** 论文失败类型 */
export type CommunityPaperFailureType =
  | "source_unavailable"
  | "queue_busy"
  | "translation_failed"
  | "external_search_unavailable"

/** 论文阅读器锚点 */
export interface CommunityPaperReaderAnchor {
  anchor_id: string
  kind: "section" | "block" | "anchor" | string
  label?: string | null
}

/** 论文阅读体验描述 */
export interface CommunityPaperExperience {
  stage_label: string
  can_leave_hint?: string | null
  failure_type?: CommunityPaperFailureType | null
}

/** 论文阅读器资源 */
export interface CommunityPaperReaderResource {
  kind: "source_html" | "source_pdf" | "external_arxiv_html" | "preview_html" | "translated_pdf"
  html_content?: string | null
  url?: string | null
  anchors?: CommunityPaperReaderAnchor[]
}

/** 论文阅读器 */
export interface CommunityPaperReader {
  preferred_mode: CommunityPaperReaderMode
  available_modes: CommunityPaperReaderMode[]
  source?: CommunityPaperReaderResource | null
  translated?: CommunityPaperReaderResource | null
  active_anchor_id?: string | null
  state: CommunityPaperReaderState
}

/** 阅读器选中文本上下文 */
export interface ReaderSelectionContext {
  text: string
  anchor_id: string | null
  mode: CommunityPaperReaderMode
  position?: { x: number, y: number }
  range?: Range
  color?: string
  note?: string
}

/** 论文注释 */
export interface PaperAnnotation {
  id: string
  text: string
  range: Range
  anchor_id: string | null
  mode: CommunityPaperReaderMode
  color: string
  note: string
}

/** 注释覆盖层矩形 */
export interface PaperAnnotationOverlayRect {
  id: string
  color: string
  top: number
  left: number
  width: number
  height: number
}

/** 结构化洞察分区 */
export interface StructuredInsightSection {
  section_key: StructuredInsightSectionKey
  content?: string | null
  raw_content?: string | null
  summary?: string | null
  blocks?: StructuredInsightBlock[] | null
  status?: string | null
  updated_at?: string | null
}

/** 结构化洞察块 */
export interface StructuredInsightBlock {
  heading: string
  content: string
}

/** 结构化洞察分区键常量 */
export const STRUCTURED_INSIGHT_SECTION_KEYS = [
  "problem",
  "solution",
  "innovation",
  "experiment",
  "future",
] as const

/** 结构化洞察分区键类型 */
export type StructuredInsightSectionKey = (typeof STRUCTURED_INSIGHT_SECTION_KEYS)[number]

/** 结构化洞察完整负载 */
export interface StructuredInsightsPayload {
  state: string
  sections: StructuredInsightSection[]
}

/** 社区论文详情响应 */
export interface CommunityPaperDetailResponse {
  paper: CommunityPaper
  preview?: CommunityPaperPreviewResponse | null
  reader_state?: "ready" | "warming" | "unavailable"
  reader?: CommunityPaperReader | null
  experience?: CommunityPaperExperience | null
  structured_insights?: StructuredInsightsPayload | null
}

/** 相似论文条目 */
export interface CommunityPaperSimilarItem {
  arxiv_id: string
  title: string
  abstract: string
  arxiv_url: string
  community_paper_id?: string | null
  link_type: "community" | "arxiv" | string
}

/** 相似论文列表响应 */
export interface CommunityPaperSimilarResponse {
  items: CommunityPaperSimilarItem[]
}

/** 论文提交响应 */
export interface CommunityPaperSubmitResponse {
  paper: CommunityPaper
  task: {
    task_id: string | null
    status: string | null
  }
  admission_result: string
}

/** 社区论文翻译响应 */
export interface CommunityPaperTranslateResponse {
  paper_id: string
  task_id: string
  status: string
  reused_existing_task: boolean
  processing_url: string
}

/** 社区论文预览响应 */
export interface CommunityPaperPreviewResponse {
  paper_id: string
  task_id: string | null
  asset: PaperAssetSummary
  html_content?: string | null
  generated_at: string | null
  fetch_url?: string | null
}

/** 社区论文下载会话响应 */
export interface CommunityPaperDownloadSessionResponse {
  paper_id: string
  asset_id: string
  download_url: string
  expires_at: string
}

/** 管理员整理任务批次条目 */
export interface AdminCurationBatchItem {
  job_id: string
  paper_id?: string | null
  source_type: string
  arxiv_id?: string | null
  original_filename?: string | null
  status: string
  error?: string | null
}

/** 管理员整理任务批次响应 */
export interface AdminCurationBatchResponse {
  batch_id: string
  status: string
  items: AdminCurationBatchItem[]
}

/** 管理员整理任务历史条目 */
export interface AdminCurationJobHistoryItem {
  job_id: string
  batch_id: string
  paper_id?: string | null
  published_paper_id?: string | null
  task_id?: string | null
  source_type: string
  arxiv_id?: string | null
  original_filename?: string | null
  status: string
  terminal_task_status?: string | null
  error?: string | null
  failed_artifact_path?: string | null
  created_at?: string | null
  updated_at?: string | null
}

/** 管理员整理任务历史响应 */
export interface AdminCurationJobHistoryResponse {
  items: AdminCurationJobHistoryItem[]
  total: number
}

/** 管理员删除论文响应 */
export interface AdminDeletePaperResponse {
  job_id: string
  paper_id: string
  status: string
}

/** 管理员删除整理任务响应 */
export interface AdminDeleteCurationJobResponse {
  job_id: string
  paper_id?: string | null
  status: string
}

/** 管理员批量删除失败条目 */
export interface AdminBatchDeleteCurationJobsFailure {
  job_id: string
  status_code: number
  detail?: string | null
}

/** 管理员批量删除整理任务响应 */
export interface AdminBatchDeleteCurationJobsResponse {
  deleted: AdminDeleteCurationJobResponse[]
  failed: AdminBatchDeleteCurationJobsFailure[]
  deleted_count: number
  failed_count: number
}

/** 论文导入请求 */
export interface CommunityPaperImportRequest {
  source: "arxiv"
  arxiv_id: string
}

/** 论文导入响应 */
export interface CommunityPaperImportResponse {
  paper_id: string
  reused: boolean
  imported: boolean
  reader_state: CommunityPaperReaderState
}

/** 社区 Feed 排序方式 */
export type CommunityFeedSort = "latest" | "hot" | "views" | "likes"
