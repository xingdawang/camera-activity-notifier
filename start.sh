#!/bin/zsh
set -euo pipefail
PLIST="$HOME/Library/LaunchAgents/com.camera-activity-notifier.plist"
[[ -f "$PLIST" ]] || { print "Not installed. Run ./install.sh first."; exit 1; }
launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null || launchctl kickstart -k "gui/$(id -u)/com.camera-activity-notifier"
