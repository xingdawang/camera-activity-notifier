from __future__ import annotations
"""Conservatively compose an existing Codex notifier with this project hook."""
import argparse
import json
import re
import shutil
from datetime import datetime
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hook", required=True)
    parser.add_argument("--wrapper", required=True)
    parser.add_argument("--original-command-file", required=True)
    parser.add_argument("--python", default="python3")
    args = parser.parse_args()
    path = Path.home() / ".codex" / "config.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    if args.hook in original or args.wrapper in original:
        print("Codex hook already configured.")
        return
    backup = path.with_name(f"config.toml.camera-notifier-backup-{datetime.now():%Y%m%d%H%M%S}")
    if path.exists():
        shutil.copy2(path, backup)
        print(f"Backup: {backup}")
    replacement = f'notify = ["{args.python}", "{args.wrapper}"]'
    match = re.search(r"(?m)^notify\s*=\s*(\[[^\n]+\])\s*$", original)
    if match:
        try:
            existing = json.loads(match.group(1))
        except json.JSONDecodeError as error:
            raise SystemExit("Existing notify command is not a one-line string array; it was left unchanged.") from error
        if not isinstance(existing, list) or not all(isinstance(part, str) for part in existing):
            raise SystemExit("Existing notify command is not a string array; it was left unchanged.")
        saved = Path(args.original_command_file)
        saved.write_text(json.dumps(existing), encoding="utf-8")
        saved.chmod(0o600)
        path.write_text(original[:match.start()] + replacement + original[match.end():], encoding="utf-8")
        print("Existing Codex notify command preserved through Camera Activity Notifier wrapper.")
    else:
        addition = ("\n" if original and not original.endswith("\n") else "") + replacement + "\n"
        path.write_text(original + addition, encoding="utf-8")
    print(f"Configured Codex notification in {path}")


if __name__ == "__main__":
    main()
