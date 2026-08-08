import unittest
from unittest.mock import patch
from app.server import Notifier

class ServerTests(unittest.TestCase):
    @patch("app.server.camera.blink")
    @patch("app.server.load_config")
    def test_debounce(self, config, _blink):
        config.return_value={"server":{"debounce_seconds":3,"host":"127.0.0.1","port":8765},"notifications":{"chatgpt_enabled":True,"codex_enabled":True}}
        notifier=Notifier()
        first={"source":"codex","event":"turn_stopped","turn_id":"turn-1"}
        self.assertEqual(notifier.submit(first)[1],"queued")
        self.assertEqual(notifier.submit(first)[1],"debounced")
        self.assertEqual(notifier.submit({"source":"codex","event":"turn_stopped","turn_id":"turn-2"})[1],"queued")

    @patch("app.server.camera.blink")
    @patch("app.server.load_config")
    def test_same_turn_is_debounced_across_completion_sources(self, config, _blink):
        config.return_value={"server":{"debounce_seconds":3,"host":"127.0.0.1","port":8765},"notifications":{"chatgpt_enabled":True,"codex_enabled":True}}
        notifier=Notifier()
        self.assertEqual(notifier.submit({"source":"codex","event":"task_complete","turn_id":"turn-1"})[1],"queued")
        self.assertEqual(notifier.submit({"source":"codex","event":"turn_stopped","turn_id":"turn-1"})[1],"debounced")
