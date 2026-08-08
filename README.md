# Camera Activity Notifier

**A local-only macOS completion cue for ChatGPT and Codex, using your webcam's hardware Activity LED.**

When a ChatGPT web response or top-level Codex task finishes, the app briefly opens the configured camera video device. For webcams such as the Logitech C925e, this lights the physical green Activity LED. The camera stream is discarded immediately: this project never saves, shows, or uploads video or audio.

> The LED reflects real camera-device access. Close the camera's physical privacy shutter whenever you do not want the sensor to be used.

## Features

- ChatGPT web completion detection through a Manifest V3 Chrome extension.
- Codex local `task_complete` watcher plus main-thread `Stop` hook, so foreground desktop tasks work without blinking for intermediate model/tool steps or subagent completions.
- One shared loopback-only notification service with token authentication, queueing, and duplicate suppression.
- FFmpeg + AVFoundation capture with no audio device and a null output sink.
- Configurable LED timing, rotating logs, LaunchAgent startup, and safe uninstall.
- C925e-compatible capture defaults: `uyvy422`, `1280x720`, 30fps.

## Architecture

```text
ChatGPT extension ────────┐
Codex task journal watcher├─ token-authenticated POST → 127.0.0.1 service → FFmpeg/AVFoundation → webcam LED
Codex Stop hook ──────────┘
```

The service accepts notification metadata only; it never receives or stores conversation content. The Codex desktop watcher follows only user-originated journals (`thread_source=user`) and parses their canonical `event_msg` / `task_complete` lifecycle lines; internal reviewer/subagent journals and all other lines are discarded.

## Requirements

- macOS
- Python 3.10+
- Homebrew
- FFmpeg with AVFoundation support
- A webcam whose activity light is triggered by video capture (tested with Logitech C925e)
- Chrome for ChatGPT web notifications

## Install

```bash
chmod +x install.sh start.sh stop.sh status.sh uninstall.sh
./install.sh
```

The installer creates a virtual environment, installs requirements, generates an ignored `config.local.yaml` containing a random token, installs a user LaunchAgent with the local Codex task-journal watcher, and adds one user-level Codex `Stop` hook in `~/.codex/hooks.json`. Existing hooks are preserved and a timestamped backup is created before an existing hooks file is changed.

Codex may require a one-time review before running a new local command hook. If Codex reports that the hook needs approval, inspect and trust the exact Camera Activity Notifier hook through the client's hooks review UI (or `/hooks` where available).

Upgrading from an older Camera Activity Notifier installation also removes the legacy camera notify wrapper while restoring the notifier command that wrapper had preserved. Computer Use and unrelated notification commands remain intact.

Then grant Camera access to the applicable Python/Terminal process in **System Settings → Privacy & Security → Camera**.

### Chrome extension

1. Open `chrome://extensions` and enable **Developer mode**.
2. Select **Load unpacked** and choose `chrome-extension` from this repository.
3. Open **Extension options**.
4. Set port to `8765` and copy `server.auth_token` from `config.local.yaml` into **Authentication token**.
5. Click **Save**, then **Test blink**. It must report `Blink queued.`
6. Enable site access for both `https://chatgpt.com/*` and `http://127.0.0.1/*`, then refresh ChatGPT.

The detector arms only after a new user message or a user-triggered regenerate/retry action. It combines semantic controls, streaming state, and a 1.5-second stable-message window to avoid firing for existing chat history.

## Commands

```bash
.venv/bin/python -m app.camera list-devices
.venv/bin/python -m app.camera test
.venv/bin/python -m app.camera blink --times 2
./status.sh
./stop.sh
./start.sh
./uninstall.sh
```

`uninstall.sh` removes the LaunchAgent, stops the service, and removes only this project's Codex `Stop` hook. It intentionally leaves local logs and camera configuration in place.

## Configuration

Defaults live in `config.yaml`; local overrides and the token live in ignored `config.local.yaml`.

```yaml
camera:
  preferred_name: "Logitech Webcam C925e"
  device_index: null
  video_size: "1280x720"
  framerate: 30
  pixel_format: "uyvy422"
  on_seconds: 0.8
  off_seconds: 0.6
  blink_times: 2
```

Camera LED cadence is limited by macOS/AVFoundation device startup and release time. Reducing `on_seconds` does not necessarily make the physical LED blink proportionally faster.

## Local API

The service binds only to `127.0.0.1`.

| Endpoint | Authentication | Purpose |
| --- | --- | --- |
| `GET /health` | No | Liveness check |
| `GET /status` | Token | Queue/service status |
| `POST /notify` | Token | Queue a completion notification |
| `POST /test` | Token | Queue a manual blink |

Send the token in `X-Camera-Notifier-Token`.

## Testing

```bash
.venv/bin/python -m unittest discover -s tests -v
node --check chrome-extension/background.js
node --check chrome-extension/content.js
node --check chrome-extension/options.js
node --check chrome-extension/routing.js
node --test tests/test_routing.js
```

The GitHub Actions workflow runs these checks on macOS. Hardware LED behaviour, other-app camera contention, and live ChatGPT UI changes require manual macOS verification.

## Security and privacy

See [SECURITY.md](SECURITY.md). In particular, never commit `config.local.yaml`, `codex-notify-original.json`, or local logs.

## License

This project is licensed under the [MIT License](LICENSE).
