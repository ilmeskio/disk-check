import json
import os
import sys
import tempfile
from pathlib import Path

from disk_check.version import __version__, REPO

_API = f"https://api.github.com/repos/{REPO}/releases/latest"
_DOWNLOAD = f"https://github.com/{REPO}/releases/download"


def _current_binary() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable)
    return Path(sys.argv[0]).resolve()


def _parse_version(tag: str) -> tuple:
    return tuple(int(x) for x in tag.lstrip("v").split("."))


def check_for_update() -> str | None:
    """Return new tag string if a newer release exists, else None. Silent on errors."""
    try:
        from disk_check.shell import run
        out = run(f"curl -fsSL --max-time 5 {_API}")
        data = json.loads(out)
        tag = data.get("tag_name", "")
        if not tag:
            return None
        if _parse_version(tag) > _parse_version(__version__):
            return tag
        return None
    except Exception:
        return None


def cmd_version() -> None:
    print(f"disk-check {__version__}")


def cmd_update() -> None:
    print(f"Current version: {__version__}")
    print("Checking for updates…")

    tag = check_for_update()
    if tag is None:
        print("Already up to date.")
        return

    print(f"New version available: {tag}")
    asset_url = f"{_DOWNLOAD}/{tag}/disk-check"
    dest = _current_binary()

    print(f"Downloading {asset_url}…")
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp:
            tmp_path = tmp.name

        ret = os.system(f"curl -fsSL --progress-bar {asset_url!r} -o {tmp_path!r}")
        if ret != 0:
            print("Error: download failed.", file=sys.stderr)
            os.unlink(tmp_path)
            sys.exit(1)

        os.chmod(tmp_path, 0o755)
        os.replace(tmp_path, dest)
        print(f"Updated to {tag}. Restart disk-check to use the new version.")
    except PermissionError:
        print(f"Permission denied writing to {dest}.", file=sys.stderr)
        print("Try: sudo disk-check update", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Update failed: {e}", file=sys.stderr)
        sys.exit(1)
