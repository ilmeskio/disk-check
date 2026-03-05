from disk_check.constants import HOME
from disk_check.output import header, color_size, human
from disk_check.shell import du_mb


def section_home() -> tuple:
    lines = [header("HOME DIRECTORY  (~)")]
    dir_names = ["Library", "Developer", "Applications", "Downloads",
                 "Documents", "Desktop", "Movies", "Music", "Pictures"]
    entries = []
    for d in dir_names:
        path = HOME / d
        if path.is_dir():
            mb = du_mb(path)
            if mb > 0:
                entries.append((mb, d))
    entries.sort(reverse=True)
    for mb, d in entries:
        lines.append(color_size(mb, f"{d} — {human(mb)}"))
    return "\n".join(lines), []
