"""Zentrale Enums und Versionskonstante fuer OpenStair."""

from enum import StrEnum

__version__ = "0.5.1"


class StairType(StrEnum):
    STRAIGHT = "Gerade Treppe"
    LANDING = "Podesttreppe"
    QUARTER = "Viertelgewendelte Treppe (90\u00b0)"
    HALF = "Halbgewendelte Treppe (180\u00b0)"


class StairDirection(StrEnum):
    RIGHT = "rechts"
    LEFT = "links"


class StairOrientation(StrEnum):
    N = "N"
    E = "O"
    S = "S"
    W = "W"


class BearingCondition(StrEnum):
    PINNED_PINNED = "gelenkig-gelenkig"
    FIXED_FIXED = "eingespannt-eingespannt"
    FIXED_PINNED = "eingespannt-gelenkig"


class SteelGrade(StrEnum):
    S235 = "S235"
    S275 = "S275"
    S355 = "S355"
    S420 = "S420"
    S460 = "S460"


class HandrailSide(StrEnum):
    SINGLE = "einseitig"
    BOTH = "beidseitig"


class SupportLayout(StrEnum):
    EQUAL = "gleichmaessig"
    ENDS_ONLY = "nur Antritt/Austritt"
    MANUAL = "manuell"


class NormProfile(StrEnum):
    DE = "DIN EN DE-NA"
    AT = "DIN EN AT-NA"
    CH = "DIN EN CH-NA"


class LandingPosition(StrEnum):
    CENTER = "mittig"
    TOP = "oben"
    BOTTOM = "unten"


class Regulation(StrEnum):
    NONE = "Keine Zusatzanforderung"
    WORKPLACE = "Arbeitsstaette"
    SPECIAL = "Sonderbau"
