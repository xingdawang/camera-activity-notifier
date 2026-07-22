#!/bin/zsh
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$ROOT_DIR/.venv/bin/python" - "$ROOT_DIR" <<'PY'
import sys, urllib.request
sys.path.insert(0,sys.argv[1]); from app.config import load_config
c=load_config()['server']; url=f"http://{c['host']}:{c['port']}/status"
request=urllib.request.Request(url,headers={'X-Camera-Notifier-Token':c['auth_token']})
print(urllib.request.urlopen(request,timeout=3).read().decode())
PY
