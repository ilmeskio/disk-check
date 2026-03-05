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
usage: disk-check <command> [options]

Commands:
  run [section…]           Scan the disk and display the report
  run --json [section…]    Structured JSON output (for LLM agents or scripts)

  Valid sections: overview, home, library, developer, docker
  (default: all sections)

General:
  --help, -h      Show this message and exit

Examples:
  disk-check run
  disk-check run developer
  disk-check run home library
  disk-check run --json overview docker
"""


def main():
    args = sys.argv[1:]

    if not args or "--help" in args or "-h" in args:
        print(_HELP, end="")
        return

    if args[0] != "run":
        print(f"Unknown subcommand: '{args[0]}'", file=sys.stderr)
        print(_HELP, end="")
        sys.exit(1)

    JSON_MODE = "--json" in args

    SECTIONS = [
        ("overview",  "Disk overview…",              section_overview),
        ("home",      "Home directory…",             section_home),
        ("library",   "Library…",                   section_library),
        ("developer", "Developer (scan pattern)…",  section_developer),
        ("docker",    "Docker…",                    section_docker),
    ]

    run_args = [a for a in args[1:] if not a.startswith("--")]
    if run_args:
        VALID_SECTIONS = {key for key, _, _ in SECTIONS}
        unknown = set(run_args) - VALID_SECTIONS
        if unknown:
            print(f"Unknown section(s): {', '.join(sorted(unknown))}", file=sys.stderr)
            print(f"Valid sections: {', '.join(sorted(VALID_SECTIONS))}", file=sys.stderr)
            sys.exit(1)
        active_sections = [(k, label, fn) for k, label, fn in SECTIONS if k in run_args]
    else:
        active_sections = SECTIONS

    spinner = NullSpinner() if JSON_MODE else MultiSpinner([(key, label) for key, label, _ in active_sections])
    spinner.start()

    all_actions = []
    section_data = {}
    with ThreadPoolExecutor(max_workers=len(active_sections)) as executor:
        futures = {executor.submit(fn): key for key, _, fn in active_sections}
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
    print(header("QUICK WINS — recoverable space"))

    df_out = run("df -h /")
    for line in df_out.splitlines()[1:2]:
        parts = line.split()
        if len(parts) >= 5:
            print(f"\n  Disk: {parts[2]} used / {parts[1]} total"
                  f"  —  {B}{parts[3]} free{RS} ({parts[4]} used)")

    actions = sorted(all_actions, reverse=True)

    if actions:
        total_rec = sum(mb for mb, _, _ in actions if mb > 0)
        if total_rec > 0:
            print(f"\n  Estimated recoverable space: {B}{C}{human(total_rec)}{RS}\n")
        for mb, label, cmd in actions:
            size_str = f"  {Y}{human(mb)}{RS}" if mb > 0 else ""
            print(f"  {B}•{RS} {label}{size_str}")
            if cmd:
                print(f"    {C}$ {cmd}{RS}")
    else:
        print(ok("No suggested actions — great!"))

    print()
    print(hr())
    print("  Scan complete.")
    print(hr())
    print()


if __name__ == "__main__":
    main()
