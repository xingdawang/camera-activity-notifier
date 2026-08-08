import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from app.codex_session_watcher import CodexSessionWatcher


class CodexSessionWatcherTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.day_dir = self.root / date.today().strftime("%Y/%m/%d")
        self.day_dir.mkdir(parents=True)
        self.path = self.day_dir / "rollout.jsonl"
        self.path.write_bytes(self._session_meta("user"))
        self.calls = []
        self.watcher = CodexSessionWatcher(self.calls.append, sessions_root=self.root)

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def _session_meta(thread_source):
        return json.dumps({
            "type": "session_meta",
            "payload": {"thread_source": thread_source, "base_instructions": {}},
        }, separators=(",", ":")).encode() + b"\n"

    @staticmethod
    def _task_complete(turn_id):
        return json.dumps({
            "type": "event_msg",
            "payload": {"type": "task_complete", "turn_id": turn_id},
        }).encode() + b"\n"

    def test_skips_historical_completion_then_reads_appended_completion(self):
        self.path.write_bytes(
            self._session_meta("user") + self._task_complete("old-turn")
        )
        self.watcher.prime()
        self.assertEqual(self.calls, [])

        with self.path.open("ab") as handle:
            handle.write(b'{"type":"event_msg","payload":{"type":"agent_message"}}\n')
            handle.write(self._task_complete("new-turn"))
        self.watcher.poll_once()

        self.assertEqual(self.calls, [{
            "source": "codex",
            "event": "task_complete",
            "turn_id": "new-turn",
        }])

    def test_reads_new_session_created_after_startup(self):
        self.watcher.prime()
        new_path = self.day_dir / "new-rollout.jsonl"
        new_path.write_bytes(self._session_meta("user") + self._task_complete("new-file-turn"))
        self.watcher.poll_once()
        self.assertEqual(self.calls[0]["turn_id"], "new-file-turn")

    def test_waits_for_complete_jsonl_line_and_deduplicates_turn(self):
        self.watcher.prime()
        event = self._task_complete("turn-1")
        with self.path.open("ab") as handle:
            handle.write(event[:-1])
        self.watcher.poll_once()
        self.assertEqual(self.calls, [])

        with self.path.open("ab") as handle:
            handle.write(event[-1:])
            handle.write(event)
        self.watcher.poll_once()
        self.assertEqual([call["turn_id"] for call in self.calls], ["turn-1"])

    def test_ignores_task_complete_text_in_conversation_content(self):
        self.watcher.prime()
        record = {
            "type": "response_item",
            "payload": {"type": "message", "content": '"type":"task_complete"'},
        }
        with self.path.open("ab") as handle:
            handle.write(json.dumps(record).encode() + b"\n")
        self.watcher.poll_once()
        self.assertEqual(self.calls, [])

    def test_ignores_internal_reviewer_and_subagent_completion(self):
        self.watcher.prime()
        internal_path = self.day_dir / "internal-rollout.jsonl"
        internal_path.write_bytes(
            self._session_meta("subagent") + self._task_complete("internal-turn")
        )
        self.watcher.poll_once()
        self.assertEqual(self.calls, [])
