from pathlib import Path

try:
    import tomllib
except ImportError:
    tomllib = None

HOME = Path.home()
CONFIG_PATH = HOME / ".disk-check.toml"


def get_dev_roots() -> list[Path]:
    """Return roots to scan from config, or default ~/Developer."""
    if tomllib is None or not CONFIG_PATH.exists():
        return _default()
    try:
        with open(CONFIG_PATH, "rb") as f:
            cfg = tomllib.load(f)
        paths = cfg.get("developer", {}).get("paths", [])
        roots = [Path(p).expanduser() for p in paths if Path(p).expanduser().is_dir()]
        return roots or _default()
    except Exception:
        return _default()


def _default() -> list[Path]:
    d = HOME / "Developer"
    return [d] if d.is_dir() else []
