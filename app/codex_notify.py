#!/usr/bin/env python3
"""Codex notify hook: return promptly and never log prompt/response content."""
from __future__ import annotations
import json, sys, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import load_config
from app.logger import get_logger

LOG = get_logger(__name__)
def read_event() -> dict:
    # Codex sends its completion payload as its first argument. Stdin support
    # makes local/manual testing convenient without logging the payload.
    if len(sys.argv) > 1:
        return json.loads(sys.argv[1])
    if not sys.stdin.isatty():
        return json.load(sys.stdin)
    return {}
def notify() -> None:
    try:
        event = read_event()
        event_type = event.get("type") or event.get("event_type")
        LOG.info("Codex notify received: event_type=%s", event_type)
        if event_type != "agent-turn-complete": return
        config = load_config(); server = config["server"]
        req = urllib.request.Request(f"http://{server['host']}:{server['port']}/notify", data=json.dumps({"source":"codex","event":"agent-turn-complete"}).encode(), headers={"Content-Type":"application/json", "X-Camera-Notifier-Token":server["auth_token"]}, method="POST")
        urllib.request.urlopen(req, timeout=0.25).close()
        LOG.info("Codex notification submitted")
    except Exception as error:
        LOG.warning("Codex notify skipped: %s", error)
def main() -> None:
    # This only makes one localhost request; blinking always happens in the service worker.
    notify()
if __name__ == "__main__": main()
