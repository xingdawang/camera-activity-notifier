"""Remove the legacy camera wrapper while preserving the notifier it wrapped."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime
from pathlib import Path


NOTIFY_LINE = re.compile(r"(?m)^notify\s*=\s*(\[[^\n]+\])\s*$")
ROOT = Path(__file__).resolve().parents[1]
LEGACY_WRAPPER = Path(__file__).with_name("codex_notify_wrapper.py")
ORIGINAL_COMMAND_FILE = ROOT / "codex-notify-original.json"


def _command(value: object) -> list[str] | None:
    return value if isinstance(value, list) and all(isinstance(part, str) for part in value) else None


def _is_legacy_wrapper(command: list[str] | None, wrapper: Path) -> bool:
    return bool(command and len(command) == 2 and Path(command[1]).resolve() == wrapper.resolve())


def unwrap(command: list[str], wrapper: Path, original: list[str] | None) -> tuple[list[str] | None, bool]:
    if _is_legacy_wrapper(command, wrapper):
        return original, True

    updated = list(command)
    for index in range(len(updated) - 1):
        if updated[index] != "--previous-notify":
            continue
        try:
            nested = _command(json.loads(updated[index + 1]))
        except json.JSONDecodeError:
            continue
        if nested is None:
            continue
        restored, changed = unwrap(nested, wrapper, original)
        if not changed:
            continue
        if restored:
            updated[index + 1] = json.dumps(restored, separators=(",", ":"))
        else:
            del updated[index:index + 2]
        return updated, True
    return command, False


def migrate_text(text: str, wrapper: Path, original: list[str] | None) -> tuple[str, bool]:
    match = NOTIFY_LINE.search(text)
    if not match:
        return text, False
    try:
        current = _command(json.loads(match.group(1)))
    except json.JSONDecodeError as error:
        raise ValueError("Existing notify command is not a one-line JSON-compatible string array") from error
    if current is None:
        raise ValueError("Existing notify command is not a string array")
    restored, changed = unwrap(current, wrapper, original)
    if not changed:
        return text, False
    if restored:
        replacement = f"notify = {json.dumps(restored)}"
        return text[:match.start()] + replacement + text[match.end():], True
    start, end = match.span()
    if end < len(text) and text[end] == "\n":
        end += 1
    return text[:start] + text[end:], True


def migrate(config_path: Path, wrapper: Path, original_path: Path) -> bool:
    if not config_path.exists():
        return False
    original: list[str] | None = None
    if original_path.exists():
        original = _command(json.loads(original_path.read_text(encoding="utf-8")))
        if original is None:
            raise ValueError("Saved original notifier is not a string array")
    current_text = config_path.read_text(encoding="utf-8")
    updated_text, changed = migrate_text(current_text, wrapper, original)
    if not changed:
        return False
    backup = config_path.with_name(f"config.toml.camera-notifier-backup-{datetime.now():%Y%m%d%H%M%S}")
    shutil.copy2(config_path, backup)
    config_path.write_text(updated_text, encoding="utf-8")
    print(f"Backup: {backup}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(Path.home() / ".codex" / "config.toml"))
    args = parser.parse_args()
    changed = migrate(Path(args.config), LEGACY_WRAPPER, ORIGINAL_COMMAND_FILE)
    print("Removed legacy camera notify wrapper." if changed else "No legacy camera notify wrapper was configured.")


if __name__ == "__main__":
    main()
