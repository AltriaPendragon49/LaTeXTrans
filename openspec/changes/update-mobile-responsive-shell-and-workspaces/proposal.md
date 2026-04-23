# Change: Mobile-responsive shell and workspace patterns

## Why
The current frontend shell and several major pages are still primarily desktop-first. On narrow viewports this causes navigation chrome to consume reading width, action buttons to compete for the same horizontal space, and dual-pane or table-oriented pages to become cramped or conflicting.

## What Changes
- Add a mobile shared-shell contract with a top action bar, a fixed 4-item bottom navigation, and safe-area-aware page spacing.
- Define responsive page-family patterns for public browse pages, reading/preview pages, workflow pages, workspace pages, and admin pages.
- Make narrow-screen paper reading and preview default to single-column translated-first presentation, with secondary controls and support panels moved into explicit tabs, drawers, or collapsible sections.
- Require high-density workspace and admin pages to degrade from desktop table or dual-pane layouts into card, expansion, and stacked action patterns on mobile.

## Impact
- Affected specs: `web-ui`, `community-paper-discovery-ui`, `community-public-read-experience`
- Affected code: shared shell and sidebar components, community feed/detail pages, preview and workflow workbenches, workspace pages, admin pages, responsive tests
