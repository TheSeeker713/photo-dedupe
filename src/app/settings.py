from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

try:
    # prefer platformdirs if available for correct config location
    from platformdirs import user_config_dir, user_cache_dir
except Exception:
    user_config_dir = None
    user_cache_dir = None


def _merge_defaults(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge src into dst where keys are missing."""
    for k, v in src.items():
        if k not in dst:
            dst[k] = v
        else:
            if isinstance(v, dict) and isinstance(dst.get(k), dict):
                _merge_defaults(dst[k], v)
    return dst


class Settings:
    """Centralized settings manager for photo-dedupe.

    Stores a JSON settings file at:
      <user_config_dir>/photo-dedupe/config/settings.json
    Falls back to %LOCALAPPDATA% on Windows if platformdirs is not available.
    """

    APP_NAME = "photo-dedupe"
    CONFIG_SUBDIR = "config"
    FILENAME = "settings.json"

    def __init__(self, config_dir: Path | None = None):
        if config_dir:
            base = Path(config_dir)
        else:
            if user_config_dir:
                base = Path(user_config_dir(self.APP_NAME))
            else:
                base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local")) / self.APP_NAME

        self.config_dir = base / self.CONFIG_SUBDIR
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.config_dir / self.FILENAME

        cpu = os.cpu_count() or 4

        self._defaults: Dict[str, Any] = {
            "General": {
                "thread_cap": max(2, min(32, cpu)),
                "io_throttle": 0.0,  # 0.0 = no throttle, >0 means ops/sec limit
                "thumbnail_strategy": "on_demand",  # on_demand | precache | hybrid
                "include_patterns": ["*.jpg", "*.jpeg", "*.png", "*.heic"],
                "exclude_patterns": [],
                "battery_saver_auto_switch": True,
                "low_battery_threshold": 20,  # Step 21: Auto-switch threshold
                "animations_enabled": True,  # Step 21: Can be disabled in Ultra-Lite
            },
            "PerformancePresets": {
                "Ultra-Lite": {
                    "thread_cap": 2,
                    "io_throttle": 1.0,
                    "memory_cap_mb": 512,
                    "skip_raw_tiff_on_low_end": True,
                    "enable_orb_fallback": False,
                },
                "Balanced": {
                    "thread_cap": max(2, cpu // 2),
                    "io_throttle": 0.5,
                    "memory_cap_mb": 2048,
                    "skip_raw_tiff_on_low_end": False,
                    "enable_orb_fallback": True,
                },
                "Accurate": {
                    "thread_cap": cpu,
                    "io_throttle": 0.0,
                    "memory_cap_mb": 8192,
                    "skip_raw_tiff_on_low_end": False,
                    "enable_orb_fallback": True,
                },
            },
            "Cache": {
                "cache_size_cap_mb": 1024,
                "cache_max_age_days": 30,
                "on_demand_thumbs": True,
                # default cache dir uses platform cache dir when available
                "cache_dir": None,
            },
            "Hashing": {
                "near_dupe_thresholds": {"phash": 8, "dhash": 8, "ahash": 10},
                "enable_orb_fallback": True,
                "use_perceptual_hash": True,
            },
            "Formats": {
                "skip_raw_tiff_on_low_end": True,
                "raw_extensions": ["*.cr2", "*.nef", "*.arw", "*.dng", "*.rw2", "*.tif", "*.tiff"],
            },
            "DeleteBehavior": {
                "default_action": "recycle",  # recycle | quarantine | delete
                "quarantine_dir": None,
                "confirm_before_delete": True,
                "original_selection_rule": "keep_largest",  # keep_largest | keep_oldest | keep_newest
            },
            "UI": {
                "show_preview": True,
                "on_demand_thumbs": True,
            },
            "Concurrency": {
                "worker_pool_type": "adaptive",  # adaptive | fixed | auto
                "max_concurrent_io": None,  # None = use thread_cap, or specific limit
                "back_off_enabled": True,
                "interaction_threshold": 3,  # interactions per second to trigger back-off
                "interaction_window": 1.0,   # time window for interaction counting (seconds)
                "back_off_duration": 2.0,    # how long to back off (seconds)
                "batch_size_scanning": 100,  # files per batch for scanning operations
                "batch_size_hashing": 50,    # files per batch for hashing operations
                "batch_size_thumbnails": 25, # files per batch for thumbnail generation
                "priority_boost_ui": True,   # boost priority for UI-related tasks
            },
        }

        # runtime state
        self._data: Dict[str, Any] = {}
        self.load()

    def _default_cache_dir(self) -> Path:
        if user_cache_dir:
            return Path(user_cache_dir(self.APP_NAME))
        else:
            # fallback to LOCALAPPDATA or home
            base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".cache"))
            return base / self.APP_NAME / "cache"

    def load(self) -> None:
        """Load settings from disk; if missing, write defaults."""
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as fh:
                    self._data = json.load(fh)
            except Exception:
                # if file corrupted, overwrite with defaults
                self._data = {}
        else:
            self._data = {}

        # merge defaults into loaded data without overwriting user settings
        self._data = _merge_defaults(self._data, json.loads(json.dumps(self._defaults)))

        # fill platform-dependent defaults
        if self._data.get("Cache", {}).get("cache_dir") is None:
            self._data["Cache"]["cache_dir"] = str(self._default_cache_dir())
        if self._data.get("DeleteBehavior", {}).get("quarantine_dir") is None:
            q = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local")) / self.APP_NAME / "quarantine"
            self._data["DeleteBehavior"]["quarantine_dir"] = str(q)

        # persist any defaults that were just filled in
        self.save()

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2)
        tmp.replace(self.path)

    def get(self, section: str, key: str, default: Any = None) -> Any:
        return self._data.get(section, {}).get(key, default)

    def set(self, section: str, key: str, value: Any) -> None:
        if section not in self._data:
            self._data[section] = {}
        self._data[section][key] = value

    def as_dict(self) -> Dict[str, Any]:
        return self._data


__all__ = ["Settings"]
