"""Normkonfiguration: DIN EN + Nationaler Anhang, Materialien, Lagerungsfaktoren."""

from enums import BearingCondition, SteelGrade

NORM_CONFIG_DE = {
    "standard_set": {
        "basis": "DIN EN 1990, DIN EN 1991-1-1+NA, DIN EN 1993-1-1+NA, DIN EN 1090",
        "country": "DE",
        "national_annex": "NA Deutschland",
    },
    "uls_factors": {"gamma_g": 1.35, "gamma_q": 1.50},
    "material_factors": {"gamma_m0": 1.0, "gamma_m1": 1.0, "gamma_m2": 1.25},
    "serviceability": {"deflection_limit_ratio": 300.0, "min_frequency_hz": 1.5},
    "geometry_rules": {
        "riser_min_mm": 140.0,
        "riser_max_mm": 190.0,
        "going_min_mm": 230.0,
        "going_max_mm": 320.0,
        "step_rule_target_mm": 630.0,
        "step_rule_tolerance_mm": 30.0,
        "min_clear_width_mm": 800.0,
        "min_headroom_mm": 2000.0,
        "landing_required_height_mm": 3600.0,
        "min_landing_length_mm": 1000.0,
    },
    "live_load_categories_kN_m2": {
        "A_Wohnen": 2.0,
        "C1_Versammlungsflaeche_leicht": 3.0,
        "C3_Versammlungsflaeche": 5.0,
        "T_Treppen_oeffentlich": 5.0,
    },
    "connections": {
        "default_plate_width_mm": 180.0,
        "default_plate_height_mm": 220.0,
        "default_bolts_per_support": 4,
        "bolt_shear_rd_kN_m12_88": 22.0,
    },
}

MATERIAL_LIBRARY: dict[str, dict[str, float]] = {
    SteelGrade.S235: {"fy_mpa": 235.0, "e_mpa": 210000.0, "density_kg_m3": 7850.0},
    SteelGrade.S275: {"fy_mpa": 275.0, "e_mpa": 210000.0, "density_kg_m3": 7850.0},
    SteelGrade.S355: {"fy_mpa": 355.0, "e_mpa": 210000.0, "density_kg_m3": 7850.0},
    SteelGrade.S420: {"fy_mpa": 420.0, "e_mpa": 210000.0, "density_kg_m3": 7850.0},
    SteelGrade.S460: {"fy_mpa": 460.0, "e_mpa": 210000.0, "density_kg_m3": 7850.0},
}

BEARING_LIBRARY: dict[str, dict[str, float]] = {
    BearingCondition.PINNED_PINNED: {
        "moment_factor": 8.0,
        "shear_factor": 2.0,
        "deflection_factor": 5.0 / 384.0,
        "buckling_length_factor": 1.0,
        "vibration_coeff": 9.8696,  # pi^2
    },
    BearingCondition.FIXED_FIXED: {
        "moment_factor": 12.0,
        "shear_factor": 2.0,
        "deflection_factor": 1.0 / 384.0,
        "buckling_length_factor": 0.5,
        "vibration_coeff": 22.3733,  # (4.73)^2
    },
    BearingCondition.FIXED_PINNED: {
        "moment_factor": 10.0,
        "shear_factor": 1.6,
        "deflection_factor": 2.5 / 384.0,
        "buckling_length_factor": 0.7,
        "vibration_coeff": 15.4182,  # (3.927)^2
    },
}
