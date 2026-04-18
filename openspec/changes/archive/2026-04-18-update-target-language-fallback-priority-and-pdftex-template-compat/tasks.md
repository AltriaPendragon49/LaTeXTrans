## 1. Investigation Guardrails
- [x] 1.1 Preserve the hard-freeze fail-fast boundary and document the confirmed regression path from server artifacts.
- [x] 1.2 Confirm the narrow compile failure trigger for `2010.11929` and keep the fix scoped to the confirmed pdfTeX-driver incompatibility family.

## 2. Section Rescue Priority Fix
- [x] 2.1 Update section-level payload-invariant handling so target-language paragraph/fragment downgrade is preferred over full source passthrough whenever rescue succeeds materially.
- [x] 2.2 Ensure rescued section output does not persist hallucinated sectioning commands in prose after payload-invariant recovery or normal translation, and allow heading-only rescue when body rescue succeeds but titles remain degraded.
- [x] 2.3 Add regression tests covering known affected section patterns from `2006.11239` and `2305.18290`.

## 3. Template Compatibility Fix
- [x] 3.1 Add a compile sanitization rule for explicit pdfTeX package driver locks that are incompatible with zh/CJK modern-engine compilation.
- [x] 3.2 Add focused regression coverage for the `2010.11929` failure family.

## 4. Verification
- [x] 4.1 Run focused local tests for translation fallback and compile sanitization.
- [x] 4.2 Sync to the server, restart if needed, and validate `2010.11929`, `2006.11239`, and `2305.18290` through the admin ingestion path.
