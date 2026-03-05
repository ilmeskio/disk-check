import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from disk_check.constants import HOME, PATTERNS, KNOWN_PATTERNS, THRESHOLD_WARN, Y, RS
from disk_check.output import header, section, warn, ok, color_size, human
from disk_check.shell import run, du_batch


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(HOME))
    except ValueError:
        return str(path)


def _scan_patterns(roots: list[Path]):
    """Single combined find + batch du for all known patterns."""
    names = [p for p, _, _ in PATTERNS]
    or_expr = " -o ".join(f'-name "{n}"' for n in names)
    roots_str = " ".join(f'"{r}"' for r in roots)
    find_out = run(
        f'find {roots_str} -maxdepth 10 -type d \\( {or_expr} \\) -prune -print 2>/dev/null'
    )
    all_dirs = [d for d in find_out.splitlines() if d]

    # Group by pattern name, cap at 100 per pattern (matches original per-pattern head -100)
    grouped: dict[str, list[str]] = {name: [] for name in names}
    for d in all_dirs:
        name = Path(d).name
        if name in grouped and len(grouped[name]) < 100:
            grouped[name].append(d)

    # Filter nested occurrences and collect paths to measure
    filtered: dict[str, list[str]] = {}
    all_paths: list[str] = []
    for pattern, _, _ in PATTERNS:
        dirs = grouped.get(pattern, [])
        # Exclude dirs where an ancestor component has the same name (nesting)
        dirs = [d for d in dirs if not any(p == pattern for p in Path(d).parts[:-1])]
        # Exclude dist/build inside node_modules
        if pattern in ("dist", "build"):
            dirs = [d for d in dirs if "/node_modules/" not in d]
        filtered[pattern] = dirs
        all_paths.extend(dirs)

    sizes = du_batch(all_paths)

    pattern_results = []
    for pattern, desc, recoverable in PATTERNS:
        entries = []
        total = 0
        for d in filtered[pattern]:
            mb = sizes.get(d, 0)
            if mb < 5:
                continue
            total += mb
            entries.append((mb, _rel(Path(d))))
        if not entries:
            continue
        entries.sort(reverse=True)
        pattern_results.append((pattern, desc, recoverable, len(entries), total, entries))

    return pattern_results


def _scan_unclassified(roots: list[Path]):
    """du -d 6 traversal to find large unclassified dirs across all roots."""
    known_pat = "|".join(re.escape(k) for k in KNOWN_PATTERNS)
    known_re = re.compile(r'/(' + known_pat + r')(/|$)')

    candidates: list[tuple[int, str, str]] = []  # (mb, rel, full_path)
    for DEV in roots:
        out = run(f'du -md 6 "{DEV}" 2>/dev/null')
        dev_depth = len(DEV.parts)
        for line in out.splitlines():
            parts = line.split(None, 1)
            if len(parts) != 2:
                continue
            try:
                mb = int(parts[0])
            except ValueError:
                continue
            path = parts[1].strip()

            # mindepth 2 relative to DEV
            if len(Path(path).parts) - dev_depth < 2:
                continue
            # Skip paths containing known patterns
            if known_re.search(path):
                continue
            if mb >= THRESHOLD_WARN:
                candidates.append((mb, _rel(Path(path)), path))

    candidates.sort(reverse=True)

    # Deduplicate nested dirs (keep outermost)
    shown_roots: list[str] = []
    deduped: list[tuple[int, str]] = []
    for mb, rel, full_path in candidates:
        if any(full_path.startswith(r + "/") for r in shown_roots):
            continue
        shown_roots.append(full_path)
        deduped.append((mb, rel))

    return deduped


def section_developer() -> tuple:
    from disk_check.config import get_dev_roots
    roots = get_dev_roots()

    lines = [header("DEVELOPER — pattern noti")]
    actions = []

    if not roots:
        lines.append(warn("Nessuna cartella Developer trovata"))
        return "\n".join(lines), actions, {"patterns": [], "unclassified_large": []}

    if len(roots) > 1:
        roots_display = ", ".join(_rel(r) for r in roots)
        lines.append(ok(f"Root: {roots_display}"))

    with ThreadPoolExecutor(max_workers=2) as ex:
        fut_patterns = ex.submit(_scan_patterns, roots)
        fut_unclassified = ex.submit(_scan_unclassified, roots)
        pattern_results = fut_patterns.result()
        unclassified = fut_unclassified.result()

    if not pattern_results:
        lines.append(ok("Nessun pattern trovato"))
    else:
        lines.append(section("  Riepilogo per pattern"))
        sorted_results = sorted(pattern_results, key=lambda x: -x[4])
        for pat, desc, rec, count, total, _ in sorted_results:
            noun = "dir" if count == 1 else "dirs"
            rec_tag = f"  {Y}↩{RS}" if rec else ""
            lines.append(color_size(total, f"[{pat}]  {count} {noun}  —  {human(total)}{rec_tag}"))

        roots_find = " ".join(f'"{r}"' for r in roots)
        for pat, desc, rec, count, total, entries in sorted_results:
            noun = "directory" if count == 1 else "directories"
            lines.append(section(f"  [{pat}] {desc} — {count} {noun}, totale {human(total)}"))
            for mb, rel in entries[:5]:
                lines.append(f"    {human(mb):>8}  {rel}")
            if len(entries) > 5:
                lines.append(f"             … e altri {len(entries) - 5}")
            if rec and total >= THRESHOLD_WARN:
                actions.append((total, f"[{pat}] {desc} ({count} dirs)",
                                f"find {roots_find} -name '{pat}' -type d | xargs rm -rf"))

    lines.append(header(f"DIRECTORY GRANDI NON CLASSIFICATE  (>{THRESHOLD_WARN} MB)"))

    if unclassified:
        for mb, rel in unclassified[:15]:
            lines.append(color_size(mb, f"{human(mb)}  {rel}"))
    else:
        lines.append(ok("Nessuna directory grande non classificata trovata"))

    data = {
        "patterns": [
            {
                "pattern": pat,
                "description": desc,
                "recoverable": rec,
                "count": count,
                "total_mb": total,
                "entries": [{"path": rel, "size_mb": mb} for mb, rel in entries],
            }
            for pat, desc, rec, count, total, entries in pattern_results
        ],
        "unclassified_large": [{"path": rel, "size_mb": mb} for mb, rel in unclassified],
    }
    return "\n".join(lines), actions, data
