from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config.yaml"
LOCAL_CONFIG = ROOT / "config.local.yaml"


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def load_config() -> dict[str, Any]:
    with DEFAULT_CONFIG.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    if LOCAL_CONFIG.exists():
        with LOCAL_CONFIG.open("r", encoding="utf-8") as handle:
            local = yaml.safe_load(handle) or {}
        _merge(config, local)
    return copy.deepcopy(config)
