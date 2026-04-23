"""ULS, SLS, Anschluesse und Phase-0-Gate."""

from __future__ import annotations

import logging
from math import pi, sqrt

from norms import NORM_CONFIG_DE

from core.models import StairInput

log = logging.getLogger(__name__)


def _check_uls(
    data: StairInput,
    loads: dict,
    bearing_data: dict,
    profile: dict,
    fy_mpa: float,
    e_mpa: float,
    area_mm2: float,
    w_el_mm3: float,
    i_mm4: float,
) -> dict:
    gamma_m0 = float(NORM_CONFIG_DE["material_factors"]["gamma_m0"])
    gamma_m1 = float(NORM_CONFIG_DE["material_factors"]["gamma_m1"])
    sigma_rd = fy_mpa / gamma_m0
    span_m = loads["span_m"]
    design_line_load = loads["design_line_load"]

    moment_factor = float(bearing_data["moment_factor"])
    shear_factor = float(bearing_data["shear_factor"])
    m_ed = design_line_load * (span_m**2) / moment_factor
    v_ed = design_line_load * span_m / shear_factor

    sigma_ed = (m_ed * 1_000_000.0) / w_el_mm3
    utilization_bending = sigma_ed / max(sigma_rd, 1e-9)

    n_ed = max(data.axial_force_kN, 0.0)
    n_pl_rd = (area_mm2 * sigma_rd) / 1000.0
    m_rd = (w_el_mm3 * sigma_rd) / 1_000_000.0
    utilization_interaction = (n_ed / max(n_pl_rd, 1e-9)) + (m_ed / max(m_rd, 1e-9))

    if "a_v_cm2" in profile:
        a_v_mm2 = float(profile["a_v_cm2"]) * 100.0
    else:
        a_v_mm2 = max(w_el_mm3 / 100.0, 1.0)
        log.warning("Profil ohne a_v_cm2 – Naeherung W_el/100 verwendet")
    tau_ed = (v_ed * 1000.0) / a_v_mm2
    tau_rd = sigma_rd / sqrt(3.0)
    utilization_shear = tau_ed / max(tau_rd, 1e-9)

    l_mm = span_m * 1000.0
    beta = float(bearing_data["buckling_length_factor"])
    l_cr_mm = beta * l_mm
    i_radius_mm = sqrt(i_mm4 / max(area_mm2, 1e-9))
    lambda_bar = (l_cr_mm / max(i_radius_mm, 1e-9)) * sqrt(sigma_rd / (pi**2 * e_mpa))
    alpha_imperfection = 0.21
    phi = 0.5 * (1.0 + alpha_imperfection * (lambda_bar - 0.2) + lambda_bar**2)
    buckling_chi = 1.0 / (phi + sqrt(max(phi**2 - lambda_bar**2, 0.0)))
    buckling_chi = min(max(buckling_chi, 0.0), 1.0)
    n_b_rd = buckling_chi * n_pl_rd
    utilization_buckling = n_ed / max(n_b_rd, 1e-9)

    h_mm = float(profile.get("height_mm", 160.0))
    b_mm = float(profile.get("width_mm", 120.0))
    ratio_hb = h_mm / max(b_mm, 1.0)
    lambda_lt = lambda_bar * sqrt(ratio_hb) * 0.9
    alpha_lt = 0.34 if ratio_hb <= 2.0 else 0.49
    phi_lt = 0.5 * (1.0 + alpha_lt * (lambda_lt - 0.2) + lambda_lt**2)
    ltb_chi = 1.0 / (phi_lt + sqrt(max(phi_lt**2 - lambda_lt**2, 0.0)))
    ltb_chi = min(max(ltb_chi, 0.0), 1.0)
    m_b_rd = ltb_chi * m_rd / gamma_m1
    utilization_ltb = m_ed / max(m_b_rd, 1e-9)

    log.debug(
        "ULS: eta_b=%.3f, eta_v=%.3f, eta_NM=%.3f, eta_knick=%.3f, eta_ltb=%.3f",
        utilization_bending, utilization_shear, utilization_interaction,
        utilization_buckling, utilization_ltb,
    )

    return {
        "m_ed": m_ed,
        "v_ed": v_ed,
        "sigma_ed": sigma_ed,
        "utilization_bending": utilization_bending,
        "n_ed": n_ed,
        "n_pl_rd": n_pl_rd,
        "utilization_interaction": utilization_interaction,
        "tau_ed": tau_ed,
        "tau_rd": tau_rd,
        "utilization_shear": utilization_shear,
        "buckling_chi": buckling_chi,
        "n_b_rd": n_b_rd,
        "utilization_buckling": utilization_buckling,
        "ltb_chi": ltb_chi,
        "m_b_rd": m_b_rd,
        "utilization_ltb": utilization_ltb,
    }


def _check_sls(loads: dict, bearing_data: dict, e_mpa: float, i_mm4: float) -> dict:
    span_m = loads["span_m"]
    l_mm = span_m * 1000.0
    deflection_factor = float(bearing_data["deflection_factor"])
    vibration_coeff = float(bearing_data["vibration_coeff"])

    q_sls_N_per_mm = loads["service_line_load"]
    deflection = deflection_factor * q_sls_N_per_mm * (l_mm**4) / (e_mpa * i_mm4)

    deflection_ratio = float(NORM_CONFIG_DE["serviceability"]["deflection_limit_ratio"])
    deflection_limit = l_mm / deflection_ratio
    utilization_deflection = deflection / max(deflection_limit, 1e-9)

    mass_line_kg_m = (loads["gk_line_kN_m"] + 0.1 * loads["qk_line_kN_m"]) * 1000.0 / 9.81
    e_n_m2 = e_mpa * 1e6
    i_m4 = i_mm4 * 1e-12
    natural_frequency = sqrt(vibration_coeff * (e_n_m2 * i_m4) / (mass_line_kg_m * (span_m**4)))
    min_frequency = float(NORM_CONFIG_DE["serviceability"]["min_frequency_hz"])
    vibration_ok = natural_frequency >= min_frequency

    log.debug(
        "SLS: w=%.2f/%.2f mm (eta=%.3f), f1=%.2f Hz (%s)",
        deflection, deflection_limit, utilization_deflection,
        natural_frequency, "OK" if vibration_ok else "NICHT OK",
    )

    return {
        "deflection": deflection,
        "deflection_limit": deflection_limit,
        "utilization_deflection": utilization_deflection,
        "natural_frequency": natural_frequency,
        "vibration_ok": vibration_ok,
    }


def _check_connections(data: StairInput, v_ed: float, sigma_rd: float) -> dict:
    conn_cfg = NORM_CONFIG_DE["connections"]
    plate_width = data.plate_width_mm if data.plate_width_mm > 0 else float(conn_cfg["default_plate_width_mm"])
    plate_height = data.plate_height_mm if data.plate_height_mm > 0 else float(conn_cfg["default_plate_height_mm"])
    bolts_per_support = data.bolts_per_support if data.bolts_per_support > 0 else int(conn_cfg["default_bolts_per_support"])
    bolt_shear_rd = data.bolt_shear_rd_kN if data.bolt_shear_rd_kN > 0 else float(conn_cfg["bolt_shear_rd_kN_m12_88"])

    reaction_kN = v_ed
    plate_area_mm2 = plate_width * plate_height
    plate_bearing_stress = (reaction_kN * 1000.0) / plate_area_mm2
    plate_bearing_rd = 0.6 * sigma_rd
    utilization_plate = plate_bearing_stress / max(plate_bearing_rd, 1e-9)
    bolt_utilization = reaction_kN / max(bolts_per_support * bolt_shear_rd, 1e-9)

    gamma_m2 = float(NORM_CONFIG_DE["material_factors"]["gamma_m2"])
    weld_rd_per_mm_kN = (0.42 * sigma_rd * data.weld_throat_mm) / (gamma_m2 * 1000.0)
    weld_length_mm = data.weld_length_mm if data.weld_length_mm > 0 else 2.0 * (plate_width + plate_height)
    weld_utilization = reaction_kN / max(weld_rd_per_mm_kN * weld_length_mm, 1e-9)
    connections_ok = utilization_plate <= 1.0 and bolt_utilization <= 1.0 and weld_utilization <= 1.0

    return {
        "plate_bearing_stress": plate_bearing_stress,
        "plate_bearing_rd": plate_bearing_rd,
        "utilization_plate": utilization_plate,
        "bolt_utilization": bolt_utilization,
        "weld_utilization": weld_utilization,
        "connections_ok": connections_ok,
    }


def _check_phase0_gate(
    geometry_ok: bool,
    uls: dict,
    sls: dict,
    tread_ok_for_width: bool,
    connections_ok: bool,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not geometry_ok:
        reasons.append("Geometrie/Kollision nicht erfuellt")
    if uls["utilization_bending"] > 1.0:
        reasons.append("ULS Biegung nicht erfuellt")
    if uls["utilization_interaction"] > 1.0:
        reasons.append("ULS Interaktion N+M nicht erfuellt")
    if uls["utilization_shear"] > 1.0:
        reasons.append("ULS Querkraft nicht erfuellt")
    if uls["utilization_buckling"] > 1.0:
        reasons.append("ULS Stabilitaet/Knick nicht erfuellt")
    if uls["utilization_ltb"] > 1.0:
        reasons.append("ULS Biegedrillknicken nicht erfuellt")
    if sls["utilization_deflection"] > 1.0:
        reasons.append("SLS Durchbiegung nicht erfuellt")
    if not sls["vibration_ok"]:
        reasons.append("SLS Schwingung/Komfort nicht erfuellt")
    if not tread_ok_for_width:
        reasons.append("Stufen-Breitencheck nicht erfuellt")
    if not connections_ok:
        reasons.append("Anschluss-/Detailnachweise nicht erfuellt")
    return len(reasons) == 0, reasons
