import unittest
from unittest.mock import patch
from app.server import Notifier

class ServerTests(unittest.TestCase):
    @patch("app.server.camera.blink")
    @patch("app.server.load_config")
    def test_debounce(self, config, _blink):
        config.return_value={"server":{"debounce_seconds":3,"host":"127.0.0.1","port":8765},"notifications":{"chatgpt_enabled":True,"codex_enabled":True}}
        notifier=Notifier()
        self.assertEqual(notifier.submit({"source":"codex","event":"agent-turn-complete"})[1],"queued")
        self.assertEqual(notifier.submit({"source":"codex","event":"agent-turn-complete"})[1],"debounced")
