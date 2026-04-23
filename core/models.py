"""Eingabe-, Ergebnis- und Stuecklisten-Modelle fuer die Treppe."""

from __future__ import annotations

from dataclasses import dataclass

from enums import (
    BearingCondition,
    HandrailSide,
    StairDirection,
    StairOrientation,
    StairType,
    SteelGrade,
    SupportLayout,
)


@dataclass
class StairInput:
    floor_height_mm: float
    going_mm: float
    stair_width_mm: float
    available_run_mm: float = 6000.0
    stair_type: str = StairType.STRAIGHT
    stair_direction: str = StairDirection.RIGHT
    stair_orientation: str = StairOrientation.N
    norm_profile: str = "DIN EN DE-NA"
    bearing_condition: str = BearingCondition.PINNED_PINNED
    stringer_profile_name: str = "HEA120"
    steel_grade: str = SteelGrade.S235
    tread_type_name: str = "MEISER SP 30/3 33x33 R11"
    tread_plate_kg_per_m2: float = 39.25
    live_load_kN_m2: float = 3.0
    steel_yield_mpa: float = 0.0
    national_annex: str = "NA Deutschland"
    regulation_profile: str = "Keine Zusatzanforderung"
    headroom_clear_mm: float = 2100.0
    landing_length_mm: float = 0.0
    landing_width_mm: float = 0.0
    landing_position: str = "mittig"
    axial_force_kN: float = 0.0
    plate_thickness_mm: float = 10.0
    plate_width_mm: float = 0.0
    plate_height_mm: float = 0.0
    bolts_per_support: int = 0
    bolt_shear_rd_kN: float = 0.0
    weld_throat_mm: float = 4.0
    weld_length_mm: float = 0.0
    handrail_enabled: bool = False
    handrail_sides: str = HandrailSide.BOTH
    handrail_profile_kg_per_m: float = 4.2
    handrail_height_mm: float = 1000.0
    supports_enabled: bool = False
    support_layout: str = SupportLayout.EQUAL
    support_count: int = 0
    support_unit_weight_kg: float = 8.0


@dataclass
class StairResult:
    riser_count: int
    tread_count: int
    stair_type: str
    stair_direction: str
    stair_orientation: str
    norm_profile: str
    bearing_condition: str
    steel_grade: str
    run_flight_1_mm: float
    run_flight_2_mm: float
    landing_length_used_mm: float
    landing_width_used_mm: float
    landing_area_m2: float
    span_lengths_mm: list[float]
    governing_span_mm: float
    stair_angle_deg: float
    riser_height_mm: float
    run_mm: float
    stringer_length_mm: float
    walking_line_mm: float
    approx_stringer_kg: float
    approx_treads_kg: float
    approx_handrail_kg: float
    approx_supports_kg: float
    handrail_length_m: float
    support_count: int
    support_layout: str
    approx_total_kg: float
    selected_profile: str
    selected_tread_type: str
    tread_type_description: str
    tread_ok_for_width: bool
    tread_allowable_width_mm: float
    recommended_tread_type: str | None
    profile_kg_per_m: float
    design_line_load_kN_m: float
    service_line_load_kN_m: float
    m_ed_kNm: float
    sigma_ed_mpa: float
    utilization_bending: float
    n_ed_kN: float
    n_pl_rd_kN: float
    utilization_interaction: float
    v_ed_kN: float
    tau_ed_mpa: float
    tau_rd_mpa: float
    utilization_shear: float
    buckling_chi: float
    n_b_rd_kN: float
    utilization_buckling: float
    ltb_chi: float
    m_b_rd_kNm: float
    utilization_ltb: float
    deflection_mm: float
    deflection_limit_mm: float
    utilization_deflection: float
    natural_frequency_hz: float
    vibration_ok: bool
    plate_bearing_stress_mpa: float
    plate_bearing_rd_mpa: float
    utilization_plate: float
    bolt_utilization: float
    weld_utilization: float
    connections_ok: bool
    geometry_checks: list[str]
    plausibility_checks: list[str]
    collisions: list[str]
    geometry_ok: bool
    phase0_gate_ok: bool
    phase0_gate_reasons: list[str]
    checks_ok: bool


@dataclass
class BomItem:
    position: int
    item: str
    material: str
    quantity: float
    unit: str
    unit_weight_kg: float
    total_weight_kg: float
    note: str = ""
