# Profilbibliothek (Datenquelle und Versionierung)

Die Profilbibliothek liegt in:

- `data/profiles_library.json`
- `data/profiles_library.csv`

Standard ist JSON; falls JSON nicht vorhanden ist, wird CSV als Fallback geladen.

## Struktur und Versionierung

- `schema_version`: Versionsstand des JSON-Schemas
- `library_version`: Versionsstand der Profildaten
- `source`: kurze Quellen-/Herkunftsangabe
- `profiles`: Liste der Profile

### CSV-Format

- Erste Zeile optional als Metadaten-Kommentar:
  - `# schema_version=...;library_version=...;source=...`
- Danach Kopfzeile mit Feldern:
  - `name;series;kg_per_m;w_el_cm3;i_cm4;height_mm;width_mm;thickness_mm`

Jedes Profil enthaelt mindestens:

- `name`
- `series` (`UPN`, `UPE`, `HEA`, `HEB`, `RHS`, `SHS`)
- `kg_per_m`
- `w_el_cm3`
- `i_cm4`
- `height_mm`
- `width_mm`
- `thickness_mm`

## Validierte Import-Pipeline

Beim Start/Lesen wird die Bibliothek in `profile_library.py` validiert:

- Root-Keys vorhanden
- Profil-Liste nicht leer
- keine doppelten Profilnamen
- nur erlaubte Reihen
- alle numerischen Werte > 0

Fehlende/ungueltige Daten fuehren zu einem klaren Fehler (`ValueError`).

## Hinweis zur Quelle

Die Werte sind aktuell als **kompakte Vorplanungs-Referenz** gepflegt und muessen fuer produktiven Einsatz mit den verbindlichen Hersteller-/Normtabellen synchronisiert werden.
