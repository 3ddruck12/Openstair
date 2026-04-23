"""Geometrie und Massenschwerpunkte (Vorplanung)."""

from __future__ import annotations

import logging
from math import atan, ceil, degrees, sqrt

from enums import HandrailSide, StairType, SupportLayout
from norms import NORM_CONFIG_DE

from core.models import StairInput

log = logging.getLogger(__name__)


def _compute_geometry(data: StairInput) -> dict:
    target_riser = 175.0
    riser_count = max(2, round(data.floor_height_mm / target_riser))
    riser_height = data.floor_height_mm / riser_count
    tread_count = riser_count - 1
    run_flight_1 = 0.0
    run_flight_2 = 0.0
    landing_length_used = 0.0
    landing_width_used = 0.0

    if data.stair_type == StairType.STRAIGHT:
        run_flight_1 = tread_count * data.going_mm
    elif data.stair_type == StairType.LANDING:
        treads_1 = tread_count // 2
        treads_2 = tread_count - treads_1
        run_flight_1 = treads_1 * data.going_mm
        run_flight_2 = treads_2 * data.going_mm
        landing_length_used = max(data.landing_length_mm, data.stair_width_mm)
        landing_width_used = max(data.landing_width_mm, data.stair_width_mm)
    elif data.stair_type == StairType.QUARTER:
        run_flight_1 = tread_count * data.going_mm * 0.85
    else:
        run_flight_1 = tread_count * data.going_mm * 0.70

    run = run_flight_1 + run_flight_2 + landing_length_used

    if data.stair_type == StairType.LANDING:
        span_lengths_mm = [
            sqrt((data.floor_height_mm / 2.0) ** 2 + run_flight_1**2),
            sqrt((data.floor_height_mm / 2.0) ** 2 + run_flight_2**2),
        ]
        stringer_length = span_lengths_mm[0] + span_lengths_mm[1]
    else:
        single_span = sqrt(data.floor_height_mm**2 + run**2)
        span_lengths_mm = [single_span]
        stringer_length = single_span

    governing_span_mm = max(span_lengths_mm)
    stair_angle_deg = degrees(atan(data.floor_height_mm / max(run, 1.0)))

    landing_area_m2 = (
        (landing_length_used / 1000.0) * (landing_width_used / 1000.0)
        if data.stair_type == StairType.LANDING
        else 0.0
    )

    log.debug(
        "Geometrie: %d Steigungen, h=%.1f mm, run=%.1f mm, winkel=%.1f°",
        riser_count, riser_height, run, stair_angle_deg,
    )

    return {
        "riser_count": riser_count,
        "riser_height": riser_height,
        "tread_count": tread_count,
        "run_flight_1": run_flight_1,
        "run_flight_2": run_flight_2,
        "landing_length_used": landing_length_used,
        "landing_width_used": landing_width_used,
        "landing_area_m2": landing_area_m2,
        "run": run,
        "span_lengths_mm": span_lengths_mm,
        "governing_span_mm": governing_span_mm,
        "stringer_length": stringer_length,
        "stair_angle_deg": stair_angle_deg,
    }


def _compute_masses(
    data: StairInput, geo: dict, profile_kg_per_m: float, tread_kg_per_m2: float,
) -> dict:
    stringer_length_m = geo["stringer_length"] / 1000.0
    tread_area_m2 = (data.going_mm / 1000.0) * (data.stair_width_mm / 1000.0)
    total_tread_area_m2 = tread_area_m2 * geo["tread_count"]
    approx_stringer_kg = 2.0 * stringer_length_m * profile_kg_per_m
    approx_treads_kg = (total_tread_area_m2 + geo["landing_area_m2"]) * tread_kg_per_m2

    walking_line = geo["stringer_length"]
    side_factor = 2.0 if data.handrail_sides == HandrailSide.BOTH else 1.0
    handrail_length_m = (walking_line / 1000.0) * side_factor if data.handrail_enabled else 0.0
    approx_handrail_kg = handrail_length_m * data.handrail_profile_kg_per_m if data.handrail_enabled else 0.0

    if not data.supports_enabled:
        auto_support_count = 0
    elif data.support_layout == SupportLayout.ENDS_ONLY:
        auto_support_count = 2
    else:
        auto_support_count = max(2, int(ceil((walking_line / 1000.0) / 1.5)))

    support_count = data.support_count if data.support_count > 0 else auto_support_count
    approx_supports_kg = float(support_count) * data.support_unit_weight_kg if data.supports_enabled else 0.0
    approx_total_kg = approx_stringer_kg + approx_treads_kg + approx_handrail_kg + approx_supports_kg

    return {
        "approx_stringer_kg": approx_stringer_kg,
        "approx_treads_kg": approx_treads_kg,
        "approx_handrail_kg": approx_handrail_kg,
        "approx_supports_kg": approx_supports_kg,
        "handrail_length_m": handrail_length_m,
        "support_count": support_count,
        "approx_total_kg": approx_total_kg,
        "walking_line": walking_line,
    }


def _check_geometry(data: StairInput, geo: dict) -> dict:
    geometry_rules = NORM_CONFIG_DE["geometry_rules"]
    riser_height = geo["riser_height"]
    run = geo["run"]
    landing_length_used = geo["landing_length_used"]
    landing_width_used = geo["landing_width_used"]
    stair_angle_deg = geo["stair_angle_deg"]

    step_rule = 2.0 * riser_height + data.going_mm
    geometry_checks: list[str] = []
    plausibility_checks: list[str] = []
    collisions: list[str] = []

    if not (geometry_rules["riser_min_mm"] <= riser_height <= geometry_rules["riser_max_mm"]):
        geometry_checks.append(
            f"Steigungshoehe ausserhalb [{geometry_rules['riser_min_mm']:.0f}, "
            f"{geometry_rules['riser_max_mm']:.0f}] mm"
        )
    if not (geometry_rules["going_min_mm"] <= data.going_mm <= geometry_rules["going_max_mm"]):
        geometry_checks.append(
            f"Auftritt ausserhalb [{geometry_rules['going_min_mm']:.0f}, "
            f"{geometry_rules['going_max_mm']:.0f}] mm"
        )
    step_target = geometry_rules["step_rule_target_mm"]
    step_tol = geometry_rules["step_rule_tolerance_mm"]
    if not (step_target - step_tol <= step_rule <= step_target + step_tol):
        geometry_checks.append(
            f"Schrittmassregel verletzt (2s+a={step_rule:.1f} mm, Ziel {step_target:.0f}+/-{step_tol:.0f})"
        )
    if data.stair_width_mm < geometry_rules["min_clear_width_mm"]:
        geometry_checks.append(
            f"Laufbreite unter Mindestwert ({data.stair_width_mm:.0f} < "
            f"{geometry_rules['min_clear_width_mm']:.0f} mm)"
        )
    if data.headroom_clear_mm < geometry_rules["min_headroom_mm"]:
        geometry_checks.append(
            f"Kopffreiheit unter Mindestwert ({data.headroom_clear_mm:.0f} < "
            f"{geometry_rules['min_headroom_mm']:.0f} mm)"
        )
    if data.floor_height_mm > geometry_rules["landing_required_height_mm"]:
        min_landing = max(geometry_rules["min_landing_length_mm"], data.stair_width_mm)
        if data.stair_type == StairType.LANDING and landing_length_used < min_landing:
            geometry_checks.append(
                f"Podestlaenge zu klein ({landing_length_used:.0f} < {min_landing:.0f} mm)"
            )
    if data.stair_type == StairType.LANDING and landing_width_used < data.stair_width_mm:
        geometry_checks.append(
            f"Podestbreite kleiner als Treppenbreite ({landing_width_used:.0f} < {data.stair_width_mm:.0f} mm)"
        )

    if stair_angle_deg < 20.0 or stair_angle_deg > 50.0:
        plausibility_checks.append(
            f"Treppenwinkel untypisch ({stair_angle_deg:.1f}\u00b0 ausserhalb 20\u00b0..50\u00b0)"
        )
    if data.floor_height_mm > 4500.0:
        plausibility_checks.append("Geschosshoehe sehr hoch - Sondernachweis empfohlen")
    if data.stair_width_mm > 1600.0:
        plausibility_checks.append("Treppenbreite sehr gross - zusaetzliche Wange pruefen")
    if run > data.available_run_mm:
        collisions.append(
            f"Kollision: benoetigter horizontaler Platz {run:.0f} mm > verfuegbar {data.available_run_mm:.0f} mm"
        )

    geometry_ok = len(geometry_checks) == 0 and len(collisions) == 0
    return {
        "geometry_checks": geometry_checks,
        "plausibility_checks": plausibility_checks,
        "collisions": collisions,
        "geometry_ok": geometry_ok,
    }
