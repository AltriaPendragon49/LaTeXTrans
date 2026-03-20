import type { CommunityPaper, CommunityPaperListResponse } from "@/types/community"

declare global {
  interface Window {
    __COMMUNITY_BOOTSTRAP__?: {
      feed?: CommunityPaperListResponse | null
    }
    __COMMUNITY_BOOTSTRAP_PROMISE__?: Promise<{
      items: CommunityPaper[]
      total: number
      source_mode?: "database" | "baseline_seed"
    } | null>
  }
}

export {}
