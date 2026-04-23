import csv
import json
from functools import lru_cache
from pathlib import Path

PROFILE_JSON_FILE = Path(__file__).resolve().parent / "data" / "profiles_library.json"
PROFILE_CSV_FILE = Path(__file__).resolve().parent / "data" / "profiles_library.csv"
REQUIRED_KEYS = {
    "name",
    "series",
    "kg_per_m",
    "w_el_cm3",
    "i_cm4",
    "height_mm",
    "width_mm",
    "thickness_mm",
}
OPTIONAL_KEYS = {"a_v_cm2"}
SUPPORTED_SERIES = {"UPN", "UPE", "HEA", "HEB", "RHS", "SHS"}


def _as_positive_float(value: object, field: str, profile_name: str) -> float:
    try:
        out = float(value)
    except Exception as exc:
        raise ValueError(f"Profil {profile_name}: Feld {field} ist keine Zahl.") from exc
    if out <= 0:
        raise ValueError(f"Profil {profile_name}: Feld {field} muss > 0 sein.")
    return out


def _validate_library(raw_data: dict) -> None:
    for root_key in ("schema_version", "library_version", "source", "profiles"):
        if root_key not in raw_data:
            raise ValueError(f"Profilbibliothek: Root-Key {root_key} fehlt.")

    profiles = raw_data["profiles"]
    if not isinstance(profiles, list) or not profiles:
        raise ValueError("Profilbibliothek: profiles muss eine nicht-leere Liste sein.")

    names_seen: set[str] = set()
    for idx, profile in enumerate(profiles, start=1):
        if not isinstance(profile, dict):
            raise ValueError(f"Profilbibliothek: Eintrag #{idx} ist kein Objekt.")
        missing = REQUIRED_KEYS - set(profile.keys())
        if missing:
            raise ValueError(f"Profilbibliothek: Eintrag #{idx} hat fehlende Felder: {sorted(missing)}")

        name = str(profile["name"]).strip()
        if not name:
            raise ValueError(f"Profilbibliothek: Eintrag #{idx} hat leeren Namen.")
        if name in names_seen:
            raise ValueError(f"Profilbibliothek: Doppelter Profilname {name}.")
        names_seen.add(name)

        series = str(profile["series"]).strip().upper()
        if series not in SUPPORTED_SERIES:
            raise ValueError(
                f"Profil {name}: Reihe {series} nicht unterstuetzt. Erlaubt: {sorted(SUPPORTED_SERIES)}"
            )

        for field in (
            "kg_per_m",
            "w_el_cm3",
            "i_cm4",
            "height_mm",
            "width_mm",
            "thickness_mm",
        ):
            _as_positive_float(profile[field], field, name)

        for opt_field in OPTIONAL_KEYS:
            if opt_field in profile and profile[opt_field] not in (None, "", "0"):
                _as_positive_float(profile[opt_field], opt_field, name)


def _parse_csv_metadata(header_comment: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    cleaned = header_comment.lstrip("#").strip()
    for token in cleaned.split(";"):
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        meta[key.strip()] = value.strip()
    return meta


def _load_raw_from_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_raw_from_csv(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise ValueError("Profilbibliothek CSV ist leer.")

    metadata = {"schema_version": "1.0", "library_version": "unknown", "source": "CSV"}
    content_lines = lines
    if lines[0].startswith("#"):
        metadata.update(_parse_csv_metadata(lines[0]))
        content_lines = lines[1:]

    if not content_lines:
        raise ValueError("Profilbibliothek CSV enthaelt keine Datenzeilen.")

    reader = csv.DictReader(content_lines, delimiter=";")
    profiles = [dict(row) for row in reader]
    return {
        "schema_version": metadata["schema_version"],
        "library_version": metadata["library_version"],
        "source": metadata["source"],
        "profiles": profiles,
    }


def _resolve_library_path(path: Path | None) -> Path:
    if path is not None:
        return path
    if PROFILE_JSON_FILE.exists():
        return PROFILE_JSON_FILE
    if PROFILE_CSV_FILE.exists():
        return PROFILE_CSV_FILE
    raise ValueError("Keine Profilbibliothek gefunden (JSON/CSV).")


@lru_cache(maxsize=1)
def load_profile_library(path: Path | None = None) -> dict:
    resolved = _resolve_library_path(path)
    if resolved.suffix.lower() == ".json":
        raw_data = _load_raw_from_json(resolved)
    elif resolved.suffix.lower() == ".csv":
        raw_data = _load_raw_from_csv(resolved)
    else:
        raise ValueError(f"Nicht unterstuetztes Profilformat: {resolved.suffix}")

    _validate_library(raw_data)
    by_name = {str(p["name"]).strip(): p for p in raw_data["profiles"]}
    return {
        "schema_version": str(raw_data["schema_version"]),
        "library_version": str(raw_data["library_version"]),
        "source": str(raw_data["source"]),
        "format": resolved.suffix.lower().lstrip("."),
        "path": str(resolved),
        "profiles_by_name": by_name,
    }


def get_profile_names() -> list[str]:
    data = load_profile_library()
    return sorted(data["profiles_by_name"].keys())


def get_profile(profile_name: str) -> dict[str, float | str]:
    data = load_profile_library()
    profiles = data["profiles_by_name"]
    if profile_name not in profiles:
        raise ValueError(f"Unbekanntes Profil: {profile_name}")
    return profiles[profile_name]


def get_profile_library_metadata() -> dict[str, str]:
    data = load_profile_library()
    return {
        "schema_version": data["schema_version"],
        "library_version": data["library_version"],
        "source": data["source"],
        "format": data["format"],
        "path": data["path"],
    }

