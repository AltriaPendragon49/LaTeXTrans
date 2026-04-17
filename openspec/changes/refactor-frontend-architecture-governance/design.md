## Context

The frontend already has useful building blocks, but their ownership is not expressed clearly through paths:

- `frontend/src/components/ui/*` already behaves like a primitive UI layer
- `frontend/src/components/community/*` already behaves like a shared business-feature layer
- translation workflow modules such as `AdvancedConfig`, `BatchTranslation`, `DropZone`, and `FormattingPanel` are shared business modules but still live in a flat `components/` folder
- several routes are composed by other routes, especially `ToolsHub -> Dashboard / History / TranslationSettings`
- `frontend/src/store/useStore.ts` centralizes workflow state, orchestration, and side effects in one place

The immediate need is not code rewrite. The immediate need is a stable governance model that future page-by-page refactors can follow.

## Goals / Non-Goals

- Goals:
  - Make frontend architecture understandable from file paths
  - Define stable placement rules for pages, features, UI primitives, hooks, and utilities
  - Reduce ambiguity for future AI-assisted refactors
  - Preserve existing behavior during early migration passes
  - Establish a low-risk first pilot page for later implementation planning

- Non-Goals:
  - No runtime behavior changes in this change
  - No whole-site rewrite
  - No visual redesign
  - No broad `useStore` rewrite yet
  - No API contract changes

## Decisions

### Decision: Path hierarchy is the primary architecture contract

The frontend SHALL move toward this target structure:

```text
src/
  ui/
  styles/
  layout/
  hooks/
  utils/
  constants/
  features/
    <feature>/
  pages/
    <page>/
      index.tsx
      components/
      hooks/
      utils/
```

This structure is not only organizational. It is the contract that tells contributors what kind of code belongs in each place.

### Decision: `page`, `feature`, and `ui` each have distinct ownership rules

`page`
- A page is a route composition boundary.
- A page owns route wiring, page-local state composition, and page-private components/hooks/utils.
- A page MUST NOT be imported by another page as if it were a reusable leaf component.

`feature`
- A feature contains reusable business capability with domain semantics.
- A feature may be used by multiple pages.
- A feature may expose business components, feature hooks, feature services, and feature-local utilities.

`ui`
- `ui/` contains style-system primitives and generic interaction components with no product/business meaning.
- `ui/` components MUST be reusable across unrelated domains.
- `ui/` components MUST NOT depend on domain models, page state, or route semantics.

### Decision: Hard classification rules govern component and hook placement

Components:
- Put a component in `ui/` when it has no business semantics and is broadly reusable.
- Put a component in `features/<feature>/components/` when it has business semantics and can serve multiple pages.
- Put a component in `pages/<page>/components/` when it only serves one route and depends on that route's context.

Hooks:
- Put a hook in `pages/<page>/hooks/` when it only supports one route.
- Put a hook in `features/<feature>/hooks/` when it contains reusable business behavior for that feature.
- Keep a hook in top-level `hooks/` only when it is domain-agnostic and broadly shared, such as viewport or environment helpers.

Utilities:
- Put a utility in `pages/<page>/utils/` when it only supports that page.
- Put a utility in `features/<feature>/utils/` when it is business-specific and shared within that feature.
- Keep a utility in top-level `utils/` only when it is domain-agnostic.

### Decision: Naming must encode responsibility, not implementation accident

Pages:
- Page directories SHOULD use route- or scenario-based names such as `paper-detail`, `tools-hub`, `app-settings`, or `translation-preferences`.
- Avoid ambiguous page names when two pages represent different responsibilities.

Features:
- Feature directories SHOULD use business-domain names such as `community-paper`, `translation-workflow`, or `auth-shell`.
- Feature names SHOULD describe product capability, not generic implementation labels like `common` or `shared-business`.

UI:
- Primitive UI components SHOULD keep short names such as `Button`, `Card`, `Input`, and `Tabs`.

### Decision: Early migration passes must preserve behavior and import compatibility

The first migration passes SHALL prioritize understanding and safe relocation over optimization.

Rules:
- A migration pass may move files, split mixed-responsibility files, and add compatibility re-exports.
- A migration pass MUST NOT intentionally change business behavior unless separately approved.
- A migration pass MUST NOT combine UI redesign, state-model rewrite, and API-contract rewrite in the same step.
- Existing import paths MAY remain temporarily through re-export shims until the new structure stabilizes.
- Old paths SHOULD only be removed after the target page or feature migration is verified and accepted.

### Decision: Avoid over-fragmentation during refactor

The refactor should not split files purely to satisfy an abstract folder shape.

Do not split when:
- the file has one clear responsibility
- the file is small and readable
- no meaningful reuse or ownership boundary is created

Do split when:
- UI, state, and request orchestration are mixed in one file
- one file owns multiple unrelated responsibilities
- a reusable business concern is trapped in a page
- naming can no longer describe the file's responsibility clearly

### Decision: Current modules should migrate by capability bucket, not by file type

Initial migration buckets:

- `ui/`
  - current `components/ui/*`

- `features/community-paper/`
  - current `components/community/*`
  - current `hooks/use-community-papers.ts`
  - current `hooks/use-paper-detail.ts`
  - current `lib/community-api.ts`

- `features/translation-workflow/`
  - current `components/AdvancedConfig.tsx`
  - current `components/BatchTranslation.tsx`
  - current `components/DropZone.tsx`
  - current `components/FormattingPanel.tsx`
  - current `components/TerminologyTable.tsx`
  - current `components/log-viewer.tsx`

- `features/auth-shell/`
  - current `components/LoginPrompt.tsx`
  - future auth-facing shell helpers now spread across route files

- `pages/<page>/...`
  - route-local composition, route-only helpers, and page-specific presentation fragments

### Decision: `PaperDetail` is the first pilot because it has the clearest boundary

`PaperDetail` is the best first architecture pilot because:

- it already has a route-level entry component
- it already has a dedicated hook
- it already has a large reusable workspace candidate
- it is less entangled with global workflow orchestration than `Dashboard`

Target blueprint for later implementation planning:

```text
src/
  pages/
    paper-detail/
      index.tsx
      components/
        PaperDetailHeader.tsx
        PaperDetailStateBoundary.tsx
      hooks/
        use-reader-mode.ts
      utils/
        mode-resolution.ts
  features/
    community-paper/
      components/
        PaperDetailWorkspace.tsx
        PaperPreviewReader.tsx
        PaperDetailSkeleton.tsx
        PaperStatusBadge.tsx
      hooks/
        use-paper-detail.ts
      services/
        community-paper-api.ts
```

Blueprint rules:
- `pages/paper-detail/index.tsx` should remain a thin route composition file.
- paper-detail-only header or route glue belongs under `pages/paper-detail/components/`.
- reusable paper-reading business modules stay under `features/community-paper/`.
- the first pilot migration must preserve current route behavior, API usage, and reader/coplayout behavior.

## Risks / Trade-offs

- Keeping compatibility re-exports during transition increases short-term duplication, but reduces migration risk.
- Delaying `useStore` decomposition means some architectural tension remains temporarily, but it avoids turning the first pilot into a whole-app rewrite.
- Creating a governance capability adds process overhead, but it is preferable to repeated subjective re-classification during later page moves.

## Migration Plan

1. Approve this governance change without touching runtime code.
2. Use the approved rules as the placement authority for future page-by-page migrations.
3. Prepare a PaperDetail implementation plan against this approved governance model.
4. Execute the PaperDetail pilot in a later approved change or implementation pass.

## Open Questions

- Should future route directory names mirror URL segments exactly, or may they use clarified internal names such as `translation-preferences` for `/tools?panel=settings`?
- Should feature services move under `features/<feature>/services/` or remain under a shared `lib/` layer for selected cross-feature clients?
- When the translation workflow pilot begins, should `useStore` be split by subdomain first or wrapped behind feature-facing hooks before any deeper rewrite?
