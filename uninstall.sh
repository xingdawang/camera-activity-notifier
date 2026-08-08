#!/bin/zsh
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST="$HOME/Library/LaunchAgents/com.camera-activity-notifier.plist"
if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  "$ROOT_DIR/.venv/bin/python" -m app.configure_codex_hook --hook "$ROOT_DIR/app/codex_stop_hook.py" --python "$ROOT_DIR/.venv/bin/python" --remove
  "$ROOT_DIR/.venv/bin/python" -m app.migrate_codex_notify
fi
if [[ -f "$PLIST" ]]; then launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true; rm "$PLIST"; fi
print "LaunchAgent and background process removed. Logs remain in ~/Library/Logs/CameraActivityNotifier."
print "Camera Activity Notifier's Codex Stop hook was removed; unrelated Codex hooks and notifiers were preserved."
