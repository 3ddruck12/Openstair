"""Zentrale Enums und Versionskonstante fuer OpenStair."""

from enum import Enum

__version__ = "0.5.0"


class StairType(str, Enum):
    STRAIGHT = "Gerade Treppe"
    LANDING = "Podesttreppe"
    QUARTER = "Viertelgewendelte Treppe (90\u00b0)"
    HALF = "Halbgewendelte Treppe (180\u00b0)"


class StairDirection(str, Enum):
    RIGHT = "rechts"
    LEFT = "links"


class StairOrientation(str, Enum):
    N = "N"
    O = "O"
    S = "S"
    W = "W"


class BearingCondition(str, Enum):
    PINNED_PINNED = "gelenkig-gelenkig"
    FIXED_FIXED = "eingespannt-eingespannt"
    FIXED_PINNED = "eingespannt-gelenkig"


class SteelGrade(str, Enum):
    S235 = "S235"
    S275 = "S275"
    S355 = "S355"
    S420 = "S420"
    S460 = "S460"


class HandrailSide(str, Enum):
    SINGLE = "einseitig"
    BOTH = "beidseitig"


class SupportLayout(str, Enum):
    EQUAL = "gleichmaessig"
    ENDS_ONLY = "nur Antritt/Austritt"
    MANUAL = "manuell"


class NormProfile(str, Enum):
    DE = "DIN EN DE-NA"
    AT = "DIN EN AT-NA"
    CH = "DIN EN CH-NA"


class LandingPosition(str, Enum):
    CENTER = "mittig"
    TOP = "oben"
    BOTTOM = "unten"


class Regulation(str, Enum):
    NONE = "Keine Zusatzanforderung"
    WORKPLACE = "Arbeitsstaette"
    SPECIAL = "Sonderbau"
