# User Guide

This guide covers the current GUI workflow for LCCN Harvester.

For plain-language definitions of ISBNs, call numbers, MARC, caching, and linked ISBNs, see [concepts.md](concepts.md).

## Table Of Contents

- [Overview](#overview)
- [Launching the App](#launching-the-app)
- [Profiles](#profiles)
  - [Important profile behavior](#important-profile-behavior)
  - [Create a profile](#create-a-profile)
  - [Switch profiles](#switch-profiles)
- [Configure: Targets](#configure-targets)
- [Configure: Harvest Settings](#configure-harvest-settings)
  - [Stop Rule options](#stop-rule-options)
- [Preparing Input Files](#preparing-input-files)
- [Harvest Page](#harvest-page)
  - [Run setup controls](#run-setup-controls)
  - [Running a harvest](#running-a-harvest)
- [Harvest Outputs](#harvest-outputs)
  - [Successful results](#successful-results)
  - [Failed results](#failed-results)
  - [Invalid results](#invalid-results)
  - [Problems results](#problems-results)
  - [Linked ISBNs snapshot](#linked-isbns-snapshot)
- [MARC Import](#marc-import)
  - [MARC import flow](#marc-import-flow)
- [Dashboard](#dashboard)
- [Help And Accessibility](#help-and-accessibility)
- [Troubleshooting](#troubleshooting)
  - [No results returned](#no-results-returned)
  - [File preview shows no valid rows](#file-preview-shows-no-valid-rows)
  - [SSL or certificate problems](#ssl-or-certificate-problems)
  - [Database locked](#database-locked)
  - [Target unavailable](#target-unavailable)
- [See Also](#see-also)

---

## Overview

LCCN Harvester reads a list of ISBNs, checks the local SQLite cache, queries enabled targets when needed, and writes timestamped result files in the active profile's output folder.

The application has four main pages:

| Page | Purpose |
|------|---------|
| `Configure` | Profile settings, harvest settings, and target management |
| `Harvest` | Input-file preview, harvest controls, and MARC import |
| `Dashboard` | Run status, KPI cards, recent results, result-file buttons, linked-ISBN tools |
| `Help` | Keyboard shortcuts, accessibility links, and documentation links |

The pages are listed above in sidebar order, which is the order they appear in the left navigation panel. The sidebar also contains a status pill showing the current run state, a `Toggle Theme` button, and an `Exit` button at the bottom. A collapse button in the sidebar header hides the labels to give more screen space.

The app opens on the `Configure` page.

---

## Launching the App

From source:

```bash
python app_entry.py
```

---

## Profiles

Profiles keep settings and targets separate for different workflows.

Each profile has:

- Its own settings JSON under `config/profiles/<slug>/`
- Its own targets TSV under `config/profiles/<slug>/` if it is a user-created profile
- Its own output folder under `data/<slug>/`

All profiles share the same SQLite database file at `data/lccn_harvester.sqlite3`.

### Important profile behavior

- `Default Settings` is built in. Its harvest settings cannot be saved back over the default profile.
- `Default Settings` uses the shared targets file at `data/targets.tsv`.
- If you want a separate combination of harvest settings and targets, create a new profile first.
- Deleting a profile removes its saved configuration files, but its existing output folder is left in place.

### Create a profile

1. Open `Configure`.
2. In `Profile Settings`, click `New Profile`.
3. Choose the source profile to copy from.
4. Enter a new name and confirm.

### Switch profiles

Use the profile selector on the `Configure` page. Switching profiles reloads settings, refreshes the active targets, and resets harvest-run state tied to the previous profile while preserving the current input file when possible.

If you changed harvest settings but have not clicked `Save Changes`, the app prompts you to save or discard them before switching profiles or making target-list changes that depend on the active profile.

---

## Configure: Targets

The targets table contains both built-in API targets and any Z39.50 targets for the active profile.

Supported target types:

- API targets
- Z39.50 targets

From this page you can:

- Enable or disable targets
- Change rank order
- Add or edit Z39.50 targets
- Search the target list
- Run connectivity checks

Lower rank numbers are tried first during a harvest.

---

## Configure: Harvest Settings

The `Harvest Settings` card stores the profile defaults used when a run begins.

| Setting | Meaning |
|---------|---------|
| `Retry Interval` | Days to wait before retrying a failed lookup |
| `Call Number Selection` | `LCCN only`, `NLMCN only`, or `Both` |
| `Stop Rule` | Active only when `Call Number Selection` is `Both` |

### Stop Rule options

| Option | Meaning |
|--------|---------|
| `Stop if either found` | Stop when either an LCCN or NLMCN is found |
| `Stop if LCCN found` | Stop once an LCCN is found |
| `Stop if NLMCN found` | Stop once an NLMCN is found |
| `Continue until both found` | Keep querying until both types are found or targets are exhausted |

These settings apply to every run started under the active profile. The only per-run override available on the `Harvest` page is `Database only for this run`.

---

## Preparing Input Files

Accepted input formats:

| Format | Extensions |
|--------|------------|
| Tab-separated text | `.tsv`, `.txt` |
| Comma-separated text | `.csv` |
| Excel | `.xlsx`, `.xls` |

Input rules:

- Column 1 is the primary ISBN.
- Columns 2 and later are treated as linked ISBN variants for the same row.
- Blank rows are ignored.
- Rows beginning with `#` are treated as comments.
- Duplicate valid ISBNs are processed once.
- Hyphens and spaces are stripped before validation.

Recognized first-column header values include:

- `ISBN`
- `ISBNs`
- `ISBN10`
- `ISBN13`

Example:

```text
ISBN
978-0-13-110362-7	0131103628
9780306406157
```

---

## Harvest Page

The `Harvest` page has three main areas:

- Run setup
- File statistics and preview
- MARC import

### Run setup controls

| Control | Meaning |
|---------|---------|
| `Active profile` | Shows the profile whose settings will be used for the run |
| `Input file` | Select or drag in the harvest input file |
| `Database only for this run` | Skip external targets and search the local database only |

Call number mode and stop rule are set on the `Configure` page under `Harvest Settings` and apply to every run under the active profile.

### Running a harvest

1. Open `Harvest`.
2. Select or drag in an input file.
3. Review the file statistics and preview.
4. Click `Start Harvest`.

During a run you can:

- Pause and resume
- Cancel the run
- Watch live status updates on the `Dashboard`

---

## Harvest Outputs

Harvest output files are written into the active profile folder under `data/<profile-slug>/`.

Each harvest creates timestamped files with names like:

- `<profile>-success-<timestamp>.tsv`
- `<profile>-failed-<timestamp>.tsv`
- `<profile>-invalid-<timestamp>.tsv`
- `<profile>-problems-<timestamp>.tsv`
- `<profile>-linked-isbns-<timestamp>.tsv`

Each TSV also gets a CSV copy with UTF-8 BOM for spreadsheet compatibility.

### Successful results

Columns depend on the active mode:

| Mode | Columns |
|------|---------|
| `LCCN only` | `ISBN`, `LCCN`, `LCCN Source`, `Classification`, `Date` |
| `NLMCN only` | `ISBN`, `NLM`, `NLM Source`, `NLM Classification`, `Date` |
| `Both` | `ISBN`, `LCCN`, `LCCN Source`, `Classification`, `NLM`, `NLM Source`, `NLM Classification`, `Date` |

### Failed results

Columns:

`Call Number Type`, `ISBN`, `Target`, `Date Attempted`, `Reason`

In `Both` mode, a single ISBN can produce more than one failed row because LCCN and NLMCN failures are tracked separately.

### Invalid results

Columns:

`ISBN`

### Problems results

Columns:

`Target`, `Problem`

This file is for target or connectivity problems, not normal "not found" results.

### Linked ISBNs snapshot

Columns:

`ISBN`, `Canonical ISBN`

This file is a snapshot of the current linked-ISBN mappings in the database at the time of the run.

---

## MARC Import

The `MARC Import` section is separate from the standard harvest run.

Supported file types:

- Binary MARC21: `.mrc`, `.marc`
- MARCXML: `.xml`

### MARC import flow

1. Select or drag in a MARC file.
2. Click `Run`.
3. Enter a source name when prompted.
4. The import uses the current call-number mode from the active configuration.
5. Matching records are saved into the shared SQLite database.
6. A timestamped TSV export is written to the active profile folder:
   `data/<profile-slug>/<profile>-marc-import-<timestamp>.tsv`
7. A CSV copy of that export is also written beside it for spreadsheet use.

If the selected source name already has overlapping ISBNs in the database, the app prompts you to import only new rows, import all rows, or cancel. Records with ISBNs but no call number are recorded in the database as attempted rows. Records with no usable ISBN are skipped.

---

## Dashboard

The `Dashboard` summarizes the current session and gives quick access to outputs and maintenance tools.

Main sections:

- Run status pill
- Pause and cancel buttons during active runs
- KPI cards for processed, successful, failed, and invalid rows
- Result-file buttons for the most recent run, including the profile folder and linked-ISBN export
- Recent results list
- `Browse Database`
- `Linked ISBNs`
- `Reset Dashboard Stats`

`Browse Database` is a read-only viewer for the `main`, `attempted`, and `linked_isbns` tables with search, filtering, and pagination.

The `Linked ISBNs` view lets you query an ISBN's canonical mapping, manually link two ISBNs, or rewrite and merge rows under the lowest ISBN.

---

## Help And Accessibility

The `Help` page provides:

- Keyboard shortcut reference
- Accessibility statement link to the maintained repository document
- Support and guidance link
- User guide link
- App version and platform summary

The application also creates a system tray icon when the platform supports it. From the tray menu you can show the window, toggle notifications, or quit.

---

## Troubleshooting

### No results returned

- Check that at least one target is enabled.
- Verify your network connection.
- Confirm the ISBN is valid and present in column 1.
- If you expect a cached result, try `Database only for this run`.

### File preview shows no valid rows

- Confirm the file format is supported.
- Make sure ISBNs are in the first column.
- Check that the first row is either real data or a recognized header.

### SSL or certificate problems

```bash
python3 -m pip install --upgrade pip certifi
```

### Database locked

Another process may still have the SQLite database open. Close other app instances and try again.

### Target unavailable

Use `Check Servers` on the `Configure` page. A normal "not found" response is different from a target problem and will not appear in the problems file.

---

## See Also

- [concepts.md](concepts.md)
- [installation_guide.md](installation_guide.md)
- [cli_reference.md](cli_reference.md)
