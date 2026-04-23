import json
import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStatusBar,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from calculations import (
    StairInput,
    build_bom,
    calculate_stair,
    get_available_bearing_conditions,
    get_available_norm_profiles,
    get_available_profiles,
    get_available_stair_directions,
    get_available_stair_orientations,
    get_available_stair_types,
    get_available_steel_grades,
    get_available_support_layouts,
    get_available_tread_types,
    get_tread_type_description,
    get_tread_type_kg_per_m2,
)
from config.logging_bootstrap import setup_logging
from dxf_export import export_stair_side_view_dxf
from dxf_settings import DxfExportSettings, load_dxf_settings
from enums import StairType, __version__
from norms import NORM_CONFIG_DE
from report_export import append_release_changelog, export_bom_csv, export_report_pdf
from ui.dxf_settings_dialog import DxfSettingsDialog
from ui.stair_preview import StairSidePreview

logger = logging.getLogger("openstair")

PROJECT_SCHEMA_VERSION = 2


def _cdll_load(name: str) -> bool:
    try:
        import ctypes

        ctypes.CDLL(name)
    except OSError:
        return False
    return True


def _param_tip(widget: QWidget, text: str) -> None:
    """Kurzinfo (Tooltip) fuer Eingabefelder."""
    widget.setToolTip(text.strip())


# Hilfetexte fuer _form_label (?) und setToolTip — eine Quelle, kein doppelter Wortlaut
PARAM_HELP: dict[str, str] = {
    "project_name": "Freier Name der Planung (erscheint im PDF und in der Stueckliste).",
    "project_number": "Interne oder Kunden-Projektnummer, z. B. fuer Angebote.",
    "customer": "Kunde oder Bauherr (fuer Berichtskopf).",
    "location": "Einsatzort / Baustelle.",
    "engineer": "Bearbeiter oder Fachplaner (Kontext im Bericht).",
    "export_dir": "Standardordner fuer DXF, PDF, CSV und Speichern-Browser. Per \"…\" aendern.",
    "btn_export_dir": "Ordner waehlen, in den Exporte geschrieben werden.",
    "height": "Geschosshoehe: lotrechter Abstand Unterkante Auflager unten bis "
    "Oberkante Auflager oben [mm]. Bestimmt mit die Stufenanzahl.",
    "going": "Auftritt (Innen): horizontale Tiefe einer Stufe an der Lauflinie [mm]. "
    "Zusammen mit Steigung fuer Gebrauchstauglichkeit.",
    "width": "Nutzbare Treppenbreite zwischen den Wangen [mm] (Laufbreite).",
    "available_run": "Maximal verfuegbarer horizontaler Platz fuer die Treppe entlang des Laufes [mm]. "
    "Die Bemessung passt die Lauflaenge daran an, wo noetig.",
    "stair_type": "Geometrie der Treppe: gerade, Podest (U), 90° oder 180° "
    "(vereinfachte Modelle je Typ).",
    "stair_direction": "Bei gewendelten Treppen: Drehrichtung im Grundriss (rechts/links), "
    "wirkt auf die Draufsicht im Export.",
    "stair_orientation": "Himmelsrichtung der Treppe im Grundriss (N/O/S/W), z. B. fuer "
    "Zeichnungsbeschriftung.",
    "bearing": "Lagerungsbedingung der Wange: z. B. gelenkig-gelenkig beeinflusst "
    "Knicklaengen und Schnittgroessen.",
    "profile": "Stahlprofil der Wange (HEA, UPN, …). Steifigkeit und Eigenmasse "
    "kommen aus der Bibliothek.",
    "steel_grade": "Stahlsorte (z. B. S235) fuer Festigkeitsnachweise.",
    "tread_type": "Rost-/Stufenbelag aus Katalog: Masche, Rutschhemmung; steuert zulaessige "
    "Breite und Masse.",
    "plate": "Flaechengewicht des Stufenblechs [kg/m2] (oder Vorgabe aus dem Stufentyp).",
    "live_category": "Nutzungskategorie nach DIN EN 1991-1-1 / Nationaler Anhang. "
    "Setzt die empfohlene Nutzlast, falls nicht Benutzerdefiniert.",
    "live_load": "Nutzlast senkrecht zur Trittflaeche [kN/m2] fuer die Bemessung der Wangen.",
    "norm_profile": "Set aus Eurocode + Nationaler Anhang (DIN EN DE-NA, AT, CH) fuer Anpassungen.",
    "fy": "Bemessungswert der Streckgrenze (Charakterwert) [MPa] falls von Standard abweichend, "
    "0 = aus Materialtabelle.",
    "national_annex": "Kennung des Nationalen Anhangs (z. B. „NA Deutschland“) im Bericht und fuer Parameter.",
    "regulation": "Zusaetzliche Anforderungen (Arbeitsstaette, Sonderbau) - wirkt in Normhinweisen.",
    "headroom": "Geforderte lichte Hoehe unter der Decke bzw. freie Durchgangshoehe [mm] (Kopffreiheits-Check).",
    "landing": "Mindestlaenge (Einlauf) des Podests bei Podesttreppe [mm], 0 = Vorgabe mindestens Breite.",
    "landing_width": "Podestbreite quer zur Laufachse [mm], 0 = gleich Treppenbreite.",
    "landing_position": "Lage des Podestbereichs relativ zur Laufverbindung: mittig, oben oder unten.",
    "axial": "Zusaetzliche Normalkraft in der Wange [kN] fuer Biegung/Normalkraft-Interaktion, 0 = keine.",
    "tread_info": "Kurzbeschreibung des gewaehlten Stufentyps (nur Lese-Info).",
    "handrail_enabled": "Wenn aktiv: Laenge und Masse des Handlaufs werden aus der Lauflinie und kg/m geschaetzt.",
    "handrail_sides": "Handlauf links, rechts oder beidseitig - Faktor auf Gesamtlaenge und Masse.",
    "handrail_kg": "Gewicht des Handlaufprofils pro Meter [kg/m] (Rohr oder Vierkant, je nach Ausfuehrung).",
    "handrail_height": "Bezugshoehe des Handlaufs ueber Auftritt [mm] (ueblicherweise 900-1000, "
    "Planung/Statik getrennt).",
    "supports_enabled": "Wenn aktiv: Stuetzenanzahl und Masse in Gesamtmenge und Stueckliste; "
    "Position nur vereinfacht.",
    "support_layout": "Verteilung der Stuetzen: gleichmaeßig, nur unten/oben, oder manuelle Anzahl.",
    "support_count": "Anzahl (0 = automatisch schaetzen laut Laenge/Layout).",
    "support_unit_kg": "Erfahrungswert Masse pro Stuetze inkl. Fuss [kg] fuer Stahl-Mengenschaetzung.",
    "plate_thk": "Dicke der Kopf-/Fuss-Lochbleche am Anschluss Wange-Node [mm] fuer Trag- und Anschlussnachweis.",
    "plate_width": "Breite der Anschlussplatte [mm], 0 = programminterne Naeherung.",
    "plate_height": "Hoehe der Anschlussplatte [mm], 0 = programminterne Naeherung.",
    "bolt_count": "Anzahl Schrauben je Anschluss (0 = Vorgabe je nach Profil).",
    "bolt_rd": "Bemessungswert der Schertragfaehigkeit je Schraube [kN] (0 = Vorgabeliste).",
    "weld_a": "Kehlnahtdicke a [mm] an den typischen Wange-Platten-Anschluessen.",
    "weld_length": "Wirksame Nahtlaenge [mm] (0 = geschaetzt aus Anschlussabmessung).",
    "input_detail_view": "Mehr technische Zeilen in der Textausgabe (Schnelluebersicht bleibt kompakt).",
    "status_ampel": "Kurzstatus: rot/gelb/gruen nach Eingabefehlern, Gate und Nachweisen.",
    "result_label": "Ergebnis der Berechnung: Kennwerte, Ausnutzungen, Hinweise. Text markier- und scrollbar.",
    "stair_preview": "Vorschau: Seite, Grundriss, 3D - nach „Berechnen“ bzw. F5 (Menue Ansicht) aktuell.",
    "btn_calc": "Eingabe pruefen und Treppe bemessen (ULS, SLS, Anschluesse, Geometrie).",
    "btn_dxf": "2D-DXF (Seite + optional Grundriss) mit aktuellen DXF-Einstellungen speichern.",
    "btn_bom": "Stueckliste als CSV-Datei exportieren.",
    "btn_pdf": "Berechnungsbericht als PDF; optional Changelog nebenan.",
    "btn_project_new": "Eingabefelder zuruecksetzen; Projektdatei-Referenz loeschen.",
    "btn_project_open": "Projektdatei *.openstair.json laden inkl. DXF-Optionen, falls enthalten.",
    "btn_project_save": "Aktuellen Eingabestand in eine Projektdatei schreiben.",
    "btn_apply_tread": "Vorgeschlagenen Stufentyp aus der letzten Berechnung uebernehmen.",
}


def _preflight_gui_linux() -> None:
    if sys.platform != "linux" or os.environ.get("OPENSTAIR_SKIP_QT_DEPS_CHECK") == "1":
        return
    if (os.environ.get("QT_QPA_PLATFORM") or "").lower() in ("offscreen", "minimal"):
        return
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        print(
            "OpenStair: Kein Display gefunden (weder DISPLAY noch WAYLAND_DISPLAY).",
            file=sys.stderr,
        )
        print(
            "  Lokal in einem Desktop-Terminal starten oder z. B. DISPLAY=:0 setzen.",
            file=sys.stderr,
        )
        sys.exit(1)
    if os.environ.get("WAYLAND_DISPLAY") and not os.environ.get("DISPLAY") and (
        os.environ.get("QT_QPA_PLATFORM") or ""
    ).lower().startswith("wayland"):
        return
    if _cdll_load("libxcb-cursor.so.0") or _cdll_load("libxcb-cursor.so"):
        return
    if os.environ.get("WAYLAND_DISPLAY") and not os.environ.get("DISPLAY"):
        return
    print(
        "OpenStair: Systembibliothek libxcb-cursor0 fehlt (Qt 6 / PySide6, X11).",
        file=sys.stderr,
    )
    print("  Debian/Ubuntu: sudo apt install libxcb-cursor0", file=sys.stderr)
    print("  Prüfung überspringen: export OPENSTAIR_SKIP_QT_DEPS_CHECK=1", file=sys.stderr)
    sys.exit(1)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"OpenStair v{__version__} - Stahltreppe Vorplanung")
        icon_path = Path(__file__).resolve().parent / "app" / "openstair-icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1100, 720)
        self.app_data_dir = Path.home() / ".openstair"
        self.app_data_dir.mkdir(parents=True, exist_ok=True)
        self.last_state_path = self.app_data_dir / "last_project_state.json"
        self.current_project_path: Path | None = None
        self.dxf_settings: DxfExportSettings = load_dxf_settings()

        self.input_project_name = QLineEdit("Neues Projekt")
        self.input_project_number = QLineEdit("")
        self.input_customer = QLineEdit("")
        self.input_location = QLineEdit("")
        self.input_engineer = QLineEdit("")
        self.input_export_dir = QLineEdit(str(Path.cwd()))
        self.btn_export_dir = QPushButton("...")
        self.btn_export_dir.clicked.connect(self.on_pick_export_dir)

        self.input_height = QLineEdit("3000")
        self.input_going = QLineEdit("270")
        self.input_width = QLineEdit("1000")
        self.input_stair_type = QComboBox()
        self.input_stair_type.addItems(get_available_stair_types())
        self.input_stair_type.setCurrentText("Gerade Treppe")
        self.input_stair_direction = QComboBox()
        self.input_stair_direction.addItems(get_available_stair_directions())
        self.input_stair_orientation = QComboBox()
        self.input_stair_orientation.addItems(get_available_stair_orientations())
        self.input_available_run = QLineEdit("6000")
        self.input_bearing = QComboBox()
        self.input_bearing.addItems(get_available_bearing_conditions())
        self.input_bearing.setCurrentText("gelenkig-gelenkig")
        self.input_profile = QComboBox()
        self.input_profile.addItems(get_available_profiles())
        self.input_profile.setCurrentText("HEA120")
        self.input_steel_grade = QComboBox()
        self.input_steel_grade.addItems(get_available_steel_grades())
        self.input_steel_grade.setCurrentText("S235")
        self.input_tread_type = QComboBox()
        self.input_tread_type.addItems(get_available_tread_types())
        self.input_tread_type.setCurrentText("MEISER SP 30/3 33x33 R11")
        self.input_plate = QLineEdit("39.25")
        self.input_live_category = QComboBox()
        self.input_live_category.addItems(
            [*NORM_CONFIG_DE["live_load_categories_kN_m2"].keys(), "Benutzerdefiniert"]
        )
        self.input_live_category.setCurrentText("C1_Versammlungsflaeche_leicht")
        self.input_live_load = QLineEdit("3.0")
        self.input_fy = QLineEdit("235")
        self.input_norm_profile = QComboBox()
        self.input_norm_profile.addItems(get_available_norm_profiles())
        self.input_national_annex = QLineEdit(NORM_CONFIG_DE["standard_set"]["national_annex"])
        self.input_regulation = QComboBox()
        self.input_regulation.addItems(
            ["Keine Zusatzanforderung", "Arbeitsstaette", "Sonderbau"]
        )
        self.input_headroom = QLineEdit("2100")
        self.input_landing = QLineEdit("0")
        self.input_landing_width = QLineEdit("0")
        self.input_landing_position = QComboBox()
        self.input_landing_position.addItems(["mittig", "oben", "unten"])
        self.input_axial = QLineEdit("0")
        self.input_plate_thk = QLineEdit("10")
        self.input_plate_width = QLineEdit("0")
        self.input_plate_height = QLineEdit("0")
        self.input_bolt_count = QLineEdit("0")
        self.input_bolt_rd = QLineEdit("0")
        self.input_weld_a = QLineEdit("4")
        self.input_weld_length = QLineEdit("0")
        self.input_handrail_enabled = QCheckBox("Handlauf aktiv")
        self.input_handrail_enabled.setChecked(False)
        self.input_handrail_sides = QComboBox()
        self.input_handrail_sides.addItems(["einseitig", "beidseitig"])
        self.input_handrail_sides.setCurrentText("beidseitig")
        self.input_handrail_kg = QLineEdit("4.2")
        self.input_handrail_height = QLineEdit("1000")
        self.input_supports_enabled = QCheckBox("Stuetzen aktiv")
        self.input_supports_enabled.setChecked(False)
        self.input_support_layout = QComboBox()
        self.input_support_layout.addItems(get_available_support_layouts())
        self.input_support_count = QLineEdit("0")
        self.input_support_unit_kg = QLineEdit("8.0")
        self.tread_info_label = QLabel("")
        self.tread_info_label.setWordWrap(True)

        stair_form = QFormLayout()
        stair_form.addRow(
            self._form_label("Geschosshoehe [mm]", "height"), self.input_height
        )
        stair_form.addRow(self._form_label("Auftritt [mm]", "going"), self.input_going)
        stair_form.addRow(
            self._form_label("Treppenbreite [mm]", "width"), self.input_width
        )
        stair_form.addRow(
            self._form_label("Verfuegbarer Platz [mm]", "available_run"),
            self.input_available_run,
        )
        stair_form.addRow(
            self._form_label("Treppentyp", "stair_type"), self.input_stair_type
        )
        stair_form.addRow(
            self._form_label("Laufrichtung", "stair_direction"), self.input_stair_direction
        )
        stair_form.addRow(
            self._form_label("Orientierung", "stair_orientation"), self.input_stair_orientation
        )
        stair_form.addRow(
            self._form_label("Lagerung je Wange", "bearing"), self.input_bearing
        )
        stair_form.addRow(
            self._form_label("Wangenprofil", "profile"), self.input_profile
        )
        stair_form.addRow(
            self._form_label("Stahlguete", "steel_grade"), self.input_steel_grade
        )
        stair_form.addRow(
            self._form_label("Stufentyp", "tread_type"), self.input_tread_type
        )
        stair_form.addRow(
            self._form_label("Stufenblech [kg/m2]", "plate"), self.input_plate
        )
        stair_form.addRow(
            self._form_label("Nutzlastkategorie (DIN EN 1991-1-1)", "live_category"),
            self.input_live_category,
        )
        stair_form.addRow(
            self._form_label("Nutzlast [kN/m2]", "live_load"), self.input_live_load
        )
        stair_form.addRow(
            self._form_label("Normprofil", "norm_profile"), self.input_norm_profile
        )
        stair_form.addRow(
            self._form_label("Stahlguete fy [MPa]", "fy"), self.input_fy
        )
        stair_form.addRow(
            self._form_label("Nationaler Anhang", "national_annex"), self.input_national_annex
        )
        stair_form.addRow(
            self._form_label("Zusatzregelwerk", "regulation"), self.input_regulation
        )
        stair_form.addRow(
            self._form_label("Kopffreiheit [mm]", "headroom"), self.input_headroom
        )
        stair_form.addRow(
            self._form_label("Podestlaenge [mm] (0 = kein Podest)", "landing"),
            self.input_landing,
        )
        stair_form.addRow(
            self._form_label("Podestbreite [mm] (0 = Treppenbreite)", "landing_width"),
            self.input_landing_width,
        )
        stair_form.addRow(
            self._form_label("Podestlage", "landing_position"), self.input_landing_position
        )
        stair_form.addRow(
            self._form_label("Normalkraft N_Ed [kN]", "axial"), self.input_axial
        )
        stair_form.addRow(
            self._form_label("Stufen-Info", "tread_info"), self.tread_info_label
        )

        handrail_form = QFormLayout()
        handrail_top = QWidget()
        handrail_top_l = QHBoxLayout(handrail_top)
        handrail_top_l.setContentsMargins(0, 0, 0, 0)
        handrail_top_l.setSpacing(6)
        handrail_top_l.addWidget(self.input_handrail_enabled, 0)
        handrail_top_l.addWidget(
            self._make_info_button("handrail_enabled", "Handlauf"), 0, Qt.AlignmentFlag.AlignLeft
        )
        handrail_top_l.addStretch(1)
        handrail_form.addRow(handrail_top)
        handrail_form.addRow(
            self._form_label("Seiten", "handrail_sides"), self.input_handrail_sides
        )
        handrail_form.addRow(
            self._form_label("Profilgewicht [kg/m]", "handrail_kg"), self.input_handrail_kg
        )
        handrail_form.addRow(
            self._form_label("Handlaufhoehe [mm]", "handrail_height"),
            self.input_handrail_height,
        )

        supports_form = QFormLayout()
        supports_top = QWidget()
        supports_top_l = QHBoxLayout(supports_top)
        supports_top_l.setContentsMargins(0, 0, 0, 0)
        supports_top_l.setSpacing(6)
        supports_top_l.addWidget(self.input_supports_enabled, 0)
        supports_top_l.addWidget(
            self._make_info_button("supports_enabled", "Stuetzen"), 0, Qt.AlignmentFlag.AlignLeft
        )
        supports_top_l.addStretch(1)
        supports_form.addRow(supports_top)
        supports_form.addRow(
            self._form_label("Layout", "support_layout"), self.input_support_layout
        )
        supports_form.addRow(
            self._form_label("Stuetzenanzahl (0 = Auto)", "support_count"),
            self.input_support_count,
        )
        supports_form.addRow(
            self._form_label("Gewicht je Stuetze [kg]", "support_unit_kg"),
            self.input_support_unit_kg,
        )

        connection_form = QFormLayout()
        connection_form.addRow(
            self._form_label("Plattendicke Anschluss [mm]", "plate_thk"), self.input_plate_thk
        )
        connection_form.addRow(
            self._form_label("Plattenbreite [mm] (0 = Auto)", "plate_width"),
            self.input_plate_width,
        )
        connection_form.addRow(
            self._form_label("Plattenhoehe [mm] (0 = Auto)", "plate_height"),
            self.input_plate_height,
        )
        connection_form.addRow(
            self._form_label("Schrauben je Anschluss (0 = Auto)", "bolt_count"),
            self.input_bolt_count,
        )
        connection_form.addRow(
            self._form_label("Bolt Shear Rd [kN] (0 = Auto)", "bolt_rd"), self.input_bolt_rd
        )
        connection_form.addRow(
            self._form_label("Kehlnahtdicke a [mm]", "weld_a"), self.input_weld_a
        )
        connection_form.addRow(
            self._form_label("Nahtlaenge [mm] (0 = Auto)", "weld_length"), self.input_weld_length
        )

        self.result_label = QLabel("Noch keine Berechnung.")
        self.result_label.setWordWrap(True)
        self.result_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.result_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.result_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.stair_preview = StairSidePreview()
        self.input_detail_view = QCheckBox("Detailansicht aufklappen")
        self.input_detail_view.setChecked(False)
        self.input_detail_view.toggled.connect(self.on_detail_toggle)
        self.status_ampel = QLabel("Status: ⚪ Noch nicht berechnet")

        self.btn_calc = QPushButton("Berechnen")
        self.btn_dxf = QPushButton("DXF exportieren")
        self.btn_bom = QPushButton("BOM exportieren")
        self.btn_pdf = QPushButton("PDF exportieren")
        self.btn_project_new = QPushButton("Neu")
        self.btn_project_open = QPushButton("Oeffnen")
        self.btn_project_save = QPushButton("Speichern")
        self.btn_apply_tread = QPushButton("Empfohlene Stufe uebernehmen")
        self.btn_calc.clicked.connect(self.on_calculate)
        self.btn_dxf.clicked.connect(self.on_export_dxf)
        self.btn_bom.clicked.connect(self.on_export_bom)
        self.btn_pdf.clicked.connect(self.on_export_pdf)
        self.btn_project_new.clicked.connect(self.on_project_new)
        self.btn_project_open.clicked.connect(self.on_project_open)
        self.btn_project_save.clicked.connect(self.on_project_save)
        self.input_stair_type.currentTextChanged.connect(self.on_stair_type_changed)
        self.input_tread_type.currentTextChanged.connect(self.on_tread_type_changed)
        self.input_live_category.currentTextChanged.connect(self.on_live_category_changed)
        self.input_handrail_enabled.toggled.connect(self.on_handrail_toggled)
        self.input_supports_enabled.toggled.connect(self.on_supports_toggled)
        self.btn_apply_tread.clicked.connect(self.on_apply_recommended_tread)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.btn_project_new)
        btn_row.addWidget(self.btn_project_open)
        btn_row.addWidget(self.btn_project_save)
        btn_row.addWidget(self.btn_calc)
        btn_row.addWidget(self.btn_apply_tread)
        btn_row.addWidget(self.btn_dxf)
        btn_row.addWidget(self.btn_bom)
        btn_row.addWidget(self.btn_pdf)

        project_form = QFormLayout()
        project_form.addRow(
            self._form_label("Projektname", "project_name"), self.input_project_name
        )
        project_form.addRow(
            self._form_label("Projektnummer", "project_number"), self.input_project_number
        )
        project_form.addRow(
            self._form_label("Kunde", "customer"), self.input_customer
        )
        project_form.addRow(
            self._form_label("Standort", "location"), self.input_location
        )
        project_form.addRow(
            self._form_label("Bearbeiter", "engineer"), self.input_engineer
        )
        export_dir_wrap = QWidget()
        export_dir_layout = QHBoxLayout(export_dir_wrap)
        export_dir_layout.setContentsMargins(0, 0, 0, 0)
        export_dir_layout.addWidget(self.input_export_dir)
        export_dir_layout.addWidget(self.btn_export_dir)
        project_form.addRow(
            self._form_label("Exportordner", "export_dir"), export_dir_wrap
        )

        tab_widget = QTabWidget()
        tab_stair = QWidget()
        tab_stair.setLayout(stair_form)
        tab_handrail = QWidget()
        tab_handrail.setLayout(handrail_form)
        tab_supports = QWidget()
        tab_supports.setLayout(supports_form)
        tab_connection = QWidget()
        tab_connection.setLayout(connection_form)
        tab_project = QWidget()
        tab_project.setLayout(project_form)
        tab_widget.addTab(tab_project, "Projekt")
        tab_widget.addTab(tab_stair, "Treppe")
        tab_widget.addTab(tab_handrail, "Handlauf")
        tab_widget.addTab(tab_supports, "Stuetzen")
        tab_widget.addTab(tab_connection, "Anschluss")

        form_wrap = QWidget()
        form_v = QVBoxLayout(form_wrap)
        form_v.setContentsMargins(0, 0, 0, 0)
        form_v.addWidget(tab_widget)
        form_v.addLayout(btn_row)

        result_header = QLabel("Berechnung")
        f_res = result_header.font()
        f_res.setBold(True)
        result_header.setFont(f_res)

        result_inner = QWidget()
        result_inner_layout = QVBoxLayout(result_inner)
        result_inner_layout.setContentsMargins(8, 4, 8, 8)
        result_inner_layout.addWidget(self.result_label)

        result_scroll = QScrollArea()
        result_scroll.setWidgetResizable(True)
        result_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        result_scroll.setFrameShape(QFrame.Shape.NoFrame)
        result_scroll.setWidget(result_inner)
        result_scroll.setMinimumWidth(360)
        result_scroll.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        result_frame = QFrame()
        result_frame.setFrameShape(QFrame.StyledPanel)
        result_frame.setLineWidth(1)
        result_fl = QVBoxLayout(result_frame)
        result_fl.setContentsMargins(8, 8, 8, 8)
        result_fl.addWidget(result_header)
        result_fl.addWidget(self.input_detail_view)
        result_fl.addWidget(self.status_ampel)
        result_fl.addWidget(result_scroll, 1)

        preview_header = QLabel("Vorschau Seitenansicht")
        f_pr = preview_header.font()
        f_pr.setBold(True)
        preview_header.setFont(f_pr)

        preview_frame = QFrame()
        preview_frame.setFrameShape(QFrame.StyledPanel)
        preview_frame.setLineWidth(1)
        preview_fl = QVBoxLayout(preview_frame)
        preview_fl.setContentsMargins(8, 8, 8, 8)
        preview_fl.addWidget(preview_header)
        preview_fl.addWidget(self.stair_preview, 1)
        self.stair_preview.setMinimumWidth(280)

        content_row = QHBoxLayout()
        content_row.addWidget(form_wrap, 2)
        content_row.addWidget(result_frame, 2)
        content_row.addWidget(preview_frame, 2)

        layout = QVBoxLayout()
        layout.addLayout(content_row, 1)

        wrapper = QWidget()
        wrapper.setLayout(layout)
        self.setCentralWidget(wrapper)
        self._build_menu_bar()

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Bereit.")

        self._dirty = False

        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(60_000)
        self._autosave_timer.timeout.connect(self._autosave)
        self._autosave_timer.start()

        self.last_input: StairInput | None = None
        self.last_result = None
        self.last_summary_lines: list[str] = []
        self.last_detail_lines: list[str] = []
        self.on_stair_type_changed(self.input_stair_type.currentText())
        self.on_tread_type_changed(self.input_tread_type.currentText())
        self.on_live_category_changed(self.input_live_category.currentText())
        self.on_handrail_toggled(self.input_handrail_enabled.isChecked())
        self.on_supports_toggled(self.input_supports_enabled.isChecked())
        self._connect_live_validation()
        self._apply_parameter_tooltips()
        self._load_last_state()
        self.validate_inputs()

    def _make_info_button(self, help_key: str, popup_title: str) -> QToolButton:
        """Hilfe neben dem Parameter: sichtbares [?] (kein reines System-Icon — unter Linux oft leer)."""
        text = PARAM_HELP[help_key]
        btn = QToolButton()
        btn.setText("?")
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        f = btn.font()
        f.setBold(True)
        if f.pointSizeF() < 9.0:
            f.setPointSize(9.0)
        btn.setFont(f)
        # Rahmen (reines System-Icon [SP_DialogHelpButton] liefert unter Linux oft kein Pixmap)
        # Kein fixes font-color — passt besser zu hellem & dunklem Theme
        btn.setStyleSheet(
            "QToolButton {"
            "  border: 1px solid #888;"
            "  border-radius: 3px;"
            "  min-width: 1.1em; min-height: 1.1em;"
            "  background: rgba(0,0,0,0.04);"
            "}"
            "QToolButton:hover {"
            "  background: rgba(0,0,0,0.1);"
            "}"
        )
        btn.setToolTip(f"Hilfe: {text}")
        btn.setAutoRaise(True)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(22, 22)

        def _show() -> None:
            QMessageBox.information(self, popup_title, text)

        btn.clicked.connect(_show)
        return btn

    def _form_label(self, text: str, help_key: str) -> QWidget:
        """Beschriftung der Formularzeile mit sichtbarem Hilfe-Button neben dem Namen."""
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lay.addWidget(QLabel(text), 0)
        lay.addWidget(self._make_info_button(help_key, text), 0, Qt.AlignmentFlag.AlignLeft)
        lay.addStretch(1)
        return w

    def _apply_parameter_tooltips(self) -> None:
        """Dieselben Texte auf die Eingabefelder; zusaetzlich (?) neben jeder Ueberschrift in _form_label."""
        for w, k in (
            (self.input_project_name, "project_name"),
            (self.input_project_number, "project_number"),
            (self.input_customer, "customer"),
            (self.input_location, "location"),
            (self.input_engineer, "engineer"),
            (self.input_export_dir, "export_dir"),
            (self.btn_export_dir, "btn_export_dir"),
            (self.input_height, "height"),
            (self.input_going, "going"),
            (self.input_width, "width"),
            (self.input_available_run, "available_run"),
            (self.input_stair_type, "stair_type"),
            (self.input_stair_direction, "stair_direction"),
            (self.input_stair_orientation, "stair_orientation"),
            (self.input_bearing, "bearing"),
            (self.input_profile, "profile"),
            (self.input_steel_grade, "steel_grade"),
            (self.input_tread_type, "tread_type"),
            (self.input_plate, "plate"),
            (self.input_live_category, "live_category"),
            (self.input_live_load, "live_load"),
            (self.input_norm_profile, "norm_profile"),
            (self.input_fy, "fy"),
            (self.input_national_annex, "national_annex"),
            (self.input_regulation, "regulation"),
            (self.input_headroom, "headroom"),
            (self.input_landing, "landing"),
            (self.input_landing_width, "landing_width"),
            (self.input_landing_position, "landing_position"),
            (self.input_axial, "axial"),
            (self.tread_info_label, "tread_info"),
            (self.input_handrail_enabled, "handrail_enabled"),
            (self.input_handrail_sides, "handrail_sides"),
            (self.input_handrail_kg, "handrail_kg"),
            (self.input_handrail_height, "handrail_height"),
            (self.input_supports_enabled, "supports_enabled"),
            (self.input_support_layout, "support_layout"),
            (self.input_support_count, "support_count"),
            (self.input_support_unit_kg, "support_unit_kg"),
            (self.input_plate_thk, "plate_thk"),
            (self.input_plate_width, "plate_width"),
            (self.input_plate_height, "plate_height"),
            (self.input_bolt_count, "bolt_count"),
            (self.input_bolt_rd, "bolt_rd"),
            (self.input_weld_a, "weld_a"),
            (self.input_weld_length, "weld_length"),
            (self.input_detail_view, "input_detail_view"),
            (self.status_ampel, "status_ampel"),
            (self.result_label, "result_label"),
            (self.stair_preview, "stair_preview"),
        ):
            _param_tip(w, PARAM_HELP[k])
        for b, k in (
            (self.btn_calc, "btn_calc"),
            (self.btn_dxf, "btn_dxf"),
            (self.btn_bom, "btn_bom"),
            (self.btn_pdf, "btn_pdf"),
            (self.btn_project_new, "btn_project_new"),
            (self.btn_project_open, "btn_project_open"),
            (self.btn_project_save, "btn_project_save"),
            (self.btn_apply_tread, "btn_apply_tread"),
        ):
            _param_tip(b, PARAM_HELP[k])

    def _build_menu_bar(self) -> None:
        bar = self.menuBar()
        m_file = bar.addMenu("&Datei")
        a_new = QAction("Neu", self)
        a_new.setShortcut("Ctrl+N")
        a_new.triggered.connect(self.on_project_new)
        m_file.addAction(a_new)
        a_open = QAction("Oeffnen…", self)
        a_open.setShortcut("Ctrl+O")
        a_open.triggered.connect(self.on_project_open)
        m_file.addAction(a_open)
        a_save = QAction("Speichern", self)
        a_save.setShortcut("Ctrl+S")
        a_save.triggered.connect(self.on_project_save)
        m_file.addAction(a_save)
        m_file.addSeparator()
        a_quit = QAction("Beenden", self)
        a_quit.setShortcut("Ctrl+Q")
        a_quit.triggered.connect(self.close)
        m_file.addAction(a_quit)

        m_view = bar.addMenu("&Ansicht")
        a_ref = QAction("Vorschau aktualisieren", self)
        a_ref.setShortcut("F5")
        a_ref.triggered.connect(self._refresh_preview)
        m_view.addAction(a_ref)

        m_edit = bar.addMenu("&Bearbeiten")
        a_set = QAction("Einstellungen…", self)
        a_set.setShortcut("Ctrl+,")
        a_set.triggered.connect(self._open_dxf_settings)
        m_edit.addAction(a_set)

        m_extras = bar.addMenu("E&xtras")
        a_dxf = QAction("DXF-Export-Einstellungen…", self)
        a_dxf.triggered.connect(self._open_dxf_settings)
        m_extras.addAction(a_dxf)

        m_help = bar.addMenu("&Hilfe")
        a_about = QAction("Ueber OpenStair", self)
        a_about.triggered.connect(self._show_about)
        m_help.addAction(a_about)

    def _refresh_preview(self) -> None:
        if self.last_input is not None and self.last_result is not None:
            self.stair_preview.set_stair(self.last_input, self.last_result)

    def _open_dxf_settings(self) -> None:
        dlg = DxfSettingsDialog(self, initial=self.dxf_settings)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.dxf_settings = dlg.settings()

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "Ueber OpenStair",
            f"OpenStair v{__version__} - Stahltreppe Vorplanung\n\n"
            "Python, PySide6, DXF/PDF-Export.\n"
            "Vorbemessung; kein Ersatz fuer die Fachpruefung.",
        )

    def on_tread_type_changed(self, tread_type_name: str) -> None:
        self.tread_info_label.setText(get_tread_type_description(tread_type_name))
        preset_weight = get_tread_type_kg_per_m2(tread_type_name)
        if preset_weight is None:
            self.input_plate.setReadOnly(False)
            return
        self.input_plate.setText(f"{preset_weight:.2f}")
        self.input_plate.setReadOnly(True)

    def on_live_category_changed(self, category_name: str) -> None:
        load_by_category = NORM_CONFIG_DE["live_load_categories_kN_m2"]
        if category_name == "Benutzerdefiniert":
            self.input_live_load.setReadOnly(False)
            return
        self.input_live_load.setText(f"{load_by_category[category_name]:.2f}")
        self.input_live_load.setReadOnly(True)

    def on_stair_type_changed(self, stair_type: str) -> None:
        is_podest = stair_type == StairType.LANDING
        is_turned = stair_type in (StairType.QUARTER, StairType.HALF)
        self.input_landing.setEnabled(is_podest)
        self.input_landing_width.setEnabled(is_podest)
        self.input_landing_position.setEnabled(is_podest)
        self.input_stair_direction.setEnabled(is_podest or is_turned)
        self.input_stair_orientation.setEnabled(True)

    def on_handrail_toggled(self, enabled: bool) -> None:
        self.input_handrail_sides.setEnabled(enabled)
        self.input_handrail_kg.setEnabled(enabled)
        self.input_handrail_height.setEnabled(enabled)

    def on_supports_toggled(self, enabled: bool) -> None:
        self.input_support_layout.setEnabled(enabled)
        self.input_support_count.setEnabled(enabled)
        self.input_support_unit_kg.setEnabled(enabled)

    def _export_base_dir(self) -> Path:
        base = Path(self.input_export_dir.text().strip() or str(Path.cwd()))
        base.mkdir(parents=True, exist_ok=True)
        return base

    def on_apply_recommended_tread(self) -> None:
        if self.last_result is None:
            QMessageBox.information(self, "Hinweis", "Bitte zuerst berechnen.")
            return
        if self.last_result.recommended_tread_type is None:
            QMessageBox.information(
                self,
                "Hinweis",
                "Aktuelle Stufe ist bereits passend oder es gibt keine Empfehlung.",
            )
            return
        self.input_tread_type.setCurrentText(self.last_result.recommended_tread_type)
        self.on_calculate()

    def _connect_live_validation(self) -> None:
        widgets = [
            self.input_project_name,
            self.input_export_dir,
            self.input_height,
            self.input_going,
            self.input_width,
            self.input_available_run,
            self.input_plate,
            self.input_live_load,
            self.input_fy,
            self.input_headroom,
            self.input_landing,
            self.input_landing_width,
            self.input_axial,
            self.input_plate_thk,
            self.input_plate_width,
            self.input_plate_height,
            self.input_bolt_count,
            self.input_bolt_rd,
            self.input_weld_a,
            self.input_weld_length,
            self.input_handrail_kg,
            self.input_handrail_height,
            self.input_support_count,
            self.input_support_unit_kg,
        ]
        for w in widgets:
            w.textChanged.connect(self.validate_inputs)
            w.textChanged.connect(lambda *_a: self._mark_dirty())
        self.input_stair_type.currentTextChanged.connect(lambda _x: self.validate_inputs())
        self.input_stair_type.currentTextChanged.connect(lambda *_a: self._mark_dirty())
        self.input_live_category.currentTextChanged.connect(lambda _x: self.validate_inputs())
        self.input_live_category.currentTextChanged.connect(lambda *_a: self._mark_dirty())
        self.input_handrail_enabled.toggled.connect(lambda _x: self.validate_inputs())
        self.input_handrail_enabled.toggled.connect(lambda *_a: self._mark_dirty())
        self.input_supports_enabled.toggled.connect(lambda _x: self.validate_inputs())
        self.input_supports_enabled.toggled.connect(lambda *_a: self._mark_dirty())

    def _mark_dirty(self) -> None:
        self._dirty = True
        self._status_bar.showMessage("Ungespeicherte Aenderungen")

    def _autosave(self) -> None:
        if not self._dirty:
            return
        try:
            self._save_last_state()
            logger.info("Autosave abgeschlossen.")
        except Exception:
            logger.exception("Autosave fehlgeschlagen")

    def _confirm_discard_changes(self) -> bool:
        """Fragt den Benutzer, ob ungespeicherte Aenderungen verworfen werden sollen.
        Gibt True zurueck, wenn fortgefahren werden darf."""
        if not self._dirty:
            return True
        answer = QMessageBox.question(
            self,
            "Ungespeicherte Aenderungen",
            "Es gibt ungespeicherte Aenderungen. Trotzdem fortfahren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _set_field_error(self, widget: QLineEdit, msg: str | None) -> None:
        if msg is None:
            widget.setStyleSheet("")
            widget.setToolTip("")
            return
        widget.setStyleSheet("border: 1px solid #d9534f;")
        widget.setToolTip(msg)

    def _read_float(self, widget: QLineEdit, label: str, *, min_value: float | None = None) -> float | None:
        try:
            value = float(widget.text().strip())
        except ValueError:
            self._set_field_error(widget, f"{label}: Zahl erwartet")
            return None
        if min_value is not None and value < min_value:
            self._set_field_error(widget, f"{label}: muss >= {min_value:g} sein")
            return None
        self._set_field_error(widget, None)
        return value

    def validate_inputs(self) -> bool:
        errors = 0
        if not self.input_project_name.text().strip():
            self._set_field_error(self.input_project_name, "Projektname fehlt")
            errors += 1
        else:
            self._set_field_error(self.input_project_name, None)

        export_dir = Path(self.input_export_dir.text().strip() or ".")
        if not export_dir.exists():
            self._set_field_error(self.input_export_dir, "Exportordner existiert nicht")
            errors += 1
        else:
            self._set_field_error(self.input_export_dir, None)

        numeric_rules = [
            (self.input_height, "Geschosshoehe", 1.0),
            (self.input_going, "Auftritt", 1.0),
            (self.input_width, "Treppenbreite", 1.0),
            (self.input_available_run, "Verfuegbarer Platz", 1.0),
            (self.input_plate, "Stufenblech", 0.0),
            (self.input_live_load, "Nutzlast", 0.0),
            (self.input_fy, "fy", 0.0),
            (self.input_headroom, "Kopffreiheit", 1.0),
            (self.input_landing, "Podestlaenge", 0.0),
            (self.input_landing_width, "Podestbreite", 0.0),
            (self.input_axial, "Normalkraft", 0.0),
            (self.input_plate_thk, "Plattendicke", 0.1),
            (self.input_plate_width, "Plattenbreite", 0.0),
            (self.input_plate_height, "Plattenhoehe", 0.0),
            (self.input_bolt_count, "Schraubenanzahl", 0.0),
            (self.input_bolt_rd, "Bolt Shear Rd", 0.0),
            (self.input_weld_a, "Kehlnaht", 0.1),
            (self.input_weld_length, "Nahtlaenge", 0.0),
            (self.input_handrail_kg, "Handlauf kg/m", 0.1),
            (self.input_handrail_height, "Handlaufhoehe", 1.0),
            (self.input_support_count, "Stuetzenanzahl", 0.0),
            (self.input_support_unit_kg, "Stuetzengewicht", 0.1),
        ]
        for widget, label, min_val in numeric_rules:
            if self._read_float(widget, label, min_value=min_val) is None:
                errors += 1

        self._update_ampel(errors_count=errors, has_result=self.last_result is not None)
        return errors == 0

    def _update_ampel(self, errors_count: int, has_result: bool) -> None:
        if errors_count > 0:
            self.status_ampel.setText("Status: 🔴 Eingabefehler vorhanden")
            return
        if not has_result:
            self.status_ampel.setText("Status: 🟡 Eingaben ok, bitte berechnen")
            return
        if self.last_result and self.last_result.phase0_gate_ok:
            self.status_ampel.setText("Status: 🟢 Nachweise ok / Phase-0 freigegeben")
            return
        self.status_ampel.setText("Status: 🔴 Nachweise nicht freigegeben")

    def on_detail_toggle(self, _checked: bool) -> None:
        self._render_result_text()

    def _render_result_text(self) -> None:
        lines = self.last_summary_lines.copy()
        if self.input_detail_view.isChecked():
            lines.extend(self.last_detail_lines)
        if not lines:
            self.result_label.setText("Noch keine Berechnung.")
            return
        self.result_label.setText("\n".join(lines))

    def _collect_project_state(self) -> dict:
        return {
            "schema_version": PROJECT_SCHEMA_VERSION,
            "project_meta": {
                "project_name": self.input_project_name.text(),
                "project_number": self.input_project_number.text(),
                "customer": self.input_customer.text(),
                "location": self.input_location.text(),
                "engineer": self.input_engineer.text(),
                "export_dir": self.input_export_dir.text(),
            },
            "inputs": {
                "height": self.input_height.text(),
                "going": self.input_going.text(),
                "width": self.input_width.text(),
                "stair_type": self.input_stair_type.currentText(),
                "stair_direction": self.input_stair_direction.currentText(),
                "stair_orientation": self.input_stair_orientation.currentText(),
                "available_run": self.input_available_run.text(),
                "bearing": self.input_bearing.currentText(),
                "profile": self.input_profile.currentText(),
                "steel_grade": self.input_steel_grade.currentText(),
                "tread_type": self.input_tread_type.currentText(),
                "plate": self.input_plate.text(),
                "live_category": self.input_live_category.currentText(),
                "live_load": self.input_live_load.text(),
                "fy": self.input_fy.text(),
                "norm_profile": self.input_norm_profile.currentText(),
                "national_annex": self.input_national_annex.text(),
                "regulation": self.input_regulation.currentText(),
                "headroom": self.input_headroom.text(),
                "landing": self.input_landing.text(),
                "landing_width": self.input_landing_width.text(),
                "landing_position": self.input_landing_position.currentText(),
                "axial": self.input_axial.text(),
                "plate_thk": self.input_plate_thk.text(),
                "plate_width": self.input_plate_width.text(),
                "plate_height": self.input_plate_height.text(),
                "bolt_count": self.input_bolt_count.text(),
                "bolt_rd": self.input_bolt_rd.text(),
                "weld_a": self.input_weld_a.text(),
                "weld_length": self.input_weld_length.text(),
                "handrail_enabled": self.input_handrail_enabled.isChecked(),
                "handrail_sides": self.input_handrail_sides.currentText(),
                "handrail_kg": self.input_handrail_kg.text(),
                "handrail_height": self.input_handrail_height.text(),
                "supports_enabled": self.input_supports_enabled.isChecked(),
                "support_layout": self.input_support_layout.currentText(),
                "support_count": self.input_support_count.text(),
                "support_unit_kg": self.input_support_unit_kg.text(),
            },
            "dxf_export": self.dxf_settings.to_dict(),
        }

    def _apply_project_state(self, state: dict) -> None:
        meta = state.get("project_meta", {})
        inputs = state.get("inputs", {})
        dxf = state.get("dxf_export")
        if isinstance(dxf, dict) and dxf:
            self.dxf_settings = DxfExportSettings.from_dict(dxf)
        self.input_project_name.setText(meta.get("project_name", self.input_project_name.text()))
        self.input_project_number.setText(meta.get("project_number", ""))
        self.input_customer.setText(meta.get("customer", ""))
        self.input_location.setText(meta.get("location", ""))
        self.input_engineer.setText(meta.get("engineer", ""))
        self.input_export_dir.setText(meta.get("export_dir", self.input_export_dir.text()))
        self.input_height.setText(inputs.get("height", self.input_height.text()))
        self.input_going.setText(inputs.get("going", self.input_going.text()))
        self.input_width.setText(inputs.get("width", self.input_width.text()))
        self.input_stair_type.setCurrentText(inputs.get("stair_type", self.input_stair_type.currentText()))
        self.input_stair_direction.setCurrentText(inputs.get("stair_direction", self.input_stair_direction.currentText()))
        self.input_stair_orientation.setCurrentText(inputs.get("stair_orientation", self.input_stair_orientation.currentText()))
        self.input_available_run.setText(inputs.get("available_run", self.input_available_run.text()))
        self.input_bearing.setCurrentText(inputs.get("bearing", self.input_bearing.currentText()))
        self.input_profile.setCurrentText(inputs.get("profile", self.input_profile.currentText()))
        self.input_steel_grade.setCurrentText(inputs.get("steel_grade", self.input_steel_grade.currentText()))
        self.input_tread_type.setCurrentText(inputs.get("tread_type", self.input_tread_type.currentText()))
        self.input_plate.setText(inputs.get("plate", self.input_plate.text()))
        self.input_live_category.setCurrentText(inputs.get("live_category", self.input_live_category.currentText()))
        self.input_live_load.setText(inputs.get("live_load", self.input_live_load.text()))
        self.input_fy.setText(inputs.get("fy", self.input_fy.text()))
        self.input_norm_profile.setCurrentText(inputs.get("norm_profile", self.input_norm_profile.currentText()))
        self.input_national_annex.setText(inputs.get("national_annex", self.input_national_annex.text()))
        self.input_regulation.setCurrentText(inputs.get("regulation", self.input_regulation.currentText()))
        self.input_headroom.setText(inputs.get("headroom", self.input_headroom.text()))
        self.input_landing.setText(inputs.get("landing", self.input_landing.text()))
        self.input_landing_width.setText(inputs.get("landing_width", self.input_landing_width.text()))
        self.input_landing_position.setCurrentText(inputs.get("landing_position", self.input_landing_position.currentText()))
        self.input_axial.setText(inputs.get("axial", self.input_axial.text()))
        self.input_plate_thk.setText(inputs.get("plate_thk", self.input_plate_thk.text()))
        self.input_plate_width.setText(inputs.get("plate_width", self.input_plate_width.text()))
        self.input_plate_height.setText(inputs.get("plate_height", self.input_plate_height.text()))
        self.input_bolt_count.setText(inputs.get("bolt_count", self.input_bolt_count.text()))
        self.input_bolt_rd.setText(inputs.get("bolt_rd", self.input_bolt_rd.text()))
        self.input_weld_a.setText(inputs.get("weld_a", self.input_weld_a.text()))
        self.input_weld_length.setText(inputs.get("weld_length", self.input_weld_length.text()))
        self.input_handrail_enabled.setChecked(bool(inputs.get("handrail_enabled", self.input_handrail_enabled.isChecked())))
        self.input_handrail_sides.setCurrentText(inputs.get("handrail_sides", self.input_handrail_sides.currentText()))
        self.input_handrail_kg.setText(inputs.get("handrail_kg", self.input_handrail_kg.text()))
        self.input_handrail_height.setText(inputs.get("handrail_height", self.input_handrail_height.text()))
        self.input_supports_enabled.setChecked(bool(inputs.get("supports_enabled", self.input_supports_enabled.isChecked())))
        self.input_support_layout.setCurrentText(inputs.get("support_layout", self.input_support_layout.currentText()))
        self.input_support_count.setText(inputs.get("support_count", self.input_support_count.text()))
        self.input_support_unit_kg.setText(inputs.get("support_unit_kg", self.input_support_unit_kg.text()))
        self.on_stair_type_changed(self.input_stair_type.currentText())
        self.on_handrail_toggled(self.input_handrail_enabled.isChecked())
        self.on_supports_toggled(self.input_supports_enabled.isChecked())

    def _save_last_state(self) -> None:
        self.last_state_path.write_text(
            json.dumps(self._collect_project_state(), ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    def _load_last_state(self) -> None:
        if not self.last_state_path.exists():
            return
        try:
            state = json.loads(self.last_state_path.read_text(encoding="utf-8"))
            self._apply_project_state(state)
        except Exception:
            return

    def on_pick_export_dir(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Exportordner waehlen", self.input_export_dir.text())
        if selected:
            self.input_export_dir.setText(selected)
            self.validate_inputs()

    def on_project_new(self) -> None:
        if not self._confirm_discard_changes():
            return
        self.current_project_path = None
        self.input_project_name.setText("Neues Projekt")
        self.input_project_number.setText("")
        self.input_customer.setText("")
        self.input_location.setText("")
        self.input_engineer.setText("")
        self.input_export_dir.setText(str(Path.cwd()))
        self.result_label.setText("Neues Projekt gestartet.")
        self.last_result = None
        self.last_summary_lines = []
        self.last_detail_lines = []
        self._dirty = False
        self._status_bar.showMessage("Neues Projekt gestartet.")
        self._update_ampel(errors_count=0, has_result=False)

    def on_project_save(self) -> None:
        if self.current_project_path is None:
            default = Path(self.input_export_dir.text().strip() or str(Path.cwd())) / "project.openstair.json"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Projekt speichern",
                str(default),
                "OpenStair Projekt (*.openstair.json)",
            )
            if not file_path:
                return
            self.current_project_path = Path(file_path)
        self.current_project_path.write_text(
            json.dumps(self._collect_project_state(), ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        self._save_last_state()
        self._dirty = False
        self._status_bar.showMessage(f"Projekt gespeichert: {self.current_project_path.name}")
        QMessageBox.information(self, "Projekt", f"Projekt gespeichert:\n{self.current_project_path}")

    def on_project_open(self) -> None:
        if not self._confirm_discard_changes():
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Projekt oeffnen",
            str(Path(self.input_export_dir.text().strip() or str(Path.cwd()))),
            "OpenStair Projekt (*.openstair.json)",
        )
        if not file_path:
            return
        state = json.loads(Path(file_path).read_text(encoding="utf-8"))
        self._apply_project_state(state)
        self.current_project_path = Path(file_path)
        self._dirty = False
        self._status_bar.showMessage(f"Projekt geladen: {self.current_project_path.name}")
        self.validate_inputs()
        QMessageBox.information(self, "Projekt", f"Projekt geladen:\n{file_path}")

    def _read_input(self) -> StairInput:
        return StairInput(
            floor_height_mm=float(self.input_height.text()),
            going_mm=float(self.input_going.text()),
            stair_width_mm=float(self.input_width.text()),
            available_run_mm=float(self.input_available_run.text()),
            stair_type=self.input_stair_type.currentText(),
            stair_direction=self.input_stair_direction.currentText(),
            stair_orientation=self.input_stair_orientation.currentText(),
            norm_profile=self.input_norm_profile.currentText(),
            bearing_condition=self.input_bearing.currentText(),
            stringer_profile_name=self.input_profile.currentText(),
            steel_grade=self.input_steel_grade.currentText(),
            tread_type_name=self.input_tread_type.currentText(),
            tread_plate_kg_per_m2=float(self.input_plate.text()),
            live_load_kN_m2=float(self.input_live_load.text()),
            steel_yield_mpa=float(self.input_fy.text()),
            national_annex=self.input_national_annex.text().strip() or "NA Deutschland",
            regulation_profile=self.input_regulation.currentText(),
            headroom_clear_mm=float(self.input_headroom.text()),
            landing_length_mm=float(self.input_landing.text()),
            landing_width_mm=float(self.input_landing_width.text()),
            landing_position=self.input_landing_position.currentText(),
            axial_force_kN=float(self.input_axial.text()),
            plate_thickness_mm=float(self.input_plate_thk.text()),
            plate_width_mm=float(self.input_plate_width.text()),
            plate_height_mm=float(self.input_plate_height.text()),
            bolts_per_support=int(float(self.input_bolt_count.text())),
            bolt_shear_rd_kN=float(self.input_bolt_rd.text()),
            weld_throat_mm=float(self.input_weld_a.text()),
            weld_length_mm=float(self.input_weld_length.text()),
            handrail_enabled=self.input_handrail_enabled.isChecked(),
            handrail_sides=self.input_handrail_sides.currentText(),
            handrail_profile_kg_per_m=float(self.input_handrail_kg.text()),
            handrail_height_mm=float(self.input_handrail_height.text()),
            supports_enabled=self.input_supports_enabled.isChecked(),
            support_layout=self.input_support_layout.currentText(),
            support_count=int(float(self.input_support_count.text())),
            support_unit_weight_kg=float(self.input_support_unit_kg.text()),
        )

    def on_calculate(self) -> None:
        if not self.validate_inputs():
            QMessageBox.warning(self, "Eingabefehler", "Bitte rot markierte Felder korrigieren.")
            return
        try:
            data = self._read_input()
            result = calculate_stair(data)
            self.last_input = data
            self.last_result = result
            self.stair_preview.set_stair(data, result)
            self.last_summary_lines = [
                        f"Normbasis: {NORM_CONFIG_DE['standard_set']['basis']}",
                        f"NA/Zusatz/Profil: {data.national_annex} | {data.regulation_profile} | {result.norm_profile}",
                        f"Treppentyp: {result.stair_type}",
                        f"Richtung/Orientierung: {result.stair_direction} | {result.stair_orientation}",
                        f"Lagerung/Stahl: {result.bearing_condition} | {result.steel_grade}",
                        f"Steigungen: {result.riser_count}",
                        f"Stufen: {result.tread_count}",
                        f"Steigungshoehe: {result.riser_height_mm:.1f} mm",
                        f"Lauflinie/Wangenlaenge: {result.stringer_length_mm:.1f} mm",
                        f"Gesamtlaenge horizontal: {result.run_mm:.1f} mm",
                        (
                            f"Lauflaengen: F1={result.run_flight_1_mm:.1f} mm, "
                            f"F2={result.run_flight_2_mm:.1f} mm, "
                            f"Podest={result.landing_length_used_mm:.1f} mm"
                        ),
                        (
                            f"Podest LxB/Flaeche: {result.landing_length_used_mm:.1f} x "
                            f"{result.landing_width_used_mm:.1f} mm / {result.landing_area_m2:.2f} m2"
                        ),
                        (
                            f"Feldlaengen: {', '.join(f'{v:.1f}' for v in result.span_lengths_mm)} mm "
                            f"(massgebend {result.governing_span_mm:.1f} mm)"
                        ),
                        f"Treppenwinkel: {result.stair_angle_deg:.1f}°",
                        f"Profil: {result.selected_profile} ({result.profile_kg_per_m:.1f} kg/m)",
                        f"Stufentyp: {result.selected_tread_type}",
                        f"Stufen-Info: {result.tread_type_description}",
                        (
                            f"Breitencheck Stufe: {'OK' if result.tread_ok_for_width else 'NICHT OK'} "
                            f"(zulaessig bis {result.tread_allowable_width_mm:.0f} mm)"
                        ),
                        (
                            f"Empfehlung: {result.recommended_tread_type}"
                            if result.recommended_tread_type
                            else "Empfehlung: keine Aenderung noetig"
                        ),
                        f"Stahl Wangen (ca.): {result.approx_stringer_kg:.1f} kg",
                        f"Stahl Stufen (ca.): {result.approx_treads_kg:.1f} kg",
                        (
                            f"Handlauf: {result.handrail_length_m:.2f} m | "
                            f"{result.approx_handrail_kg:.1f} kg | {data.handrail_sides}"
                        ),
                        (
                            f"Stuetzen: {result.support_count} Stk | "
                            f"{result.approx_supports_kg:.1f} kg | Layout: {result.support_layout}"
                        ),
                        f"Stahl gesamt (ca.): {result.approx_total_kg:.1f} kg",
            ]
            self.last_detail_lines = [
                        f"q_d je Wange: {result.design_line_load_kN_m:.2f} kN/m",
                        f"M_Ed je Wange: {result.m_ed_kNm:.2f} kNm",
                        f"sigma_Ed: {result.sigma_ed_mpa:.1f} MPa",
                        f"Ausnutzung Biegung: {result.utilization_bending:.2f}",
                        (
                            f"N_Ed/N_pl,Rd: {result.n_ed_kN:.2f}/{result.n_pl_rd_kN:.2f} kN "
                            f"(eta_NM={result.utilization_interaction:.2f})"
                        ),
                        (
                            f"V_Ed je Wange: {result.v_ed_kN:.2f} kN | "
                            f"tau_Ed/tau_Rd: {result.tau_ed_mpa:.2f}/{result.tau_rd_mpa:.2f} MPa "
                            f"(eta={result.utilization_shear:.2f})"
                        ),
                        (
                            f"Stabilitaet: chi={result.buckling_chi:.2f} | "
                            f"N_b,Rd={result.n_b_rd_kN:.2f} kN "
                            f"(eta={result.utilization_buckling:.2f})"
                        ),
                        (
                            f"Biegedrillknicken: chi_LT={result.ltb_chi:.2f} | "
                            f"M_b,Rd={result.m_b_rd_kNm:.2f} kNm "
                            f"(eta={result.utilization_ltb:.2f})"
                        ),
                        (
                            f"Durchbiegung: {result.deflection_mm:.1f} / "
                            f"{result.deflection_limit_mm:.1f} mm "
                            f"(eta={result.utilization_deflection:.2f})"
                        ),
                        (
                            f"Schwingung: f1={result.natural_frequency_hz:.2f} Hz "
                            f"({'OK' if result.vibration_ok else 'NICHT OK'})"
                        ),
                        (
                            f"Anschluss: Platte eta={result.utilization_plate:.2f}, "
                            f"Schrauben eta={result.bolt_utilization:.2f}, "
                            f"Naht eta={result.weld_utilization:.2f} "
                            f"({'OK' if result.connections_ok else 'NICHT OK'})"
                        ),
                        (
                            "Geometriechecks: OK"
                            if result.geometry_ok
                            else "Geometriechecks: " + " | ".join(result.geometry_checks)
                        ),
                        (
                            "Plausibilitaet: OK"
                            if not result.plausibility_checks
                            else "Plausibilitaet: " + " | ".join(result.plausibility_checks)
                        ),
                        (
                            "Kollision: keine"
                            if not result.collisions
                            else "Kollision: " + " | ".join(result.collisions)
                        ),
                        (
                            "Phase-0-Gate: FREIGEGEBEN"
                            if result.phase0_gate_ok
                            else "Phase-0-Gate: NICHT FREIGEGEBEN - "
                            + " | ".join(result.phase0_gate_reasons)
                        ),
                        f"Nachweis: {'OK' if result.checks_ok else 'NICHT OK'}",
            ]
            self._render_result_text()
            self._update_ampel(errors_count=0, has_result=True)
            self._save_last_state()
            self._dirty = False
            self._status_bar.showMessage("Berechnung abgeschlossen.")
        except ValueError as exc:
            QMessageBox.warning(self, "Eingabefehler", str(exc))
            self._update_ampel(errors_count=1, has_result=False)
        except Exception as exc:
            logging.exception("Berechnung fehlgeschlagen")
            QMessageBox.critical(self, "Fehler", f"Berechnung fehlgeschlagen:\n{exc}")
            self._update_ampel(errors_count=1, has_result=False)

    def on_export_dxf(self) -> None:
        if self.last_input is None or self.last_result is None:
            QMessageBox.information(
                self,
                "Hinweis",
                "Bitte zuerst berechnen, dann exportieren.",
            )
            return

        default_path = self._export_base_dir() / "staircase_side_view.dxf"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "DXF speichern",
            str(default_path),
            "DXF Dateien (*.dxf)",
        )
        if not file_path:
            return

        try:
            export_stair_side_view_dxf(
                file_path, self.last_input, self.last_result, self.dxf_settings
            )
            QMessageBox.information(self, "Export", f"DXF gespeichert:\n{file_path}")
        except Exception as exc:
            logging.exception("DXF Export fehlgeschlagen")
            QMessageBox.critical(self, "Fehler", f"DXF Export fehlgeschlagen:\n{exc}")

    def on_export_bom(self) -> None:
        if self.last_input is None or self.last_result is None:
            QMessageBox.information(
                self,
                "Hinweis",
                "Bitte zuerst berechnen, dann exportieren.",
            )
            return

        default_path = self._export_base_dir() / "staircase_bom.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "BOM speichern",
            str(default_path),
            "CSV Dateien (*.csv)",
        )
        if not file_path:
            return

        try:
            bom_items = build_bom(self.last_input, self.last_result)
            export_bom_csv(file_path, bom_items)
            QMessageBox.information(self, "Export", f"BOM gespeichert:\n{file_path}")
        except Exception as exc:
            logging.exception("BOM Export fehlgeschlagen")
            QMessageBox.critical(self, "Fehler", f"BOM Export fehlgeschlagen:\n{exc}")

    def on_export_pdf(self) -> None:
        if self.last_input is None or self.last_result is None:
            QMessageBox.information(
                self,
                "Hinweis",
                "Bitte zuerst berechnen, dann exportieren.",
            )
            return

        default_path = self._export_base_dir() / "staircase_report.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "PDF speichern",
            str(default_path),
            "PDF Dateien (*.pdf)",
        )
        if not file_path:
            return

        try:
            bom_items = build_bom(self.last_input, self.last_result)
            export_report_pdf(file_path, self.last_input, self.last_result, bom_items)
            changelog_path = Path(file_path).parent / "CHANGELOG.md"
            append_release_changelog(changelog_path, self.last_input, self.last_result)
            QMessageBox.information(self, "Export", f"PDF gespeichert:\n{file_path}")
        except Exception as exc:
            logging.exception("PDF Export fehlgeschlagen")
            QMessageBox.critical(self, "Fehler", f"PDF Export fehlgeschlagen:\n{exc}")

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if not self._confirm_discard_changes():
            event.ignore()
            return
        try:
            self._save_last_state()
        except Exception:
            logger.exception("Zustand konnte beim Schliessen nicht gespeichert werden")
        super().closeEvent(event)


def main() -> None:
    setup_logging()
    _preflight_gui_linux()
    app = QApplication(sys.argv)
    icon_path = Path(__file__).resolve().parent / "app" / "openstair-icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
