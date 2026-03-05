import re
from pathlib import Path

from disk_check.constants import HOME, PATTERNS, KNOWN_PATTERNS, THRESHOLD_WARN, Y, RS
from disk_check.output import header, section, warn, ok, color_size, human
from disk_check.shell import run, du_mb


def section_developer() -> tuple:
    DEV = HOME / "Developer"
    lines = [header("DEVELOPER — pattern noti")]
    actions = []

    if not DEV.is_dir():
        lines.append(warn("Cartella Developer non trovata"))
        return "\n".join(lines), actions

    pattern_results = []  # [(pattern, desc, recoverable, count, total_mb, entries)]

    for pattern, desc, recoverable in PATTERNS:
        find_out = run(
            f'find "{DEV}" -name "{pattern}" -type d -maxdepth 10 '
            f'-not -path "*/{pattern}/*/{pattern}" 2>/dev/null | head -100'
        )
        dirs = [d for d in find_out.splitlines() if d]
        if not dirs:
            continue

        entries = []
        total = 0
        for d in dirs:
            if pattern in ("dist", "build") and "/node_modules/" in d:
                continue
            mb = du_mb(d)
            if mb < 5:
                continue
            total += mb
            rel = str(Path(d).relative_to(HOME))
            entries.append((mb, rel))

        if not entries:
            continue

        entries.sort(reverse=True)
        pattern_results.append((pattern, desc, recoverable, len(entries), total, entries))

    if not pattern_results:
        lines.append(ok("Nessun pattern trovato"))
        return "\n".join(lines), actions

    lines.append(section("  Riepilogo per pattern"))
    sorted_results = sorted(pattern_results, key=lambda x: -x[4])
    for pat, desc, rec, count, total, _ in sorted_results:
        noun = "dir" if count == 1 else "dirs"
        rec_tag = f"  {Y}↩{RS}" if rec else ""
        lines.append(color_size(total, f"[{pat}]  {count} {noun}  —  {human(total)}{rec_tag}"))

    for pat, desc, rec, count, total, entries in sorted_results:
        noun = "directory" if count == 1 else "directories"
        lines.append(section(f"  [{pat}] {desc} — {count} {noun}, totale {human(total)}"))
        for mb, rel in entries[:5]:
            lines.append(f"    {human(mb):>8}  {rel}")
        if len(entries) > 5:
            lines.append(f"             … e altri {len(entries) - 5}")
        if rec and total >= THRESHOLD_WARN:
            actions.append((total, f"[{pat}] {desc} ({count} dirs)",
                            f"find ~/Developer -name '{pat}' -type d | xargs rm -rf"))

    lines.append(header(f"DIRECTORY GRANDI NON CLASSIFICATE  (>{THRESHOLD_WARN} MB)"))

    known_pat = "|".join(re.escape(k) for k in KNOWN_PATTERNS)
    find_cmd = (
        f'find "{DEV}" -mindepth 2 -maxdepth 6 -type d 2>/dev/null '
        f'| grep -vE "/({known_pat})(/|$)"'
    )
    raw_dirs = [d for d in run(find_cmd).splitlines() if d]

    candidates = []
    for d in raw_dirs:
        mb = du_mb(d)
        if mb >= THRESHOLD_WARN:
            rel = str(Path(d).relative_to(HOME))
            candidates.append((mb, rel))

    candidates.sort(reverse=True)
    shown_roots = []
    deduped = []
    for mb, rel in candidates:
        full = str(HOME / rel)
        if any(full.startswith(r + "/") for r in shown_roots):
            continue
        shown_roots.append(full)
        deduped.append((mb, rel))

    if deduped:
        for mb, rel in deduped[:15]:
            lines.append(color_size(mb, f"{human(mb)}  {rel}"))
    else:
        lines.append(ok("Nessuna directory grande non classificata trovata"))

    return "\n".join(lines), actions
