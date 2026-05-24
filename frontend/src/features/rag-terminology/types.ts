export type TermSourceType = "system" | "user" | "imported" | "auto_extracted" | "manual" | "bibtex_imported" | "shared_by_user";

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

export interface TerminologyUploadResult {
  accepted: number;
  rejected: number;
  errors: string[];
  term_ids: string[];
}

export interface CreateTermPayload {
  source_term: string;
  target_term: string;
  source_lang?: string;
  target_lang?: string;
  domain?: string;
  source_type?: string;
  status?: string;
}

export interface UpdateTermPayload {
  source_term?: string;
  target_term?: string;
  source_lang?: string;
  target_lang?: string;
  domain?: string;
  status?: string;
}

export interface BatchOperationPayload {
  term_ids: string[];
  operation: "approve" | "reject" | "delete";
  reason?: string;
}

export interface DomainInfo {
  value: string;
  label_zh: string;
  group: string | null;
}

export interface DomainsResponse {
  domains: DomainInfo[];
  groups: Record<string, { label_zh: string; members: string[] }>;
}

export interface TermFormData {
  source_term: string;
  target_term: string;
  source_lang: string;
  target_lang: string;
  domain?: string;
}
