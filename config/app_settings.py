"""
App-weite Einstellungen: JSON-Datei (~/.openstair/app_settings.json).
DXF-Parameter bleiben zusaetzlich in dxf_settings.json (siehe `export.dxf.settings`).
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class AppSettings:
    """Erweiterbar; unbekannte Schluessel beim Speichern erhalten (merge)."""

    version: int = 1
    log_level: str = "INFO"
    # z. B. spaeter: theme, last_project_dir, etc.

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> AppSettings:
        if not d:
            return cls()
        base = asdict(cls())
        for key in list(base.keys()):
            if key not in d:
                continue
            val = d[key]
            if key == "version":
                try:
                    base[key] = int(val)
                except (TypeError, ValueError):
                    pass
            elif key == "log_level":
                s = str(val).upper().strip()
                if s in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
                    base[key] = s
        return cls(**base)  # type: ignore[arg-type]


def default_app_settings_path() -> Path:
    return Path.home() / ".openstair" / "app_settings.json"


def load_app_settings(path: Path | None = None) -> AppSettings:
    p = path or default_app_settings_path()
    if not p.is_file():
        return AppSettings()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return AppSettings()
        return AppSettings.from_dict(data)
    except (OSError, json.JSONDecodeError, TypeError):
        return AppSettings()


def save_app_settings(settings: AppSettings, path: Path | None = None) -> None:
    p = path or default_app_settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(settings.to_dict(), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def log_level_for_startup() -> str:
    """Umgebung OPENSTAIR_LOG_LEVEL hat Vorrang, sonst JSON, sonst INFO."""
    env = os.environ.get("OPENSTAIR_LOG_LEVEL", "").strip().upper()
    if env in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        return env
    return load_app_settings().log_level
