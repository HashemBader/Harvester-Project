# CLI Reference

The repository includes a small command-line utility for running the harvest pipeline without the GUI.

Main entry points:

- `python src/harvester_cli.py`
- `python -m src`

---

## What The CLI Currently Does

The CLI:

1. Validates the input path.
2. Initializes the shared SQLite database.
3. Parses the input file with the same parser used by the GUI.
4. Runs the harvest pipeline.
5. Prints a text summary to the terminal.

The CLI is intentionally narrower than the GUI. It does not expose profile switching, target editing, live GUI output files, or MARC import.

By default it uses the shared database at `data/lccn_harvester.sqlite3` and the built-in API target factory used by the harvest pipeline. It does not read the GUI profile target TSV files.

---

## Supported Input Files

The shared parser accepts:

- `.tsv`
- `.txt`
- `.csv`
- `.xlsx`
- `.xls`

Column 1 is treated as the primary ISBN. Extra columns are treated as linked variants.

---

## Usage

Basic run:

```bash
python src/harvester_cli.py --input path/to/input.tsv
```

Short flag:

```bash
python src/harvester_cli.py -i path/to/input.tsv
```

Dry run:

```bash
python src/harvester_cli.py -i path/to/input.tsv --dry-run
```

Alternative package entry point:

```bash
python -m src -i path/to/input.tsv
```

---

## Arguments

| Argument | Required | Meaning |
|----------|----------|---------|
| `--input`, `-i` | Yes | Input file path |
| `--dry-run` | No | Query targets without writing to the database |
| `--stop-rule` | No | Stop behavior for the underlying `both`-mode harvest logic |

Supported `--stop-rule` values:

- `stop_either`
- `stop_lccn`
- `stop_nlmcn`
- `continue_both`

The CLI does not currently expose a separate `call_number_mode` flag, so the stop rule applies to the pipeline's default `both` mode.

---

## Example Console Output

```text
LCCN Harvester
- Input TSV: /full/path/to/input.tsv
- Dry run:   False
- Database:  initialized (tables ready)
- ISBNs:     parsed 3 entries
- Preview:   9780131103627, 0131103628, 9780306406157

Summary:
- Total ISBNs:          3
- Cached hits:          0
- Skipped recent fails: 0
- Attempted:            3
- Successes:            2
- Failures:             1
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | The command completed |
| `1` | Input validation or database initialization failed |

---

## Limitations

- No target-management flags
- No MARC import
- No GUI-style timestamped export files
- No profile-selection flag

For the full workflow, use the desktop application.

---

## See Also

- [user_guide.md](user_guide.md)
- [technical_manual.md](technical_manual.md)
