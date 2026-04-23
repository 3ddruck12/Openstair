# OpenStair – Technisches Audit

Erstellt: 2026-04-23
Bezug: Vollstaendige Code-Analyse aller 9 Quelldateien (~4100 LOC), 2 Testdateien, Roadmap, Normkonfiguration.

---

## Zusammenfassung

OpenStair ist eine solide Vorbemessungs-Anwendung mit funktionierendem Rechenkern, GUI, drei Vorschau-Tabs und drei Exportformaten. Die Grundstruktur traegt, aber der naechste Qualitaetssprung erfordert Arbeit an **Architektur**, **Testabdeckung**, **Normtreue** und **Robustheit**. Die folgenden Punkte sind nach Dringlichkeit sortiert: zuerst was die Ergebnisse verfaelschen kann, dann Wartbarkeit, dann Komfort.

---

## 1) Rechenkern – Korrektheit und Normkonformitaet

### 1.1 KRITISCH: Einheiteninkonsistenz Durchbiegung

```
q_n_per_mm = service_line_load        # kN/m
deflection = deflection_factor * q_n_per_mm * (l_mm**4) / (e_mpa * i_mm4)
```

Die Balkenformel erwartet Last in N/mm, aber `service_line_load` ist in **kN/m**. Numerisch gleich (1 kN/m = 1 N/mm), aber es fehlt ein expliziter Umrechnungskommentar. Bei kuenftiger Aenderung der Einheiten droht ein stiller Fehler.

**Empfehlung:** Variable umbenennen in `q_sls_N_per_mm` und expliziten Kommentar setzen, oder einheitlich mit SI-Basiseinheiten rechnen.

### 1.2 KRITISCH: Schubflaeche ist eine Naeherung ohne Herleitung

```python
approx_shear_area_mm2 = max(w_el_mm3 / 100.0, 1.0)
```

EC3 verlangt A_v nach EN 1993-1-1 §6.2.6 (profilspezifisch). Die Naeherung `W_el / 100` hat keinen normativen Bezug. Fuer HEA-Profile passt es grob, fuer RHS/SHS oder UPN kann die Abweichung gross sein.

**Empfehlung:** `a_v_mm2` (Schubflaeche) als Pflichtfeld in die Profilbibliothek aufnehmen. Alternativ: profilspezifische Formel nach EC3 §6.2.6(3).

### 1.3 HOCH: Kein Biegedrillknicken (LTB)

`buckling_chi` berechnet nur Druckstabknicken. Fuer Biegetraeger (Wangen unter Biegung!) ist **Biegedrillknicken (lateral-torsional buckling)** oft massgebend – besonders bei UPN und HEA ohne seitliche Halterung.

**Empfehlung:** Mindestens vereinfachten LTB-Nachweis nach EC3 §6.3.2 ergaenzen, mit chi_LT aus Schlankheitsgrad. Stufenanschluss als Gabellagerung auswerten.

### 1.4 HOCH: Knicklaenge pauschal = Systemlaenge

```python
l_mm = span_m * 1000.0
```

Fuer alle Lagerungsbedingungen wird die volle Feldlaenge als Knicklaenge angenommen. Bei eingespannten Lagern muss s_k < L sein (EC3 Tabelle, z. B. 0,5 L fuer beidseitig eingespannt).

**Empfehlung:** `BEARING_LIBRARY` um Knicklaengenfaktor `beta` erweitern und `l_cr = beta * L` verwenden.

### 1.5 MITTEL: Interaktionsnachweis zu konservativ

```python
utilization_interaction = (n_ed / n_pl_rd) + (m_ed / m_rd)
```

Die lineare Addition ist zwar auf der sicheren Seite, aber EC3 §6.3.3 erlaubt plastische Interaktion mit Exponenten. Fuer reine Treppenstatik (i. d. R. N_Ed ≈ 0) ist das unkritisch, aber bei hohen Axialkraeften ueberzeichnet.

### 1.6 MITTEL: Schwingungsnachweis vereinfacht

`f1 = (pi/2) * sqrt(EI / (m*L^4))` gilt nur fuer Einfeldtraeger gelenkig-gelenkig. Fuer eingespannte Lager aendert sich der Beiwert (z. B. 22.4 statt pi fuer beidseitig eingespannt).

**Empfehlung:** Schwingungsbeiwert lagerungsabhaengig machen.

### 1.7 NIEDRIG: Stufenanzahl-Rundung

```python
riser_count = max(2, round(data.floor_height_mm / target_riser))
```

`round()` kann je nach Python-Version Banker's Rounding (IEEE 754) verwenden. Fuer Stufenanzahl waere `ceil` oder ein explizites Verfahren transparenter.

---

## 2) Architektur und Codestruktur

### 2.1 HOCH: Monolithische Module

| Datei | Zeilen | Problem |
|---|---|---|
| `main.py` | 1372 | Gesamte GUI in einer Datei, `__init__` > 500 Zeilen |
| `calculations.py` | 802 | `calculate_stair` ist eine einzelne ~385-Zeilen-Funktion |
| `stair_preview.py` | 1025 | Viel Code-Duplizierung zwischen Treppentypen |

**Empfehlung (Paketstruktur):**
```
openstair/
  __init__.py
  __main__.py          # Einstieg: from openstair.app import main; main()
  core/
    geometry.py        # Stufenzahl, Laeufe, Schrittmass
    loads.py           # Lastermittlung, Kombinationen
    checks_uls.py      # Biegung, Querkraft, Knicken, LTB
    checks_sls.py      # Durchbiegung, Schwingung
    connections.py     # Anschlussnachweis
    gate.py            # Phase-0-Gate Logik
    types.py           # StairInput, StairResult, BomItem
  data/
    norms.py
    materials.py
    profiles_library.json
  ui/
    main_window.py
    input_tabs.py
    result_panel.py
    preview/
      side_view.py
      plan_view.py
      iso_view.py
  export/
    dxf_export.py
    pdf_report.py
    bom_csv.py
    dxf_settings.py
```

### 2.2 HOCH: God Function `calculate_stair`

Eine Funktion berechnet Geometrie, Lasten, 6 Nachweise, Anschluesse, Geometriechecks, Plausibilitaet, Kollision und Phase-0-Gate. Das erschwert:
- Einzelne Nachweise unabhaengig zu testen
- Fehler zu isolieren
- Neue Nachweise hinzuzufuegen

**Empfehlung:** Aufteilen in:
1. `compute_geometry(data) -> GeometryResult`
2. `compute_loads(data, geometry) -> LoadResult`
3. `check_uls(loads, profile, steel) -> UlsResult`
4. `check_sls(loads, profile, steel) -> SlsResult`
5. `check_connections(loads, data) -> ConnectionResult`
6. `check_phase0_gate(*results) -> GateResult`

### 2.3 MITTEL: Fragile Zustandsserialisierung

`_collect_project_state` und `_apply_project_state` mappen 40+ Felder manuell per String-Key. Wird ein Feld hinzugefuegt, aber in einer der beiden Methoden vergessen, geht der Wert verloren.

**Empfehlung:** Eingabefelder registrierungsbasiert verwalten (z. B. Dict `field_name → widget`) und serialisierung/deserialisierung automatisch daraus ableiten.

### 2.4 MITTEL: Magic Strings ueberall

```python
if data.stair_type == "Podesttreppe":
if data.handrail_sides == "beidseitig":
if data.support_layout == "nur Antritt/Austritt":
```

Diese Strings sind quer ueber 5 Dateien verteilt. Ein Tippfehler bricht die Logik still.

**Empfehlung:** `enum.Enum` oder `typing.Literal` verwenden:
```python
class StairType(str, Enum):
    STRAIGHT = "Gerade Treppe"
    LANDING = "Podesttreppe"
    QUARTER = "Viertelgewendelte Treppe (90°)"
    HALF = "Halbgewendelte Treppe (180°)"
```

### 2.5 NIEDRIG: Kein Logging

Keine einzige `logging`-Anweisung im Code. Bei Fehleranalyse (warum liefert die Berechnung X?) ist man blind.

**Empfehlung:** `logging.getLogger(__name__)` in jedem Modul, Debug-Level fuer Zwischenergebnisse.

---

## 3) GUI und UX

### 3.1 HOCH: Export blockiert den UI-Thread

`on_export_dxf`, `on_export_pdf` und `on_calculate` laufen synchron im Main-Thread. Bei grossen Dateien oder langsamer Platte friert das Fenster ein.

**Empfehlung:** `QThread` oder `concurrent.futures.ThreadPoolExecutor` mit einem Fortschrittsdialog.

### 3.2 HOCH: Keine Warnung bei ungespeicherten Aenderungen

`closeEvent` speichert still den letzten Zustand, aber warnt den Benutzer nicht, wenn ein Projekt geaendert, aber nicht gespeichert wurde.

**Empfehlung:** Dirty-Flag setzen bei jeder Eingabeaenderung, bei Close/Neu/Oeffnen nachfragen.

### 3.3 MITTEL: Keine Statusleiste

Die Anwendung hat keinen `QStatusBar`. Operationen wie Export geben nur MessageBoxen – keine laufende Rueckmeldung.

### 3.4 MITTEL: Keine "Letzte Dateien" Liste

Beim Start muss man immer ueber den Dialog oeffnen. Eine MRU-Liste in Datei > Zuletzt geöffnet spart Arbeitsschritte.

### 3.5 NIEDRIG: Kein Versionskennzeichen in der App

Weder im Fenstertitel noch im "Ueber"-Dialog wird eine Versionsnummer angezeigt. Bei QA-Freigabe ist unklar, welcher Stand laueft.

**Empfehlung:** `__version__` in `__init__.py`, anzeigen im Fenstertitel und PDF-Bericht.

---

## 4) Tests und Qualitaetssicherung

### 4.1 KRITISCH: Sehr geringe Testabdeckung

| Modul | Testdatei | Abdeckung |
|---|---|---|
| `calculations.py` | `test_golden_cases.py` | 8 Tests, nur Happy/Sad Paths |
| `profile_library.py` | `test_profile_library.py` | 4 Tests |
| `dxf_export.py` | – | **0 Tests** |
| `report_export.py` | – | **0 Tests** |
| `stair_preview.py` | – | **0 Tests** |
| `main.py` | – | **0 Tests** |
| `norms.py` | – | **0 Tests** |
| `dxf_settings.py` | – | **0 Tests** |

**Empfehlung (Prioritaet):**
1. **Rechenkern-Einheitentests**: Jede Berechnungsstufe einzeln testen (Geometrie, Lasten, ULS, SLS, Anschluss) mit bekannten Handrechenresultaten.
2. **Grenzwert-Tests**: Division by Zero, extreme Hoehen, winzige Profile, NaN-Eingaben.
3. **Regressionstests DXF**: Erzeuge DXF, pruefe programmatisch Layer-Anzahl und Entity-Typen.
4. **PDF Smoke-Test**: PDF erzeugen, pruefen dass Datei > 0 Bytes und gueltig.
5. **Serialisierungs-Roundtrip**: Projekt speichern → laden → alle Felder identisch.

### 4.2 HOCH: Keine CI-Pipeline

Kein `.github/workflows`, kein `tox.ini`, kein `Makefile`. Tests laufen nur manuell.

**Empfehlung:** Minimale GitHub Actions Pipeline:
```yaml
- pytest --tb=short
- ruff check .
- mypy --strict (schrittweise)
```

### 4.3 MITTEL: Kein Type-Checking

Trotz `dataclass` und Type-Hints gibt es keine `mypy`/`pyright` Konfiguration. Die Hints sind vorhanden, werden aber nicht verifiziert.

### 4.4 MITTEL: Kein Linter konfiguriert

`ruff` oder `flake8` fehlt in `requirements.txt` und es gibt keine Konfigurationsdatei (`pyproject.toml`, `.ruff.toml`).

---

## 5) Exporte

### 5.1 HOCH: PDF-Bericht hat keine automatische Seitenumbruch-Logik

```python
y -= step
# ... viele Zeilen spaeter ...
if y < 80:
    c.showPage()
```

Die `y`-Koordinate wird manuell verfolgt. Der Seitenumbruch wird nur **innerhalb der BOM-Schleife** geprueft. Wenn die Nachweisabschnitte laenger als eine Seite werden (z. B. viele Geometriechecks + Plausibilitaet), laeuft der Text ueber den Seitenrand.

**Empfehlung:** `line()`-Funktion um automatischen Seitenumbruch erweitern:
```python
def line(text, step=18):
    nonlocal y
    if y - step < MARGIN_BOTTOM:
        c.showPage()
        c.setFont(current_font, current_size)
        y = height - MARGIN_TOP
    c.drawString(50, y, text)
    y -= step
```

### 5.2 HOCH: DXF ohne echte Bemassung

Der DXF-Export verwendet nur `add_text` und `add_line` fuer Masse. Echte DXF-DIMENSION-Entities (die in CAD editierbar und skalierbar sind) fehlen.

**Empfehlung:** `ezdxf` bietet `msp.add_linear_dim()` und `msp.add_aligned_dim()` – diese fuer Hauptmasse verwenden.

### 5.3 MITTEL: BOM-Gewicht Anschlussplatten/Schrauben pauschal

```python
BomItem(position=4, ..., quantity=4.0, unit_weight_kg=2.5, total_weight_kg=10.0,
        note="Pauschalansatz fuer Vorplanung"),
```

Feste 10 kg Anschlussplatten und 1,92 kg Schrauben unabhaengig von Treppengroesse. Fuer eine Vorplanung akzeptabel, sollte aber bei groesseren Treppen skaliert werden.

### 5.4 NIEDRIG: CSV-Trennzeichen Semikolon

Semikolon als Delimiter ist in DE/AT ueblich (Excel-kompatibel), aber sollte dokumentiert oder konfigurierbar sein. International erwartet man Komma.

---

## 6) Daten und Konfiguration

### 6.1 HOCH: Stufentyp-Bibliothek hardcoded

`TREAD_TYPE_LIBRARY` ist direkt in `calculations.py` definiert. Die Profilbibliothek wurde bereits korrekt in JSON ausgelagert – die Stufentypen sollten denselben Weg gehen.

**Empfehlung:** `data/tread_types.json` analog `data/profiles_library.json`.

### 6.2 MITTEL: requirements.txt ohne Versionen

```
PySide6
ezdxf
reportlab
pytest
```

Kein Pinning. Ein `pip install` kann mit einer inkompatiblen Major-Version fehlschlagen.

**Empfehlung:** Mindestens Major-Versionen pinnen:
```
PySide6>=6.5,<7
ezdxf>=1.0,<2
reportlab>=4.0,<5
pytest>=7.0,<9
```

### 6.3 MITTEL: Materialbibliothek nur S235/S355

Nur zwei Stahlsorten. Fuer Stahl nach EN 10025-2 fehlen S275, S420, S460.

**Empfehlung:** `MATERIAL_LIBRARY` in `data/materials.json` auslagern und um gaengige Sorten erweitern.

### 6.4 NIEDRIG: Nationaler Anhang nur DE

`norms.py` enthaelt nur `NORM_CONFIG_DE`. Die Roadmap fragt ob AT/CH unterstuetzt werden soll – der Code hat keine Weiche dafuer.

**Empfehlung:** Beim Refactoring `NORM_CONFIG` als Dict-of-Dicts mit Laenderschluessel anlegen.

---

## 7) Robustheit und Sicherheit

### 7.1 HOCH: Keine Schema-Validierung fuer Projektdateien

`on_project_open` laedt JSON direkt und uebergibt es an `_apply_project_state`. Eine manipulierte oder veraltete Datei kann Felder ueberschreiben oder Crashes ausloesen.

**Empfehlung:** JSON-Schema-Version im Projektformat, Migrations-Logik fuer aeltere Versionen.

### 7.2 MITTEL: Breite Exception-Faenger

```python
except Exception as exc:  # noqa: BLE001
    QMessageBox.critical(self, "Fehler", f"...")
```

Alle Export- und Berechnungsmethoden fangen `Exception` generisch. Stack-Traces werden verschluckt. Der Benutzer sieht nur den Fehlertext, aber fuer Debugging ist der Traceback verloren.

**Empfehlung:** `logging.exception()` vor der MessageBox, damit der Fehler in einem Logfile landet.

### 7.3 MITTEL: Kein Autosave-Intervall

`_save_last_state()` wird nur bei Berechnen, Speichern und Schliessen aufgerufen. Wenn die Anwendung abstuerzt (z. B. durch Qt-Segfault), gehen alle Eingaben seit dem letzten Event verloren.

**Empfehlung:** Timer-basierter Autosave alle 60 Sekunden.

---

## 8) Deployment

### 8.1 MITTEL: Kein `pyproject.toml`

Das Projekt hat kein standardkonformes Python-Packaging. `pyproject.toml` wuerde `pip install -e .` und Tool-Konfiguration (ruff, mypy, pytest) zentralisieren.

### 8.2 MITTEL: Kein Desktop-Entry

Fuer eine Linux-Desktop-Anwendung fehlt `openstair.desktop` und eine Freedesktop-konforme Icon-Installation.

### 8.3 NIEDRIG: run.sh ohne Fehlerbehandlung bei Abhaengigkeiten

`run.sh` prueft ob Python existiert, aber nicht ob `PySide6`/`ezdxf`/`reportlab` installiert sind. Ein `ImportError` beim Start ist nicht benutzerfreundlich.

---

## 9) Priorisierte Massnahmen-Empfehlung

### Sofort (vor naechstem Release)

| # | Massnahme | Aufwand | Auswirkung |
|---|---|---|---|
| 1 | Schubflaeche `a_v_mm2` in Profilbibliothek aufnehmen | 2h | Korrekter Querkraftnachweis |
| 2 | Knicklaengenfaktor lagerungsabhaengig machen | 1h | Korrekter Stabilitaetsnachweis |
| 3 | Einheiten-Kommentar/Rename bei Durchbiegung | 15min | Wartbarkeit, Fehlervorbeugung |
| 4 | PDF-Seitenumbruch generisch machen | 1h | Kein Textabschnitt ueber Seitenrand |
| 5 | `requirements.txt` Version-Pinning | 15min | Reproduzierbare Builds |

### Kurzfristig (1-2 Wochen)

| # | Massnahme | Aufwand | Auswirkung |
|---|---|---|---|
| 6 | `calculate_stair` in Teilfunktionen aufteilen | 4h | Testbarkeit, Wartbarkeit |
| 7 | Magic Strings durch Enums ersetzen | 2h | Typsicherheit |
| 8 | 20+ Unit-Tests fuer Teilnachweise schreiben | 6h | Qualitaetssicherung |
| 9 | `TREAD_TYPE_LIBRARY` in JSON auslagern | 1h | Erweiterbarkeit |
| 10 | Warnung bei ungespeicherten Aenderungen | 1h | UX |
| 11 | Logging-Framework einfuehren | 2h | Debugging |
| 12 | `pyproject.toml` anlegen | 1h | Standard-Packaging |

### Mittelfristig (2-6 Wochen)

| # | Massnahme | Aufwand | Auswirkung |
|---|---|---|---|
| 13 | Paketstruktur `openstair/` einfuehren | 8h | Langfristige Wartbarkeit |
| 14 | LTB-Nachweis nach EC3 §6.3.2 | 6h | Normkonformitaet |
| 15 | CI-Pipeline (pytest + ruff + mypy) | 3h | Automatische QA |
| 16 | DXF echte DIMENSION-Entities | 4h | CAD-Kompatibilitaet |
| 17 | Exportvorgaenge in Worker-Thread | 4h | Kein UI-Freeze |
| 18 | Projektdatei Schema-Versionierung | 3h | Rueckwaertskompatibilitaet |
| 19 | PDF-Bericht Annahmen + Rechenweg | 6h | Prueffaehigkeit |

---

## 10) Positiv-Befunde

Was bereits gut funktioniert und beibehalten werden sollte:

- **Profilbibliothek** mit JSON+CSV Dualformat, Validierung, Versionierung – vorbildlich.
- **Phase-0-Gate** als zentraler Freigabemechanismus – gute Idee, konsequent umgesetzt.
- **Tooltip-System** (`PARAM_HELP` + `_form_label` + `_make_info_button`) – konsistent und hilfreich.
- **Vorschau-Tabs** (Seite/Grundriss/3D) – ohne OpenGL und trotzdem informativ.
- **DXF-Einstellungen** persistent + im Projekt gespeichert – durchdacht.
- **Live-Validierung** mit Ampelstatus – sofortiges Feedback.
- **Golden-Case Tests** – richtiger Ansatz, braucht nur mehr Abdeckung.
- **Linux-Preflight** (`_preflight_gui_linux`) – praxisnahe Fehlervermeidung.
- **Changelog bei PDF-Export** – gute QA-Praxis.

---

*Dieses Audit bezieht sich auf den Stand 2026-04-23. Fuer Rueckfragen zu einzelnen Punkten oder Hilfe bei der Umsetzung stehe ich zur Verfuegung.*
