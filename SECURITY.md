# Security and privacy

## Privacy model

Camera Activity Notifier is designed to stay on the local Mac:

- The service binds only to `127.0.0.1`.
- A random token is required for notification endpoints.
- Video is sent to FFmpeg's null sink; no image, audio, screenshot, or video file is created.
- AVFoundation is explicitly configured with no audio device (`video_index:none`) and FFmpeg uses `-an`.
- The Codex desktop watcher reads local session journals, follows only journals marked `thread_source=user`, parses their `event_msg` / `task_complete` lifecycle records, and sends only the opaque turn ID to the loopback service. Internal reviewer/subagent journals and other lines are discarded without being parsed or logged.
- Logs contain source, event type, opaque session/turn identifiers, timing, and errors only. They never contain ChatGPT prompts/responses, Codex prompts/responses, or camera frames.

## Files that must remain local

Do not commit, paste into an issue, or upload these files:

- `config.local.yaml` — contains the local authentication token.
- `codex-notify-original.json` — may contain another local notifier command.
- `~/Library/Logs/CameraActivityNotifier/` — diagnostic logs.

## Reporting a vulnerability

Please report suspected security issues privately to the repository owner. Do not include local tokens, prompts, responses, or logs with sensitive data in a public issue.
