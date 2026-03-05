# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running

```bash
python3 disk-check.py        # via shim
python3 -m disk_check        # via package
./dist/disk-check            # standalone binary (after make build)
```

No dependencies beyond the Python standard library. Requires macOS (uses `df`, `du`, `find`, and optionally `docker`).

## Build

```bash
make build      # creates dist/disk-check (ARM64 binary, ~8 MB)
make install    # copies to /usr/local/bin/disk-check
make clean      # removes build/, dist/, .venv-build/
```

Requires `/usr/local/bin/python3.12`. PyInstaller 6.19.0 is installed into `.venv-build/` (gitignored). The committed `disk-check.spec` is the source of truth for reproducible rebuilds.

## Architecture

`disk-check.py` is a 3-line shim. All logic lives in the `disk_check/` package:

```
disk_check/
├── __init__.py              ← empty
├── __main__.py              ← main() + ThreadPoolExecutor + Quick Wins
├── constants.py             ← ANSI colors, THRESHOLD_WARN/CRIT, HOME, PATTERNS, KNOWN_PATTERNS
├── output.py                ← header(), section(), warn(), crit(), ok(), info(), hr(), human(), color_size()
├── shell.py                 ← run(), du_mb(), top_dirs()
├── spinner.py               ← MultiSpinner class
└── sections/
    ├── overview.py          ← section_overview()
    ├── home.py              ← section_home()
    ├── library.py           ← section_library()
    ├── developer.py         ← section_developer()
    └── docker.py            ← section_docker()
```

Five sections run concurrently via `ThreadPoolExecutor`. Each section function returns `tuple[str, list]` — the formatted output string and a list of `(mb, label, cmd)` action tuples. `main()` merges all actions after futures complete (no global state or locks needed).

- `section_overview` — `df -h` output, color-coded by usage %
- `section_home` — sizes of standard home subdirectories
- `section_library` — `~/Library` breakdown with top-10 subdirs for Application Support, Caches, Containers
- `section_developer` — scans `~/Developer` for known heavyweight patterns (`node_modules`, `.venv`, `target`, etc.) plus unclassified large directories
- `section_docker` — Docker images, containers, and dangling volumes (skipped gracefully if Docker is absent or stopped)

A `MultiSpinner` thread animates during collection and is stopped before output is printed.

## Thresholds

`THRESHOLD_WARN = 500 MB`, `THRESHOLD_CRIT = 2000 MB` — used by `color_size()` to pick between green/yellow/red output.
