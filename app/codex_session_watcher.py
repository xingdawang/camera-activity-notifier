from __future__ import annotations

import json
import threading
from datetime import date, timedelta
from pathlib import Path
from typing import Callable

from .logger import get_logger

LOG = get_logger(__name__)


class CodexSessionWatcher:
    """Watch local Codex session journals for canonical task completion events."""

    def __init__(
        self,
        on_complete: Callable[[dict], object],
        *,
        sessions_root: Path | None = None,
        poll_seconds: float = 0.5,
        days_to_scan: int = 2,
    ) -> None:
        self.on_complete = on_complete
        self.sessions_root = sessions_root or Path.home() / ".codex" / "sessions"
        self.poll_seconds = max(0.1, float(poll_seconds))
        self.days_to_scan = max(1, int(days_to_scan))
        self.offsets: dict[Path, int] = {}
        self.journal_sources: dict[Path, str | None] = {}
        self.seen_turn_ids: set[str] = set()
        self.poll_count = 0
        self.journal_count = 0
        self.top_level_journal_count = 0
        self.files_advanced = 0
        self.bytes_read = 0
        self.completion_count = 0
        self.stop_event = threading.Event()
        self.thread = threading.Thread(
            target=self._run,
            name="codex-session-watcher",
            daemon=True,
        )

    def _candidate_paths(self) -> set[Path]:
        paths: set[Path] = set()
        today = date.today()
        for days_ago in range(self.days_to_scan):
            day = today - timedelta(days=days_ago)
            directory = self.sessions_root / day.strftime("%Y/%m/%d")
            try:
                paths.update(directory.glob("*.jsonl"))
            except OSError as error:
                LOG.warning("could not scan Codex session directory: path=%s detail=%s", directory, error)
        return paths

    def prime(self) -> None:
        """Start at EOF so service startup never replays historical completions."""
        paths = self._candidate_paths()
        self.journal_count = len(paths)
        for path in paths:
            try:
                self.journal_sources[path] = self._classify_journal(path)
                self.offsets[path] = path.stat().st_size
            except OSError:
                continue
        self.top_level_journal_count = sum(
            source == "user" for source in self.journal_sources.values()
        )
        LOG.info(
            "Codex desktop session watcher primed: journals=%s top_level=%s",
            len(self.offsets),
            self.top_level_journal_count,
        )

    @staticmethod
    def _classify_journal(path: Path) -> str | None:
        """Classify from early session metadata without parsing conversation data."""
        with path.open("rb") as handle:
            header = handle.read(65_536)
        metadata = header.split(b'"base_instructions"', 1)[0]
        if b'"type":"session_meta"' not in metadata:
            return None
        if b'"thread_source":"user"' in metadata:
            return "user"
        if b'"thread_source":"subagent"' in metadata:
            return "subagent"
        return None

    def _process_line(self, line: bytes) -> None:
        # Most journal lines contain conversation data. Parse only lines that may
        # contain the lifecycle event we need, and never log their raw contents.
        if b'"task_complete"' not in line:
            return
        try:
            record = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return
        payload = record.get("payload", {})
        if record.get("type") != "event_msg" or payload.get("type") != "task_complete":
            return
        turn_id = str(payload.get("turn_id", ""))
        if not turn_id or turn_id in self.seen_turn_ids:
            return
        self.seen_turn_ids.add(turn_id)
        self.on_complete({"source": "codex", "event": "task_complete", "turn_id": turn_id})
        self.completion_count += 1
        LOG.info("Codex desktop task completion submitted: turn_id=%s", turn_id)

    def _read_appended(self, path: Path) -> None:
        offset = self.offsets.get(path, 0)
        try:
            size = path.stat().st_size
            if size < offset:
                offset = 0
            if size == offset:
                self.offsets[path] = offset
                return
            with path.open("rb") as handle:
                handle.seek(offset)
                data = handle.read()
        except OSError as error:
            LOG.debug("could not read Codex session journal: path=%s detail=%s", path, error)
            return

        self.files_advanced += 1
        self.bytes_read += len(data)
        complete_bytes = 0
        for line in data.splitlines(keepends=True):
            if not line.endswith((b"\n", b"\r")):
                break
            complete_bytes += len(line)
            try:
                self._process_line(line)
            except Exception:
                LOG.exception("Codex session completion callback failed: path=%s", path)
        self.offsets[path] = offset + complete_bytes

    def poll_once(self) -> None:
        paths = self._candidate_paths()
        self.poll_count += 1
        self.journal_count = len(paths)
        for path in paths:
            if path not in self.offsets:
                self.offsets[path] = 0
            source = self.journal_sources.get(path)
            if source is None:
                try:
                    source = self._classify_journal(path)
                except OSError:
                    continue
                self.journal_sources[path] = source
            if source != "user":
                try:
                    self.offsets[path] = path.stat().st_size
                except OSError:
                    pass
                continue
            self._read_appended(path)
        self.top_level_journal_count = sum(
            source == "user" for source in self.journal_sources.values()
        )

    def status(self) -> dict:
        return {
            "running": self.thread.is_alive(),
            "poll_count": self.poll_count,
            "journal_count": self.journal_count,
            "top_level_journal_count": self.top_level_journal_count,
            "files_advanced": self.files_advanced,
            "bytes_read": self.bytes_read,
            "completion_count": self.completion_count,
        }

    def _run(self) -> None:
        while not self.stop_event.wait(self.poll_seconds):
            self.poll_once()

    def start(self) -> None:
        self.prime()
        self.thread.start()
        LOG.info("Codex desktop session watcher started: root=%s", self.sessions_root)

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread.is_alive():
            self.thread.join(timeout=self.poll_seconds + 1)
