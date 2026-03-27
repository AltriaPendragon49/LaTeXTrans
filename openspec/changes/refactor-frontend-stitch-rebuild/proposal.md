# Change: Stitch Frontend Rebuild

## Why
The current frontend requires a complete visual and structural rebuild based on the new Stitch design files (Project 16773706219050097299). The new design introduces a refined, compact, and maximized UX layout across four key operational contexts: Paper Detail, Tools Hub, Community Conversation, and Community Feed. A unified rebuild is necessary to harmonize these views into a cohesive UI/UX foundation for LaTeXTrans.

## What Changes
- Re-architect Community Feed to use the "Compact Layout".
- Re-architect Paper Detail to use the "Maximized Reader" and "Refined Layout" (for Conversation).
- Relocate legacy translation utility actions to the "Functional Core" inside the Tools Hub.
- **BREAKING**: Overhaul the shared app shell to support the new responsive dual-pane layout strictly defined by Stitch visual sources.

## Impact
- Affected specs: `community-paper-discovery-ui`, `community-public-read-experience`, `web-ui`
- Affected code: `frontend/src/*` (Global layout structures, nested route components, and core styling configs).
