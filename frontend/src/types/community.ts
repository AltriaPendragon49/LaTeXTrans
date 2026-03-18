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
}

export interface CommunityPaperDetailResponse {
  paper: CommunityPaper
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
  html_content: string
  generated_at: string | null
}

export interface CommunityPaperDownloadSessionResponse {
  paper_id: string
  asset_id: string
  download_url: string
  expires_at: string
}

export type CommunityFeedSort = "latest" | "translated" | "hot"
