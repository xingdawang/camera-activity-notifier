# Contributing

## Development setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
node --check chrome-extension/background.js
node --check chrome-extension/content.js
node --check chrome-extension/routing.js
node --test tests/test_routing.js
```

## Scope and safety rules

- Keep all notification endpoints loopback-only.
- Never add video, audio, screenshot, cloud upload, telemetry, or persistent browser-profile handling.
- Keep ChatGPT selector heuristics in `chrome-extension/selectors.js`; do not scatter site-specific selectors.
- Do not log prompts, model answers, tokens, or camera data.
- Test camera changes manually on macOS. Unit tests must not require a camera.

## Pull requests

Describe the macOS version, FFmpeg version, camera model, and whether you tested with another camera application already holding the device. Never include your local authentication token.
