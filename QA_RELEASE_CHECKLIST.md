# QA Release Checklist (OpenStair)

Diese Checkliste ist fuer die interne Freigabe vor einem baubaren Release gedacht.

## 1) Rechenkern / Normen

- [ ] Normbasis geprueft: DIN EN 1990 / 1991-1-1+NA / 1993-1-1+NA / 1090
- [ ] Nationaler Anhang korrekt im Projekt gesetzt
- [ ] Lastkategorie korrekt gewaehlt und dokumentiert
- [ ] ULS Nachweise: Biegung, Querkraft, Interaktion, Stabilitaet = OK
- [ ] SLS Nachweise: Durchbiegung, Schwingung = OK
- [ ] Geometriechecks: Schrittmass, Kopffreiheit, Laufbreite, Podestregel = OK
- [ ] Anschlusschecks: Platte, Schrauben, Naht = OK

## 2) Ergebnisdokumente

- [ ] PDF erzeugt und inhaltlich geprueft
- [ ] PDF enthaelt Normverweise, Eingaben, Lasten, Nachweistabellen, Formeln
- [ ] BOM CSV erzeugt und Plausibilitaet geprueft
- [ ] DXF erzeugt und baurelevante Masse/Notizen geprueft

## 3) Test und technische Qualitaet

- [ ] `pytest` erfolgreich
- [ ] Linter ohne neue Fehler
- [ ] Manuelle Smoke-Tests in GUI erfolgreich (Berechnen + Exporte)
- [ ] Keine offenen Blocker fuer den Release

## 4) Freigabeprotokoll

- [ ] Version festgelegt
- [ ] `CHANGELOG.md` Eintrag vorhanden
- [ ] Pruefende Person dokumentiert
- [ ] Datum/Uhrzeit dokumentiert
- [ ] Freigabestatus gesetzt: `FREIGEGEBEN` / `NICHT FREIGEGEBEN`

## Freigabevermerk

- Version:
- Geprueft von:
- Datum:
- Status:
- Kommentar:
