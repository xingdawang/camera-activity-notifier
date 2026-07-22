#!/usr/bin/env python3
"""Compose a pre-existing Codex notifier with Camera Activity Notifier."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_COMMAND_FILE = ROOT / "codex-notify-original.json"


def payload() -> str:
    return sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()


def run_original(raw_payload: str) -> None:
    """Launch the old command without waiting or exposing its arguments in logs."""
    try:
        command = json.loads(ORIGINAL_COMMAND_FILE.read_text(encoding="utf-8"))
        if isinstance(command, list) and all(isinstance(part, str) for part in command):
            subprocess.Popen(command + [raw_payload], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except (OSError, ValueError, json.JSONDecodeError):
        pass


def main() -> None:
    raw_payload = payload()
    run_original(raw_payload)
    sys.path.insert(0, str(ROOT))
    from app.codex_notify import notify
    old_argv = sys.argv
    try:
        sys.argv = [str(Path(__file__)), raw_payload]
        notify()
    finally:
        sys.argv = old_argv


if __name__ == "__main__":
    main()
