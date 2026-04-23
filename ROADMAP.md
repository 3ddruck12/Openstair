# OpenStair Roadmap

Diese Roadmap beschreibt, was in eine vollwertige Linux-Anwendung fuer Stahl-Treppenplanung mit Python + PySide6 + DXF-Export rein sollte.
Prioritaet ist jetzt: **DIN EN zuerst vollstaendig**, damit die Anwendung als belastbare Grundlage fuer Bau/Fertigung genutzt werden kann.

## A) Ist-Stand: implementierte Funktionen (Anwendung)

Hier: was im Repository **tatsaechlich** enthalten ist (ohne vollstaendigen Norm- oder Prueffall-Abgleich). Dient der Einordnung neben den Ziel-Checklisten unten.

### A.1 Rechenkern und Daten

- [x] `calculations.py`: Treppenbemessung inkl. ULS/SLS, Stabilitaet, Anschluesse, Geometriechecks, Phase-0-Gate; Treppentypen **gerade**, **Podesttreppe**, **90°-Viertelgewendelt**, **180°-Halbgewendelt** (letztere statisch vereinfacht, nicht alle Vorschauen voll detailliert).
- [x] **Handlauf** und **Stuetzen** in der Bemessung und Mengenermittlung: optional, Eingabe (Hoehe, Seiten, Profil [kg/m]; Stuetzen: Anzahl, Layout, Einzelmasse, Vorschlagsanzahl je Layout), Ausgabe Laenge/Masse in **Ergebnis** und **BOM**; in `calculations.py` in **Gesamtmasse** und Stueckliste eingerechnet.
- [x] `norms.py`, Profiltabellen (`data/profiles_library.json`, `profile_library.py`), Stufen-/Belagbibliothek in `calculations.py`.
- [x] **Tests** (`pytest`): Golden Cases (Referenzwerte) und Profilbibliothek-Import (`tests/test_golden_cases.py`, `tests/test_profile_library.py`).

### A.2 GUI (PySide6, `main.py`)

- [x] Eingabe: **Projektstammdaten** (Name, Nummer, Kunde, Ort, Ingenieur), Exportordner, **Geometrie** (Geschosshoehe, Auftritt, Breite, verfuegbarer Lauf, Podestlaenge/-breite, Treppentyp, Richtung, Himmelsrichtung), **Lager/Profil/Stahl/Material**, Nutzlastkategorie, Normprofil, Auflagen, Stufenbelag, Plattenparameter, **Handlauf** (Gelaender: Laenge und Masse Rohr/Profil; optional, Hoehe, beidseitig/einseitig, kg/m), **Stuetzen** (optional, Anzahl, Layout, Einzelmasse) mit Toggle in der Maske.
- [x] **Berechnen** mit validierter Eingabe; Ergebnis als **scrollbare** Textansicht (Kennwerte, Nachweise, Hinweise, Phase-0-Gate).
- [x] **Grafische Vorschau** (`ui/stair_preview.py` / `StairSidePreview`): Register **Seitenansicht**, **Grundriss**, **3D (isometrisch)**; Aktualisierung nach Berechnung.
- [x] **Export**: DXF, **Stueckliste CSV**, **PDF-Berechnungsbericht**; beim PDF-Export **Changelog**-Eintrag optional (`CHANGELOG.md` neben Ziel, `append_release_changelog`). **DXF**: Layer-Namen, Textgroessen, Grundriss ja/nein, Abstand U-Treppe, optionale leere Layer Achsen/Schweiss – Dialog **Bearbeiten → Einstellungen** bzw. **Extras → DXF-Export-Einstellungen**, Speicher in `~/.openstair/dxf_settings.json` und in der Projektdatei.
- [x] **Projektdatei** `*.openstair.json` (**Speichern** / **Oeffnen**), **letzter Arbeitsstand** in `~/.openstair/last_project_state.json` beim Start und nach Speichern.
- [x] **Fenster-Icon** `app/openstair-icon.png`, **Start** z. B. `run.sh` (venv/Python).
- [x] **Linux-Preflight** (`_preflight_gui_linux` in `main.py`): Hinweis bei fehlendem Display, fehlendem `libxcb-cursor0` (X11/Qt); Uebersteuerbar mit `OPENSTAIR_SKIP_QT_DEPS_CHECK=1`.

### A.3 Vorschau / Darstellung (Details)

- [x] **Seitenansicht**: Abwicklung; Podest: zwei Laeufe + Podest; 90°: eigener Abwicklungspfad; nicht alle Typen gleich tief modelliert.
- [x] **Grundriss**: an **DXF-Logik** angelehnt (L-U-Formen, Aufteilungen); U-Podest: **Mittel-Podest**-Anmutung, **gespiegelte** Draufsicht (Wende links), **Zwischenraum**-Bemassung, leichte **Rost-Andeutung**; 90°-L-Grundriss mit `_l_quarter_geometry`.
- [x] **3D-Isometrie** (30°-Projektion, kein OpenGL): Standard: „Band“ entlang **Mittellinie**; **Podesttreppe** zusaetzlich: **Wangen-Kontur**, Stufen/Stuerze, Podestkoerper, 2. Lauf, **Handlauffuehrung** (Hilfslinien in Handlaufhoehe, kein Gelaender mit Staendern in 3D), **Eckstuetzen**-Andeutung (Podest), Mittellinie und Schatten. Andere Treppen: keine separaten Stuetzen-Grafiken in der 3D-Vorschau.

### A.4 DXF-Export (`export/dxf/`, Einstiegs-Import `dxf_export.py`)

- [x] **Seitenansicht** und **Grundriss** in einer DXF-Datei (u. a. Schichten Geometrie, Bemaßung, Notizen) – im Wesentlichen schemaorientiert, keine vollautomatische Masskette wie in Abschnitt 4 angestrebt.

### A.5 Bewusst nicht oder nur teilweise

- [x] **Handlauf- und Stuetzen-Mengen** sind in **Berechnung, Ergebnistext, BOM und PDF** enthalten (siehe A.1/A.2).
- [~] 3D/DXF: **drehbarer** Viewer, Photorealistik, vollstaendiges **Gelaender** (Staender, Fuellungen) als **CAD-** oder **IFC/STEP-**Modell; **Bauteil-**CAD-Export allgemein offen, siehe Abschnitt 1 und 4.
- [~] Vorschau = **schematisch**; verbindlich bleibt Berechnung + geprueftes PDF, nicht der Bildschirm.

## 0) DIN EN Freigabe (MUSS vor allem anderen fertig sein)

### 0.0 Normen-MVP (Start jetzt)

- [x] DIN-EN/NA-Parameter als zentrale Konfiguration festziehen (keine verstreuten Konstanten).
- [x] Lastmodell-Defaults auf normkonforme Kategorien abbilden (mit dokumentierter Quelle).
- [x] ULS-Mindestset im Rechenkern finalisieren: Biegung + Querkraft.
- [x] SLS-Mindestset im Rechenkern finalisieren: Durchbiegung mit klarem Grenzwert.
- [x] PDF-Reporting fuer jeden Nachweis um Formel, Einheiten und Grenzwertvergleich ergaenzen.
- [x] 3-5 Referenzfaelle (Handrechnung) definieren und als Golden Cases in Tests ablegen.
- [x] Phase-0-Gate festlegen: Nur bei 100% Pflichtnachweisen + Referenztests = freigegeben.

### 0.1 Normgrundlage (Deutschland)

- [x] DIN EN 1990 (Grundlagen der Tragwerksplanung)
- [x] DIN EN 1991-1-1 + NA (Einwirkungen/Nutzlasten inkl. Nutzungskategorien)
- [x] DIN EN 1993-1-1 + NA (Stahlbau-Nachweise)
- [x] DIN EN 1090 (Ausfuehrungsklassen, Fertigungsanforderungen)
- [x] Optional je Projekt: Landesbauordnung/Arbeitsstaettenvorgaben

### 0.2 Verpflichtende Nachweise im Rechenkern

- [x] Geometrie-/Gebrauchstauglichkeit:
  - [x] Schrittmassregel, Steigungsgrenzen, Auftrittsgrenzen
  - [x] Kopffreiheit, Mindestlaufbreiten, Podestregeln
- [x] ULS:
  - [x] Biegung, Querkraft
  - [x] Interaktion Biegung/Normalkraft (falls erforderlich)
  - [x] Stabilitaet (Kippen/Beulen/Knicknachweise je Bauteiltyp)
- [x] SLS:
  - [x] Durchbiegung mit normgerechtem Grenzwert
  - [x] Schwingungs-/Komfortkriterium (falls gefordert)
- [x] Anschluss-/Detailnachweise:
  - [x] Kopf-/Fussplatten
  - [x] Schrauben/Schweissnaehte in Lastpfadrichtung

### 0.3 Normparameter und Dokumentation

- [x] Nationaler Anhang als Pflichtparameter im Projekt.
- [x] Lastkategorien mit normkonformen Voreinstellungen.
- [x] Materialteilsicherheitsbeiwerte transparent ausgeben.
- [x] Jeder Nachweis im PDF mit Formel, Einheiten und Ergebnis dokumentieren.

### 0.4 Freigabekriterien fuer "baubar"

- [x] Alle Pflichtnachweise = OK.
- [x] PDF-Bericht enthaelt Normverweise, Eingaben, Lastansaetze, Nachweistabellen.
- [x] Plaene (DXF) enthalten alle baurelevanten Maße/Detailangaben.
- [x] Rechenkern gegen Referenzfaelle verifiziert.
- [ ] QA-Freigabe mit Versionsstand und Aenderungsprotokoll.
  - [x] QA-Release-Checkliste erstellt (`QA_RELEASE_CHECKLIST.md`)
  - [x] Changelog-Mechanismus beim PDF-Export umgesetzt (`CHANGELOG.md`)

## 1) Produktziel und Scope

- [x] Zielgruppe definiert:
  - Primaer: Schlosserei/Metallbau (Angebot, Vorplanung, Mengenschaetzung)
  - Sekundaer: Statik-Vorplanung und technischer Vertrieb
- [x] Abgrenzung klar dokumentiert:
  - OpenStair liefert Vorbemessung und technische Vorplanung
  - Kein verbindlicher statischer Nachweis ohne qualifizierte Fachpruefung
- [x] Unterstuetzte Treppentypen festgelegt:
  - [x] gerade Treppe (MVP/aktiv)
  - [x] Podesttreppe (Rechenkern + Vorschau + DXF-Grundriss, U-Ansicht)
  - [~] Viertelgewendelte Treppe (90°) (Rechenkern + Vorschau/3D/Grundriss, vereinfachte Modellannahmen)
  - [~] Halbgewendelte Treppe (180°) (Rechenkern; Vorschau weniger detailliert als Podest)
- [x] Exportziele festgelegt:
  - [x] DXF 2D (Pflicht)
  - [x] PDF Bericht (Pflicht)
  - [ ] optional IFC/STEP (spaeter)

## 2) Berechnungs-Kern

- [x] Geometrie-Modul robust machen:
  - [x] Schrittmassregel (2s + a)
  - [x] Plausibilitaetspruefungen (Mindest-/Maximalwerte)
  - [x] Kollisions- und Kopffreiheitscheck
- [ ] Lastmodell erweitern:
  - [x] Eigenlasten aus Profil + Stufen + Belag
  - [x] Nutzlast nach Nutzungskategorie
  - [x] Lastkombinationen (ULS/SLS)
- [x] Tragwerksmodell je Wange:
  - [x] Lagerungsvarianten (gelenkig, eingespannt, gemischt)
  - [x] Feldlaengen und Teilsysteme (mit Podest)
- [x] Nachweise:
  - [x] Biegung
  - [x] Querkraft
  - [x] Durchbiegung
  - [x] optional Schwingungskomfort
- [x] Materialdaten:
  - [x] S235/S355 etc.
  - [x] E-Modul, Dichte, Teilsicherheitsbeiwerte

## 3) Profilbibliothek und Datenhaltung

- [x] Profilbibliothek auslagern (JSON/CSV statt hardcoded).
- [x] Unterstuetzte Reihen:
  - [x] UPN/UPE
  - [x] HEA/HEB
  - [x] RHS/SHS
- [x] Daten je Profil:
  - [x] Gewicht [kg/m]
  - [x] Flaechentraegheitsmomente
  - [x] Widerstandsmomente
  - [x] Hoehe/Breite/Wandstaerke
- [x] Validierte Import-Pipeline bauen:
  - [x] Datenquelle dokumentieren
  - [x] Versionierung der Tabellen

## 4) DXF-Engine

- [~] Layer-Standard definieren (Namen editierbar, optional leere Layer; Speicher `~/.openstair/dxf_settings.json` +Projektdatei):
  - [x] Geometrie
  - [x] Bemaßung
  - [~] Achsen (optional leerer Layer, Anlage waehlbar)
  - [x] Text/Notizen
  - [~] Schweiß-/Fertigungsinfos (optional leerer Layer, Anlage waehlbar)
- [ ] Zeichnungsinhalte erweitern:
  - [x] Seitenansicht (`export/dxf/side_view.py`, modelspace)
  - [x] Grundriss (optional per `DxfExportSettings.include_plan_view`)
  - [ ] Detailschnitte Fuss/Kopf: zusaetzliche Geometrie + `INSERT`/Unterbloecke, eigener Massstab/Layer, keine Duplikation der Seitenansicht-Logik (Refaktor-Hilfsfunktionen)
- [ ] Bemaßungslogik (`ezdxf`, naechste Schritte):
  - [ ] Massketten: gestaffelte `DIMENSION`/Hilfspunkte, konstante `dimstyle`-Parameter, eine Funktion pro Kettentyp (horizontal/vertikal entlang Treppenpolyline)
  - [ ] Hoehenkoten: vertikale `DIMENSION` / Y-Abstaende mit gemeinsamem Nullpunkt (Referenzlinie), optional `dimlfac`
  - [~] Steigung/Auftritt: `TEXT` Schrittmass `2h+a` inkl. Ziel aus `NORM_CONFIG_DE`; erstes Stufenmass vertikal (`DIMENSION`); vollstaendige Kette/Auftritt je Stufe offen
  - [ ] Hilfslinien: dedizierte Layer/Linetypes (`doc.linetypes`), Offset-Geometrie vs. Rohlinie, Abstaende parametrierbar in `DxfExportSettings`
- [~] Plot-Setup (DXF-Struktur):
  - [ ] `LAYOUT` + Papiergroesse (Layout-Attribute, Plotsettings / Zeichnungsfenster in mm)
  - [ ] `VIEWPORT` + Massstab (`vp.dxf.scale` bzw. Einheiten `INSUNITS`, konsistent mit Modellkoordinaten)
  - [ ] Trennung Modellbereich vs. Layout: Vorschau bleibt Modell; Plot-Ziel = Layout mit Viewport
  - [ ] Plankopf: `BLOCK` mit `ATTRIB` oder statischer `INSERT`, Daten aus Projekt-Dict/Metadaten
  - [x] Textgroessen (`DxfExportSettings.text_height_*`, dimstyle `OPENSTAIR` in `_setup_dim_style`)

## 5) GUI und UX (PySide6)

- [x] Strukturierte Eingabe-Masken (umgesetzt, siehe Abschnitt A.2):
  - [x] Projektstammdaten
  - [x] Geometrie
  - [x] Lasten/Normparameter
  - [x] Profilwahl, Handlauf/Stuetzen, Stufenbelag
- [~] Live-Validierung:
  - [~] `validate_inputs` / Eingabefehler-Dialog; keine vollstaendigen Feld-in-place-Meldungen
  - [x] Ampelstatus (Ampel-Widget) fuer Ueberblick
- [x] Ergebnisansicht:
  - [x] Kennwerte kompakt (Scrollbereich)
  - [ ] Detailansicht aufklappbar
  - [x] Warnungen/Empfehlungen, Phase-0-Gate, Plausibilitaet
- [x] Projektverwaltung (Basis):
  - [x] Neu/Oeffnen/Speichern (`*.openstair.json`)
  - [x] letzter Arbeitsstand (`~/.openstair/last_project_state.json`)
  - [x] Exportordner waehlbar, Exporte dorthin
- [x] Treppen-Vorschau: Seitenansicht, Grundriss, 3D-Register
- [x] Menueleiste: **Datei** (Neu, Oeffnen, Speichern, Beenden), **Ansicht** (Vorschau aktualisieren), **Bearbeiten** (Einstellungen → DXF), **Extras** (DXF-Export-Einstellungen), **Hilfe** (Ueber)

## 6) Berichtswesen

- [x] Automatischen Berechnungsbericht als PDF erzeugen:
  - [x] Eingabedaten
  - [ ] Annahmen
  - [ ] Rechenweg (kurz + detailliert)
  - [x] Nachweiswerte
  - [ ] DXF/Plaene als Verweis
- [x] Haftungshinweise und Versionsstand im Bericht ausgeben.

## 7) Qualitaetssicherung

- [x] Unit-/Referenz-Tests: `tests/test_golden_cases.py` (Rechenkern-Referenzwerte), `tests/test_profile_library.py`.
- [x] Golden Cases (Handrechnung) als Testdaten in Code ausgelagert bzw. abgeglichen.
- [ ] Regressionstests fuer DXF-Generierung.
- [ ] CI-Pipeline:
  - [ ] Lint
  - [ ] Test
  - [ ] Build
- [ ] Numerische Stabilitaetspruefungen fuer Grenzfaelle.

## 8) Architektur und Codequalitaet

- [~] Module sauber trennen:
  - [x] `core/geometry`, `core/loads`, `core/checks` (+ `core/models.py`)
  - [x] `export/dxf` (Shims: `dxf_export.py`, `dxf_settings.py` im Root)
  - [~] `ui/` (`ui/stair_preview`, `ui/dxf_settings_dialog`; Einstieg/`MainWindow` weiter `main.py`)
- [x] Typisierung verbessern (dataclasses + typing).
- [x] Logging-Konzept einfuehren (`config/logging_bootstrap.py`, Logger `openstair`, `OPENSTAIR_LOG_LEVEL` / `app_settings.json`).
- [~] Konfigurationsmanagement: **JSON** `~/.openstair/app_settings.json` (`config/app_settings.py`), DXF weiter `dxf_settings.json`; **TOML** optional spaeter; Beispiel `data/default_app_settings.json`.

## 9) Deployment fuer Linux

- [~] Verpackung:
  - [ ] `pip`-Installierbar (pyproject: Metadaten vorhanden, Paketlayout fuer `pip install .` fehlt)
  - [~] **GitHub Actions** `Release (Linux)`: .deb (amd64) + AppImage (x86_64) per `packaging/scripts/build-linux-release.sh` + `packaging/pyinstaller/openstair.spec` (siehe README)
- [x] Startskript `run.sh` (venv/Interpreter).
- [~] Desktop-Entry: Vorlage `packaging/openstair.desktop` (Exec/Icon-Pfad anpassen, ggf. nach `~/.local/share/applications/` kopieren); in .deb inkludiert.
- [x] Changelog-Mechanismus beim PDF-Export (`CHANGELOG.md`); **Versionsschema** projektseitig noch zu vereinheitlichen.
- [ ] Beispielprojekte als Demo mitliefern.

## 10) Priorisierte Umsetzungsreihenfolge

Status: `[x]` erledigt, `[~]` teilweise, `[ ]` offen.

### Phase 0 (jetzt, DIN EN vollstaendig)

- [x] Normbasis fest auf DIN EN + deutscher NA umsetzen. (zentrale Konfiguration in `norms.py`)
- [~] Pflichtnachweise ULS/SLS inkl. Anschlussdetails komplett implementieren. (weitgehend vorhanden, normativ noch nicht final)
- [~] PDF-Nachweisbericht auf Prueffallniveau bringen. (stark erweitert, aber noch nicht finaler Prueffallstandard)
- [~] Referenzfaelle + automatisierte Tests fuer jeden Nachweis. (Golden Cases vorhanden, Abdeckung noch nicht vollstaendig)
- [ ] Erst nach erfolgreicher Phase 0 weitere Funktionsausbauten. (derzeit nicht strikt eingehalten)

### Phase A (kurzfristig, 1-2 Wochen)

- [x] Profilbibliothek in JSON/CSV auslagern. (`data/profiles_library.json` + `profile_library.py`)
- [~] Lastmodell + Nachweise mit DIN-EN Parametern final absichern. (Parameter integriert, finale Absicherung offen)
- [~] GUI-Validierung und bessere Fehlermeldungen. (teilweise umgesetzt, keine vollstaendige Livevalidierung)
- [~] DXF: saubere Layer + Grundriss ergaenzen. (Grundriss umgesetzt, Layer/Fertigungsinfos weiter offen)

### Phase B (mittelfristig, 2-6 Wochen)

- [x] Podesttreppen: Kern + Vorschau + DXF-Grundriss (Lagerungsvarianten bleiben erweiterbar).
- [x] PDF-Bericht mit Kennwerten und Nachweiswerte (Tiefe/„Prueffall-PDF“ weiter offen, siehe Phase 0).
- [x] Projekt speichern/laden (JSON) + letzter Arbeitsstand.
- [~] Testabdeckung (Goldencases, Profile); [ ] CI.

### Phase C (langfristig)

- [ ] Anschlussdetails/Fertigungsausgabe.
- [ ] Erweiterte Treppentypen (gewendelt).

## 11) Offene Entscheidungen

- [ ] Nationaler Anhang spaeter optional auf AT/CH erweiterbar oder nur DE?
- [ ] Soll zusaetzlich ein Pruefmodus fuer "Vorbemessung" erhalten bleiben?
- [ ] Welche CAD-Zielsysteme muessen sicher kompatibel sein (AutoCAD, BricsCAD, etc.)?

## 12) Vollstaendigkeits-Check (neu)

- [ ] Projektdateiformat festlegen (Schema-Version, Rueckwaertskompatibilitaet, Migration).
- [ ] Daten-/Lizenzlage dokumentieren (Profiltabellen, Normbezug, Quellenrechte).
- [ ] Fehler- und Absturzstrategie definieren (autosave, recover, saubere Fehlermeldungen).
- [ ] Akzeptanzkriterien je Phase als Go/No-Go-Liste scharf definieren.
- [ ] Performance-Ziele definieren (max. Rechenzeit, max. DXF/PDF-Exportzeit).
- [ ] Nachvollziehbarkeit im Bericht staerken (Einheitenkonsistenz, Formelquelle, Rundungsregeln).
- [ ] Versionierte Beispiel- und Referenzprojekte fuer QS aufnehmen.
- [ ] Release-Checkliste aufnehmen (Smoke-Test Linux, Packaging, Changelog, Tagging).

