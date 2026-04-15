# WCAG Self-Check Report

This report captures the repository's current internal accessibility self-check for the desktop application.

Status: internal self-check  
Review date: 2026-04-14  
Audit type: code-and-doc review only

This is not a formal conformance certification.

---

## Scope Reviewed

The review covered the current GUI code and related documentation for:

- Global navigation and shortcuts
- `Configure` page labels and controls
- `Harvest` page controls and run-state feedback
- `Dashboard` status, result access, and maintenance tools
- `Help` page accessibility/discoverability content

Primary implementation references reviewed:

- `src/gui/modern_window.py`
- `src/gui/config_tab.py`
- `src/gui/harvest_tab.py`
- `src/gui/dashboard.py`
- `src/gui/help_tab.py`
- `src/config/help_links.py`
- `src/gui/accessibility_statement_dialog.py`

---

## What Was Verified In Code

### Keyboard support

- Global application shortcuts are registered in `ModernMainWindow._setup_shortcuts()`.
- Harvest-specific shortcuts are registered in `HarvestTab._setup_shortcuts()`.
- The Help page includes a visible shortcut summary for major actions.

### Accessible labels and descriptions

- The sidebar toggle has both accessible name and description.
- Navigation buttons are given accessible names derived from their page labels.
- The `Configure` page exposes accessible names/descriptions for profile and harvest-setting controls.
- The `Harvest` page exposes an accessible name for the live status message and pause control.

### Visual state communication

- Status/state styling is driven by named properties rather than ad hoc text only.
- The dashboard and harvest UI distinguish idle, running, paused, completed, and error/cancelled states visually.
- Light and dark theme support is built into the shared styling system.

### Accessibility help discoverability

- The Help page includes an explicit accessibility section.
- The Help page opens the maintained repository accessibility statement from `docs/WCAG_ACCESSIBILITY.md`.
- The legacy accessibility viewer also resolves the same document as its source of truth.

---

## Current Gaps

The following items were not verified by automated or formal testing in this review:

- Screen-reader output quality with NVDA, VoiceOver, JAWS, or Orca
- Tab order verification for every dialog and edge-case workflow
- Contrast measurements against specific WCAG ratios
- Zoom or high-DPI validation across all supported platforms
- Full keyboard traversal for every modal dialog

These remain manual validation items.

---

## Follow-Up Manual Checks

Recommended release-time checks:

1. Navigate the full app with keyboard only.
2. Start a harvest, pause it, resume it, and cancel it without using the mouse.
3. Confirm focus visibility on all major actions in both light and dark themes.
4. Use a screen reader to inspect the main navigation, profile controls, run controls, and dashboard actions.
5. Open Help and confirm that the accessibility statement and documentation links resolve correctly.
6. Resize the main window and confirm dashboard readability at narrow widths.

---

## Related Files

- [WCAG_ACCESSIBILITY.md](WCAG_ACCESSIBILITY.md)
- [user_guide.md](user_guide.md)
- [technical_manual.md](technical_manual.md)
