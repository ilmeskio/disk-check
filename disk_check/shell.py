import os
import subprocess


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
