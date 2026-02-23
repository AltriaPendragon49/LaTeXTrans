## ADDED Requirements
### Requirement: Intra-Section Translation Parallelization
The TranslatorAgent SHALL translate child environments and captions within each section concurrently using `asyncio.gather()`, rather than sequentially awaiting each one. The parallelization follows a 3-phase approach: (1) translate section body, (2) translate all environments concurrently, (3) translate all captions concurrently. Phases 2 and 3 remain sequential relative to each other to ensure captions discovered inside environment content are not missed.

#### Scenario: Section with multiple environments translated concurrently
- **WHEN** a section contains N environment placeholders (N > 1)
- **THEN** all N `_translate_env()` calls SHALL be dispatched concurrently via `asyncio.gather()`
- **AND** results are written back to the correct indices in the envs list
- **AND** total wall-clock time is approximately equal to the slowest single environment translation rather than the sum of all

#### Scenario: Section with multiple captions translated concurrently
- **WHEN** a section (and its child environments) reference M caption placeholders (M > 1)
- **THEN** all M `_translate_caption()` calls SHALL be dispatched concurrently via `asyncio.gather()`
- **AND** results are written back to the correct indices in the captions list

#### Scenario: Caption discovery from environments preserved
- **WHEN** an environment's content contains `<PLACEHOLDER_CAP_X>` references
- **THEN** those captions SHALL be collected during Phase 2 (environment translation) and translated in Phase 3 (caption translation)
- **AND** no captions are missed due to concurrent execution

#### Scenario: Inter-section semaphore unchanged
- **WHEN** the TranslatorAgent translates a full document
- **THEN** the existing `Semaphore(10)` concurrency limit across sections SHALL remain unchanged
- **AND** intra-section parallelization operates independently within each semaphore slot
