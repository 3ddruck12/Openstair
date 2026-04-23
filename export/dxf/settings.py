"""
DXF-Export: konfigurierbare Layer-Namen, Textgroessen, Grundriss-Optionen.
Speicherort: ~/.openstair/dxf_settings.json
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class DxfExportSettings:
    """Einstellungen fuer `export_stair_side_view_dxf` (R2010)."""

    layer_geometry: str = "GEOMETRY"
    layer_dimensions: str = "DIMENSIONS"
    layer_notes: str = "NOTES"
    layer_axes: str = "AXES"
    layer_weld: str = "WELD_SHOP"
    include_empty_axes_layer: bool = False
    include_empty_weld_layer: bool = False
    text_height_notes: float = 35.0
    text_height_dimensions: float = 30.0
    text_height_plan_title: float = 45.0
    include_plan_view: bool = True
    plan_gap_mm: float = 250.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> DxfExportSettings:
        if not d:
            return cls()
        base = asdict(cls())
        for key in list(base.keys()):
            if key not in d:
                continue
            t = type(base[key])
            try:
                if t is bool:
                    base[key] = bool(d[key])
                elif t is float:
                    base[key] = float(d[key])
                elif t is int:
                    base[key] = int(d[key])
                else:
                    s = str(d[key]).strip()
                    if s:
                        base[key] = s
            except (TypeError, ValueError):
                pass
        return cls(**base)


def default_settings_path() -> Path:
    return Path.home() / ".openstair" / "dxf_settings.json"


def load_dxf_settings(path: Path | None = None) -> DxfExportSettings:
    p = path or default_settings_path()
    if not p.is_file():
        return DxfExportSettings()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return DxfExportSettings.from_dict(data)
    except (OSError, json.JSONDecodeError, TypeError):
        return DxfExportSettings()


def save_dxf_settings(settings: DxfExportSettings, path: Path | None = None) -> None:
    p = path or default_settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(settings.to_dict(), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
