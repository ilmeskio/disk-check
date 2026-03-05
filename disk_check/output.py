from disk_check.constants import R, Y, G, C, B, RS, THRESHOLD_WARN, THRESHOLD_CRIT


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
