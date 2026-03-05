#!/usr/bin/env python3
"""disk-check — analisi spazio disco macOS"""

import json
import os
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ─── colori ───────────────────────────────────────────────────────────────────
R  = '\033[0;31m'
Y  = '\033[0;33m'
G  = '\033[0;32m'
C  = '\033[0;36m'
B  = '\033[1m'
RS = '\033[0m'

THRESHOLD_WARN = 500   # MB
THRESHOLD_CRIT = 2000  # MB

HOME = Path.home()

# ─── helpers output ───────────────────────────────────────────────────────────
def header(text):  return f"\n{B}{C}══ {text} ══{RS}"
def section(text): return f"\n{B}{text}{RS}"
def warn(text):    return f"  {Y}[!]{RS} {text}"
def crit(text):    return f"  {R}[!!]{RS} {text}"
def ok(text):      return f"  {G}[ok]{RS} {text}"
def info(text):    return f"       {text}"
def hr():          return f"{C}──────────────────────────────────────────────────────{RS}"

def human(mb):
    if mb >= 1024: return f"{mb / 1024:.1f} GB"
    return f"{mb} MB"

def color_size(mb, label):
    if mb >= THRESHOLD_CRIT: return crit(label)
    if mb >= THRESHOLD_WARN: return warn(label)
    return ok(label)

def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        return r.stdout.strip()
    except Exception:
        return ""

def du_mb(path):
    out = run(f'du -sm "{path}"')
    if out:
        try:
            return int(out.split()[0])
        except (ValueError, IndexError):
            pass
    return 0

def top_dirs(path, n=10):
    out = run(f'du -sm "{path}"/* 2>/dev/null | sort -rn | head -{n}')
    results = []
    for line in out.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2:
            try:
                mb = int(parts[0])
                name = os.path.basename(parts[1].strip())
                results.append((mb, name))
            except ValueError:
                pass
    return results

# ─── azioni per il riepilogo finale ───────────────────────────────────────────
_actions = []   # list of (mb, label, cmd_or_None)
_actions_lock = threading.Lock()

def add_action(mb, label, cmd=None):
    with _actions_lock:
        _actions.append((mb, label, cmd))

# ─── spinner multiplo ─────────────────────────────────────────────────────────
class MultiSpinner:
    FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, sections):
        # sections: [(key, label), ...]
        self._sections = list(sections)
        self._n = len(self._sections)
        self._done = set()
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._initialized = threading.Event()

    def _redraw(self, frame_idx):
        frame = self.FRAMES[frame_idx % len(self.FRAMES)]
        for key, label in self._sections:
            if key in self._done:
                sys.stdout.write(f"\r\033[K  {G}✓{RS}  {label}\n")
            else:
                sys.stdout.write(f"\r\033[K  {C}{frame}{RS}  {label}\n")

    def _spin(self):
        with self._lock:
            for _ in range(self._n):
                sys.stdout.write("\n")
            sys.stdout.flush()
        self._initialized.set()
        i = 0
        while self._running:
            with self._lock:
                sys.stdout.write(f"\033[{self._n}A")
                self._redraw(i)
                sys.stdout.flush()
            time.sleep(0.08)
            i += 1

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        self._initialized.wait()

    def section_done(self, key, output):
        with self._lock:
            # Move to top of spinner block
            sys.stdout.write(f"\033[{self._n}A")
            # Clear all spinner lines
            for _ in range(self._n):
                sys.stdout.write(f"\r\033[K\n")
            # Back to top
            sys.stdout.write(f"\033[{self._n}A")
            # Print section output — this pushes spinner area down
            sys.stdout.write(output + "\n")
            # Mark done and redraw spinners below output
            self._done.add(key)
            self._redraw(0)
            sys.stdout.flush()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()
        with self._lock:
            sys.stdout.write(f"\033[{self._n}A")
            for _ in range(self._n):
                sys.stdout.write(f"\r\033[K\n")
            sys.stdout.write(f"\033[{self._n}A")
            sys.stdout.flush()


# ─── sezioni ──────────────────────────────────────────────────────────────────

def section_overview():
    lines = [header("PANORAMICA DISCO")]
    out = run("df -h")
    for line in out.splitlines():
        if "Filesystem" in line or "disk3s" in line:
            parts = line.split()
            cap_str = parts[4].rstrip('%') if len(parts) > 4 else ""
            try:
                cap = int(cap_str)
                if cap >= 90:   lines.append(f"  {R}{line}{RS}")
                elif cap >= 75: lines.append(f"  {Y}{line}{RS}")
                else:           lines.append(f"  {G}{line}{RS}")
            except ValueError:
                lines.append(f"  {line}")
    return "\n".join(lines)


def section_home():
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
    return "\n".join(lines)


def section_library():
    LIB = HOME / "Library"
    lines = [header("LIBRARY — sottocartelle")]

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
        add_action(total_cache,
                   f"Cache app ({names}…) — {human(total_cache)}",
                   "open ~/Library/Caches  # elimina manualmente le cartelle")

    lines.append(section("  Containers — top 10"))
    for mb, name in top_dirs(LIB / "Containers"):
        lines.append(color_size(mb, f"{name} — {human(mb)}"))

    return "\n".join(lines)


# pattern globale condiviso con section_developer
PATTERNS = [
    ("node_modules",     "Node.js deps",         True),
    ("bower_components", "Bower deps",            True),
    ("vendor",           "Vendor (PHP/Ruby/Go)",  True),
    (".gradle",          "Gradle cache",          True),
    (".cargo",           "Rust cargo",            False),
    ("Pods",             "CocoaPods (iOS)",       True),
    ("__pycache__",      "Python cache",          True),
    (".venv",            "Python virtualenv",     True),
    ("venv",             "Python virtualenv",     True),
    (".tox",             "Python tox",            True),
    ("target",           "Rust/Java build",       True),
    ("dist",             "Build output",          True),
    ("build",            "Build output",          True),
    (".next",            "Next.js build",         True),
    (".nuxt",            "Nuxt.js build",         True),
    (".turbo",           "Turborepo cache",       True),
    (".parcel-cache",    "Parcel cache",          True),
    (".terraform",       "Terraform providers",   True),
]
KNOWN_PATTERNS = {p for p, _, _ in PATTERNS}


def section_developer():
    DEV = HOME / "Developer"
    lines = [header("DEVELOPER — pattern noti")]

    if not DEV.is_dir():
        lines.append(warn("Cartella Developer non trovata"))
        return "\n".join(lines)

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
            # Evita dist/build annidati dentro node_modules (falsi positivi)
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
        return "\n".join(lines)

    # Tabella riepilogativa ordinata per dimensione totale
    lines.append(section("  Riepilogo per pattern"))
    sorted_results = sorted(pattern_results, key=lambda x: -x[4])
    for pat, desc, rec, count, total, _ in sorted_results:
        noun = "dir" if count == 1 else "dirs"
        rec_tag = f"  {Y}↩{RS}" if rec else ""
        lines.append(color_size(total, f"[{pat}]  {count} {noun}  —  {human(total)}{rec_tag}"))

    # Dettaglio per pattern
    for pat, desc, rec, count, total, entries in sorted_results:
        noun = "directory" if count == 1 else "directories"
        lines.append(section(f"  [{pat}] {desc} — {count} {noun}, totale {human(total)}"))
        for mb, rel in entries[:5]:
            lines.append(f"    {human(mb):>8}  {rel}")
        if len(entries) > 5:
            lines.append(f"             … e altri {len(entries) - 5}")
        if rec and total >= THRESHOLD_WARN:
            add_action(total, f"[{pat}] {desc} ({count} dirs)",
                       f"find ~/Developer -name '{pat}' -type d | xargs rm -rf")

    # Directory grandi non classificate
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

    # Deduplica: salta sottodirectory di path già mostrati
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

    return "\n".join(lines)


def section_docker():
    lines = [header("DOCKER")]

    if not run("command -v docker"):
        lines.append(warn("docker non trovato nel PATH"))
        return "\n".join(lines)

    test = subprocess.run("docker info", shell=True, capture_output=True)
    if test.returncode != 0:
        lines.append(warn("Docker non in esecuzione — avvialo e rilancia lo script"))
        return "\n".join(lines)

    # Panoramica + parse volumi reclaimable
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

    # Mappa immagine → lista container che la usano
    img_to_containers = {}
    fmt_ps = "{{.Image}}\t{{.Names}}\t{{.Status}}"
    for line in run(f'docker ps -a --format "{fmt_ps}"').splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        img_name, cname, cstatus = parts
        # Normalizza: aggiungi :latest se manca il tag
        if ":" not in img_name:
            img_name += ":latest"
        img_to_containers.setdefault(img_name, []).append((cname, cstatus))

    lines.append(section("  Immagini"))
    fmt = "{{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}\t{{.Size}}"
    for line in run(f'docker images --format "{fmt}"').splitlines():
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        repo, tag, img_id, created_at, size = parts
        # CreatedAt format: "2024-03-15 10:30:00 +0100 CET" — anno 1970 = corrotto
        try:
            created = created_at[:10] if int(created_at[:4]) > 1970 else "data n/d"
        except ValueError:
            created = created_at[:10]
        # Uso: cerca nei container
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

    lines.append(section("  Container"))
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
    if stopped:
        add_action(0, f"Container fermi da rimuovere ({len(stopped)})",
                   f"docker rm {' '.join(stopped)}")

    lines.append(section("  Volumi orfani (dangling)"))
    orphans = [v for v in run("docker volume ls -qf dangling=true").splitlines() if v]
    if not orphans:
        lines.append(ok("Nessun volume orfano"))
    else:
        lines.append(crit(f"{len(orphans)} volumi orfani trovati — docker volume prune"))
        for v in orphans:
            lines.append(info(v))
        add_action(vol_reclaimable_mb or 500,
                   f"Docker: {len(orphans)} volumi orfani ({human(vol_reclaimable_mb)} recuperabili)",
                   "docker volume prune")

    lines.append(section("  Volumi attivi"))
    orphan_set = set(orphans)
    active = [v for v in run("docker volume ls -q").splitlines() if v and v not in orphan_set]
    if active:
        for v in active:
            lines.append(info(v))
    else:
        lines.append(info("Nessun volume attivo"))

    return "\n".join(lines)


# ─── main ─────────────────────────────────────────────────────────────────────
def main():
    SECTIONS = [
        ("overview",  "Panoramica disco…",          section_overview),
        ("home",      "Home directory…",             section_home),
        ("library",   "Library…",                   section_library),
        ("developer", "Developer (scan pattern)…",  section_developer),
        ("docker",    "Docker…",                    section_docker),
    ]

    spinner = MultiSpinner([(key, label) for key, label, _ in SECTIONS])
    spinner.start()

    with ThreadPoolExecutor(max_workers=len(SECTIONS)) as executor:
        futures = {executor.submit(fn): key for key, _, fn in SECTIONS}
        for future in as_completed(futures):
            key = futures[future]
            output = future.result()
            spinner.section_done(key, output)

    spinner.stop()

    # ── Quick Wins ────────────────────────────────────────────────────────────
    print(header("QUICK WINS — spazio recuperabile"))

    df_out = run("df -h /")
    for line in df_out.splitlines()[1:2]:
        parts = line.split()
        if len(parts) >= 5:
            print(f"\n  Disco: {parts[2]} usati / {parts[1]} totali"
                  f"  —  {B}{parts[3]} liberi{RS} ({parts[4]} usato)")

    with _actions_lock:
        actions = sorted(_actions, reverse=True)

    if actions:
        total_rec = sum(mb for mb, _, _ in actions if mb > 0)
        if total_rec > 0:
            print(f"\n  Spazio recuperabile stimato: {B}{C}{human(total_rec)}{RS}\n")
        for mb, label, cmd in actions:
            size_str = f"  {Y}{human(mb)}{RS}" if mb > 0 else ""
            print(f"  {B}•{RS} {label}{size_str}")
            if cmd:
                print(f"    {C}$ {cmd}{RS}")
    else:
        print(ok("Nessuna azione suggerita — ottimo!"))

    print()
    print(hr())
    print("  Script completato.")
    print(hr())
    print()


if __name__ == "__main__":
    main()
