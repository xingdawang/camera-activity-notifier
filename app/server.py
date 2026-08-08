from __future__ import annotations

import json
import queue
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import camera
from .codex_session_watcher import CodexSessionWatcher
from .config import load_config
from .logger import get_logger

LOG = get_logger(__name__)


class Notifier:
    def __init__(self) -> None:
        self.config = load_config()
        self.jobs: queue.Queue[dict] = queue.Queue()
        self.last_events: dict[str, float] = {}
        self.lock = threading.Lock()
        self.codex_watcher: CodexSessionWatcher | None = None
        self.worker = threading.Thread(target=self._work, name="camera-notifier", daemon=True)
        self.worker.start()

    def submit(self, payload: dict) -> tuple[bool, str]:
        source = str(payload.get("source", ""))
        if source not in {"chatgpt", "codex", "test"}:
            return False, "invalid source"
        if source != "test" and not self.config["notifications"].get(f"{source}_enabled", True):
            return False, "source disabled"
        event = str(payload.get("event", ""))
        turn_id = payload.get("turn_id")
        event_identity = turn_id or payload.get("conversation_url", "")
        key = f"{source}:turn:{turn_id}" if turn_id else f"{source}:{event}:{event_identity}"
        now = time.monotonic()
        with self.lock:
            if now - self.last_events.get(key, 0) < float(self.config["server"]["debounce_seconds"]):
                LOG.info("duplicate notification merged: source=%s event=%s", source, event)
                return True, "debounced"
            self.last_events[key] = now
        self.jobs.put({"source": source, "event": event})
        LOG.info("notification queued: source=%s event=%s", source, event)
        return True, "queued"

    def _work(self) -> None:
        while True:
            job = self.jobs.get()
            try:
                camera.blink()
                LOG.info("notification completed: source=%s event=%s", job["source"], job["event"])
            except camera.CameraBusy as error:
                LOG.warning("camera busy; notification skipped: source=%s detail=%s", job["source"], error)
            except Exception:
                LOG.exception("notification failed: source=%s", job["source"])
            finally:
                self.jobs.task_done()

    def status(self) -> dict:
        status = {"ok": True, "queue_depth": self.jobs.qsize(), "host": self.config["server"]["host"], "port": self.config["server"]["port"]}
        if self.codex_watcher is not None:
            status["codex_watcher"] = self.codex_watcher.status()
        return status


NOTIFIER = Notifier()


class Handler(BaseHTTPRequestHandler):
    server_version = "CameraActivityNotifier/1"

    def log_message(self, *_: object) -> None:
        pass

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        return self.headers.get("X-Camera-Notifier-Token") == NOTIFIER.config["server"]["auth_token"]

    def do_GET(self) -> None:
        if self.path == "/health":
            return self._json(200, {"ok": True})
        if self.path == "/status":
            if not self._authorized():
                return self._json(401, {"error": "unauthorized"})
            return self._json(200, NOTIFIER.status())
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path not in {"/notify", "/test"}:
            return self._json(404, {"error": "not found"})
        if not self._authorized():
            return self._json(401, {"error": "unauthorized"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 16_384:
                raise ValueError("body too large")
            payload = json.loads(self.rfile.read(length) or b"{}")
            if self.path == "/test":
                payload = {"source": "test", "event": "manual_test"}
            ok, detail = NOTIFIER.submit(payload)
            self._json(202 if ok else 400, {"ok": ok, "detail": detail})
        except (ValueError, json.JSONDecodeError) as error:
            self._json(400, {"error": str(error)})


def main() -> None:
    full_config = load_config()
    config = full_config["server"]
    if config["host"] != "127.0.0.1":
        raise SystemExit("For privacy, Camera Activity Notifier only permits server.host = 127.0.0.1")
    server = ThreadingHTTPServer((config["host"], int(config["port"])), Handler)
    watcher = None
    notifications = full_config["notifications"]
    if notifications.get("codex_enabled", True) and notifications.get("codex_session_watcher_enabled", True):
        watcher = CodexSessionWatcher(
            NOTIFIER.submit,
            poll_seconds=float(notifications.get("codex_session_poll_seconds", 0.5)),
        )
        watcher.start()
        NOTIFIER.codex_watcher = watcher
    LOG.info("service listening on %s:%s", config["host"], config["port"])
    signal.signal(signal.SIGTERM, lambda *_: threading.Thread(target=server.shutdown, daemon=True).start())
    signal.signal(signal.SIGINT, lambda *_: threading.Thread(target=server.shutdown, daemon=True).start())
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        if watcher is not None:
            watcher.stop()


if __name__ == "__main__":
    main()
