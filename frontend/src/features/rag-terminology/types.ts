export interface TerminologyTerm {
  id: string;
  source_term: string;
  target_term: string;
  source_lang: string;
  target_lang: string;
  domain?: string;
  source_type: "system" | "user" | "imported" | "auto_extracted";
  status: "pending_review" | "approved" | "rejected";
  provenance?: Record<string, unknown>;
  created_at: string;
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
