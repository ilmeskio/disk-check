import subprocess

from disk_check.constants import G, Y, RS
from disk_check.output import header, section, warn, crit, ok, info, human
from disk_check.shell import run


def section_docker() -> tuple:
    lines = [header("DOCKER")]
    actions = []

    if not run("command -v docker"):
        lines.append(warn("docker non trovato nel PATH"))
        return "\n".join(lines), actions, {"available": False}

    test = subprocess.run("docker info", shell=True, capture_output=True)
    if test.returncode != 0:
        lines.append(warn("Docker non in esecuzione — avvialo e rilancia lo script"))
        return "\n".join(lines), actions, {"available": True, "running": False}

    df_out = run("docker system df")
    lines.append(section("  Utilizzo complessivo"))
    vol_reclaimable_mb = 0
    for line in df_out.splitlines():
        lines.append(info(line))
        if "Volumes" in line:
            parts = line.split()
            if len(parts) >= 5:
                rec_str = parts[4]
                try:
                    if rec_str.endswith("GB"):
                        vol_reclaimable_mb = int(float(rec_str[:-2]) * 1024)
                    elif rec_str.endswith("MB"):
                        vol_reclaimable_mb = int(float(rec_str[:-2]))
                except ValueError:
                    pass

    img_to_containers = {}
    fmt_ps = "{{.Image}}\t{{.Names}}\t{{.Status}}"
    for line in run(f'docker ps -a --format "{fmt_ps}"').splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        img_name, cname, cstatus = parts
        if ":" not in img_name:
            img_name += ":latest"
        img_to_containers.setdefault(img_name, []).append((cname, cstatus))

    lines.append(section("  Immagini"))
    images_data = []
    fmt = "{{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}\t{{.Size}}"
    for line in run(f'docker images --format "{fmt}"').splitlines():
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        repo, tag, img_id, created_at, size = parts
        try:
            created = created_at[:10] if int(created_at[:4]) > 1970 else "data n/d"
        except ValueError:
            created = created_at[:10]
        key = f"{repo}:{tag}"
        containers = img_to_containers.get(key, [])
        if containers:
            cnames = ", ".join(n for n, _ in containers)
            usage = f"  {G}[in uso: {cnames}]{RS}"
        else:
            usage = f"  {Y}[non usata ↩]{RS}"
        if repo == "<none>":
            lines.append(warn(f"DANGLING  {size}  ({created}) — docker rmi {img_id}"))
        else:
            lines.append(info(f"{repo}:{tag}  {size}  ({created}){usage}"))
        images_data.append({
            "repository": repo,
            "tag": tag,
            "id": img_id,
            "created": created,
            "size": size,
            "in_use": bool(containers),
            "containers": [{"name": n, "status": s} for n, s in containers],
        })

    lines.append(section("  Container"))
    containers_data = []
    stopped = []
    fmt = "{{.Names}}\t{{.Status}}\t{{.Image}}"
    for line in run(f'docker ps -a --format "{fmt}"').splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        name, status, image = parts
        if status.startswith(("Exited", "Dead")):
            lines.append(warn(f"STOPPED  {name}  ({image})  — docker rm {name}"))
            stopped.append(name)
        else:
            lines.append(ok(f"RUNNING  {name}  ({image})"))
        containers_data.append({"name": name, "status": status, "image": image})
    if stopped:
        actions.append((0, f"Container fermi da rimuovere ({len(stopped)})",
                        f"docker rm {' '.join(stopped)}"))

    lines.append(section("  Volumi orfani (dangling)"))
    orphans = [v for v in run("docker volume ls -qf dangling=true").splitlines() if v]
    if not orphans:
        lines.append(ok("Nessun volume orfano"))
    else:
        lines.append(crit(f"{len(orphans)} volumi orfani trovati — docker volume prune"))
        for v in orphans:
            lines.append(info(v))
        actions.append((vol_reclaimable_mb or 500,
                        f"Docker: {len(orphans)} volumi orfani ({human(vol_reclaimable_mb)} recuperabili)",
                        "docker volume prune"))

    lines.append(section("  Volumi attivi"))
    orphan_set = set(orphans)
    active = [v for v in run("docker volume ls -q").splitlines() if v and v not in orphan_set]
    if active:
        for v in active:
            lines.append(info(v))
    else:
        lines.append(info("Nessun volume attivo"))

    data = {
        "available": True,
        "running": True,
        "images": images_data,
        "containers": containers_data,
        "dangling_volumes": orphans,
        "active_volumes": active,
    }
    return "\n".join(lines), actions, data
