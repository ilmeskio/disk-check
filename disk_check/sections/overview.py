from disk_check.constants import R, Y, G, RS
from disk_check.output import header
from disk_check.shell import run


def section_overview() -> tuple:
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
    return "\n".join(lines), []
