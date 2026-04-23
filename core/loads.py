"""Ersatzlasten (EC3-Vorplanung) fuer den Rechenweg."""

from __future__ import annotations

import logging

from norms import NORM_CONFIG_DE

from core.models import StairInput

log = logging.getLogger(__name__)


def _compute_loads(
    data: StairInput, geo: dict, profile_kg_per_m: float, tread_kg_per_m2: float,
) -> dict:
    run_m = max(geo["run"] / 1000.0, 0.001)
    width_m = data.stair_width_mm / 1000.0
    span_m = geo["governing_span_mm"] / 1000.0
    tributary_width_m = width_m / 2.0
    incline_factor = run_m / max(geo["stringer_length"] / 1000.0, 0.001)

    gk_treads_kN_m2 = tread_kg_per_m2 * 9.81 / 1000.0
    qk_live_kN_m2 = data.live_load_kN_m2
    gk_stringer_kN_m = profile_kg_per_m * 9.81 / 1000.0

    gk_line_kN_m = gk_treads_kN_m2 * tributary_width_m * incline_factor + gk_stringer_kN_m
    qk_line_kN_m = qk_live_kN_m2 * tributary_width_m * incline_factor

    gamma_g = float(NORM_CONFIG_DE["uls_factors"]["gamma_g"])
    gamma_q = float(NORM_CONFIG_DE["uls_factors"]["gamma_q"])
    design_line_load = gamma_g * gk_line_kN_m + gamma_q * qk_line_kN_m
    service_line_load = gk_line_kN_m + qk_line_kN_m

    log.debug(
        "Lasten: q_d=%.3f kN/m, q_sls=%.3f kN/m, span=%.3f m",
        design_line_load, service_line_load, span_m,
    )

    return {
        "design_line_load": design_line_load,
        "service_line_load": service_line_load,
        "span_m": span_m,
        "gk_line_kN_m": gk_line_kN_m,
        "qk_line_kN_m": qk_line_kN_m,
    }
