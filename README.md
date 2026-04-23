# OpenStair (Python + PySide6)

**Repository:** [github.com/3ddruck12/Openstair](https://github.com/3ddruck12/Openstair)

Kleines Linux-Tool zur Vorplanung von Stahl-Treppen:

- Eingabe von Grundparametern (Geschosshoehe, Auftritt, Treppenbreite)
- Treppentypen: gerade, Podest, viertelgewendelt, halbgewendelt
- GUI-Reiter fuer `Handlauf` und separaten Reiter `Stuetzen` (mit An/Aus-Checkbox)
- Dynamische Treppenparameter je Treppentyp (Podestabmessung, Laufrichtung, Orientierung)
- Separater Anschluss-Reiter (Platte, Schrauben, Naht als Detailparameter)
- Projektreiter mit Stammdaten + Projektverwaltung (Neu/Oeffnen/Speichern)
- Live-Validierung direkt am Feld und Ampelstatus fuer Nachweise
- Detailansicht im Ergebnis aufklappbar
- Exporte standardmaessig pro Projektordner + letzter Arbeitsstand wird gemerkt
- Profilwahl (UPN/HEA/RHS aus kleiner Tabelle)
- Stufentyp-Auswahl fuer Gittertreppenstufen (mit hinterlegten kg/m2)
- Breitencheck der Stufe inkl. automatischer Typ-Empfehlung
- Lastannahmen (Nutzlast) und einfache Vorbemessung je Wange
- Berechnung von Stufenanzahl, Steigung, Lauflinie, Stahlbedarf
- DIN-EN-MVP Nachweise: ULS (Biegung, Querkraft, Interaktion N+M, Knicken)
- SLS: Durchbiegung + vereinfachter Schwingungscheck (f1)
- Geometriechecks: Schrittmassregel, Grenzwerte, Mindestlaufbreite, Kopffreiheit, Podestregel
- Kollisionscheck gegen verfuegbaren Platz
- Tragwerksmodell je Wange mit Lagerungsvarianten und Feldlaengen (Podest)
- Materialdaten via Stahlgueten S235/S355 (fy, E, Dichte)
- Profilbibliothek extern in `data/profiles_library.json`/`data/profiles_library.csv` (mit Validierung)
- Anschlusschecks: Kopf/Fussplatte, Schrauben, Schweissnaht (vereinfachte Vorbemessung)
- Export einer 2D-Seitenansicht **und** Grundriss als DXF (Layer fuer Geometrie, Bemassung, Notizen)
- BOM/Stueckliste als CSV exportieren
- PDF-Bericht mit Eingaben, Ergebnissen und BOM exportieren
- Phase-0 Gate Anzeige (freigegeben / nicht freigegeben)
- QA-Checkliste als `QA_RELEASE_CHECKLIST.md`
- Automatischer `CHANGELOG.md` Eintrag bei PDF-Export

## Schnellstart (Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

Tests ausfuehren:

```bash
pytest
```

### Release-Build (Linux: .deb + AppImage)

Auf **GitHub Actions** (Workflow `Release (Linux)`): bei **Tag** `v*` werden `openstair_*_amd64.deb` und `OpenStair-*-x86_64.AppImage` gebaut und an die Release-Assets angehaengt. Manuell: **Actions → Release (Linux) → Run workflow** (optional Versionsfeld).

Lokal (Ubuntu, `sudo` fuer `dpkg-deb`):

```bash
bash packaging/scripts/build-linux-release.sh
# Artefakte: packaging/_artifacts/
```

Profildaten und Versionierung:

- `PROFILE_DATA.md`

## Hinweis

Die Berechnung in diesem MVP ist fuer Vorplanung und Mengenschaetzung gedacht.
Sie ersetzt **keinen** statischen Nachweis durch eine qualifizierte Fachperson.
