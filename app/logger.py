from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import load_config

LOG_DIR = Path.home() / "Library" / "Logs" / "CameraActivityNotifier"


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    config = load_config()["logging"]
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.setLevel(getattr(logging, config.get("level", "INFO").upper(), logging.INFO))
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler = RotatingFileHandler(LOG_DIR / "camera-activity-notifier.log", maxBytes=int(config["max_bytes"]), backupCount=int(config["backup_count"]), encoding="utf-8")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger
