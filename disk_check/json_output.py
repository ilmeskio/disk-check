import json
import sys


def emit_json(section_data: dict, all_actions: list) -> None:
    output = {
        "schema_version": 1,
        "sections": section_data,
        "quick_wins": [
            {"size_mb": mb, "label": label, "command": cmd}
            for mb, label, cmd in sorted(all_actions, reverse=True)
        ],
    }
    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
