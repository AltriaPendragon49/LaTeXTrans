# queue-token-isolation Specification

## Purpose
TBD - created by archiving change isolate-token-queues. Update Purpose after archive.
## Requirements
### Requirement: Partition queues by API Token Hash
The TaskQueue macro dispatcher MUST partition all incoming background translations by the hashed value of the translation LLM API token employed by the configuration context.

#### Scenario: Mapping task to token-specific queue
- **WHEN** a translation task is submitted with a specific LLM Token
- **THEN** the system generates a hash of the token
- **AND** routes the task to a queue dedicated to that token hash

### Requirement: Concurrent processing of divergent tokens
The TaskQueue MUST concurrently process translation bundles belonging to completely different designated token sets, bypassing any shared global limiting semaphore bottlenecks across conflicting credentials.

#### Scenario: Submitting multi-batch tasks alongside user custom token tasks
- **Given** user A begins 9 simultaneous translation requests bound explicitly to a customized LLM Token Key.
- **When** user B subsequently hits the batch trigger with 1 task using another differing custom LLM Token immediately following.
- **Then** the TaskQueue system maps user A to a fully autonomous logic boundary (`Queue<TokenHash_A>`) and dynamically allocates user B identically to `Queue<TokenHash_B>`.
- **And** user B's translation starts computation immediately oblivious to user A queuing status, because `Queue<Token_B>` retains unoccupied standalone concurrency execution slots mapping exclusively to its API key bandwidth without intersecting traffic with A.

### Requirement: Maintain Independent User Admission Control
The TaskQueue MUST maintain user connection limits scaling (`max_user_active_tasks` guard rails) entirely independent from the aforementioned hashed token queuing model, gracefully dropping/refusing overload admissions per User ID prior to applying mapping algorithms.

#### Scenario: Exceeding global active tasks limit
- **Given** user A has reached the maximum permitted active tasks threshold globally across the platform.
- **When** user A attempts to enqueue another translation utilizing any valid LLM Token.
- **Then** the system MUST block the admission entirely at the User ID level limits.
- **And** the task is never subjected to the token-partitioned Queue mapping.

