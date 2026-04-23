"""Export: PDF-Berechnungsbericht, BOM-CSV, Changelog."""

import csv
import logging
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from calculations import BomItem, StairInput, StairResult
from enums import __version__
from norms import NORM_CONFIG_DE

log = logging.getLogger(__name__)

MARGIN_TOP = 50
MARGIN_BOTTOM = 60


def export_bom_csv(path: str | Path, bom_items: list[BomItem]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile, delimiter=";")
        writer.writerow(
            [
                "Pos",
                "Bauteil",
                "Material",
                "Menge",
                "Einheit",
                "Einzelgewicht [kg]",
                "Gesamtgewicht [kg]",
                "Hinweis",
            ]
        )
        for item in bom_items:
            writer.writerow(
                [
                    item.position,
                    item.item,
                    item.material,
                    f"{item.quantity:.3f}",
                    item.unit,
                    f"{item.unit_weight_kg:.3f}",
                    f"{item.total_weight_kg:.3f}",
                    item.note,
                ]
            )
    log.info("BOM CSV geschrieben: %s (%d Positionen)", path, len(bom_items))


def export_report_pdf(
    path: str | Path,
    data: StairInput,
    result: StairResult,
    bom_items: list[BomItem],
) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    _width, height = A4
    y = height - MARGIN_TOP
    current_font_name = "Helvetica"
    current_font_size = 10

    def _set_font(name: str, size: int) -> None:
        nonlocal current_font_name, current_font_size
        current_font_name = name
        current_font_size = size
        c.setFont(name, size)

    def line(text: str, step: int = 18) -> None:
        nonlocal y
        if y - step < MARGIN_BOTTOM:
            c.showPage()
            c.setFont(current_font_name, current_font_size)
            y = height - MARGIN_TOP
        c.drawString(50, y, text)
        y -= step

    _set_font("Helvetica-Bold", 16)
    line("OpenStair - Treppenbericht", 24)
    _set_font("Helvetica", 10)
    line(f"Version: {__version__}", 14)
    line("Normbasis: " + NORM_CONFIG_DE["standard_set"]["basis"], 14)
    line("Nationaler Anhang: " + data.national_annex, 14)
    line("Zusatzregelwerk: " + data.regulation_profile, 14)
    line("Hinweis: Phase-0 DIN-EN-MVP, kein Ersatz fuer Pruefstatik/Pruefingenieur.", 20)

    _set_font("Helvetica-Bold", 12)
    line("Eingaben", 18)
    _set_font("Helvetica", 10)
    line(f"Geschosshoehe: {data.floor_height_mm:.1f} mm")
    line(f"Auftritt: {data.going_mm:.1f} mm")
    line(f"Treppenbreite: {data.stair_width_mm:.1f} mm")
    line(f"Verfuegbarer Platz: {data.available_run_mm:.1f} mm")
    line(f"Treppentyp: {result.stair_type}")
    line(f"Richtung/Orientierung: {result.stair_direction} / {result.stair_orientation}")
    line(f"Lagerung je Wange: {result.bearing_condition}")
    line(f"Wangenprofil: {data.stringer_profile_name}")
    line(f"Stahlguete: {result.steel_grade}")
    line(f"Stufentyp: {data.tread_type_name}")
    line(f"Nutzlast: {data.live_load_kN_m2:.2f} kN/m2")
    line(f"Normprofil: {result.norm_profile}")
    line(f"Stahlguete fy: {data.steel_yield_mpa:.1f} MPa", 20)
    line(f"Kopffreiheit: {data.headroom_clear_mm:.1f} mm")
    line(f"Podestlaenge/-breite: {data.landing_length_mm:.1f}/{data.landing_width_mm:.1f} mm")
    line(f"Podestlage: {data.landing_position}")
    line(f"Normalkraft N_Ed: {data.axial_force_kN:.2f} kN", 20)
    line(
        f"Handlauf: {'ja' if data.handrail_enabled else 'nein'} | "
        f"Seiten: {data.handrail_sides}"
    )
    line(
        f"Stuetzen: {'ja' if data.supports_enabled else 'nein'} | "
        f"Anzahlvorgabe: {data.support_count}",
        20,
    )

    _set_font("Helvetica-Bold", 12)
    line("Annahmen", 18)
    _set_font("Helvetica", 9)
    line("Tragwerksmodell: Einfeldtraeger je Wange (Biegebalken auf zwei Stuetzen)")
    line("Lasteinzugsbreite: halbe Treppenbreite je Wange")
    line("Neigungsfaktor: horizontale Projektion / Wangenlaenge")
    line("Eigengewicht: aus Profil (kg/m) + Stufenbelag (kg/m2 x Einzugsbreite)")
    line("Anschluss: vereinfachte Pressung + Schraubenschub + Kehlnaht", 20)

    _set_font("Helvetica-Bold", 12)
    line("Nachweise ULS/SLS", 18)
    _set_font("Helvetica", 10)
    line(f"Steigungen/Stufen: {result.riser_count}/{result.tread_count}")
    line(f"Steigungshoehe: {result.riser_height_mm:.1f} mm")
    line(f"Treppenwinkel: {result.stair_angle_deg:.1f}\u00b0")
    line(f"Wangenlaenge: {result.stringer_length_mm:.1f} mm")
    line(
        f"Lauflaengen F1/F2/Podest: {result.run_flight_1_mm:.1f}/"
        f"{result.run_flight_2_mm:.1f}/{result.landing_length_used_mm:.1f} mm"
    )
    line(f"Podestflaeche: {result.landing_area_m2:.2f} m2")
    line(
        f"Feldlaengen: {', '.join(f'{v:.1f}' for v in result.span_lengths_mm)} mm "
        f"(massgebend {result.governing_span_mm:.1f} mm)"
    )
    line(f"Stahl gesamt (ca.): {result.approx_total_kg:.1f} kg")
    line(f"Handlauflaenge/Gewicht: {result.handrail_length_m:.2f} m / {result.approx_handrail_kg:.1f} kg")
    line(
        f"Stuetzen Anzahl/Gewicht/Layout: {result.support_count} / "
        f"{result.approx_supports_kg:.1f} kg / {result.support_layout}"
    )
    line(f"M_Ed je Wange: {result.m_ed_kNm:.2f} kNm")
    line(f"sigma_Ed: {result.sigma_ed_mpa:.1f} MPa")
    line(f"Ausnutzung Biegung: {result.utilization_bending:.2f}")
    line(
        f"N_Ed/N_pl,Rd: {result.n_ed_kN:.2f}/{result.n_pl_rd_kN:.2f} kN "
        f"(eta_NM={result.utilization_interaction:.2f})"
    )
    line(f"V_Ed je Wange: {result.v_ed_kN:.2f} kN")
    line(
        f"tau_Ed/tau_Rd: {result.tau_ed_mpa:.2f}/{result.tau_rd_mpa:.2f} MPa "
        f"(eta={result.utilization_shear:.2f})"
    )
    line(
        f"Stabilitaet/Knick: chi={result.buckling_chi:.2f} | "
        f"N_b,Rd={result.n_b_rd_kN:.2f} kN (eta={result.utilization_buckling:.2f})"
    )
    line(
        f"Biegedrillknicken: chi_LT={result.ltb_chi:.2f} | "
        f"M_b,Rd={result.m_b_rd_kNm:.2f} kNm (eta={result.utilization_ltb:.2f})"
    )
    line(
        f"Durchbiegung: {result.deflection_mm:.1f} / {result.deflection_limit_mm:.1f} mm "
        f"(eta={result.utilization_deflection:.2f})"
    )
    line(
        f"Schwingung: f1={result.natural_frequency_hz:.2f} Hz "
        f"(Mindestwert {NORM_CONFIG_DE['serviceability']['min_frequency_hz']:.1f} Hz) "
        f"{'OK' if result.vibration_ok else 'NICHT OK'}"
    )
    line(
        f"Anschluss Platte: sigma={result.plate_bearing_stress_mpa:.2f}/{result.plate_bearing_rd_mpa:.2f} MPa "
        f"(eta={result.utilization_plate:.2f})"
    )
    line(
        f"Anschluss Schrauben/Naht: eta_bolt={result.bolt_utilization:.2f} | "
        f"eta_weld={result.weld_utilization:.2f} | "
        f"{'OK' if result.connections_ok else 'NICHT OK'}"
    )
    line(f"Breitencheck Stufe: {'OK' if result.tread_ok_for_width else 'NICHT OK'}")
    line(
        f"Stufen-Empfehlung: {result.recommended_tread_type or 'keine Aenderung noetig'}",
        20,
    )

    _set_font("Helvetica-Bold", 12)
    line("Formeln und Grenzwerte", 18)
    _set_font("Helvetica", 9)
    line("ULS Lastkombination: q_d = gamma_G * g_k + gamma_Q * q_k  (EC0 Gl. 6.10)")
    line("Biegung: M_Ed = q_d * L^2 / c_M ; sigma_Ed = M_Ed / W_el  (EC3 §6.2.5)")
    line("Interaktion: eta_NM = N_Ed/N_pl,Rd + M_Ed/M_Rd  (EC3 §6.2.9, konservativ)")
    line("Querkraft: V_Ed = q_d * L / c_V ; tau_Ed = V_Ed / A_v ; tau_Rd = fy/(sqrt(3)*gamma_M0)  (EC3 §6.2.6)")
    line("Stabilitaet: N_b,Rd = chi * A * fy / gamma_M1 mit l_cr = beta * L  (EC3 §6.3.1)")
    line("Biegedrillknicken: M_b,Rd = chi_LT * W_el * fy / gamma_M1  (EC3 §6.3.2)")
    line("SLS Durchbiegung: w = c_w * q_sls * L^4 / (E*I) ; Grenzwert L/300  (EC3 §7.2)")
    line("SLS Schwingung: f_n = sqrt(lambda_n * E*I / (m*L^4))  (lagerungsabh.)  (EC3 §7.2.3)", 20)

    _set_font("Helvetica-Bold", 12)
    line("Geometrie und Phase-0 Gate", 18)
    _set_font("Helvetica", 9)
    line(f"Geometriecheck: {'OK' if result.geometry_ok else 'NICHT OK'}")
    if not result.geometry_ok:
        for msg in result.geometry_checks:
            line(f"- {msg}", 14)
    line(f"Phase-0-Gate: {'FREIGEGEBEN' if result.phase0_gate_ok else 'NICHT FREIGEGEBEN'}")
    if not result.phase0_gate_ok:
        for reason in result.phase0_gate_reasons:
            line(f"- {reason}", 14)
    if result.plausibility_checks:
        line("Plausibilitaetshinweise:", 16)
        for msg in result.plausibility_checks:
            line(f"- {msg}", 14)
    if result.collisions:
        line("Kollisionshinweise:", 16)
        for msg in result.collisions:
            line(f"- {msg}", 14)
    y -= 8

    _set_font("Helvetica-Bold", 12)
    line("BOM / Stueckliste", 18)
    _set_font("Helvetica", 9)
    for item in bom_items:
        line(
            f"{item.position}. {item.item} | {item.quantity:.2f} {item.unit} | "
            f"{item.total_weight_kg:.2f} kg"
        )
        if item.note:
            line(f"    Hinweis: {item.note}", 14)

    total_bom_weight = sum(item.total_weight_kg for item in bom_items)
    line(f"Gesamtgewicht BOM: {total_bom_weight:.2f} kg", 20)
    line(f"Erstellt mit OpenStair v{__version__}")

    c.save()
    log.info("PDF Bericht geschrieben: %s", path)


def append_release_changelog(
    path: str | Path,
    data: StairInput,
    result: StairResult,
) -> None:
    changelog_path = Path(path)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    status = "FREIGEGEBEN" if result.phase0_gate_ok else "NICHT FREIGEGEBEN"

    header = "# Changelog\n\n"
    if not changelog_path.exists():
        changelog_path.write_text(header, encoding="utf-8")

    entry_lines = [
        f"## {timestamp} - QA Export Snapshot (v{__version__})",
        "",
        f"- Normbasis: {NORM_CONFIG_DE['standard_set']['basis']}",
        f"- Nationaler Anhang: {data.national_annex}",
        f"- Zusatzregelwerk: {data.regulation_profile}",
        f"- Normprofil: {result.norm_profile}",
        f"- Lastkategorie/Last: {data.live_load_kN_m2:.2f} kN/m2",
        f"- Profil/Stufe: {result.selected_profile} / {result.selected_tread_type}",
        f"- Handlauf/Stuetzen: {result.handrail_length_m:.2f} m / {result.support_count} Stk",
        f"- Treppentyp/Lagerung/Stahl: {result.stair_type} / {result.bearing_condition} / {result.steel_grade}",
        f"- Richtung/Orientierung: {result.stair_direction} / {result.stair_orientation}",
        f"- Podest LxB/Flaeche: {result.landing_length_used_mm:.0f}x{result.landing_width_used_mm:.0f} mm / {result.landing_area_m2:.2f} m2",
        f"- ULS: eta_b={result.utilization_bending:.2f}, eta_v={result.utilization_shear:.2f}, "
        f"eta_NM={result.utilization_interaction:.2f}, eta_knick={result.utilization_buckling:.2f}, "
        f"eta_ltb={result.utilization_ltb:.2f}",
        f"- SLS: eta_f={result.utilization_deflection:.2f}, f1={result.natural_frequency_hz:.2f} Hz",
        f"- Anschluss: eta_pl={result.utilization_plate:.2f}, "
        f"eta_bolt={result.bolt_utilization:.2f}, eta_weld={result.weld_utilization:.2f}",
        f"- Geometrie OK: {'ja' if result.geometry_ok else 'nein'}",
        f"- Phase-0 Gate: {status}",
    ]

    if not result.phase0_gate_ok and result.phase0_gate_reasons:
        entry_lines.append(
            "- Gruende: " + "; ".join(result.phase0_gate_reasons)
        )

    entry_lines.append("")
    entry_lines.append("")

    with changelog_path.open("a", encoding="utf-8") as f:
        f.write("\n".join(entry_lines))
