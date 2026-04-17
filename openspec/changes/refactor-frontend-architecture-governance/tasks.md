## 1. Governance Approval
- [ ] 1.1 Approve the path-based frontend layering model for `ui/`, `features/`, and `pages/<page>/...`
- [ ] 1.2 Approve hard classification rules for components, hooks, utilities, and route composition
- [ ] 1.3 Approve naming rules for pages, features, and UI primitives
- [ ] 1.4 Approve compatibility-first migration constraints and anti-over-fragmentation rules

## 2. Migration Planning
- [ ] 2.1 Approve the migration buckets for current shared modules and page-local code
- [ ] 2.2 Approve the rule that early migrations may use compatibility re-exports before old paths are removed
- [ ] 2.3 Approve the rule that a migration step must not combine behavior changes, UI redesign, state rewrites, and API rewrites in the same pass

## 3. Pilot Blueprint
- [ ] 3.1 Approve `PaperDetail` as the first single-page architecture pilot
- [ ] 3.2 Approve the PaperDetail target directory blueprint and page/feature split
- [ ] 3.3 Begin implementation planning only after this OpenSpec change is reviewed and approved
