from disk_check.constants import HOME, THRESHOLD_WARN
from disk_check.output import header, section, warn, info, color_size, human
from disk_check.shell import du_mb, top_dirs


def section_library() -> tuple:
    LIB = HOME / "Library"
    lines = [header("LIBRARY — sottocartelle")]
    actions = []

    for d in ["Application Support", "Caches", "Containers",
              "Group Containers", "Logs", "Mail", "CloudStorage"]:
        path = LIB / d
        if not path.is_dir():
            continue
        mb = du_mb(path)
        if mb == 0:
            continue
        lines.append(color_size(mb, f"{d} — {human(mb)}"))

    lines.append(section("  Application Support — top 10"))
    for mb, name in top_dirs(LIB / "Application Support"):
        lines.append(color_size(mb, f"{name} — {human(mb)}"))

    lines.append(section("  Caches — top 10"))
    big_caches = []
    for mb, name in top_dirs(LIB / "Caches"):
        if mb >= THRESHOLD_WARN:
            lines.append(warn(f"{name} — {human(mb)} (eliminabile)"))
            big_caches.append((mb, name))
        else:
            lines.append(info(f"{name} — {human(mb)}"))
    if big_caches:
        total_cache = sum(m for m, _ in big_caches)
        names = ", ".join(n for _, n in big_caches[:3])
        actions.append((total_cache,
                        f"Cache app ({names}…) — {human(total_cache)}",
                        "open ~/Library/Caches  # elimina manualmente le cartelle"))

    lines.append(section("  Containers — top 10"))
    for mb, name in top_dirs(LIB / "Containers"):
        lines.append(color_size(mb, f"{name} — {human(mb)}"))

    return "\n".join(lines), actions
