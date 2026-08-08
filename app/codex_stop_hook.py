#!/usr/bin/env python3
"""Submit one camera notification when the main Codex turn really stops."""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path
from typing import TextIO

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import load_config
from app.logger import get_logger


LOG = get_logger(__name__)


def read_event(stream: TextIO | None = None) -> dict:
    event = json.load(stream or sys.stdin)
    if not isinstance(event, dict):
        raise ValueError("Codex hook input must be a JSON object")
    return event


def notification_for(event: dict) -> dict | None:
    if event.get("hook_event_name") != "Stop":
        return None
    session_id = str(event.get("session_id") or "").strip()
    turn_id = str(event.get("turn_id") or "").strip()
    if not session_id or not turn_id:
        raise ValueError("Codex Stop hook input is missing session_id or turn_id")
    return {
        "source": "codex",
        "event": "turn_stopped",
        "session_id": session_id,
        "turn_id": turn_id,
    }


def submit(event: dict) -> bool:
    payload = notification_for(event)
    if payload is None:
        return False
    server = load_config()["server"]
    request = urllib.request.Request(
        f"http://{server['host']}:{server['port']}/notify",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Camera-Notifier-Token": server["auth_token"],
        },
        method="POST",
    )
    urllib.request.urlopen(request, timeout=0.25).close()
    LOG.info(
        "Codex Stop notification submitted: session_id=%s turn_id=%s",
        payload["session_id"],
        payload["turn_id"],
    )
    return True


def main() -> None:
    try:
        submit(read_event())
    except Exception as error:
        # A notification failure must never block or continue the Codex turn.
        LOG.warning("Codex Stop notification skipped: %s", error)
    # Stop hooks expect JSON on stdout.  An empty object has no control effect.
    print("{}")


if __name__ == "__main__":
    main()
