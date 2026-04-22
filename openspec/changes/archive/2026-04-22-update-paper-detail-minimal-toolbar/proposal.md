# Change: update paper detail minimal toolbar

## Why
The current paper detail header spends too much vertical space on metadata and expansion chrome, which weakens the reading-first experience. The reader needs a thinner, quieter toolbar that preserves core actions without keeping title, badges, and metadata permanently visible.

## What Changes
- Replace the current expandable paper detail header with a single-row minimal toolbar.
- Keep the back action pinned to the far left of the row.
- Keep the reader mode switch centered as a transparent rectangular content strip instead of a large capsule container.
- Replace the right-side grouped header actions with four independent icon actions in this order: favorite placeholder, translated-PDF download, paper info, and share.
- Open paper metadata in an on-demand card-style info popover instead of rendering it inline in the header.
- Make share copy the current paper detail URL to the clipboard.

## Impact
- Affected specs: `community-public-read-experience`
- Affected code: `frontend/src/features/community-paper/components/PaperDetailHeader.tsx`, `frontend/src/features/community-paper/components/PaperDetailScreen.tsx`, `frontend/src/pages/PaperDetail.reader-first.test.tsx`, locale resources under `frontend/src/locales/`
