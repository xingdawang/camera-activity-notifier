from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .config import load_config
from .logger import get_logger

LOG = get_logger(__name__)


class CameraError(RuntimeError):
    pass


class CameraBusy(CameraError):
    pass


@dataclass(frozen=True)
class Device:
    index: int
    name: str


def _ffmpeg() -> str:
    binary = shutil.which("ffmpeg")
    if not binary:
        # launchd intentionally starts with a minimal PATH; Homebrew lives in
        # one of these locations on supported Intel/Apple Silicon macOS hosts.
        binary = next((str(path) for path in (Path("/opt/homebrew/bin/ffmpeg"), Path("/usr/local/bin/ffmpeg")) if path.is_file() and os.access(path, os.X_OK)), None)
    if not binary:
        raise CameraError("ffmpeg was not found. Install it with Homebrew: brew install ffmpeg")
    return binary


def list_devices() -> list[Device]:
    """Use AVFoundation's device listing. It opens no capture stream."""
    result = subprocess.run([_ffmpeg(), "-hide_banner", "-f", "avfoundation", "-list_devices", "true", "-i", ""], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10, check=False)
    devices: list[Device] = []
    video_section = False
    for line in result.stderr.splitlines():
        if "AVFoundation video devices" in line:
            video_section = True
            continue
        if "AVFoundation audio devices" in line:
            video_section = False
        match = re.search(r"\[(\d+)\]\s+(.+)$", line)
        if video_section and match:
            devices.append(Device(int(match.group(1)), match.group(2).strip()))
    return devices


def resolve_device(config: dict | None = None) -> Device:
    config = config or load_config()
    camera = config["camera"]
    devices = list_devices()
    chosen_index = camera.get("device_index")
    if chosen_index is not None:
        for device in devices:
            if device.index == int(chosen_index):
                return device
        raise CameraError(f"Configured video device index {chosen_index} was not found")
    wanted = str(camera.get("preferred_name", "")).casefold()
    matches = [device for device in devices if wanted in device.name.casefold() or device.name.casefold() in wanted]
    if not matches:
        matches = [device for device in devices if "logitech" in device.name.casefold() and "c925" in device.name.casefold()]
    if not matches:
        available = ", ".join(f"{d.index}: {d.name}" for d in devices) or "none"
        raise CameraError(f"Could not find the configured Logitech camera. Available video devices: {available}")
    return matches[0]


def _capture_for(device: Device, seconds: float, timeout: float, camera_config: dict) -> None:
    # ':none' explicitly selects no AVFoundation audio device. Null muxer creates no file.
    # C925e is unreliable with AVFoundation's yuv420p default.  Its UYVY mode
    # is broadly supported and still sends every frame directly to null.
    command = [_ffmpeg(), "-hide_banner", "-nostdin", "-loglevel", "warning", "-f", "avfoundation",
               "-pixel_format", str(camera_config.get("pixel_format", "uyvy422")),
               "-framerate", str(camera_config.get("framerate", 30)),
               "-video_size", str(camera_config.get("video_size", "1280x720")),
               "-i", f"{device.index}:none", "-t", str(seconds), "-an", "-f", "null", "-"]
    process: subprocess.Popen[str] | None = None
    try:
        process = subprocess.Popen(command, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        _, stderr = process.communicate(timeout=timeout)
        if process.returncode != 0:
            message = (stderr or "ffmpeg capture failed").strip()[-500:]
            if any(marker in message.casefold() for marker in ("busy", "in use", "resource", "cannot open", "input/output error")):
                raise CameraBusy(message)
            raise CameraError(message)
    except subprocess.TimeoutExpired as error:
        raise CameraError(f"ffmpeg timed out after {timeout} seconds") from error
    finally:
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)


def blink(times: int | None = None) -> None:
    config = load_config()
    camera = config["camera"]
    device = resolve_device(config)
    times = int(times if times is not None else camera["blink_times"])
    on_seconds, off_seconds = float(camera["on_seconds"]), float(camera["off_seconds"])
    timeout = float(camera["ffmpeg_timeout_seconds"])
    for count in range(times):
        _capture_for(device, on_seconds, timeout, camera)
        if count < times - 1:
            time.sleep(off_seconds)
    LOG.info("blink completed: device=%s times=%s", device.name, times)


def main() -> None:
    parser = argparse.ArgumentParser(description="Safely blink a macOS camera activity LED without recording.")
    parser.add_argument("command", choices=["list-devices", "test", "blink"])
    parser.add_argument("--times", type=int, default=None)
    args = parser.parse_args()
    try:
        if args.command == "list-devices":
            for device in list_devices():
                print(f"{device.index}: {device.name}")
        elif args.command == "test":
            print(f"Testing {resolve_device().name}")
            blink()
        else:
            blink(args.times)
    except CameraError as error:
        LOG.warning("camera command failed: %s", error)
        raise SystemExit(f"Camera notifier: {error}")


if __name__ == "__main__":
    main()
