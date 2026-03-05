from disk_check.constants import HOME
from disk_check.output import header, color_size, human
from disk_check.shell import du_batch


def section_home() -> tuple:
    lines = [header("HOME DIRECTORY  (~)")]
    dir_names = ["Library", "Developer", "Applications", "Downloads",
                 "Documents", "Desktop", "Movies", "Music", "Pictures"]
    existing = {d: str(HOME / d) for d in dir_names if (HOME / d).is_dir()}
    sizes = du_batch(list(existing.values()))
    entries = [(sizes.get(p, 0), d) for d, p in existing.items() if sizes.get(p, 0) > 0]
    entries.sort(reverse=True)
    for mb, d in entries:
        lines.append(color_size(mb, f"{d} — {human(mb)}"))
    return "\n".join(lines), [], {"directories": [{"name": d, "size_mb": mb} for mb, d in entries]}
