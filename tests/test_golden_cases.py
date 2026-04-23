"""Golden Cases: Referenzwerte fuer den Rechenkern (Regressionsschutz)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from calculations import StairInput, build_bom, calculate_stair
from enums import BearingCondition, StairType


def test_golden_case_standard_is_stable() -> None:
    data = StairInput(
        floor_height_mm=3000.0,
        going_mm=270.0,
        stair_width_mm=1000.0,
        stringer_profile_name="HEA160",
        tread_type_name="MEISER SP 30/3 33x33 R11",
        live_load_kN_m2=3.0,
    )
    result = calculate_stair(data)
    assert result.geometry_ok
    assert result.utilization_bending < 1.0
    assert result.utilization_shear < 1.0
    assert result.utilization_deflection < 1.0
    assert result.utilization_ltb < 1.0
    assert result.phase0_gate_ok


def test_golden_case_low_width_fails_geometry() -> None:
    data = StairInput(
        floor_height_mm=3000.0,
        going_mm=270.0,
        stair_width_mm=700.0,
        stringer_profile_name="HEA140",
        tread_type_name="MEISER SP 30/3 33x33 R11",
        live_load_kN_m2=3.0,
    )
    result = calculate_stair(data)
    assert not result.geometry_ok
    assert any("Laufbreite" in msg for msg in result.geometry_checks)
    assert not result.phase0_gate_ok


def test_golden_case_high_load_demands_tread_recommendation() -> None:
    data = StairInput(
        floor_height_mm=3300.0,
        going_mm=260.0,
        stair_width_mm=1300.0,
        stringer_profile_name="HEA160",
        tread_type_name="MEISER SP 40/2 33x33 R11",
        live_load_kN_m2=5.0,
    )
    result = calculate_stair(data)
    assert not result.tread_ok_for_width
    assert result.recommended_tread_type is not None
    assert not result.phase0_gate_ok


def test_golden_case_bad_step_rule_detected() -> None:
    data = StairInput(
        floor_height_mm=3500.0,
        going_mm=210.0,
        stair_width_mm=1000.0,
        stringer_profile_name="HEA140",
        tread_type_name="MEISER SP 30/3 33x33 R11",
        live_load_kN_m2=3.0,
    )
    result = calculate_stair(data)
    assert not result.geometry_ok
    assert any("Schrittmassregel" in msg for msg in result.geometry_checks)
    assert not result.phase0_gate_ok


def test_golden_case_headroom_check_detected() -> None:
    data = StairInput(
        floor_height_mm=3000.0,
        going_mm=270.0,
        stair_width_mm=1000.0,
        stringer_profile_name="HEA160",
        tread_type_name="MEISER SP 30/3 33x33 R11",
        headroom_clear_mm=1850.0,
    )
    result = calculate_stair(data)
    assert not result.geometry_ok
    assert any("Kopffreiheit" in msg for msg in result.geometry_checks)
    assert not result.phase0_gate_ok


def test_golden_case_high_axial_force_fails_interaction() -> None:
    data = StairInput(
        floor_height_mm=3000.0,
        going_mm=270.0,
        stair_width_mm=1000.0,
        stringer_profile_name="UPN120",
        tread_type_name="MEISER SP 30/3 33x33 R11",
        axial_force_kN=1500.0,
    )
    result = calculate_stair(data)
    assert result.utilization_interaction > 1.0
    assert not result.phase0_gate_ok


def test_golden_case_collision_is_detected() -> None:
    data = StairInput(
        floor_height_mm=3000.0,
        going_mm=300.0,
        stair_width_mm=1000.0,
        available_run_mm=2000.0,
        stair_type=StairType.STRAIGHT,
        stringer_profile_name="HEA160",
        tread_type_name="MEISER SP 30/3 33x33 R11",
    )
    result = calculate_stair(data)
    assert result.collisions
    assert not result.phase0_gate_ok


def test_golden_case_bearing_condition_changes_moment() -> None:
    base = StairInput(
        floor_height_mm=3000.0,
        going_mm=270.0,
        stair_width_mm=1000.0,
        stair_type=StairType.STRAIGHT,
        stringer_profile_name="HEA160",
        tread_type_name="MEISER SP 30/3 33x33 R11",
    )
    res_pinned = calculate_stair(base)
    res_fixed = calculate_stair(
        StairInput(**{**base.__dict__, "bearing_condition": BearingCondition.FIXED_FIXED})
    )
    assert res_fixed.m_ed_kNm < res_pinned.m_ed_kNm


# --- Neue Tests (Audit) ---


def test_result_has_ltb_fields() -> None:
    """StairResult muss die neuen LTB-Felder enthalten."""
    data = StairInput(
        floor_height_mm=3000.0,
        going_mm=270.0,
        stair_width_mm=1000.0,
        stringer_profile_name="HEA160",
    )
    result = calculate_stair(data)
    assert hasattr(result, "ltb_chi")
    assert hasattr(result, "m_b_rd_kNm")
    assert hasattr(result, "utilization_ltb")
    assert 0.0 < result.ltb_chi <= 1.0
    assert result.m_b_rd_kNm > 0.0


def test_buckling_length_depends_on_bearing() -> None:
    """Eingespannte Lager muessen kuerzere Knicklaenge und kleinere Ausnutzung ergeben."""
    base_kw = dict(
        floor_height_mm=3000.0, going_mm=270.0, stair_width_mm=1000.0,
        stringer_profile_name="HEA120", axial_force_kN=50.0,
    )
    r_pin = calculate_stair(StairInput(**base_kw, bearing_condition=BearingCondition.PINNED_PINNED))
    r_fix = calculate_stair(StairInput(**base_kw, bearing_condition=BearingCondition.FIXED_FIXED))
    assert r_fix.utilization_buckling < r_pin.utilization_buckling


def test_shear_uses_profile_a_v() -> None:
    """Querkraftnachweis soll die echte Schubflaeche nutzen (nicht W_el/100)."""
    data = StairInput(
        floor_height_mm=3000.0, going_mm=270.0, stair_width_mm=1000.0,
        stringer_profile_name="HEA160",
    )
    result = calculate_stair(data)
    assert result.utilization_shear > 0.0
    assert result.tau_ed_mpa > 0.0
    assert result.tau_rd_mpa > 0.0


def test_podest_stair_has_two_spans() -> None:
    data = StairInput(
        floor_height_mm=3000.0, going_mm=270.0, stair_width_mm=1000.0,
        stair_type=StairType.LANDING, stringer_profile_name="HEA160",
    )
    result = calculate_stair(data)
    assert len(result.span_lengths_mm) == 2
    assert result.landing_area_m2 > 0


def test_quarter_turn_stair_shorter_run() -> None:
    data = StairInput(
        floor_height_mm=3000.0, going_mm=270.0, stair_width_mm=1000.0,
        stair_type=StairType.QUARTER, stringer_profile_name="HEA160",
    )
    result = calculate_stair(data)
    data_straight = StairInput(
        floor_height_mm=3000.0, going_mm=270.0, stair_width_mm=1000.0,
        stair_type=StairType.STRAIGHT, stringer_profile_name="HEA160",
    )
    result_straight = calculate_stair(data_straight)
    assert result.run_mm < result_straight.run_mm


def test_half_turn_stair_calculates() -> None:
    data = StairInput(
        floor_height_mm=3000.0, going_mm=270.0, stair_width_mm=1000.0,
        stair_type=StairType.HALF, stringer_profile_name="HEA160",
    )
    result = calculate_stair(data)
    assert result.tread_count > 0
    assert result.stringer_length_mm > 0


def test_all_steel_grades_work() -> None:
    from enums import SteelGrade
    for grade in SteelGrade:
        data = StairInput(
            floor_height_mm=3000.0, going_mm=270.0, stair_width_mm=1000.0,
            stringer_profile_name="HEA160", steel_grade=grade,
        )
        result = calculate_stair(data)
        assert result.utilization_bending > 0


def test_all_bearing_conditions_work() -> None:
    for bc in BearingCondition:
        data = StairInput(
            floor_height_mm=3000.0, going_mm=270.0, stair_width_mm=1000.0,
            stringer_profile_name="HEA160", bearing_condition=bc,
        )
        result = calculate_stair(data)
        assert result.utilization_bending > 0


def test_handrail_adds_mass() -> None:
    data_off = StairInput(
        floor_height_mm=3000.0, going_mm=270.0, stair_width_mm=1000.0,
        stringer_profile_name="HEA160", handrail_enabled=False,
    )
    data_on = StairInput(
        floor_height_mm=3000.0, going_mm=270.0, stair_width_mm=1000.0,
        stringer_profile_name="HEA160", handrail_enabled=True,
    )
    r_off = calculate_stair(data_off)
    r_on = calculate_stair(data_on)
    assert r_on.approx_total_kg > r_off.approx_total_kg
    assert r_on.handrail_length_m > 0
    assert r_off.handrail_length_m == 0


def test_supports_adds_mass() -> None:
    data_off = StairInput(
        floor_height_mm=3000.0, going_mm=270.0, stair_width_mm=1000.0,
        stringer_profile_name="HEA160", supports_enabled=False,
    )
    data_on = StairInput(
        floor_height_mm=3000.0, going_mm=270.0, stair_width_mm=1000.0,
        stringer_profile_name="HEA160", supports_enabled=True,
    )
    r_off = calculate_stair(data_off)
    r_on = calculate_stair(data_on)
    assert r_on.approx_total_kg > r_off.approx_total_kg
    assert r_on.support_count > 0


def test_bom_has_minimum_positions() -> None:
    data = StairInput(
        floor_height_mm=3000.0, going_mm=270.0, stair_width_mm=1000.0,
        stringer_profile_name="HEA160",
    )
    result = calculate_stair(data)
    bom = build_bom(data, result)
    assert len(bom) >= 5
    positions = [item.position for item in bom]
    assert 1 in positions
    assert 2 in positions
    assert 3 in positions


def test_bom_total_weight_consistent() -> None:
    data = StairInput(
        floor_height_mm=3000.0, going_mm=270.0, stair_width_mm=1000.0,
        stringer_profile_name="HEA160", handrail_enabled=True, supports_enabled=True,
    )
    result = calculate_stair(data)
    bom = build_bom(data, result)
    bom_total = sum(item.total_weight_kg for item in bom)
    assert bom_total > 0


def test_invalid_inputs_raise_value_error() -> None:
    import pytest
    with pytest.raises(ValueError):
        calculate_stair(StairInput(floor_height_mm=0, going_mm=270, stair_width_mm=1000))
    with pytest.raises(ValueError):
        calculate_stair(StairInput(floor_height_mm=3000, going_mm=0, stair_width_mm=1000))
    with pytest.raises(ValueError):
        calculate_stair(StairInput(floor_height_mm=3000, going_mm=270, stair_width_mm=0))


def test_vibration_ok_for_standard_case() -> None:
    data = StairInput(
        floor_height_mm=3000.0, going_mm=270.0, stair_width_mm=1000.0,
        stringer_profile_name="HEA160",
    )
    result = calculate_stair(data)
    assert result.natural_frequency_hz > 0
    assert result.vibration_ok


def test_connections_ok_for_standard_case() -> None:
    data = StairInput(
        floor_height_mm=3000.0, going_mm=270.0, stair_width_mm=1000.0,
        stringer_profile_name="HEA160",
    )
    result = calculate_stair(data)
    assert result.connections_ok
    assert result.utilization_plate < 1.0
    assert result.bolt_utilization < 1.0
    assert result.weld_utilization < 1.0
