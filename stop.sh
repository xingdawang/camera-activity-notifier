#!/bin/zsh
set -euo pipefail
PLIST="$HOME/Library/LaunchAgents/com.camera-activity-notifier.plist"
[[ -f "$PLIST" ]] && launchctl bootout "gui/$(id -u)" "$PLIST" || true
