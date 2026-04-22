# Change: Update Community-Paper Public Model And Feed Cache

## Why
The public community-paper product still carries an obsolete `official` vs `user_fallback` model even though non-official papers are no longer admitted into the public community library. At the same time, the current process-local `_PUBLIC_FEED_CACHE` cannot provide consistent multi-instance ordering or a clean foundation for `latest`, `views`, and `likes` ranking.

## What Changes
- Remove public-ranking, public-copy, and public-UI dependence on `official` / `user_fallback` semantics for community papers.
- Define the public community library as one peer set of published community papers, with `latest`, `views`, and `likes` as the only feed sort modes.
- Replace the in-process public feed cache with Redis-backed shared caching and Redis ranking indexes for public non-search feed requests.
- Keep the read-path hydration layer canonical-DB first, but shape it so a future per-paper Redis metadata cache can be inserted without changing the API contract.
- Keep MySQL as the source of truth for paper metadata, counts, and viewer engagement state.
- Keep `community_status` in storage temporarily for compatibility and migration safety, but treat it as internal-only and no longer part of public product semantics.
- Keep engagement-triggered ranking refreshes narrowly scoped to the affected paper or cache slice, using single-entry Redis updates where possible.
- Make the stale official-first cleanup part of the implementation scope for this change, including frontend copy, status affordances, API assumptions, and backend ordering logic.

## Impact
- Affected specs: `community-paper-intake-api`, `community-paper-discovery-ui`, `deployment-infra`
- Affected code: public paper API routes, community paper repository/service sorting logic, Redis integration/config, public feed cache/index management, frontend community feed hooks/components/locales, paper detail metadata presentation
