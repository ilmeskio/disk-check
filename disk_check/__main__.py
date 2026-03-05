import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from disk_check.constants import B, C, Y, RS
from disk_check.output import header, hr, ok, human
from disk_check.shell import run
from disk_check.spinner import MultiSpinner, NullSpinner
from disk_check.json_output import emit_json
from disk_check.sections.overview import section_overview
from disk_check.sections.home import section_home
from disk_check.sections.library import section_library
from disk_check.sections.developer import section_developer
from disk_check.sections.docker import section_docker

_HELP = """\
uso: disk-check <comando> [opzioni]

Comandi:
  run         Analizza il disco e mostra il report

Opzioni per 'run':
  --json      Output JSON strutturato (per agenti LLM o script)

Generali:
  --help, -h  Mostra questo messaggio ed esce

Sezioni analizzate: panoramica disco, home, Library, Developer, Docker.
"""


def main():
    args = sys.argv[1:]

    if not args or "--help" in args or "-h" in args:
        print(_HELP, end="")
        return

    if args[0] != "run":
        print(f"Sottocomando sconosciuto: '{args[0]}'", file=sys.stderr)
        print(_HELP, end="")
        sys.exit(1)

    JSON_MODE = "--json" in args

    SECTIONS = [
        ("overview",  "Panoramica disco…",          section_overview),
        ("home",      "Home directory…",             section_home),
        ("library",   "Library…",                   section_library),
        ("developer", "Developer (scan pattern)…",  section_developer),
        ("docker",    "Docker…",                    section_docker),
    ]

    spinner = NullSpinner() if JSON_MODE else MultiSpinner([(key, label) for key, label, _ in SECTIONS])
    spinner.start()

    all_actions = []
    section_data = {}
    with ThreadPoolExecutor(max_workers=len(SECTIONS)) as executor:
        futures = {executor.submit(fn): key for key, _, fn in SECTIONS}
        for future in as_completed(futures):
            key = futures[future]
            output, actions, data = future.result()
            all_actions.extend(actions)
            section_data[key] = data
            spinner.section_done(key, output)

    spinner.stop()

    if JSON_MODE:
        emit_json(section_data, all_actions)
        return

    # ── Quick Wins ────────────────────────────────────────────────────────────
    print(header("QUICK WINS — spazio recuperabile"))

    df_out = run("df -h /")
    for line in df_out.splitlines()[1:2]:
        parts = line.split()
        if len(parts) >= 5:
            print(f"\n  Disco: {parts[2]} usati / {parts[1]} totali"
                  f"  —  {B}{parts[3]} liberi{RS} ({parts[4]} usato)")

    actions = sorted(all_actions, reverse=True)

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
