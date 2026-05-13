# Specification: RAG Terminology Management

## ADDED Requirements

### Requirement: Optional RAG Terminology Mode
The system SHALL provide RAG terminology enhancement as an explicit opt-in capability for the translation tool, disabled by default.

#### Scenario: Default translation remains unchanged
- **WHEN** a translation task is created without the RAG terminology option
- **THEN** the system MUST execute the existing default translation behavior without terminology RAG retrieval or glossary injection
- **AND** the system MUST NOT change default `origin_cli_parity` behavior.

#### Scenario: User enables RAG terminology
- **WHEN** a user explicitly enables RAG terminology in the translation tool
- **THEN** the system MUST run terminology retrieval for eligible translation chunks
- **AND** the system MAY inject retrieved terms into translation prompts for that opted-in execution only.

### Requirement: MySQL Terminology Review Store
The system SHALL use MySQL as the source of truth for terminology entries, review status, ownership, provenance metadata, and vector synchronization metadata.

#### Scenario: Term is stored for review
- **WHEN** a new terminology pair is uploaded, imported, or auto-extracted
- **THEN** the system MUST persist it in MySQL with source term, target term, language pair, domain, source type, status, provenance metadata, creator/reviewer metadata, and timestamps.

#### Scenario: Supabase is not required
- **WHEN** the RAG terminology service starts or executes retrieval
- **THEN** it MUST NOT require Supabase tables, Supabase RPC functions, Supabase RLS policies, or Supabase credentials.

#### Scenario: Provenance metadata is preserved
- **WHEN** a term is imported from CSV or extracted from BibTeX
- **THEN** the system MUST store provenance metadata (source file, row number, citation key) in a JSON field
- **AND** the provenance MUST be inspectable via the terminology management API.

### Requirement: Milvus Approved-Term Vector Index
The system SHALL use Milvus as the vector retrieval index for approved terminology embeddings when vector retrieval is enabled.

#### Scenario: Approved term is indexed
- **WHEN** an administrator approves a term and embedding generation succeeds
- **THEN** the system MUST upsert the term embedding into the configured Milvus collection
- **AND** update MySQL vector synchronization metadata for that term.

#### Scenario: Pending terms are excluded from vector retrieval
- **WHEN** a term has `pending_review` or `rejected` status
- **THEN** the system MUST NOT return that term from Milvus vector retrieval.

### Requirement: Three-Stage RAG Pipeline
The system SHALL implement the terminology RAG flow as query transformation, hybrid retrieval (BM25 + vector), and Cross-Encoder reranking before prompt injection.

#### Scenario: Pipeline runs for an opted-in chunk
- **WHEN** an eligible LaTeX chunk is translated with RAG terminology enabled
- **THEN** the system MUST extract plain text or terminology queries from the chunk
- **AND** retrieve candidates through BM25 keyword and Milvus vector paths
- **AND** rerank candidates with a Cross-Encoder model before selecting terms for injection.

### Requirement: BM25 Keyword Retrieval
The system SHALL use BM25 scoring as the keyword retrieval path for approved terminology terms.

#### Scenario: BM25 scores approved terms against query
- **WHEN** a query string is submitted for terminology retrieval
- **THEN** the system MUST build or refresh an in-memory BM25 index from approved term source texts
- **AND** score each approved term against the query using BM25
- **AND** return a ranked list of candidate terms with BM25 scores.

#### Scenario: BM25 index refreshes on approval changes
- **WHEN** a term is approved, rejected, added, or removed
- **THEN** the system MUST refresh the BM25 index on the next retrieval call or within a configurable interval.

#### Scenario: BM25 complements exact MySQL matching
- **WHEN** BM25 retrieval and MySQL exact matching both execute
- **THEN** the system MUST merge and deduplicate candidates by MySQL term id
- **AND** preserve the higher score from either path for deduplicated results.

### Requirement: Cross-Encoder Reranking
The system SHALL use a Cross-Encoder model to rerank merged retrieval candidates before glossary injection.

#### Scenario: Cross-Encoder scores candidate terms
- **WHEN** merged keyword and vector candidates are available
- **THEN** the system MUST score each (chunk_text, candidate_source_term) pair using a Cross-Encoder model
- **AND** select the Top-N terms by Cross-Encoder relevance score.

#### Scenario: Cross-Encoder is unavailable
- **WHEN** the configured Cross-Encoder model fails, is unavailable, or is not configured
- **THEN** the system MUST fall back to BM25 and vector similarity score merge with priority ordering
- **AND** continue translation without failing the task.

### Requirement: Multi-Source Knowledge Base Ingestion
The system SHALL ingest terminology candidates from multiple external sources: CSV batch import, BibTeX citation parsing, and post-translation auto-extraction.

#### Scenario: CSV terminology import
- **WHEN** a user uploads a CSV file with source_term, target_term, and language pair columns
- **THEN** the system MUST validate row format, detect duplicates by (source_term, target_term, language pair)
- **AND** store valid rows in MySQL with `source_type=imported` and `status=pending_review`
- **AND** reject invalid rows with a descriptive error.

#### Scenario: BibTeX citation-based term extraction
- **WHEN** a user uploads a BibTeX file with citation entries
- **THEN** the system MUST parse citation keys and entry metadata
- **AND** use LLM to suggest source-target term candidates from citation context
- **AND** store candidates with `source_type=auto_extracted` and provenance metadata linking back to the citation.

#### Scenario: Post-translation auto-extraction
- **WHEN** an opted-in translation chunk completes and terminology extraction finds source-target pairs
- **THEN** the system MUST store those pairs in MySQL with `status=pending_review` and link them to the translation task.

### Requirement: Term Priority And Conflict Handling
The system SHALL prioritize user/imported terms over system terms when multiple approved terms conflict for the same source phrase.

#### Scenario: User term conflicts with system term
- **WHEN** an approved user/imported term and an approved system term share the same source phrase for the same language pair
- **THEN** the user/imported term MUST be preferred for that user's opted-in translation.

### Requirement: Glossary Injection
The system SHALL select a bounded Top-N set of terms and inject them as a compact `<Glossary>` block only for opted-in translation executions.

#### Scenario: Relevant terms are injected
- **WHEN** Cross-Encoder reranking succeeds for retrieved terminology candidates
- **THEN** the system MUST select the configured Top-N relevant terms
- **AND** include them in the translation prompt as a bounded `<Glossary>` block.

#### Scenario: Reranking is unavailable
- **WHEN** the Cross-Encoder reranker fails or is unavailable
- **THEN** the system MUST fall back to merged BM25 and vector scores with priority ordering
- **AND** continue translation without failing the task.

### Requirement: Terminology Auto-Extraction And Admin Review
The system SHALL submit all ingested candidates (CSV, BibTeX, auto-extracted) to the same admin review workflow.

#### Scenario: Candidate term is stored as pending
- **WHEN** a candidate term enters the system from any ingestion source
- **THEN** the system MUST store it in MySQL with `status=pending_review`
- **AND** the term MUST NOT participate in retrieval until approved.

#### Scenario: Administrator approves a candidate
- **WHEN** an administrator approves a pending term
- **THEN** the system MUST mark it `approved`
- **AND** refresh the BM25 index for that term's source language
- **AND** attempt embedding generation and Milvus upsert.

#### Scenario: Administrator rejects a candidate
- **WHEN** an administrator rejects a pending term
- **THEN** the system MUST mark it `rejected`
- **AND** exclude it from BM25 keyword and Milvus vector retrieval.

### Requirement: Terminology Management API
The system SHALL expose API endpoints for terminology listing, upload (CSV, BibTeX), pending review, approval, rejection, and task-level matched-term inspection.

#### Scenario: Admin review requires authorization
- **WHEN** a non-admin user calls an admin review endpoint
- **THEN** the system MUST reject the request with an authorization error.

#### Scenario: CSV and BibTeX upload endpoints
- **WHEN** a user calls the upload endpoint with a CSV or BibTeX file
- **THEN** the system MUST validate file size (configurable limit), content type, and format
- **AND** return a processing result with counts of accepted and rejected rows.

#### Scenario: Matched terms are inspectable
- **WHEN** a RAG-enabled translation task records matched or injected terms
- **THEN** the system SHOULD expose those terms to authorized clients for UI display and evaluation.

### Requirement: Graceful Degradation
The RAG terminology pipeline SHALL fail gracefully without blocking translation.

#### Scenario: Retrieval dependency fails
- **WHEN** query transformation, BM25 index build, embedding, Milvus retrieval, MySQL retrieval, or Cross-Encoder reranking fails for a chunk
- **THEN** the system MUST continue translation without RAG terminology injection for that chunk
- **AND** record a warning or diagnostic event.

### Requirement: Evaluation Observability
The system SHALL record enough matched-term evidence to compare baseline and RAG-enabled translation runs for graduation-design evaluation.

#### Scenario: RAG run records evidence
- **WHEN** a task runs with RAG terminology enabled
- **THEN** the system MUST record selected term ids, source terms, target terms, retrieval source (BM25 / vector / both), and whether each term was injected
- **AND** the record MUST be usable for terminology consistency evaluation.

### Requirement: BLEU/ROUGE Evaluation
The system SHALL provide evaluation scripts to compute BLEU and ROUGE scores comparing baseline (no RAG) and RAG-enabled translation outputs.

#### Scenario: Evaluation script compares paired outputs
- **WHEN** the evaluation script runs on a baseline and a RAG-enabled translation of the same source paper
- **THEN** the system MUST compute sentence-level and document-level BLEU and ROUGE scores for both outputs
- **AND** report the delta (RAG - baseline) for each metric.

#### Scenario: Terminology consistency measurement
- **WHEN** the evaluation script runs on a paired output
- **THEN** the system MUST compute a terminology consistency score: the proportion of predefined key terms that are translated identically across all their occurrences in the output
- **AND** report the per-term consistency rate and the aggregate rate.

### Requirement: Evaluation Artifacts
The system SHALL export evaluation artifacts suitable for graduation-design thesis reporting.

#### Scenario: Evaluation report is generated
- **WHEN** the evaluation completes on a test dataset
- **THEN** the system MUST generate a structured report (JSON or CSV) containing BLEU, ROUGE, and terminology consistency scores
- **AND** include matched-term logs from the RAG-enabled run for qualitative analysis.
