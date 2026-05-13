## 1. Source Research And Policy
- [ ] 1.1 Confirm adapter eligibility and terms for alphaXiv, arXiv, OpenAlex, Semantic Scholar, Hugging Face Papers, GitHub, OpenReview, and any Papers-with-Code replacement source.
- [ ] 1.2 Document source weights, source family labels, rate-limit expectations, and fail-soft behavior.

## 2. Ranked Artifact Design
- [ ] 2.1 Define the ranked hot artifact schema, including score breakdown, confidence, source evidence, selected reason, and exclusion reasons.
- [ ] 2.2 Define artifact paths for `3d`, `7d`, `30d`, `90d`, and `all` windows.
- [ ] 2.3 Define dedupe and source-priority behavior for already translated or already queued arXiv IDs.

## 3. Ranking Algorithm
- [ ] 3.1 Implement source-local normalization, reciprocal-rank or percentile features, and winsorized count transforms.
- [ ] 3.2 Implement the external hot score components and confidence model.
- [ ] 3.3 Implement display hot blending for published community papers after external scores exist.
- [ ] 3.4 Add tests for interval filtering, missing-source behavior, score stability, and explainability payloads.

## 4. Admin And Content Pool Integration
- [ ] 4.1 Expose ranked candidates for operator review without automatically starting translation.
- [ ] 4.2 Support batch submission of approved arXiv IDs through the existing admin curation path.
- [ ] 4.3 Track candidate reuse when a paper is already translated, queued, or published.

## 5. Frontend Filter Experience
- [ ] 5.1 Add the filter icon beside the feed sort tabs and render an active date-window pill.
- [ ] 5.2 Add the desktop anchored popover for publication-date window selection.
- [ ] 5.3 Add the mobile bottom-sheet equivalent.
- [ ] 5.4 Wire selected windows into feed requests, loading states, empty states, and cache keys.

## 6. Verification
- [ ] 6.1 Run unit tests for ranking adapters and scoring.
- [ ] 6.2 Run backend feed API tests for `hotWindow` semantics.
- [ ] 6.3 Run frontend tests for filter popover/sheet behavior and active-pill reset.
- [ ] 6.4 Manually inspect generated `latest.md` artifacts for a representative window.
