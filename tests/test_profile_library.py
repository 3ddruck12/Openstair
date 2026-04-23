import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from profile_library import (
    PROFILE_CSV_FILE,
    get_profile,
    get_profile_library_metadata,
    get_profile_names,
    load_profile_library,
)


def test_profile_library_has_expected_series() -> None:
    names = get_profile_names()
    assert "UPN120" in names
    assert "UPE160" in names
    assert "HEA160" in names
    assert "HEB160" in names
    assert "RHS140x80x5" in names
    assert "SHS120x120x5" in names


def test_profile_has_required_fields() -> None:
    p = get_profile("HEA160")
    for key in (
        "name",
        "series",
        "kg_per_m",
        "w_el_cm3",
        "i_cm4",
        "height_mm",
        "width_mm",
        "thickness_mm",
    ):
        assert key in p


def test_profile_metadata_versioning() -> None:
    meta = get_profile_library_metadata()
    assert meta["schema_version"]
    assert meta["library_version"]
    assert meta["source"]
    assert meta["format"] in {"json", "csv"}


def test_profile_library_can_read_csv() -> None:
    data = load_profile_library(PROFILE_CSV_FILE)
    assert data["format"] == "csv"
    assert "HEA160" in data["profiles_by_name"]
