# WCAG Accessibility Notes

This document summarizes the current accessibility-related behavior of the desktop application in this repository.

Status: self-assessment only  
Last reviewed: 2026-04-14

This is not a formal WCAG certification, VPAT, or third-party audit report.

---

## Scope

These notes apply to the current PyQt6 desktop GUI, including:

- `Configure`
- `Harvest`
- `Dashboard`
- `Help`

The maintained compatibility stub at `docs/wcag.md` points to this file. The Help page links users to this document, and the legacy accessibility viewer reads the same file as its source of truth.

---

## Implemented Accessibility Features

### Keyboard operation

The current GUI exposes keyboard access for core navigation and run control.

- Application-wide shortcuts are registered in `src/gui/modern_window.py`.
- Harvest-page shortcuts are registered in `src/gui/harvest_tab.py`.
- The Help page presents a visible shortcut reference for the main supported actions.
- Shortcut labels are platform-aware rather than hard-coded to one operating system.

Examples of currently implemented shortcuts include:

- Sidebar toggle
- Page navigation (`Configure`, `Harvest`, `Dashboard`, `Help`)
- Start harvest
- Stop or cancel harvest
- Refresh dashboard
- Browse for an input file

### Accessible names, descriptions, and tooltips

The codebase currently applies accessible names, accessible descriptions, or tooltips to several core controls, including:

- Sidebar toggle and navigation buttons
- Exit button
- Active profile selector on the `Configure` page
- Profile-management buttons (`New Profile`, `Save Changes`, `Delete Profile`)
- Harvest settings controls such as retry interval, call-number selection, and stop rule
- Harvest status messaging and pause control
- Dashboard actions such as database browsing, linked-ISBN tools, and results-folder access

These labels are intended to improve discoverability for assistive technologies and for keyboard-first users who rely on descriptive tooltips.

### Visual clarity and state feedback

The current UI includes several visual accessibility-oriented behaviors:

- Visible focus styling through the shared Qt stylesheet
- Distinct status colours for idle, running, paused, success, and error states
- Readable helper text and status text across the main workflow
- Light and dark theme support
- Responsive dashboard layout changes below 900 px so KPI cards and content areas remain usable on narrower window sizes

### Help and documentation access

The `Help` page currently provides:

- A built-in keyboard shortcuts reference
- A button that opens this accessibility statement
- Links to support/guidance documentation and the user guide
- Version and platform summary information

The accessibility statement link is repository-aware. When the app is running from a Git checkout, the Help page resolves repository-hosted documentation against the current `origin` remote and current branch when possible.

---

## Current Limitations

The repository does not currently claim full WCAG conformance.

Known limitations in the current documentation and verification posture:

- No formal WCAG audit has been performed
- No VPAT is included
- No committed automated screen-reader test suite is present in this repository
- No documented manual assistive-technology test matrix is bundled yet for NVDA, VoiceOver, JAWS, or Orca
- Accessibility coverage is strongest for core navigation and harvest workflow controls; dialogs and edge-case flows should still be manually checked before release

---

## Recommended Manual Verification

Before calling any release accessibility-ready, manually verify at minimum:

- Keyboard-only navigation across all four main pages
- Focus visibility in both light and dark themes
- Harvest start, pause, resume, and cancel flows without mouse input
- Help-page access to shortcut and accessibility information
- Screen-reader announcement quality for labeled controls
- Readability of status text, helper text, and contrast-sensitive states
- Dashboard behavior at narrower widths
- Dialog flows such as profile creation, delete confirmation, database browsing, and linked-ISBN actions

---

## Related Documents

- [WCAG_SELF_CHECK_REPORT.md](WCAG_SELF_CHECK_REPORT.md)
- [user_guide.md](user_guide.md)
- [technical_manual.md](technical_manual.md)

---

## Maintenance Note

Review this file whenever the GUI changes materially, especially when updating:

- Global shortcuts
- Help-page links
- Accessible labels or descriptions
- Dashboard layout
- Harvest controls
