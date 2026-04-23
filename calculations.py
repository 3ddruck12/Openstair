"""Rechenkern: Katalog, `calculate_stair` / `build_bom` — Geometrie/Lasten/Checks in `core/`."""

from __future__ import annotations

import json
import logging
from math import sqrt
from pathlib import Path

from enums import StairDirection, StairOrientation, StairType, SupportLayout
from norms import BEARING_LIBRARY, MATERIAL_LIBRARY, NORM_CONFIG_DE
from profile_library import get_profile, get_profile_names

from core.checks import _check_connections, _check_phase0_gate, _check_sls, _check_uls
from core.geometry import _check_geometry, _compute_geometry, _compute_masses
from core.loads import _compute_loads
from core.models import BomItem, StairInput, StairResult

log = logging.getLogger(__name__)

TREAD_TYPES_JSON = Path(__file__).resolve().parent / "data" / "tread_types.json"
CUSTOM_TREAD_TYPE = "Benutzerdefiniert"
NORM_PROFILES = ["DIN EN DE-NA", "DIN EN AT-NA", "DIN EN CH-NA"]

_tread_cache: dict[str, dict] | None = None


def _load_tread_types() -> dict[str, dict]:
    global _tread_cache
    if _tread_cache is not None:
        return _tread_cache
    raw = json.loads(TREAD_TYPES_JSON.read_text(encoding="utf-8"))
    _tread_cache = {t["name"]: t for t in raw["tread_types"]}
    return _tread_cache


def get_available_profiles() -> list[str]:
    return get_profile_names()


def get_available_steel_grades() -> list[str]:
    return sorted(MATERIAL_LIBRARY.keys())


def get_steel_data(grade: str) -> dict[str, float]:
    if grade not in MATERIAL_LIBRARY:
        raise ValueError(f"Unbekannte Stahlguete: {grade}")
    return MATERIAL_LIBRARY[grade]


def get_available_bearing_conditions() -> list[str]:
    return sorted(BEARING_LIBRARY.keys())


def get_bearing_data(name: str) -> dict[str, float]:
    if name not in BEARING_LIBRARY:
        raise ValueError(f"Unbekannte Lagerung: {name}")
    return BEARING_LIBRARY[name]


def get_available_stair_types() -> list[str]:
    return [e.value for e in StairType]


def get_available_stair_directions() -> list[str]:
    return [e.value for e in StairDirection]


def get_available_stair_orientations() -> list[str]:
    return [e.value for e in StairOrientation]


def get_available_support_layouts() -> list[str]:
    return [e.value for e in SupportLayout]


def get_available_norm_profiles() -> list[str]:
    return NORM_PROFILES.copy()


def get_profile_data(profile_name: str) -> dict[str, float]:
    profile = get_profile(profile_name)
    result = {
        "kg_per_m": float(profile["kg_per_m"]),
        "w_el_cm3": float(profile["w_el_cm3"]),
        "i_cm4": float(profile["i_cm4"]),
        "height_mm": float(profile["height_mm"]),
        "width_mm": float(profile["width_mm"]),
        "thickness_mm": float(profile["thickness_mm"]),
    }
    if "a_v_cm2" in profile:
        result["a_v_cm2"] = float(profile["a_v_cm2"])
    return result


def get_available_tread_types() -> list[str]:
    return sorted(_load_tread_types().keys()) + [CUSTOM_TREAD_TYPE]


def get_tread_type_kg_per_m2(tread_type_name: str) -> float | None:
    if tread_type_name == CUSTOM_TREAD_TYPE:
        return None
    lib = _load_tread_types()
    if tread_type_name not in lib:
        raise ValueError(f"Unbekannter Stufentyp: {tread_type_name}")
    return float(lib[tread_type_name]["kg_per_m2"])


def get_tread_type_data(tread_type_name: str) -> dict | None:
    if tread_type_name == CUSTOM_TREAD_TYPE:
        return None
    lib = _load_tread_types()
    if tread_type_name not in lib:
        raise ValueError(f"Unbekannter Stufentyp: {tread_type_name}")
    return lib[tread_type_name]


def get_tread_type_description(tread_type_name: str) -> str:
    tread_data = get_tread_type_data(tread_type_name)
    if tread_data is None:
        return "Benutzerdefinierte Stufe - Daten manuell eingeben."
    return (
        f"Masche {tread_data['mesh']} | Tragstab {tread_data['bearing_bar']} | "
        f"Rutschhemmung {tread_data['slip_rating']} | "
        f"ca. {tread_data['kg_per_m2']:.1f} kg/m2"
    )


def _allowable_width_for_tread_type(tread_type_name: str, live_load_kN_m2: float) -> float:
    tread_data = get_tread_type_data(tread_type_name)
    if tread_data is None:
        return 9e9
    base_span = float(tread_data["max_span_mm_ref_load"])
    ref_load = float(tread_data["ref_live_load_kN_m2"])
    load_factor = sqrt(ref_load / live_load_kN_m2)
    return base_span * load_factor


def _recommend_tread_type(required_width_mm: float, live_load_kN_m2: float) -> str | None:
    fitting_types = []
    for tread_type_name in get_available_tread_types():
        if tread_type_name == CUSTOM_TREAD_TYPE:
            continue
        allowable_width = _allowable_width_for_tread_type(tread_type_name, live_load_kN_m2)
        if allowable_width >= required_width_mm:
            fit_kg = get_tread_type_kg_per_m2(tread_type_name)
            fitting_types.append((tread_type_name, fit_kg))
    if not fitting_types:
        return None
    fitting_types.sort(key=lambda item: item[1])
    return fitting_types[0][0]


def calculate_stair(data: StairInput) -> StairResult:
    if (
        data.floor_height_mm <= 0
        or data.going_mm <= 0
        or data.stair_width_mm <= 0
        or data.available_run_mm <= 0
        or data.live_load_kN_m2 <= 0
        or data.tread_plate_kg_per_m2 <= 0
        or data.headroom_clear_mm <= 0
        or data.plate_thickness_mm <= 0
        or data.weld_throat_mm <= 0
        or data.handrail_profile_kg_per_m <= 0
        or data.handrail_height_mm <= 0
        or data.support_unit_weight_kg <= 0
    ):
        raise ValueError("Alle Eingabewerte muessen groesser 0 sein.")
    if data.support_count < 0:
        raise ValueError("Stuetzenanzahl darf nicht negativ sein.")

    stair_types = [e.value for e in StairType]
    directions = [e.value for e in StairDirection]
    orientations = [e.value for e in StairOrientation]
    layouts = [e.value for e in SupportLayout]

    if data.stair_direction not in directions:
        raise ValueError(f"Unbekannte Laufrichtung: {data.stair_direction}")
    if data.stair_orientation not in orientations:
        raise ValueError(f"Unbekannte Orientierung: {data.stair_orientation}")
    if data.norm_profile not in NORM_PROFILES:
        raise ValueError(f"Unbekanntes Normprofil: {data.norm_profile}")
    if data.support_layout not in layouts:
        raise ValueError(f"Unbekanntes Stuetzenlayout: {data.support_layout}")
    if data.stair_type not in stair_types:
        raise ValueError(f"Unbekannter Treppentyp: {data.stair_type}")

    profile = get_profile_data(data.stringer_profile_name)
    steel_data = get_steel_data(data.steel_grade)
    bearing_data = get_bearing_data(data.bearing_condition)
    fy_mpa = data.steel_yield_mpa if data.steel_yield_mpa > 0 else steel_data["fy_mpa"]
    e_mpa = steel_data["e_mpa"]
    density = steel_data["density_kg_m3"]

    tread_type_weight = get_tread_type_kg_per_m2(data.tread_type_name)
    tread_kg_per_m2 = data.tread_plate_kg_per_m2 if tread_type_weight is None else tread_type_weight
    tread_desc = get_tread_type_description(data.tread_type_name)

    profile_kg_per_m = profile["kg_per_m"]
    w_el_mm3 = profile["w_el_cm3"] * 1000.0
    i_mm4 = profile["i_cm4"] * 10000.0
    area_mm2 = (profile_kg_per_m / density) * 1_000_000.0
    gamma_m0 = float(NORM_CONFIG_DE["material_factors"]["gamma_m0"])
    sigma_rd = fy_mpa / gamma_m0

    geo = _compute_geometry(data)
    masses = _compute_masses(data, geo, profile_kg_per_m, tread_kg_per_m2)
    loads = _compute_loads(data, geo, profile_kg_per_m, tread_kg_per_m2)
    uls = _check_uls(data, loads, bearing_data, profile, fy_mpa, e_mpa, area_mm2, w_el_mm3, i_mm4)
    sls = _check_sls(loads, bearing_data, e_mpa, i_mm4)
    conn = _check_connections(data, uls["v_ed"], sigma_rd)
    geo_checks = _check_geometry(data, geo)

    tread_allowable_width = _allowable_width_for_tread_type(data.tread_type_name, data.live_load_kN_m2)
    tread_ok_for_width = data.stair_width_mm <= tread_allowable_width
    recommended_tread_type = (
        None if tread_ok_for_width
        else _recommend_tread_type(data.stair_width_mm, data.live_load_kN_m2)
    )

    checks_ok = (
        uls["utilization_bending"] <= 1.0
        and uls["utilization_interaction"] <= 1.0
        and uls["utilization_shear"] <= 1.0
        and uls["utilization_buckling"] <= 1.0
        and uls["utilization_ltb"] <= 1.0
        and sls["utilization_deflection"] <= 1.0
        and sls["vibration_ok"]
        and tread_ok_for_width
        and conn["connections_ok"]
        and geo_checks["geometry_ok"]
    )

    phase0_gate_ok, phase0_gate_reasons = _check_phase0_gate(
        geo_checks["geometry_ok"], uls, sls, tread_ok_for_width, conn["connections_ok"],
    )

    return StairResult(
        riser_count=geo["riser_count"],
        tread_count=geo["tread_count"],
        stair_type=data.stair_type,
        stair_direction=data.stair_direction,
        stair_orientation=data.stair_orientation,
        norm_profile=data.norm_profile,
        bearing_condition=data.bearing_condition,
        steel_grade=data.steel_grade,
        run_flight_1_mm=geo["run_flight_1"],
        run_flight_2_mm=geo["run_flight_2"],
        landing_length_used_mm=geo["landing_length_used"],
        landing_width_used_mm=geo["landing_width_used"],
        landing_area_m2=geo["landing_area_m2"],
        span_lengths_mm=geo["span_lengths_mm"],
        governing_span_mm=geo["governing_span_mm"],
        stair_angle_deg=geo["stair_angle_deg"],
        riser_height_mm=geo["riser_height"],
        run_mm=geo["run"],
        stringer_length_mm=geo["stringer_length"],
        walking_line_mm=masses["walking_line"],
        approx_stringer_kg=masses["approx_stringer_kg"],
        approx_treads_kg=masses["approx_treads_kg"],
        approx_handrail_kg=masses["approx_handrail_kg"],
        approx_supports_kg=masses["approx_supports_kg"],
        handrail_length_m=masses["handrail_length_m"],
        support_count=masses["support_count"],
        support_layout=data.support_layout,
        approx_total_kg=masses["approx_total_kg"],
        selected_profile=data.stringer_profile_name,
        selected_tread_type=data.tread_type_name,
        tread_type_description=tread_desc,
        tread_ok_for_width=tread_ok_for_width,
        tread_allowable_width_mm=tread_allowable_width,
        recommended_tread_type=recommended_tread_type,
        profile_kg_per_m=profile_kg_per_m,
        design_line_load_kN_m=loads["design_line_load"],
        service_line_load_kN_m=loads["service_line_load"],
        m_ed_kNm=uls["m_ed"],
        sigma_ed_mpa=uls["sigma_ed"],
        utilization_bending=uls["utilization_bending"],
        n_ed_kN=uls["n_ed"],
        n_pl_rd_kN=uls["n_pl_rd"],
        utilization_interaction=uls["utilization_interaction"],
        v_ed_kN=uls["v_ed"],
        tau_ed_mpa=uls["tau_ed"],
        tau_rd_mpa=uls["tau_rd"],
        utilization_shear=uls["utilization_shear"],
        buckling_chi=uls["buckling_chi"],
        n_b_rd_kN=uls["n_b_rd"],
        utilization_buckling=uls["utilization_buckling"],
        ltb_chi=uls["ltb_chi"],
        m_b_rd_kNm=uls["m_b_rd"],
        utilization_ltb=uls["utilization_ltb"],
        deflection_mm=sls["deflection"],
        deflection_limit_mm=sls["deflection_limit"],
        utilization_deflection=sls["utilization_deflection"],
        natural_frequency_hz=sls["natural_frequency"],
        vibration_ok=sls["vibration_ok"],
        plate_bearing_stress_mpa=conn["plate_bearing_stress"],
        plate_bearing_rd_mpa=conn["plate_bearing_rd"],
        utilization_plate=conn["utilization_plate"],
        bolt_utilization=conn["bolt_utilization"],
        weld_utilization=conn["weld_utilization"],
        connections_ok=conn["connections_ok"],
        geometry_checks=geo_checks["geometry_checks"],
        plausibility_checks=geo_checks["plausibility_checks"],
        collisions=geo_checks["collisions"],
        geometry_ok=geo_checks["geometry_ok"],
        phase0_gate_ok=phase0_gate_ok,
        phase0_gate_reasons=phase0_gate_reasons,
        checks_ok=checks_ok,
    )


def build_bom(data: StairInput, result: StairResult) -> list[BomItem]:
    stringer_length_m = result.stringer_length_mm / 1000.0
    tread_single_area_m2 = (data.going_mm / 1000.0) * (data.stair_width_mm / 1000.0)
    tread_kg_per_m2 = result.approx_treads_kg / max(result.tread_count * tread_single_area_m2, 1e-9)

    bom_items = [
        BomItem(
            position=1,
            item=f"Wange links ({result.selected_profile})",
            material=data.steel_grade,
            quantity=stringer_length_m,
            unit="m",
            unit_weight_kg=result.profile_kg_per_m,
            total_weight_kg=stringer_length_m * result.profile_kg_per_m,
        ),
        BomItem(
            position=2,
            item=f"Wange rechts ({result.selected_profile})",
            material=data.steel_grade,
            quantity=stringer_length_m,
            unit="m",
            unit_weight_kg=result.profile_kg_per_m,
            total_weight_kg=stringer_length_m * result.profile_kg_per_m,
        ),
        BomItem(
            position=3,
            item=f"Treppenstufen ({result.selected_tread_type})",
            material="Stahl verzinkt",
            quantity=float(result.tread_count),
            unit="Stk",
            unit_weight_kg=tread_single_area_m2 * tread_kg_per_m2,
            total_weight_kg=result.approx_treads_kg,
            note=f"{data.stair_width_mm:.0f}x{data.going_mm:.0f} mm je Stufe",
        ),
        BomItem(
            position=4,
            item="Anschlussplatten Kopf/Fuss",
            material=data.steel_grade,
            quantity=4.0,
            unit="Stk",
            unit_weight_kg=2.5,
            total_weight_kg=10.0,
            note="Pauschalansatz fuer Vorplanung",
        ),
        BomItem(
            position=5,
            item="Schrauben M12 + Muttern + Scheiben",
            material="8.8 verzinkt",
            quantity=24.0,
            unit="Stk",
            unit_weight_kg=0.08,
            total_weight_kg=1.92,
            note="Pauschalansatz fuer Vorplanung",
        ),
    ]

    next_pos = 6
    if result.landing_area_m2 > 0:
        bom_items.append(
            BomItem(
                position=next_pos,
                item="Podestflaeche",
                material="Stahl verzinkt",
                quantity=result.landing_area_m2,
                unit="m2",
                unit_weight_kg=(
                    result.approx_treads_kg / max((result.tread_count * tread_single_area_m2) + result.landing_area_m2, 1e-9)
                ),
                total_weight_kg=(
                    result.approx_treads_kg * (
                        result.landing_area_m2 / max((result.tread_count * tread_single_area_m2) + result.landing_area_m2, 1e-9)
                    )
                ),
                note=f"{result.landing_length_used_mm:.0f}x{result.landing_width_used_mm:.0f} mm",
            )
        )
        next_pos += 1

    if data.handrail_enabled and result.handrail_length_m > 0:
        bom_items.append(
            BomItem(
                position=next_pos,
                item=f"Handlauf ({data.handrail_sides})",
                material=data.steel_grade,
                quantity=result.handrail_length_m,
                unit="m",
                unit_weight_kg=data.handrail_profile_kg_per_m,
                total_weight_kg=result.approx_handrail_kg,
                note=f"Handlaufhoehe {data.handrail_height_mm:.0f} mm",
            )
        )
        next_pos += 1

    if data.supports_enabled and result.support_count > 0:
        bom_items.append(
            BomItem(
                position=next_pos,
                item="Stuetzen",
                material=data.steel_grade,
                quantity=float(result.support_count),
                unit="Stk",
                unit_weight_kg=data.support_unit_weight_kg,
                total_weight_kg=result.approx_supports_kg,
                note=f"Layout: {result.support_layout}",
            )
        )

    return bom_items
