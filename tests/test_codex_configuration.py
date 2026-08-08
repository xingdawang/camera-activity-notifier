import json
import tempfile
import unittest
from pathlib import Path

from app.configure_codex_hook import configure, update_document
from app.migrate_codex_notify import migrate_text


class CodexHookConfigurationTests(unittest.TestCase):
    def test_add_is_idempotent_and_preserves_other_hooks(self):
        python=Path("/runtime/python")
        hook=Path("/project/app/codex_stop_hook.py")
        document={"hooks":{"PostToolUse":[{"hooks":[{"type":"command","command":"review"}]}]}}
        updated, changed=update_document(document, python, hook)
        self.assertTrue(changed)
        self.assertIn("PostToolUse", updated["hooks"])
        _, changed_again=update_document(updated, python, hook)
        self.assertFalse(changed_again)

    def test_remove_preserves_unrelated_stop_handlers(self):
        python=Path("/runtime/python")
        hook=Path("/project/app/codex_stop_hook.py")
        document={"hooks":{"Stop":[{"hooks":[
            {"type":"command","command":"other-stop"},
            {"type":"command","command":"/runtime/python /project/app/codex_stop_hook.py"},
        ]}]}}
        updated, changed=update_document(document, python, hook, remove=True)
        self.assertTrue(changed)
        self.assertEqual(updated["hooks"]["Stop"][0]["hooks"], [{"type":"command","command":"other-stop"}])

    def test_add_updates_the_project_interpreter_without_duplicating_hook(self):
        hook=Path("/project/app/codex_stop_hook.py")
        document={"hooks":{"Stop":[{"hooks":[
            {"type":"command","command":"/old/python /project/app/codex_stop_hook.py","timeout":3},
        ]}]}}
        updated, changed=update_document(document, Path("/new/venv/bin/python"), hook)
        self.assertTrue(changed)
        handlers=updated["hooks"]["Stop"][0]["hooks"]
        self.assertEqual(len(handlers), 1)
        self.assertEqual(handlers[0]["command"], "/new/venv/bin/python /project/app/codex_stop_hook.py")

    def test_configure_writes_private_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"hooks.json"
            changed=configure(path, Path("/runtime/python"), Path("/project/app/codex_stop_hook.py"))
            self.assertTrue(changed)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertIn("Stop", json.loads(path.read_text())["hooks"])


class LegacyNotifyMigrationTests(unittest.TestCase):
    def setUp(self):
        self.wrapper=Path("/project/app/codex_notify_wrapper.py")
        self.legacy=["/runtime/python", str(self.wrapper)]
        self.original=["/existing/notifier", "turn-ended"]

    def test_direct_wrapper_is_restored(self):
        text=f"model = \"test\"\nnotify = {json.dumps(self.legacy)}\n"
        updated, changed=migrate_text(text, self.wrapper, self.original)
        self.assertTrue(changed)
        self.assertIn(f"notify = {json.dumps(self.original)}", updated)

    def test_nested_previous_notify_is_restored(self):
        outer=["/computer-use", "turn-ended", "--previous-notify", json.dumps(self.legacy)]
        text=f"notify = {json.dumps(outer)}\n"
        updated, changed=migrate_text(text, self.wrapper, self.original)
        self.assertTrue(changed)
        restored=json.loads(updated.split("=",1)[1])
        self.assertEqual(json.loads(restored[-1]), self.original)

    def test_deeply_nested_previous_notify_is_restored(self):
        middle=["/other-wrapper", "turn-ended", "--previous-notify", json.dumps(self.legacy)]
        outer=["/computer-use", "turn-ended", "--previous-notify", json.dumps(middle)]
        text=f"notify = {json.dumps(outer)}\n"
        updated, changed=migrate_text(text, self.wrapper, self.original)
        self.assertTrue(changed)
        restored_outer=json.loads(updated.split("=",1)[1])
        restored_middle=json.loads(restored_outer[-1])
        self.assertEqual(json.loads(restored_middle[-1]), self.original)

    def test_direct_wrapper_without_original_is_removed(self):
        text=f"notify = {json.dumps(self.legacy)}\nmodel = \"test\"\n"
        updated, changed=migrate_text(text, self.wrapper, None)
        self.assertTrue(changed)
        self.assertNotIn("notify =", updated)


if __name__ == "__main__":
    unittest.main()
