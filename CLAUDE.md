# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running

```bash
python3 disk-check.py
```

No dependencies beyond the Python standard library. Requires macOS (uses `df`, `du`, `find`, and optionally `docker`).

## Architecture

Single-file script (`disk-check.py`) that analyzes disk usage on macOS. It runs five analysis sections concurrently via `ThreadPoolExecutor`, collects results, then prints them in order:

- `section_overview` — `df -h` output, color-coded by usage %
- `section_home` — sizes of standard home subdirectories
- `section_library` — `~/Library` breakdown with top-10 subdirs for Application Support, Caches, Containers
- `section_developer` — scans `~/Developer` for known heavyweight patterns (`node_modules`, `.venv`, `target`, etc.) plus unclassified large directories
- `section_docker` — Docker images, containers, and dangling volumes (skipped gracefully if Docker is absent or stopped)

A `Spinner` thread runs during collection and is stopped before output is printed.

## Thresholds

`THRESHOLD_WARN = 500 MB`, `THRESHOLD_CRIT = 2000 MB` — used by `color_size()` to pick between green/yellow/red output.
