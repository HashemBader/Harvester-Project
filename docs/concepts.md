# Key Concepts

This glossary explains the main library and application terms used throughout the project.

---

## ISBN

An ISBN identifies a specific edition of a book.

LCCN Harvester accepts:

- ISBN-10
- ISBN-13

The app strips spaces and hyphens, validates the number, and ignores duplicate valid ISBNs within the same input file.

---

## LCCN

In this project, `LCCN` refers to the Library of Congress call number pulled from MARC field `050`, not the separate Library of Congress control number from MARC field `010`.

Example:

```text
QA76.73.P98 L86 2019
```

The application also stores the leading classification letters separately, such as `QA`.

---

## NLMCN

`NLMCN` refers to the National Library of Medicine call number pulled from MARC field `060`.

Example:

```text
WK 810 H438 2021
```

---

## MARC

MARC is the cataloguing data format used by the sources this app queries and imports.

Relevant fields:

| Field | Meaning |
|-------|---------|
| `020` | ISBN |
| `050` | Library of Congress call number |
| `060` | National Library of Medicine call number |

LCCN Harvester can read MARC data from live lookups or from imported MARC files.

---

## Harvesting

Harvesting is the app's normal lookup workflow:

1. Read ISBNs from an input file.
2. Check the local database first.
3. Query enabled targets when needed.
4. Save results and write output files.

---

## Targets

A target is a source the harvester can query.

Two target types are supported:

- API targets
- Z39.50 targets

Built-in API targets are included automatically in the target list. Additional Z39.50 targets can be added per profile.

---

## Profiles

A profile is a named configuration set used for a particular workflow.

Profiles separate:

- Harvest settings
- Target lists
- Output folders

Profiles do not get separate database files. The app uses one shared SQLite database and keeps profile-specific configuration on disk beside it.

---

## Caching

Caching means the app can return a previously found result from the local database instead of querying targets again.

The cache is stored in:

```text
data/lccn_harvester.sqlite3
```

---

## Linked ISBNs

Some books appear under more than one ISBN, such as ISBN-10 and ISBN-13 forms of the same edition.

LCCN Harvester links those ISBNs so one canonical ISBN can satisfy the others from cache. The mappings are stored in the `linked_isbns` table and exported in the linked-ISBNs result snapshot.

---

## Retry Window

If an ISBN fails across all relevant targets, the app records that attempt and can skip retrying it until the configured retry interval has passed.

This can be overridden for a run, or bypassed entirely by using local-database-only mode.

---

## MARC Import

MARC import is separate from the standard harvest run. It lets you seed the database from local catalog records instead of querying external sources live.

Supported import files:

- Binary MARC21: `.mrc`, `.marc`
- MARCXML: `.xml`

---

## Output Files

Normal harvests write timestamped TSV and CSV result files into the active profile folder. MARC import writes its own timestamped export file into that same profile folder.

---

## See Also

- [user_guide.md](user_guide.md)
- [technical_manual.md](technical_manual.md)
