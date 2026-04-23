"""Dialog: DXF-Export-Einstellungen."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from dxf_settings import DxfExportSettings, load_dxf_settings, save_dxf_settings


class DxfSettingsDialog(QDialog):
    def __init__(
        self, parent: QWidget | None = None, initial: DxfExportSettings | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("DXF-Export – Einstellungen")
        self.setMinimumWidth(460)
        base = initial if initial is not None else load_dxf_settings()
        self._s = DxfExportSettings.from_dict(base.to_dict())

        lay_layers = QFormLayout()
        self._e_geo = QLineEdit(self._s.layer_geometry)
        self._e_dim = QLineEdit(self._s.layer_dimensions)
        self._e_notes = QLineEdit(self._s.layer_notes)
        self._e_axes = QLineEdit(self._s.layer_axes)
        self._e_weld = QLineEdit(self._s.layer_weld)
        lay_layers.addRow("Geometrie / Konstruktion:", self._e_geo)
        lay_layers.addRow("Bemaßung / Hilfslinien:", self._e_dim)
        lay_layers.addRow("Text / Notizen:", self._e_notes)
        lay_layers.addRow("Achsen (leerer Layer):", self._e_axes)
        lay_layers.addRow("Schweiß / Fertigung (leerer Layer):", self._e_weld)

        gb_l = QGroupBox("Layer-Namen (DXF)")
        gb_l.setLayout(lay_layers)

        self._c_axes = QCheckBox("Leeren Layer „Achsen“ anlegen")
        self._c_axes.setChecked(self._s.include_empty_axes_layer)
        self._c_weld = QCheckBox("Leeren Layer „Schweiß/Fertigung“ anlegen")
        self._c_weld.setChecked(self._s.include_empty_weld_layer)

        self._sp_dim = self._spin(self._s.text_height_dimensions, 5, 120)
        self._sp_notes = self._spin(self._s.text_height_notes, 5, 120)
        self._sp_plan = self._spin(self._s.text_height_plan_title, 5, 120)
        lay_txt = QFormLayout()
        lay_txt.addRow("Text Seitenansicht Bemaßung [mm]:", self._sp_dim)
        lay_txt.addRow("Text Seitenansicht Notizen [mm]:", self._sp_notes)
        lay_txt.addRow("Text Grundriss Titel [mm]:", self._sp_plan)
        gb_t = QGroupBox("Textgroessen (Zeichnungseinheiten = mm)")
        gb_t.setLayout(lay_txt)

        self._c_plan = QCheckBox("Grundriss in dieselbe DXF-Datei exportieren")
        self._c_plan.setChecked(self._s.include_plan_view)
        self._sp_gap = self._spin(self._s.plan_gap_mm, 50, 2000)
        f_gap = QFormLayout()
        f_gap.addRow("Abstand paralleler Laeufe U-Treppe [mm]:", self._sp_gap)
        w_gap = QWidget()
        w_gap.setLayout(f_gap)

        hint = QLabel(
            "Hinweis: Nur gueltige DXF-Layer-Namen verwenden (keine Sonderzeichen wie < > / \\)."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666;")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addWidget(gb_l)
        root.addWidget(self._c_axes)
        root.addWidget(self._c_weld)
        root.addWidget(gb_t)
        root.addWidget(self._c_plan)
        root.addWidget(w_gap)
        root.addWidget(hint)
        root.addWidget(buttons)

    @staticmethod
    def _spin(val: float, lo: float, hi: float) -> QDoubleSpinBox:
        sp = QDoubleSpinBox()
        sp.setRange(lo, hi)
        sp.setDecimals(1)
        sp.setValue(val)
        return sp

    def _on_ok(self) -> None:
        def name(w: QLineEdit, default: str) -> str:
            t = w.text().strip()
            return t if t else default

        self._s.layer_geometry = name(self._e_geo, "GEOMETRY")
        self._s.layer_dimensions = name(self._e_dim, "DIMENSIONS")
        self._s.layer_notes = name(self._e_notes, "NOTES")
        self._s.layer_axes = name(self._e_axes, "AXES")
        self._s.layer_weld = name(self._e_weld, "WELD_SHOP")
        self._s.include_empty_axes_layer = self._c_axes.isChecked()
        self._s.include_empty_weld_layer = self._c_weld.isChecked()
        self._s.text_height_dimensions = self._sp_dim.value()
        self._s.text_height_notes = self._sp_notes.value()
        self._s.text_height_plan_title = self._sp_plan.value()
        self._s.include_plan_view = self._c_plan.isChecked()
        self._s.plan_gap_mm = self._sp_gap.value()
        save_dxf_settings(self._s)
        self.accept()

    def settings(self) -> DxfExportSettings:
        return self._s
