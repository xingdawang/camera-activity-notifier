#!/bin/zsh
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT_DIR/.venv"
CONFIG="$ROOT_DIR/config.local.yaml"
PLIST="$HOME/Library/LaunchAgents/com.camera-activity-notifier.plist"
if ! command -v brew >/dev/null; then print "Homebrew is required to install ffmpeg: https://brew.sh"; exit 1; fi
if ! command -v ffmpeg >/dev/null; then brew install ffmpeg; fi
python3 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip >/dev/null
"$VENV/bin/pip" install -r "$ROOT_DIR/requirements.txt"
if [[ ! -f "$CONFIG" ]]; then
  TOKEN="$("$VENV/bin/python" -c 'import secrets; print(secrets.token_urlsafe(32))')"
  "$VENV/bin/python" - "$ROOT_DIR/config.yaml" "$CONFIG" "$TOKEN" <<'PY'
import sys, yaml
source, destination, token = sys.argv[1:]
with open(source) as f: config=yaml.safe_load(f)
config['server']['auth_token']=token
with open(destination,'w') as f: yaml.safe_dump(config,f,sort_keys=False)
PY
  chmod 600 "$CONFIG"
fi
mkdir -p "$HOME/Library/LaunchAgents"
"$VENV/bin/python" - "$PLIST" "$VENV/bin/python" "$ROOT_DIR" <<'PY'
import plistlib, sys
path, python, root=sys.argv[1:]
payload={'Label':'com.camera-activity-notifier','ProgramArguments':[python,'-m','app.server'],'WorkingDirectory':root,'RunAtLoad':True,'KeepAlive':True,'ProcessType':'Background','StandardOutPath':'/tmp/camera-activity-notifier.out','StandardErrorPath':'/tmp/camera-activity-notifier.err'}
with open(path,'wb') as f: plistlib.dump(payload,f)
PY
launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
"$VENV/bin/python" -m app.migrate_codex_notify
"$VENV/bin/python" -m app.configure_codex_hook --hook "$ROOT_DIR/app/codex_stop_hook.py" --python "$VENV/bin/python"
print "\nInstalled. In Chrome: chrome://extensions → Developer mode → Load unpacked → $ROOT_DIR/chrome-extension"
print "Review and trust the Camera Activity Notifier Stop hook if Codex reports that a new hook needs approval."
print "Grant the running Python process/Terminal Camera access in System Settings → Privacy & Security → Camera."
print "Testing local service (camera test is deliberately left for you after granting permission):"
for attempt in {1..10}; do
  if "$ROOT_DIR/status.sh"; then break; fi
  [[ "$attempt" == 10 ]] && { print "Service did not become healthy; inspect /tmp/camera-activity-notifier.err"; exit 1; }
  sleep 1
done
