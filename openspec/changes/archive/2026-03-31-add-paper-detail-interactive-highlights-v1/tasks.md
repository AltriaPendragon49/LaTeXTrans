## 1. Implementation
- [x] 1.1 Refactor PaperDetail.tsx selection and annotations state
- [x] 1.2 Implement CSS Highlight API synchronization logic in useEffect
- [x] 1.3 Replace floating button with Advanced Toolbar in PaperDetailWorkspace.tsx
- [x] 1.4 Add highlight color styles to index.css
- [x] 1.5 Update onAskAI to sync toolbar notes with agent input and context
- [x] 1.6 Perform final UI alignment check on the new toolbar
- [x] 1.7 Verify persistent highlights remain after clearing native selection

## 2. Behavior Alignment
- [x] 2.1 Remove explicit `Highlight` action and switch to color-click immediate apply
- [x] 2.2 Keep explicit `取消高亮` option for manual highlight removal
- [x] 2.3 Ensure outside click dismisses toolbar without dropping persisted highlights
- [x] 2.4 Keep toolbar panel solid-white and readable (remove overly transparent style)

## 3. Regression Guard
- [x] 3.1 Add regression test for persisted highlight visibility across scroll interactions
- [x] 3.2 Run focused reader-first tests and verify no highlight regression
