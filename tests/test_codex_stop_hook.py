import json
import unittest
from unittest.mock import patch

from app import codex_stop_hook


class CodexStopHookTests(unittest.TestCase):
    @patch("app.codex_stop_hook.urllib.request.urlopen")
    @patch("app.codex_stop_hook.load_config")
    def test_stop_hook_posts_metadata_only(self, config, urlopen):
        config.return_value = {
            "server": {"host": "127.0.0.1", "port": 8765, "auth_token": "test"}
        }
        event = {
            "hook_event_name": "Stop",
            "session_id": "session-1",
            "turn_id": "turn-1",
            "last_assistant_message": "private answer",
        }
        self.assertTrue(codex_stop_hook.submit(event))
        request = urlopen.call_args.args[0]
        self.assertEqual(
            json.loads(request.data),
            {
                "source": "codex",
                "event": "turn_stopped",
                "session_id": "session-1",
                "turn_id": "turn-1",
            },
        )
        self.assertEqual(request.get_header("X-camera-notifier-token"), "test")

    @patch("app.codex_stop_hook.urllib.request.urlopen")
    def test_non_stop_hook_event_is_ignored(self, urlopen):
        self.assertFalse(codex_stop_hook.submit({"hook_event_name": "SubagentStop"}))
        self.assertFalse(urlopen.called)
