"""Tests fuer Projektdatei-Serialisierung und DXF-Settings."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dxf_settings import DxfExportSettings, load_dxf_settings, save_dxf_settings


def test_dxf_settings_roundtrip() -> None:
    original = DxfExportSettings(
        layer_geometry="GEOM_TEST",
        text_height_notes=42.0,
        include_plan_view=False,
        plan_gap_mm=300.0,
    )
    d = original.to_dict()
    restored = DxfExportSettings.from_dict(d)
    assert restored.layer_geometry == "GEOM_TEST"
    assert restored.text_height_notes == 42.0
    assert restored.include_plan_view is False
    assert restored.plan_gap_mm == 300.0


def test_dxf_settings_file_roundtrip() -> None:
    original = DxfExportSettings(layer_notes="MY_NOTES", text_height_dimensions=50.0)
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp = Path(f.name)
    try:
        save_dxf_settings(original, tmp)
        loaded = load_dxf_settings(tmp)
        assert loaded.layer_notes == "MY_NOTES"
        assert loaded.text_height_dimensions == 50.0
    finally:
        tmp.unlink(missing_ok=True)


def test_dxf_settings_from_empty_dict() -> None:
    s = DxfExportSettings.from_dict({})
    assert s.layer_geometry == "GEOMETRY"
    assert s.include_plan_view is True


def test_dxf_settings_from_partial_dict() -> None:
    s = DxfExportSettings.from_dict({"layer_geometry": "CUSTOM"})
    assert s.layer_geometry == "CUSTOM"
    assert s.layer_dimensions == "DIMENSIONS"


def test_load_missing_settings_returns_default() -> None:
    s = load_dxf_settings(Path("/tmp/nonexistent_openstair_settings.json"))
    assert s.layer_geometry == "GEOMETRY"
