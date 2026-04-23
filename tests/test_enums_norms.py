"""Tests fuer Enums, Normkonfiguration und Tread-Type JSON."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enums import (
    BearingCondition,
    HandrailSide,
    StairDirection,
    StairOrientation,
    StairType,
    SteelGrade,
    SupportLayout,
    __version__,
)
from norms import BEARING_LIBRARY, MATERIAL_LIBRARY, NORM_CONFIG_DE
from calculations import (
    get_available_bearing_conditions,
    get_available_stair_types,
    get_available_steel_grades,
    get_available_tread_types,
    get_tread_type_data,
    get_tread_type_description,
    get_tread_type_kg_per_m2,
)


def test_version_is_set() -> None:
    assert __version__
    parts = __version__.split(".")
    assert len(parts) == 3


def test_stair_type_values_match_display() -> None:
    assert StairType.STRAIGHT == "Gerade Treppe"
    assert StairType.LANDING == "Podesttreppe"


def test_all_enum_members_are_strings() -> None:
    for e in (StairType, StairDirection, StairOrientation, BearingCondition, SteelGrade, HandrailSide, SupportLayout):
        for member in e:
            assert isinstance(member.value, str)


def test_bearing_library_has_all_conditions() -> None:
    for bc in BearingCondition:
        assert bc in BEARING_LIBRARY
        assert "moment_factor" in BEARING_LIBRARY[bc]
        assert "buckling_length_factor" in BEARING_LIBRARY[bc]
        assert "vibration_coeff" in BEARING_LIBRARY[bc]


def test_material_library_has_all_grades() -> None:
    for sg in SteelGrade:
        assert sg in MATERIAL_LIBRARY
        assert MATERIAL_LIBRARY[sg]["fy_mpa"] > 0


def test_material_library_s275_s460() -> None:
    assert MATERIAL_LIBRARY[SteelGrade.S275]["fy_mpa"] == 275.0
    assert MATERIAL_LIBRARY[SteelGrade.S460]["fy_mpa"] == 460.0


def test_norm_config_has_gamma_m1() -> None:
    assert "gamma_m1" in NORM_CONFIG_DE["material_factors"]


def test_tread_types_loaded_from_json() -> None:
    types = get_available_tread_types()
    assert len(types) >= 5
    assert "Benutzerdefiniert" in types
    assert "MEISER SP 30/3 33x33 R11" in types


def test_tread_type_data_returns_dict() -> None:
    d = get_tread_type_data("MEISER SP 30/3 33x33 R11")
    assert d is not None
    assert "kg_per_m2" in d
    assert "mesh" in d


def test_tread_type_custom_returns_none() -> None:
    assert get_tread_type_data("Benutzerdefiniert") is None
    assert get_tread_type_kg_per_m2("Benutzerdefiniert") is None


def test_tread_type_description() -> None:
    desc = get_tread_type_description("MEISER SP 30/3 33x33 R11")
    assert "R11" in desc
    assert "33x33" in desc


def test_available_steel_grades_includes_new() -> None:
    grades = get_available_steel_grades()
    assert "S275" in grades
    assert "S420" in grades
    assert "S460" in grades


def test_available_bearing_conditions() -> None:
    conds = get_available_bearing_conditions()
    assert len(conds) == 3
    assert BearingCondition.PINNED_PINNED in conds


def test_available_stair_types() -> None:
    types = get_available_stair_types()
    assert len(types) == 4
    assert StairType.STRAIGHT in types
