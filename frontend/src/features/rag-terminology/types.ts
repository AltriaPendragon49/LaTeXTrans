/** 术语来源类型 */
export type TermSourceType = "system" | "user" | "imported" | "auto_extracted" | "manual" | "bibtex_imported" | "shared_by_user";

/** 术语条目接口 */
export interface TerminologyTerm {
  id: string;
  source_term: string;
  target_term: string;
  source_lang: string;
  target_lang: string;
  domain?: string;
  source_type: TermSourceType;
  status: "pending_review" | "approved" | "rejected";
  owner_user_id?: string;
  created_by_user_id?: string;
  reviewed_by_user_id?: string;
  reviewed_at?: string;
  rejection_reason?: string;
  extracted_from_task_id?: string;
  provenance?: Record<string, unknown>;
  created_at: string;
  updated_at?: string;
}

/** 匹配日志条目接口 */
export interface MatchLogEntry {
  id: string;
  task_id: string;
  term_id: string;
  source_term: string;
  target_term: string;
  chunk_index: number;
  retrieval_source: string;
  was_injected: boolean;
  rerank_score?: number;
}

/** 术语上传结果接口 */
export interface TerminologyUploadResult {
  accepted: number;
  rejected: number;
  errors: string[];
  term_ids: string[];
}

/** 创建术语的请求体 */
export interface CreateTermPayload {
  source_term: string;
  target_term: string;
  source_lang?: string;
  target_lang?: string;
  domain?: string;
  source_type?: string;
  status?: string;
}

/** 更新术语的请求体 */
export interface UpdateTermPayload {
  source_term?: string;
  target_term?: string;
  source_lang?: string;
  target_lang?: string;
  domain?: string;
  status?: string;
}

/** 批量操作请求体 */
export interface BatchOperationPayload {
  term_ids: string[];
  operation: "approve" | "reject" | "delete";
  reason?: string;
}

/** 领域信息接口 */
export interface DomainInfo {
  value: string;
  label_zh: string;
  group: string | null;
}

/** 领域列表响应接口 */
export interface DomainsResponse {
  domains: DomainInfo[];
  groups: Record<string, { label_zh: string; members: string[] }>;
}

/** 术语表单数据接口 */
export interface TermFormData {
  source_term: string;
  target_term: string;
  source_lang: string;
  target_lang: string;
  domain?: string;
}
