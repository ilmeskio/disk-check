from concurrent.futures import ThreadPoolExecutor

from disk_check.constants import HOME, THRESHOLD_WARN
from disk_check.output import header, section, warn, info, color_size, human
from disk_check.shell import du_mb, top_dirs


def section_library() -> tuple:
    LIB = HOME / "Library"
    lines = [header("LIBRARY — sottocartelle")]
    actions = []

    subdirs = ["Application Support", "Caches", "Containers",
               "Group Containers", "Logs", "Mail", "CloudStorage"]
    existing = [d for d in subdirs if (LIB / d).is_dir()]

    with ThreadPoolExecutor(max_workers=8) as ex:
        size_futs = {d: ex.submit(du_mb, str(LIB / d)) for d in existing}
        app_sup_fut = ex.submit(top_dirs, LIB / "Application Support")
        caches_fut = ex.submit(top_dirs, LIB / "Caches")
        containers_fut = ex.submit(top_dirs, LIB / "Containers")
        sizes = {d: f.result() for d, f in size_futs.items()}
        app_sup = app_sup_fut.result()
        caches = caches_fut.result()
        containers = containers_fut.result()

    for d in existing:
        mb = sizes.get(d, 0)
        if mb == 0:
            continue
        lines.append(color_size(mb, f"{d} — {human(mb)}"))

    lines.append(section("  Application Support — top 10"))
    for mb, name in app_sup:
        lines.append(color_size(mb, f"{name} — {human(mb)}"))

    lines.append(section("  Caches — top 10"))
    big_caches = []
    for mb, name in caches:
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
    for mb, name in containers:
        lines.append(color_size(mb, f"{name} — {human(mb)}"))

    data = {
        "subdirectories": [{"name": d, "size_mb": sizes.get(d, 0)} for d in existing if sizes.get(d, 0) > 0],
        "application_support_top": [{"name": name, "size_mb": mb} for mb, name in app_sup],
        "caches_top": [{"name": name, "size_mb": mb} for mb, name in caches],
        "containers_top": [{"name": name, "size_mb": mb} for mb, name in containers],
    }
    return "\n".join(lines), actions, data
