"""
Treppen-Vorschau: Seitenansicht, Grundriss (wie DXF) und 3D-Isometrie.

Koordinaten: Plan (px, pz) horizontal, py nach oben (3D). Seitenansicht: x horizontal, y vertikal.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QFrame,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from calculations import StairInput, StairResult

BG = QColor(42, 45, 52)
PLAN_LANDING = QColor(100, 140, 180, 120)
PLAN_F1 = QColor(200, 120, 80, 100)
PLAN_F2 = QColor(200, 160, 80, 100)
PLAN_90 = QColor(120, 180, 200, 90)
GAP_PLAN = 250.0


def _plan_x_mirror_uleft(x_left: float, width: float, span: float) -> float:
    """
    Rechte Kante (span) abwickeln: linkes Drittel/Teil erscheint links - ueblich bei
    Mittel-Podest-Grundrissen (Wende links, beide Laeufe parallel rechts).
    """
    return span - x_left - width


def _plan_grating_hint(
    painter: QPainter, to_plan, x: float, z: float, rw: float, rh: float, n: int
) -> None:
    """Leichtes Orthogonalgiter (Rost-Andeutung), sehr dezent."""
    if rw <= 0 or rh <= 0 or n < 2:
        return
    pen = QPen(QColor(255, 255, 255, 38), 0.4)
    painter.setPen(pen)
    for i in range(1, n):
        t = i / n
        painter.drawLine(to_plan(x + t * rw, z), to_plan(x + t * rw, z + rh))
    for j in range(1, n):
        t = j / n
        painter.drawLine(to_plan(x, z + t * rh), to_plan(x + rw, z + t * rh))


def _l_quarter_geometry(
    run1_total: float, stair_width: float, tread_count: int
) -> tuple[float, float, int, int]:
    """
    Viertelgewendelter Grundriss wie dxf_export: turn_x=0,55*run1,
    zweite Lauflaenge max(run1 - turn_x, B). Tritt-Verteilung n1/n2
    im Verhaeltnis der Lauflaengen (Gesamtzahl = `tread_count`).
    """
    b = stair_width
    turn_x = run1_total * 0.55
    r2_leg = max(run1_total - turn_x, b)
    u = turn_x + r2_leg
    if u < 1e-6 or tread_count < 1:
        return turn_x, r2_leg, 1, max(0, tread_count - 1)
    n1 = round(tread_count * (turn_x / u))
    n1 = max(1, min(tread_count, n1))
    n2 = tread_count - n1
    if n2 < 1 and tread_count > 1:
        n1 = tread_count - 1
        n2 = 1
    return turn_x, r2_leg, n1, n2


def _plan_riser_lines(
    painter: QPainter,
    to_plan,
    x0: float,
    z0: float,
    run_len: float,
    width_b: float,
    going_mm: float,
    n_treads: int,
) -> None:
    """Auftritts-/Stufenlinien senkrecht zur Laufrichtung (architektonisch ueblich)."""
    if n_treads < 1 or run_len <= 0 or going_mm <= 0:
        return
    pen = QPen(QColor(55, 62, 78), 1.0, Qt.SolidLine)
    painter.setPen(pen)
    for i in range(1, n_treads):
        xi = x0 + min(i * going_mm, run_len - 0.5)
        if xi >= x0 + run_len - 0.1:
            break
        painter.drawLine(to_plan(xi, z0), to_plan(xi, z0 + width_b))


def _plan_arrow_along(
    painter: QPainter,
    to_plan,
    x0: float,
    z0: float,
    dx: float,
    dz: float,
    center_t: float,
    head_len: float,
) -> None:
    """Steigpfeil in Laufrichtung (t=0..1 entlang Vektor)."""
    sl = math.hypot(dx, dz)
    if sl < 1e-6:
        return
    ux, uz = dx / sl, dz / sl
    cx = x0 + ux * center_t * sl
    cz = z0 + uz * center_t * sl
    tip = to_plan(cx + ux * head_len * 0.35, cz + uz * head_len * 0.35)
    px, pz = -uz, ux
    w = head_len * 0.2
    p1 = to_plan(cx + ux * head_len * 0.1 + px * w, cz + uz * head_len * 0.1 + pz * w)
    p2 = to_plan(cx + ux * head_len * 0.1 - px * w, cz + uz * head_len * 0.1 - pz * w)
    path = QPainterPath()
    path.moveTo(tip)
    path.lineTo(p1)
    path.lineTo(p2)
    path.closeSubpath()
    painter.setPen(QPen(QColor(240, 210, 120), 1.2))
    painter.setBrush(QColor(240, 200, 80, 200))
    painter.drawPath(path)
    painter.setBrush(Qt.NoBrush)


def _plan_riser_lines_along_north(
    painter: QPainter,
    to_plan,
    x0: float,
    z0: float,
    width_x: float,
    run_len_z: float,
    going_mm: float,
    n_treads: int,
) -> None:
    """Stufenlinien bei Lauf in +z (Norden), Linien parallel zur x-Seite des Laufes."""
    if n_treads < 1 or run_len_z <= 0 or going_mm <= 0:
        return
    pen = QPen(QColor(55, 62, 78), 1.0, Qt.SolidLine)
    painter.setPen(pen)
    for i in range(1, n_treads):
        zi = z0 + min(i * going_mm, run_len_z - 0.5)
        painter.drawLine(to_plan(x0, zi), to_plan(x0 + width_x, zi))


def _side_polyline(
    data: StairInput, result: StairResult
) -> tuple[list[tuple[float, float]], str]:
    """2D-Seite (x, y) mit y nach oben in mm. Abwicklung entlang Lauflinie."""
    rise = result.riser_height_mm
    going = data.going_mm
    floor_h = data.floor_height_mm
    treads = result.tread_count
    t1 = treads // 2
    t2 = treads - t1

    if data.stair_type == "Podesttreppe":
        points: list[tuple[float, float]] = [(0.0, 0.0)]
        x, y = 0.0, 0.0
        for _ in range(t1):
            y += rise
            points.append((x, y))
            x += going
            points.append((x, y))
        x_end_land = result.run_flight_1_mm + result.landing_length_used_mm
        points.append((result.run_flight_1_mm, y))
        points.append((x_end_land, y))
        x = x_end_land
        for _ in range(t2):
            y += rise
            points.append((x, y))
            x += going
            points.append((x, y))
        if y < floor_h - 0.1:
            points.append((x, floor_h))
        return points, "podest"

    if data.stair_type == "Viertelgewendelte Treppe (90°)":
        run1 = result.run_flight_1_mm
        b = data.stair_width_mm
        turn_x, r2_leg, n1, n2 = _l_quarter_geometry(run1, b, treads)
        s = 0.0
        yv = 0.0
        g1 = turn_x / max(n1, 1)
        g2 = r2_leg / max(n2, 1) if n2 > 0 else 0.0
        lpts: list[tuple[float, float]] = [(0.0, 0.0)]
        for _ in range(n1):
            yv += rise
            s += g1
            lpts.append((s, yv))
        for _ in range(n2):
            yv += rise
            s += g2
            lpts.append((s, yv))
        if yv < floor_h - 0.1:
            lpts.append((s, floor_h))
        return lpts, "viertel"

    points = [(0.0, 0.0)]
    x, y = 0.0, 0.0
    for _ in range(treads):
        y += rise
        points.append((x, y))
        x += going
        points.append((x, y))
    if y < floor_h - 0.1:
        last_x = x
        points.append((last_x, floor_h))
    return points, "gerade"


def _iso_raw(px: float, py: float, pz: float) -> tuple[float, float]:
    """
    Ebenenkoordinaten vorm Maßstab (s=1). Echte Isometrie: 30° zu den
    waagerechten Achsen, alle drei Raumachsen unverzerrt (uebliche Technik-
    Darstellung).
    """
    c = 0.86602540378  # cos(30°) = sqrt(3)/2
    t = 0.5  # sin(30°)
    xs = (px - pz) * c
    ys = -py * 1.0 + (px + pz) * t
    return xs, ys


def _iso(
    px: float, py: float, pz: float, scale: float, ox: float, oy: float
) -> QPointF:
    """Isometrische Projektion: px Ost, pz Nord, py hoch (mm). -> Bildschirmpixel."""
    xs, ys = _iso_raw(px, py, pz)
    return QPointF(ox + xs * scale, oy + ys * scale)


def _fit_iso_transform(
    points3: list[tuple[float, float, float]], w: float, h: float, margin: float
) -> tuple[float, float, float] | None:
    """Liefert (scale, ox, oy) für _iso()."""
    if not points3 or w < 2 or h < 2:
        return None
    projs = [_iso_raw(a, b, c) for a, b, c in points3]
    min_x = min(t[0] for t in projs)
    max_x = max(t[0] for t in projs)
    min_y = min(t[1] for t in projs)
    max_y = max(t[1] for t in projs)
    rw, rh = max_x - min_x, max_y - min_y
    if rw < 1e-6 or rh < 1e-6:
        return None
    s = min((w - 2 * margin) / rw, (h - 2 * margin) / rh) * 0.95
    eff_w, eff_h = rw * s, rh * s
    ox0 = (w - eff_w) / 2.0 - min_x * s
    oy0 = (h - eff_h) / 2.0 - min_y * s
    return s, ox0, oy0


def _draw_u_podest_steel_isometric(
    p: QPainter,
    to_pt,
    tr: StairResult,
    g: float,
    b: float,
    rise: float,
) -> None:
    """
    U-Podest in technischer Isometrie: Stufentraeger, Stuerze, Podest, Wangenkontur,
    2. Lauf mit Zwischenraum, Eckstuetzen (kein OpenGL).
    """
    r1 = tr.run_flight_1_mm
    r2 = tr.run_flight_2_mm
    land = max(tr.landing_length_used_mm, b)
    t1 = tr.tread_count // 2
    t2 = tr.tread_count - t1
    gap = GAP_PLAN
    y_l = t1 * rise
    x2s = r1 + land - r2
    z2_lo, z2_hi = b + gap, b + gap + b

    fill_t = QColor(102, 106, 112)
    fill_t_hi = QColor(118, 122, 128)
    fill_r = QColor(86, 90, 96)
    fill_l = QColor(90, 96, 104)
    fill_l_end = QColor(76, 82, 90)
    edge = QColor(28, 32, 38)
    p_th = QPen(edge, 0.55)
    p_th2 = QPen(edge, 0.45)
    t_th = min(32.0, b * 0.06, rise * 0.3)
    p_wang = QPen(QColor(36, 40, 48), 2.0)
    p_wang2 = QPen(QColor(36, 40, 48), 1.45)

    for k in range(t1):
        yb, yt = k * rise, (k + 1) * rise
        x0, x1 = k * g, (k + 1) * g
        p.setPen(p_th)
        p.setBrush(fill_r)
        p.drawPolygon(
            QPolygonF(
                [
                    to_pt(x1, yb, 0.0),
                    to_pt(x1, yt, 0.0),
                    to_pt(x1, yt, b),
                    to_pt(x1, yb, b),
                ]
            )
        )
        p.setBrush(Qt.NoBrush)
        g1 = QLinearGradient(to_pt(x0, yt, 0.0), to_pt(x1, yt, b))
        g1.setColorAt(0, fill_t)
        g1.setColorAt(1, fill_t_hi)
        p.setPen(p_th2)
        p.setBrush(g1)
        p.drawPolygon(
            QPolygonF(
                [
                    to_pt(x0, yt, 0.0),
                    to_pt(x1, yt, 0.0),
                    to_pt(x1, yt, b),
                    to_pt(x0, yt, b),
                ]
            )
        )
        p.setBrush(Qt.NoBrush)

    y_top = y_l - t_th
    for x_edge in (r1 + land, r1):
        p.setPen(p_th)
        p.setBrush(fill_l_end)
        p.drawPolygon(
            QPolygonF(
                [
                    to_pt(x_edge, y_top, 0.0),
                    to_pt(x_edge, y_l, 0.0),
                    to_pt(x_edge, y_l, b),
                    to_pt(x_edge, y_top, b),
                ]
            )
        )
        p.setBrush(Qt.NoBrush)
    g_l = QLinearGradient(to_pt(r1, y_l, 0.0), to_pt(r1 + land, y_l, b))
    g_l.setColorAt(0, fill_l)
    g_l.setColorAt(1, fill_l)
    p.setPen(p_th2)
    p.setBrush(g_l)
    p.drawPolygon(
        QPolygonF(
            [
                to_pt(r1, y_l, 0.0),
                to_pt(r1 + land, y_l, 0.0),
                to_pt(r1 + land, y_l, b),
                to_pt(r1, y_l, b),
            ]
        )
    )
    p.setBrush(Qt.NoBrush)

    for j in range(t2):
        yb, yt = y_l + j * rise, y_l + (j + 1) * rise
        x0, x1 = x2s + j * g, x2s + (j + 1) * g
        p.setPen(p_th)
        p.setBrush(fill_r)
        p.drawPolygon(
            QPolygonF(
                [
                    to_pt(x1, yb, z2_lo),
                    to_pt(x1, yt, z2_lo),
                    to_pt(x1, yt, z2_hi),
                    to_pt(x1, yb, z2_hi),
                ]
            )
        )
        p.setBrush(Qt.NoBrush)
        g2 = QLinearGradient(to_pt(x0, yt, z2_lo), to_pt(x1, yt, z2_hi))
        g2.setColorAt(0, fill_t)
        g2.setColorAt(1, fill_t_hi)
        p.setPen(p_th2)
        p.setBrush(g2)
        p.drawPolygon(
            QPolygonF(
                [
                    to_pt(x0, yt, z2_lo),
                    to_pt(x1, yt, z2_lo),
                    to_pt(x1, yt, z2_hi),
                    to_pt(x0, yt, z2_hi),
                ]
            )
        )
        p.setBrush(Qt.NoBrush)

    def saw_f1_land(zz: float) -> QPainterPath:
        ph = QPainterPath()
        x, y = 0.0, 0.0
        ph.moveTo(to_pt(0, 0, zz))
        for _ in range(t1):
            y += rise
            ph.lineTo(to_pt(x, y, zz))
            x += g
            ph.lineTo(to_pt(x, y, zz))
        ph.lineTo(to_pt(r1 + land, y, zz))
        ph.lineTo(to_pt(x2s, y, zz))
        return ph

    p.setPen(p_wang)
    p.drawPath(saw_f1_land(0.0))
    p.drawPath(saw_f1_land(b))
    ph2l = QPainterPath()
    x, y = x2s, y_l
    ph2l.moveTo(to_pt(x2s, y, z2_lo))
    for _ in range(t2):
        y += rise
        ph2l.lineTo(to_pt(x, y, z2_lo))
        x += g
        ph2l.lineTo(to_pt(x, y, z2_lo))
    p.setPen(p_wang2)
    p.drawPath(ph2l)
    ph2h = QPainterPath()
    x, y = x2s, y_l
    ph2h.moveTo(to_pt(x2s, y, z2_hi))
    for _ in range(t2):
        y += rise
        ph2h.lineTo(to_pt(x, y, z2_hi))
        x += g
        ph2h.lineTo(to_pt(x, y, z2_hi))
    p.drawPath(ph2h)

    hhr = min(900.0, max(800.0, 2.4 * rise))
    p.setPen(QPen(QColor(185, 200, 215, 190), 0.85))
    phr2 = QPainterPath()
    x, y = 0.0, 0.0
    phr2.moveTo(to_pt(0, hhr, 0.0))
    for _ in range(t1):
        y += rise
        phr2.lineTo(to_pt(x, y + hhr, 0.0))
        x += g
        phr2.lineTo(to_pt(x, y + hhr, 0.0))
    phr2.lineTo(to_pt(r1 + land, y + hhr, 0.0))
    phr2.lineTo(to_pt(x2s, y + hhr, 0.0))
    x, y = x2s, y_l
    for _ in range(t2):
        y += rise
        phr2.lineTo(to_pt(x, y + hhr, 0.0))
        x += g
        phr2.lineTo(to_pt(x, y + hhr, 0.0))
    p.drawPath(phr2)
    phr3 = QPainterPath()
    x, y = 0.0, 0.0
    phr3.moveTo(to_pt(0, hhr, b))
    for _ in range(t1):
        y += rise
        phr3.lineTo(to_pt(x, y + hhr, b))
        x += g
        phr3.lineTo(to_pt(x, y + hhr, b))
    phr3.lineTo(to_pt(r1 + land, y + hhr, b))
    phr3.lineTo(to_pt(x2s, y + hhr, b))
    x, y = x2s, y_l
    for _ in range(t2):
        y += rise
        phr3.lineTo(to_pt(x, y + hhr, b))
        x += g
        phr3.lineTo(to_pt(x, y + hhr, b))
    p.drawPath(phr3)
    p_hr2 = QPainterPath()
    x, y = x2s, y_l
    p_hr2.moveTo(to_pt(x2s, y + hhr, z2_lo))
    for _ in range(t2):
        y += rise
        p_hr2.lineTo(to_pt(x, y + hhr, z2_lo))
        x += g
        p_hr2.lineTo(to_pt(x, y + hhr, z2_lo))
    p.drawPath(p_hr2)
    p_hr2b = QPainterPath()
    x, y = x2s, y_l
    p_hr2b.moveTo(to_pt(x2s, y + hhr, z2_hi))
    for _ in range(t2):
        y += rise
        p_hr2b.lineTo(to_pt(x, y + hhr, z2_hi))
        x += g
        p_hr2b.lineTo(to_pt(x, y + hhr, z2_hi))
    p.drawPath(p_hr2b)

    p_y0 = y_l - 50.0
    for (xc, zc) in ((r1, 0.0), (r1 + land, 0.0), (r1 + land, b), (r1, b)):
        p.setPen(QPen(QColor(55, 60, 70), 1.0))
        p.drawLine(to_pt(xc, 0, zc), to_pt(xc, p_y0, zc))


def _path_centerline_3d(data: StairInput, result: StairResult) -> list[tuple[float, float, float]]:
    """3D-Mittellinie (Stufenlauf) in mm: px, py, pz. py = Hoehe."""
    rise = result.riser_height_mm
    going = data.going_mm
    floor_h = data.floor_height_mm
    b = data.stair_width_mm
    run1 = result.run_flight_1_mm
    run2 = result.run_flight_2_mm
    land = result.landing_length_used_mm
    t1 = result.tread_count // 2
    t2 = result.tread_count - t1
    z0 = b / 2.0
    out: list[tuple[float, float, float]] = []

    st = data.stair_type
    if st == "Podesttreppe":
        # U-Treppe: Lauf1 am Sued-Stringer, Podest durchlaufen, Umlauf, Lauf2 parallel (Nord)
        x, y, z = 0.0, 0.0, z0
        out.append((x, y, z))
        for _ in range(t1):
            y += rise
            out.append((x, y, z))
            x += going
            out.append((x, y, z))
        y_l = y
        x_back = run1 + land
        z2 = b + GAP_PLAN + b / 2.0
        x2_start = run1 + land - run2
        out.append((run1, y_l, z0))
        out.append((x_back, y_l, z0))
        out.append((x2_start, y_l, z2))
        x, z = x2_start, z2
        for _ in range(t2):
            y += rise
            out.append((x, y, z))
            x += going
            out.append((x, y, z))
        if y < floor_h - 0.1:
            out.append((x, floor_h, z))
    elif st == "Gerade Treppe":
        x, y, z = 0.0, 0.0, z0
        out.append((x, y, z))
        for _ in range(result.tread_count):
            y += rise
            out.append((x, y, z))
            x += going
            out.append((x, y, z))
        if y < floor_h - 0.1:
            out.append((x, floor_h, z0))
    elif st == "Viertelgewendelte Treppe (90°)":
        # Grundriss wie dxf_export: 1. Lauf in +x, 2. in +z, Ecke b x b
        turn_x, r2_leg, n1, n2 = _l_quarter_geometry(run1, b, result.tread_count)
        g1x = turn_x / max(n1, 1)
        g2z = r2_leg / max(n2, 1) if n2 > 0 else 0.0
        x, y, z = 0.0, 0.0, z0
        out.append((x, y, z))
        for _ in range(n1):
            y += rise
            x += g1x
            out.append((x, y, z))
        out.append((turn_x, y, b))
        xc2 = turn_x - b / 2.0
        out.append((xc2, y, b))
        z = b
        for _ in range(n2):
            y += rise
            z += g2z
            out.append((xc2, y, z))
        if y < floor_h - 0.1:
            out.append((xc2, floor_h, z))
    else:
        hlen = max(run1 / 2.0, b)
        x, y, z = 0.0, 0.0, z0
        n1 = max(1, result.tread_count // 2)
        for _ in range(n1):
            y += rise
            out.append((x, y, z))
            x += min(going, hlen / n1) if n1 else going
            out.append((x, y, z))
        y += rise
        out.append((hlen, y, z0))
        out.append((hlen, y, b + GAP_PLAN + z0))
        x = hlen
        z2 = b + GAP_PLAN + z0
        for _ in range(result.tread_count - n1):
            y += rise
            out.append((x, y, z2))
            x -= min(going, hlen / max(result.tread_count - n1, 1))
            out.append((x, y, z2))
        if y < floor_h - 0.1:
            out.append((x, floor_h, z2))
    return out


class _SideViewWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._data: StairInput | None = None
        self._result: StairResult | None = None
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_stair(self, data: StairInput | None, result: StairResult | None) -> None:
        self._data = data
        self._result = result
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect()
        p.fillRect(rect, BG)
        if self._data is None or self._result is None:
            p.setPen(QColor(160, 165, 175))
            p.drawText(rect, Qt.AlignCenter, "Berechnen druecken")
            return
        data, result = self._data, self._result
        floor_h = data.floor_height_mm
        run_total = result.run_mm
        points, _mode = _side_polyline(data, result)

        margin = 20.0
        w, h = float(rect.width()) - 2 * margin, float(rect.height()) - 2 * margin
        if w <= 1 or h <= 1:
            return
        xs = [pt[0] for pt in points]
        ys = [pt[1] for pt in points]
        x_min, x_max = min(xs) - 50, max(xs) + 50
        y_min, y_max = 0.0, max(floor_h, max(ys) + 50)
        world_w, world_h = x_max - x_min, y_max - y_min
        scale = min(w / max(world_w, 1e-6), h / max(world_h, 1e-6))
        ox = margin + (w - (x_max - x_min) * scale) / 2.0 - x_min * scale
        oy = margin + h - (0.0 - y_min) * scale

        def to_s(x: float, y: float) -> QPointF:
            return QPointF(ox + x * scale, oy - y * scale)

        pen_f = QPen(QColor(90, 100, 120), 1.2)
        pen_s = QPen(QColor(120, 130, 150), 1.5)
        pen_t = QPen(QColor(220, 225, 235), 2.2)
        p.setPen(pen_f)
        p.drawLine(to_s(x_min, 0), to_s(0, 0))
        p.drawLine(to_s(max(xs), floor_h), to_s(x_max, floor_h))
        p.setPen(pen_s)
        p.drawLine(to_s(0, 0), to_s(max(xs), floor_h))
        p.setPen(pen_t)
        sp = [to_s(a, b) for a, b in points]
        for i in range(len(sp) - 1):
            p.drawLine(sp[i], sp[i + 1])
        p.setPen(QColor(180, 185, 195))
        p.drawText(
            rect.adjusted(6, 6, -6, -6),
            Qt.AlignTop | Qt.AlignRight,
            f"{data.stair_type} | H={floor_h:.0f} Run={run_total:.0f} mm",
        )


class _PlanViewWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._data: StairInput | None = None
        self._result: StairResult | None = None
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_stair(self, data: StairInput | None, result: StairResult | None) -> None:
        self._data = data
        self._result = result
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect()
        p.fillRect(rect, BG)
        if self._data is None or self._result is None:
            p.setPen(QColor(160, 165, 175))
            p.drawText(rect, Qt.AlignCenter, "Berechnen druecken")
            return
        data, tr = self._data, self._result
        B = data.stair_width_mm
        run1 = tr.run_flight_1_mm
        run2 = tr.run_flight_2_mm
        landing = max(tr.landing_length_used_mm, B)
        gap = GAP_PLAN
        y0 = 0.0
        margin = 18.0
        w, h = float(rect.width()) - 2 * margin, float(rect.height()) - 2 * margin

        t1 = tr.tread_count // 2
        t2 = tr.tread_count - t1
        g = data.going_mm

        if tr.stair_type == "Gerade Treppe":
            bounds = (0, tr.run_mm, 0, B)
        elif tr.stair_type == "Podesttreppe":
            bounds = (0, run1 + landing + run2, 0, B + gap + B)
        elif tr.stair_type == "Viertelgewendelte Treppe (90°)":
            # L-Form wie dxf_export: Lauf1 Breite 0,55*run1, 2. Lauf max(run1-0,55*run1, B)
            turn_x, r2_leg, _, _ = _l_quarter_geometry(run1, B, tr.tread_count)
            bounds = (0, turn_x, 0, B + r2_leg)
        else:
            half = max(run1 / 2.0, B)
            bounds = (0, half, 0, B + gap + B)

        min_x, max_x, min_y, max_y = bounds
        world_w = max_x - min_x
        world_h = max_y - min_y
        scale = min(w / max(world_w, 1e-6), h / max(world_h, 1e-6)) * 0.92
        off_x = margin + (w - world_w * scale) / 2.0
        off_y = margin + (h - world_h * scale) / 2.0

        def to_plan(px: float, pz: float) -> QPointF:
            # pz: Norden oben, Sueden unten
            return QPointF(
                off_x + (px - min_x) * scale,
                off_y + (max_y - pz) * scale,
            )

        def draw_rect_filled(x: float, z: float, rw: float, rh: float, col: QColor) -> None:
            poly = QPolygonF(
                [
                    to_plan(x, z),
                    to_plan(x + rw, z),
                    to_plan(x + rw, z + rh),
                    to_plan(x, z + rh),
                ]
            )
            p.setPen(QPen(col.darker(120), 1.2))
            p.setBrush(col)
            p.drawPolygon(poly)
            p.setBrush(Qt.NoBrush)

        p.setFont(QFont("Arial", 9))
        p.setPen(QColor(200, 205, 215))

        if tr.stair_type == "Gerade Treppe":
            draw_rect_filled(0, y0, tr.run_mm, B, PLAN_F1)
            _plan_riser_lines(p, to_plan, 0, y0, tr.run_mm, B, g, tr.tread_count)
            _plan_arrow_along(p, to_plan, 0, y0 + B * 0.5, tr.run_mm, 0, 0.45, max(400, tr.run_mm * 0.12))
            p.setPen(QColor(220, 220, 230))
            p.drawText(
                to_plan(tr.run_mm * 0.08, y0 + B * 0.32),
                f"gerade | Lauf {tr.run_mm:.0f} mm  B {B:.0f} mm  Auftritt {g:.0f} mm",
            )
        elif tr.stair_type == "Podesttreppe":
            # Wende links (gespiegelt an rechter Aussenkante), wie typische
            # Mittel-Podest-Draufsicht (vgl. Auslegertreppen-Grundriss).
            x_span = run1 + landing
            f1l = _plan_x_mirror_uleft(0, run1, x_span)
            podl = _plan_x_mirror_uleft(run1, landing, x_span)
            x2 = run1 + landing - run2
            x2d = _plan_x_mirror_uleft(x2, run2, x_span)
            z2 = y0 + B + gap
            draw_rect_filled(f1l, y0, run1, B, PLAN_F1)
            draw_rect_filled(podl, y0, landing, B, PLAN_LANDING)
            draw_rect_filled(x2d, z2, run2, B, PLAN_F2)
            n_grid = 6
            _plan_grating_hint(p, to_plan, f1l, y0, run1, B, n_grid)
            _plan_grating_hint(p, to_plan, podl, y0, landing, B, n_grid)
            _plan_grating_hint(p, to_plan, x2d, z2, run2, B, n_grid)
            _plan_riser_lines(p, to_plan, f1l, y0, run1, B, g, t1)
            nl = max(2, min(6, int(landing / 400) + 1))
            _plan_riser_lines(
                p, to_plan, podl, y0, landing, B, landing / float(nl), nl
            )
            _plan_riser_lines(p, to_plan, x2d, z2, run2, B, g, t2)
            p.setPen(QPen(QColor(200, 200, 220), 1.0, Qt.DashLine))
            p.drawLine(to_plan(0, y0 + B * 0.12), to_plan(0, z2 + B * 0.88))
            b_edge = y0 + B
            z_edge = z2
            dmx = max(podl * 0.25, 0.04 * x_span, 5.0)
            if z_edge > b_edge + 8:
                p.setPen(QPen(QColor(160, 200, 220), 0.9))
                p.drawLine(to_plan(dmx, b_edge), to_plan(dmx, z_edge))
                p.drawLine(to_plan(dmx - 2.5, b_edge), to_plan(dmx + 2.5, b_edge))
                p.drawLine(to_plan(dmx - 2.5, z_edge), to_plan(dmx + 2.5, z_edge))
                p.setPen(QColor(180, 210, 220))
                p.setFont(QFont("Arial", 7))
                p.drawText(
                    to_plan(dmx + 4, b_edge + gap * 0.35 - g * 0.1),
                    f"Zwischenraum {gap:.0f} mm",
                )
            p.setFont(QFont("Arial", 9))
            p.setPen(QColor(210, 215, 225))
            p.drawText(
                to_plan(4, y0 + 4),
                "Mittel-Podest (U), Draufsicht - parallele Laeufe, Wende links",
            )
            _plan_arrow_along(
                p, to_plan, f1l, y0 + B * 0.5, run1, 0, 0.4, max(350, run1 * 0.1)
            )
            _plan_arrow_along(
                p, to_plan, x2d, z2 + B * 0.5, run2, 0, 0.45, max(300, run2 * 0.12)
            )
            p.setPen(QColor(130, 195, 160))
            p.drawText(to_plan(podl + 5, y0 + B * 0.38), "Wende (Podest)")
            p.setPen(QColor(190, 200, 215))
            p.drawText(to_plan(f1l + 4, y0 + B * 0.4), "Lauf 1")
            p.drawText(to_plan(x2d + 4, z2 + B * 0.4), "Lauf 2")
        elif tr.stair_type == "Viertelgewendelte Treppe (90°)":
            turn_x, r2_leg, n1, n2 = _l_quarter_geometry(run1, B, tr.tread_count)
            brx = turn_x
            draw_rect_filled(0, y0, turn_x, B, PLAN_F1)
            draw_rect_filled(turn_x - B, y0 + B, B, r2_leg, PLAN_90)
            _plan_riser_lines(p, to_plan, 0, y0, turn_x, B, g, n1)
            _plan_riser_lines_along_north(
                p, to_plan, turn_x - B, y0 + B, B, r2_leg, g, n2
            )
            _plan_arrow_along(
                p, to_plan, 0, y0 + B * 0.5, turn_x, 0, 0.45, max(300, turn_x * 0.1)
            )
            _plan_arrow_along(
                p,
                to_plan,
                brx - B * 0.5,
                y0 + B * 1.15,
                0,
                r2_leg,
                0.5,
                max(280, r2_leg * 0.12),
            )
            p.drawText(
                to_plan(4, y0 + 4),
                "L-Treppe (90°) - Grundriss analog DXF-Export (erster Lauf 0,55xRun)",
            )
        else:
            half = max(run1 / 2.0, B)
            draw_rect_filled(0, y0, half, B, PLAN_F1)
            draw_rect_filled(0, y0 + B + gap, half, B, PLAN_F2)
            _plan_riser_lines(p, to_plan, 0, y0, half, B, g, max(1, t1))
            _plan_riser_lines(p, to_plan, 0, y0 + B + gap, half, B, g, max(1, t2))
            p.setPen(QPen(QColor(200, 200, 220), 1.0, Qt.DashLine))
            p.drawLine(to_plan(half, y0 + B), to_plan(half, y0 + B + gap))
            p.drawText(to_plan(4, y0 + 4), "180°-Treppe / U (schematisch)")
            _plan_arrow_along(p, to_plan, half * 0.4, y0 + B * 0.5, half, 0, 0.45, max(280, half * 0.1))

        p.setPen(QColor(140, 150, 165))
        p.drawText(
            rect.adjusted(6, 6, -6, -6),
            Qt.AlignTop | Qt.AlignLeft,
            f"Grundriss (schematisch, Pfeil = Aufstieg) | B={B:.0f} mm | {tr.stair_type}",
        )


class _Iso3DWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._data: StairInput | None = None
        self._result: StairResult | None = None
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_stair(self, data: StairInput | None, result: StairResult | None) -> None:
        self._data = data
        self._result = result
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect()
        p.fillRect(rect, BG)
        if self._data is None or self._result is None:
            p.setPen(QColor(160, 165, 175))
            p.drawText(rect, Qt.AlignCenter, "Berechnen druecken")
            return
        data, tr = self._data, self._result
        path3 = _path_centerline_3d(data, tr)
        if not path3:
            return
        w, h = float(rect.width()) - 20.0, float(rect.height()) - 40.0
        b = data.stair_width_mm
        fh = data.floor_height_mm
        run = tr.run_mm
        extra = [
            *path3,
            (0, 0, 0),
            (run, 0, 0),
            (0, fh, 0),
            (0, 0, b),
            (run, fh, b),
        ]
        if tr.stair_type == "Podesttreppe":
            r1 = tr.run_flight_1_mm
            r2 = tr.run_flight_2_mm
            ll = tr.landing_length_used_mm
            zc = b + GAP_PLAN + b / 2.0
            hhr = min(900.0, max(800.0, 2.4 * tr.riser_height_mm))
            extra += [
                (r1 + ll, fh, b * 0.5),
                (r1 + ll - r2, fh, zc),
                (0, hhr, 0.0),
                (0, hhr, b),
            ]
        fit = _fit_iso_transform(extra, w, h, 16.0)
        if fit is None:
            return
        s, ox0, oy0 = fit

        def to_pt(x: float, y: float, z: float) -> QPointF:
            return _iso(x, y, z, s, ox0, oy0)

        def draw_base(xa: float, za: float, xb: float, zb: float) -> None:
            poly = QPolygonF(
                [
                    to_pt(xa, 0, za),
                    to_pt(xb, 0, za),
                    to_pt(xb, 0, zb),
                    to_pt(xa, 0, zb),
                ]
            )
            g = QLinearGradient(to_pt(xa, 0, za), to_pt(xb, 0, zb))
            g.setColorAt(0, QColor(30, 34, 42))
            g.setColorAt(1, QColor(50, 54, 64))
            p.setPen(QPen(QColor(70, 78, 92), 1.0))
            p.setBrush(g)
            p.drawPolygon(poly)
            p.setBrush(Qt.NoBrush)

        rx = max(tr.run_mm, data.stair_width_mm * 1.2)
        rz = max(data.stair_width_mm + GAP_PLAN, tr.run_mm * 0.4)
        if tr.stair_type == "Viertelgewendelte Treppe (90°)":
            tx, r2, _, _ = _l_quarter_geometry(tr.run_flight_1_mm, b, tr.tread_count)
            rx = max(rx, tx * 1.15)
            rz = max(rz, b + r2)
        if tr.stair_type == "Podesttreppe":
            r1e, l2e = tr.run_flight_1_mm, tr.landing_length_used_mm
            rx = max(rx, r1e + max(l2e, b) + 0.05 * rx)
            rz = max(rz, b + GAP_PLAN + b + 0.15 * fh)
        draw_base(-rx * 0.05, -rz * 0.05, rx * 1.05, rz * 1.1)

        if tr.stair_type == "Podesttreppe":
            _draw_u_podest_steel_isometric(
                p, to_pt, tr, data.going_mm, b, tr.riser_height_mm
            )
        else:
            hw = b * 0.42
            for i in range(len(path3) - 1):
                ax, ay, az = path3[i]
                bx, by, bz = path3[i + 1]
                dx, dy, dz = bx - ax, by - ay, bz - az
                dhx = math.hypot(dx, dz)
                if dhx < 0.1 and abs(dy) < 0.1:
                    continue
                is_flat = abs(by - ay) < 0.1 and abs(dy) < 0.1
                if dhx < 0.1:
                    continue
                ox = -dz / dhx * hw
                oz = dx / dhx * hw
                top = (
                    QColor(95, 110, 135, 200)
                    if is_flat or abs(dy) < 0.1
                    else QColor(150, 105, 75, 205)
                )
                ed = top.darker(150)
                poly = QPolygonF(
                    [
                        to_pt(ax + ox, ay, az + oz),
                        to_pt(bx + ox, by, bz + oz),
                        to_pt(bx - ox, by, bz - oz),
                        to_pt(ax - ox, ay, az - oz),
                    ]
                )
                p.setPen(QPen(ed, 0.6))
                p.setBrush(top)
                p.drawPolygon(poly)
                p.setBrush(Qt.NoBrush)

        p.setPen(QPen(QColor(35, 40, 48), 2.4))
        for i in range(len(path3) - 1):
            x1, y1, z1 = path3[i]
            x2, y2, z2 = path3[i + 1]
            p1 = to_pt(x1, y1, z1)
            p2 = to_pt(x2, y2, z2)
            p.drawLine(
                p1.x() + 2,
                p1.y() + 3,
                p2.x() + 2,
                p2.y() + 3,
            )
        p.setPen(QPen(QColor(240, 235, 220), 2.0))
        for i in range(len(path3) - 1):
            x1, y1, z1 = path3[i]
            x2, y2, z2 = path3[i + 1]
            p.drawLine(to_pt(x1, y1, z1), to_pt(x2, y2, z2))

        p.setPen(QColor(160, 170, 180))
        if tr.stair_type == "Podesttreppe":
            cap = (
                "3D: U-Mittelpodest, Isometrie (30°) - Stufen, Podest, Wangen, Stuetzen, "
                "Handlauf (Vorschau, kein OpenGL)."
            )
        else:
            cap = "3D: klassische Isometrie (30°), py = Hoehe (mm). Schematisch, kein OpenGL."
        p.drawText(rect.adjusted(6, 6, -6, -6), Qt.AlignTop | Qt.AlignLeft, cap)
        p.setPen(QColor(130, 140, 150))
        if tr.stair_type == "Podesttreppe":
            foot = f"{tr.stair_type} | Vorschau analog Werkstattzeichnung"
        else:
            foot = f"{tr.stair_type} | Band = ca. 0,85x Laufbreite"
        p.drawText(rect.adjusted(6, 6, -6, -6), Qt.AlignBottom | Qt.AlignRight, foot)


class StairPreviewPanel(QFrame):
    """
    Tabs: Seitenansicht, Grundriss, 3D-Isometrie.
    `set_stair` wie bisher.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setFrameShape(QFrame.NoFrame)
        self._side = _SideViewWidget()
        self._plan = _PlanViewWidget()
        self._iso = _Iso3DWidget()
        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.addTab(self._side, "Seitenansicht")
        tabs.addTab(self._plan, "Grundriss")
        tabs.addTab(self._iso, "3D (isometrisch)")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(tabs, 1)

    def set_stair(self, data: StairInput | None, result: StairResult | None) -> None:
        self._side.set_stair(data, result)
        self._plan.set_stair(data, result)
        self._iso.set_stair(data, result)


# Abwaertskompatibler Name
StairSidePreview = StairPreviewPanel
