import unittest
from unittest.mock import patch
from app import codex_notify
from app import codex_notify_wrapper

class CodexNotifyTests(unittest.TestCase):
    @patch("app.codex_notify.urllib.request.urlopen")
    @patch("app.codex_notify.load_config")
    @patch("app.codex_notify.read_event")
    def test_only_completion_is_posted(self, event, config, urlopen):
        config.return_value={"server":{"host":"127.0.0.1","port":8765,"auth_token":"test"}}
        event.return_value={"type":"agent-turn-complete"}
        codex_notify.notify()
        self.assertTrue(urlopen.called)
    @patch("app.codex_notify.urllib.request.urlopen")
    @patch("app.codex_notify.read_event", return_value={"type":"other"})
    def test_other_event_is_ignored(self, _event, urlopen):
        codex_notify.notify()
        self.assertFalse(urlopen.called)

    @patch("app.codex_notify_wrapper.subprocess.Popen")
    @patch("app.codex_notify_wrapper.ORIGINAL_COMMAND_FILE")
    def test_wrapper_forwards_original_payload(self, command_file, popen):
        command_file.read_text.return_value='["/tmp/existing", "turn-ended"]'
        codex_notify_wrapper.run_original('{"type":"agent-turn-complete"}')
        self.assertEqual(popen.call_args.args[0], ["/tmp/existing", "turn-ended", '{"type":"agent-turn-complete"}'])
