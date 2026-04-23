"""DXF-Export: Seitenansicht + Grundriss mit echten DIMENSION-Entities wo moeglich."""

import logging
from pathlib import Path

import ezdxf

from core.models import StairInput, StairResult
from enums import StairDirection, StairType
from export.dxf.settings import DxfExportSettings
from norms import NORM_CONFIG_DE

log = logging.getLogger(__name__)


def _add_rect(msp, x: float, y: float, w: float, h: float, layer: str) -> None:
    msp.add_lwpolyline(
        [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)],
        dxfattribs={"layer": layer},
    )


def _add_plan_view(
    msp,
    data: StairInput,
    result: StairResult,
    y_offset: float,
    s: DxfExportSettings,
) -> None:
    width = data.stair_width_mm
    run1 = result.run_flight_1_mm
    run2 = result.run_flight_2_mm
    landing = max(result.landing_length_used_mm, width)
    gap = s.plan_gap_mm
    dir_sign = -1.0 if result.stair_direction == StairDirection.LEFT else 1.0
    y_base = y_offset if dir_sign > 0 else y_offset - width
    layer = s.layer_geometry
    lay_notes = s.layer_notes
    lay_dim = s.layer_dimensions
    ht_p = s.text_height_plan_title

    msp.add_text(
        f"GRUNDRISS - {result.stair_type}",
        dxfattribs={"height": ht_p, "layer": lay_notes},
    ).set_placement((0, y_offset + width + 180))

    if result.stair_type == StairType.STRAIGHT:
        _add_rect(msp, 0, y_base, result.run_mm, width, layer)
    elif result.stair_type == StairType.LANDING:
        landing_w = max(result.landing_width_used_mm, width)
        _add_rect(msp, 0, y_base, run1, width, layer)
        _add_rect(msp, run1, y_base, landing, landing_w, layer)
        _add_rect(
            msp,
            run1 + landing - run2,
            y_base + dir_sign * (width + gap),
            run2,
            width,
            layer,
        )
        msp.add_line(
            (run1 + landing, y_base + dir_sign * width),
            (run1 + landing, y_base + dir_sign * (width + gap)),
            dxfattribs={"layer": lay_dim},
        )
    elif result.stair_type == StairType.QUARTER:
        turn_x = run1 * 0.55
        _add_rect(msp, 0, y_base, turn_x, width, layer)
        _add_rect(
            msp,
            turn_x - width,
            y_base + dir_sign * width,
            width,
            max(run1 - turn_x, width),
            layer,
        )
    else:
        half = max(run1 / 2.0, width)
        _add_rect(msp, 0, y_base, half, width, layer)
        _add_rect(msp, 0, y_base + dir_sign * (width + gap), half, width, layer)
        msp.add_line(
            (half, y_base + dir_sign * width),
            (half, y_base + dir_sign * (width + gap)),
            dxfattribs={"layer": lay_dim},
        )

    if data.supports_enabled and result.support_count > 0:
        spacing = max(result.run_mm / max(result.support_count - 1, 1), 1.0)
        for i in range(result.support_count):
            x = min(i * spacing, result.run_mm)
            y = y_base + (width * 0.5)
            msp.add_circle((x, y), radius=45, dxfattribs={"layer": lay_dim})

    msp.add_text(
        (
            f"B = {width:.0f} mm | Run gesamt = {result.run_mm:.0f} mm | "
            f"Richtung {result.stair_direction} | Orientierung {result.stair_orientation}"
        ),
        dxfattribs={"height": s.text_height_dimensions, "layer": lay_dim},
    ).set_placement((0, y_base - 70))


def _setup_dim_style(doc) -> str:
    """Einheitlicher Bemasssungsstil fuer alle DIMENSION-Entities."""
    style_name = "OPENSTAIR"
    if style_name not in doc.dimstyles:
        ds = doc.dimstyles.new(style_name)
        ds.dxf.dimtxt = 25.0
        ds.dxf.dimasz = 18.0
        ds.dxf.dimexe = 8.0
        ds.dxf.dimexo = 6.0
        ds.dxf.dimgap = 6.0
        ds.dxf.dimlfac = 1.0
        ds.dxf.dimdec = 0
    return style_name


def export_stair_side_view_dxf(
    path: str | Path,
    data: StairInput,
    result: StairResult,
    settings: DxfExportSettings | None = None,
) -> None:
    s = settings if settings is not None else DxfExportSettings()
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    def _layer(name: str, color: int) -> str:
        if name not in doc.layers:
            doc.layers.add(name, color=color)
        return name

    lg = _layer(s.layer_geometry, 7)
    ld = _layer(s.layer_dimensions, 3)
    ln = _layer(s.layer_notes, 2)
    if s.include_empty_axes_layer:
        _layer(s.layer_axes, 1)
    if s.include_empty_weld_layer:
        _layer(s.layer_weld, 6)
    th_dim = s.text_height_dimensions
    th_notes = s.text_height_notes
    dim_style = _setup_dim_style(doc)

    rise = result.riser_height_mm
    going = data.going_mm
    treads = result.tread_count
    floor_height = data.floor_height_mm

    msp.add_line((0, 0), (result.run_mm, floor_height), dxfattribs={"layer": lg})

    points = [(0, 0)]
    x = 0.0
    y = 0.0
    for _ in range(treads):
        y += rise
        points.append((x, y))
        x += going
        points.append((x, y))
    msp.add_lwpolyline(points, dxfattribs={"layer": lg})

    msp.add_line((-400, 0), (0, 0), dxfattribs={"layer": lg})
    msp.add_line(
        (result.run_mm, floor_height),
        (result.run_mm + 400, floor_height),
        dxfattribs={"layer": lg},
    )

    # --- Echte DIMENSION-Entities ---
    dim_y_base = -350

    msp.add_linear_dim(
        base=(0, dim_y_base),
        p1=(0, 0),
        p2=(result.run_mm, 0),
        dimstyle=dim_style,
        override={"dimtxt": th_dim * 0.7},
        dxfattribs={"layer": ld},
    ).render()

    dim_x_offset = result.run_mm + 350
    msp.add_linear_dim(
        base=(dim_x_offset, 0),
        p1=(result.run_mm, 0),
        p2=(result.run_mm, floor_height),
        angle=90,
        dimstyle=dim_style,
        override={"dimtxt": th_dim * 0.7},
        dxfattribs={"layer": ld},
    ).render()

    # Erstes Stufenmaß (Hoehe) — Massketten-Start, weitere Stufen folgen spaeter
    msp.add_linear_dim(
        base=(-90.0, rise * 0.5),
        p1=(0.0, 0.0),
        p2=(0.0, rise),
        angle=90.0,
        dimstyle=dim_style,
        override={"dimtxt": th_dim * 0.55},
        dxfattribs={"layer": ld},
    ).render()

    # --- Ergaenzende Textnotizen ---
    text_y = dim_y_base - 80
    msp.add_text(
        (
            f"Typ: {result.stair_type} | F1/F2/Podest: "
            f"{result.run_flight_1_mm:.0f}/{result.run_flight_2_mm:.0f}/{result.landing_length_used_mm:.0f} mm"
        ),
        dxfattribs={"height": th_dim, "layer": ld},
    ).set_placement((0, text_y))
    msp.add_text(
        (
            f"Lagerung: {result.bearing_condition} | Stahl: {result.steel_grade} | "
            f"Winkel: {result.stair_angle_deg:.1f} deg | Normprofil: {result.norm_profile}"
        ),
        dxfattribs={"height": th_dim, "layer": ld},
    ).set_placement((0, text_y - 45))

    gr = NORM_CONFIG_DE["geometry_rules"]
    step_target = float(gr["step_rule_target_mm"])
    step_tol = float(gr["step_rule_tolerance_mm"])
    step_2h_a = 2.0 * rise + going
    msp.add_text(
        (
            f"Schrittmass 2h+a = {step_2h_a:.1f} mm "
            f"(Ziel {step_target:.0f} +/- {step_tol:.0f} mm, Quelle: norms.NORM_CONFIG_DE)"
        ),
        dxfattribs={"height": th_notes * 0.95, "layer": ln},
    ).set_placement((0, floor_height + 200))
    msp.add_text(
        (
            f"Stufen n={treads} | Steigung h={rise:.1f} mm | Auftritt a={going:.1f} mm | "
            f"Winkel ~{result.stair_angle_deg:.1f} deg"
        ),
        dxfattribs={"height": th_notes, "layer": ln},
    ).set_placement((0, floor_height + 130))

    msp.add_text(
        (
            f"Profil: {result.selected_profile} | Stufentyp: {result.selected_tread_type} | "
            f"Wangenlaenge: {result.stringer_length_mm:.1f} mm "
            f"| Stahl geschaetzt: {result.approx_total_kg:.1f} kg"
        ),
        dxfattribs={"height": th_notes, "layer": ln},
    ).set_placement((0, floor_height + 260))

    msp.add_text(
        (
            f"M_Ed: {result.m_ed_kNm:.2f} kNm | sigma_Ed: {result.sigma_ed_mpa:.1f} MPa | "
            f"eta_b: {result.utilization_bending:.2f} | eta_v: {result.utilization_shear:.2f} | "
            f"eta_ltb: {result.utilization_ltb:.2f} | eta_f: {result.utilization_deflection:.2f} | "
            f"Check: {'OK' if result.checks_ok else 'NICHT OK'}"
        ),
        dxfattribs={"height": th_dim, "layer": ln},
    ).set_placement((0, floor_height + 340))

    recommendation = (
        result.recommended_tread_type
        if result.recommended_tread_type is not None
        else "keine Aenderung noetig"
    )
    msp.add_text(
        (
            f"Stufencheck: {'OK' if result.tread_ok_for_width else 'NICHT OK'} | "
            f"zulaessige Breite: {result.tread_allowable_width_mm:.0f} mm | "
            f"Empfehlung: {recommendation} | "
            f"Phase-0: {'FREIGEGEBEN' if result.phase0_gate_ok else 'NICHT FREIGEGEBEN'}"
        ),
        dxfattribs={"height": th_dim, "layer": ln},
    ).set_placement((0, floor_height + 420))

    msp.add_text(
        (
            f"Kopffreiheit: {data.headroom_clear_mm:.0f} mm | "
            f"Podest LxB/Flaeche: {result.landing_length_used_mm:.0f}x{result.landing_width_used_mm:.0f} mm/"
            f"{result.landing_area_m2:.2f} m2 | "
            f"Anschluss eta_pl/eta_b/eta_w: {result.utilization_plate:.2f}/"
            f"{result.bolt_utilization:.2f}/{result.weld_utilization:.2f}"
        ),
        dxfattribs={"height": th_dim, "layer": ln},
    ).set_placement((0, floor_height + 500))
    msp.add_text(
        (
            f"Handlauf: {result.handrail_length_m:.2f} m / {result.approx_handrail_kg:.1f} kg | "
            f"Stuetzen: {result.support_count} Stk / {result.approx_supports_kg:.1f} kg"
        ),
        dxfattribs={"height": th_dim, "layer": ln},
    ).set_placement((0, floor_height + 580))

    if s.include_plan_view:
        plan_offset_y = -(data.stair_width_mm * 3.5 + 1500.0)
        _add_plan_view(msp, data, result, plan_offset_y, s)

    doc.saveas(str(path))
    log.info("DXF geschrieben: %s", path)
