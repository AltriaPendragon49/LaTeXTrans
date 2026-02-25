# Specification: RAG Terminology Management

## ADDED Requirements

### Requirement: Three-Stage RAG Pipeline
The system MUST implement a three-stage RAG pipeline for terminology retrieval: Query Transformation → Hybrid Retrieval → Cross-Encoder Re-ranking.
#### Scenario: Full pipeline execution
Given a LaTeX section to translate,
When the system prepares the translation prompt,
Then the system MUST:
1. Extract plain text and key terminology from the LaTeX content
2. Execute both vector search and keyword search in parallel
3. Re-rank results using a Cross-Encoder model
4. Inject Top-N terms into the prompt as a `<Glossary>` block

### Requirement: Hybrid Retrieval (Dual-Path)
The system MUST execute both vector similarity search (pgvector) and keyword/full-text search (tsvector) in parallel when retrieving terminology.
#### Scenario: Semantic vs exact match
Given the query text contains "self-supervised contrastive learning",
When hybrid retrieval is executed,
Then the vector path MUST return semantically similar terms (e.g., "contrastive learning", "self-supervised pre-training")
And the keyword path MUST return exact/phrase matches (e.g., "self-supervised learning")
And both result sets MUST be merged and deduplicated.

### Requirement: Cross-Encoder Re-ranking
The system MUST use a Cross-Encoder model to re-rank the merged candidate terms from hybrid retrieval before injection.
#### Scenario: Filtering noise
Given 30 candidate terms from hybrid retrieval,
When re-ranking is applied,
Then the system MUST select only the Top-N most contextually relevant terms (default N=10)
And irrelevant terms MUST be excluded from the prompt.

### Requirement: Universal Mode Enhancement
The RAG terminology pipeline MUST apply to ALL translation modes (0, 1, 2, 3), not just mode 2.
#### Scenario: Translation in mode 0
Given a translation task in mode 0 (standard translation),
When a section is being translated,
Then the system MUST retrieve and inject relevant terms via RAG, the same as every other mode.

### Requirement: System Default Glossary
The system MUST provide a default terminology library populated with standard academic terms stored in Supabase pgvector.
#### Scenario: Translation without user glossary
Given a translation task,
When no user glossary is provided,
Then the system MUST retrieve terms from the system default glossary.

### Requirement: User Custom Glossary Priority
Users MUST be able to define custom glossaries which take precedence over the system default glossary during re-ranking.
#### Scenario: Conflicting terms
Given both a system glossary and a user glossary contain the term "Field",
When the user glossary defines it as "域" and system defines it as "字段",
Then after re-ranking, the system MUST prioritize the user-defined "域" in the translation.

### Requirement: Terminology Auto-Extraction
The system MUST automatically extract source-translation pairs for new terminology during translation and save them to the database for admin review.
#### Scenario: Extracting new terms
Given a translated section,
When translation completes,
Then the system MUST extract new terms and insert them into Supabase `glossary_terms` table with `status = 'pending_review'`.

### Requirement: RAG Injection
The system MUST retrieve relevant terms using RAG and inject them into the translation prompt.
#### Scenario: Translating with context
Given a source text chunk,
When preparing the LLM prompt,
Then the system MUST retrieve matching terms from the glossary and include them in the prompt.

### Requirement: Graceful Degradation
The RAG pipeline MUST fail gracefully without blocking translation.
#### Scenario: RAG service unavailable
Given the NVIDIA NIM API is unreachable or returns an error,
When the system attempts to retrieve terms,
Then the system MUST fall back to the existing CSV-based terminology dictionary
And the translation MUST proceed without RAG enhancement
And a warning MUST be logged.

### Requirement: Performance Constraint
The RAG pipeline MUST NOT significantly degrade translation speed.
#### Scenario: Latency budget
Given a standard 30-section paper,
When RAG terminology retrieval is enabled,
Then total RAG overhead per section MUST be under 2 seconds
And total additional time for the full paper MUST be under 60 seconds.
