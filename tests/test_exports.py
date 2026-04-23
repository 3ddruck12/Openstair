"""Tests fuer DXF, PDF und BOM Export (Regressionstests)."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from calculations import StairInput, build_bom, calculate_stair
from dxf_export import export_stair_side_view_dxf
from dxf_settings import DxfExportSettings
from report_export import export_bom_csv, export_report_pdf


def _standard_input() -> StairInput:
    return StairInput(
        floor_height_mm=3000.0,
        going_mm=270.0,
        stair_width_mm=1000.0,
        stringer_profile_name="HEA160",
    )


def test_dxf_export_creates_valid_file() -> None:
    data = _standard_input()
    result = calculate_stair(data)
    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as f:
        tmp = Path(f.name)
    try:
        export_stair_side_view_dxf(tmp, data, result)
        assert tmp.exists()
        assert tmp.stat().st_size > 100
        content = tmp.read_text(encoding="utf-8", errors="replace")
        assert "GEOMETRY" in content
        assert "DIMENSIONS" in content
        assert "Schrittmass 2h+a" in content
        assert "2h+a" in content
    finally:
        tmp.unlink(missing_ok=True)


def test_dxf_export_with_plan_view() -> None:
    data = _standard_input()
    result = calculate_stair(data)
    settings = DxfExportSettings(include_plan_view=True)
    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as f:
        tmp = Path(f.name)
    try:
        export_stair_side_view_dxf(tmp, data, result, settings)
        assert tmp.stat().st_size > 200
    finally:
        tmp.unlink(missing_ok=True)


def test_dxf_export_has_dimension_entities() -> None:
    import ezdxf
    data = _standard_input()
    result = calculate_stair(data)
    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as f:
        tmp = Path(f.name)
    try:
        export_stair_side_view_dxf(tmp, data, result)
        doc = ezdxf.readfile(str(tmp))
        msp = doc.modelspace()
        dim_entities = [e for e in msp if e.dxftype() == "DIMENSION"]
        assert len(dim_entities) >= 3
    finally:
        tmp.unlink(missing_ok=True)


def test_pdf_export_creates_valid_file() -> None:
    data = _standard_input()
    result = calculate_stair(data)
    bom = build_bom(data, result)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        tmp = Path(f.name)
    try:
        export_report_pdf(tmp, data, result, bom)
        assert tmp.exists()
        assert tmp.stat().st_size > 500
        header = tmp.read_bytes()[:5]
        assert header == b"%PDF-"
    finally:
        tmp.unlink(missing_ok=True)


def test_bom_csv_export_creates_valid_file() -> None:
    data = _standard_input()
    result = calculate_stair(data)
    bom = build_bom(data, result)
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        tmp = Path(f.name)
    try:
        export_bom_csv(tmp, bom)
        assert tmp.exists()
        lines = tmp.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) >= 6
        assert "Pos" in lines[0]
        assert ";" in lines[0]
    finally:
        tmp.unlink(missing_ok=True)


def test_bom_csv_has_semicolon_delimiter() -> None:
    data = _standard_input()
    result = calculate_stair(data)
    bom = build_bom(data, result)
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        tmp = Path(f.name)
    try:
        export_bom_csv(tmp, bom)
        content = tmp.read_text(encoding="utf-8")
        for line in content.strip().split("\n"):
            assert ";" in line
    finally:
        tmp.unlink(missing_ok=True)
