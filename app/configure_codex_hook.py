"""Add or remove this project's user-level Codex Stop hook."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import tempfile
from datetime import datetime
from pathlib import Path


def _is_project_handler(handler: object, hook_path: Path) -> bool:
    if not isinstance(handler, dict) or not isinstance(handler.get("command"), str):
        return False
    try:
        return str(hook_path) in shlex.split(handler["command"])
    except ValueError:
        return False


def update_document(document: dict, python: Path, hook_path: Path, remove: bool = False) -> tuple[dict, bool]:
    hooks = document.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("hooks.json field 'hooks' must be an object")
    stop_groups = hooks.setdefault("Stop", [])
    if not isinstance(stop_groups, list):
        raise ValueError("hooks.json field 'hooks.Stop' must be an array")

    command = f"{shlex.quote(str(python))} {shlex.quote(str(hook_path))}"
    expected_handler = {"type": "command", "command": command, "timeout": 3}
    found = False
    changed = False
    kept_groups: list[object] = []
    for group in stop_groups:
        if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
            kept_groups.append(group)
            continue
        handlers = group["hooks"]
        matches = [_is_project_handler(handler, hook_path) for handler in handlers]
        if any(matches):
            found = True
        if remove:
            handlers = [handler for handler, matches_project in zip(handlers, matches) if not matches_project]
            if handlers:
                updated_group = dict(group)
                updated_group["hooks"] = handlers
                kept_groups.append(updated_group)
        else:
            updated_handlers = [expected_handler if matches_project else handler for handler, matches_project in zip(handlers, matches)]
            if updated_handlers != handlers:
                changed = True
                updated_group = dict(group)
                updated_group["hooks"] = updated_handlers
                kept_groups.append(updated_group)
            else:
                kept_groups.append(group)

    if remove:
        if found:
            if kept_groups:
                hooks["Stop"] = kept_groups
            else:
                hooks.pop("Stop", None)
        return document, found

    if found:
        if changed:
            hooks["Stop"] = kept_groups
        return document, changed
    stop_groups.append({"hooks": [expected_handler]})
    return document, True


def _atomic_write(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(document, handle, indent=2)
            handle.write("\n")
        temporary.chmod(0o600)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def configure(path: Path, python: Path, hook_path: Path, remove: bool = False) -> bool:
    if path.exists():
        document = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValueError("hooks.json must contain a JSON object")
    else:
        document = {"description": "User-level Codex lifecycle hooks.", "hooks": {}}
    updated, changed = update_document(document, python, hook_path, remove=remove)
    if not changed:
        return False
    if path.exists():
        backup = path.with_name(f"hooks.json.camera-notifier-backup-{datetime.now():%Y%m%d%H%M%S}")
        backup.write_bytes(path.read_bytes())
        backup.chmod(path.stat().st_mode & 0o777)
        print(f"Backup: {backup}")
    _atomic_write(path, updated)
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hook", required=True)
    parser.add_argument("--python", default="python3")
    parser.add_argument("--path", default=str(Path.home() / ".codex" / "hooks.json"))
    parser.add_argument("--remove", action="store_true")
    args = parser.parse_args()
    changed = configure(
        Path(args.path),
        Path(args.python).expanduser().absolute(),
        Path(args.hook).resolve(),
        remove=args.remove,
    )
    action = "Removed" if args.remove else "Configured"
    print(f"{action} Codex Stop hook in {args.path}" if changed else "Codex Stop hook already in the requested state.")


if __name__ == "__main__":
    main()
