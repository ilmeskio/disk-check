from pathlib import Path

# ─── ANSI colors ───────────────────────────────────────────────────────────────
R  = '\033[0;31m'
Y  = '\033[0;33m'
G  = '\033[0;32m'
C  = '\033[0;36m'
B  = '\033[1m'
RS = '\033[0m'

THRESHOLD_WARN = 500   # MB
THRESHOLD_CRIT = 2000  # MB

HOME = Path.home()

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
