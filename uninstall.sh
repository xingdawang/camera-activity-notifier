#!/bin/zsh
set -euo pipefail
PLIST="$HOME/Library/LaunchAgents/com.camera-activity-notifier.plist"
if [[ -f "$PLIST" ]]; then launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true; rm "$PLIST"; fi
print "LaunchAgent and background process removed. Logs remain in ~/Library/Logs/CameraActivityNotifier."
print "Your Codex config is intentionally retained; remove this project's notify entry manually if desired."
