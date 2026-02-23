## ADDED Requirements
### Requirement: Global API Rate Limiting
The system SHALL implement a globally shared concurrency limit for all outbound LLM API requests to prevent overwhelming external API providers (e.g., NVIDIA NIM, OpenAI) and to avoid `HTTP 429 Too Many Requests` errors.

#### Scenario: Configurable global concurrency limit
- **WHEN** the application starts up
- **THEN** it SHALL initialize a single, globally shared `asyncio.Semaphore` based on the `LLM_MAX_CONCURRENT_REQUESTS` configuration variable (defaulting to 30)

#### Scenario: Enforcing limits across multiple tasks
- **WHEN** multiple users submit multiple translation tasks simultaneously, resulting in a theoretical demand of 100 concurrent LLM requests
- **AND** the global limit is set to 30
- **THEN** only 30 HTTP requests SHALL be executing concurrently at any given moment
- **AND** the remaining 70 requests SHALL securely queue in the asynchronous event loop without blocking the main application thread or timing out prematurely

#### Scenario: Enforcing limits across sub-task elements
- **WHEN** a single `TranslatorAgent` utilizes intra-section parallelization (`asyncio.gather`) to request translations for 1 section body, 5 environments, and 4 captions simultaneously
- **THEN** all 10 requests MUST acquire the global semaphore before initiating the network call
- **AND** if only 5 slots are available globally, 5 requests will execute while the other 5 await their turn
