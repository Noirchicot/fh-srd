"""Class level-progression table parser for the French SRD 5.2.1.

CALIBRATED against the pinned FR PDF on 2026-08-08, one table per class
chapter (p.30-84). Twelve tables, 240 level rows, 0 anomalies.

The row mechanics are arithmetic on line counts and carry no language, so they
are imported from the English module rather than copied -- the same call
already made for `_dehyphenate_numbered`. What is French here is everything
that names something: the twelve classes, their chapter order, the anchors
that identify a table, and all thirty-one column labels.

WHAT FRENCH DID DIFFERENTLY, measured on its own pages rather than assumed
from the English calibration:

  * **The chapter order is not the English one.** French sorts its own class
    names, so the twelve tables come back as Barbare, Barde, Clerc, Druide,
    Ensorceleur, Guerrier, Magicien, Moine, Occultiste, Paladin, Rôdeur,
    Roublard -- Ensorceleur (Sorcerer) fifth where English has Fighter, and
    Roublard (Rogue) last where English has Wizard. Pairing tables with
    classes by position and NOT checking the page would have handed the
    Sorcerer's spell slots to the Fighter, silently, in a file that looks
    complete. That is why the anchor check is a refusal and not a warning.
  * **The Clerc table has no header text before its rows at all** (p.38):
    every header cell lands after the last row, including the class's own
    title. English never does this on any of its twelve pages. The parser
    reads the whole page for the label check, so it does not care -- recorded
    because "the header is missing" is the kind of observation that gets
    mistaken for a broken extract.
  * **French hyphenates its header cells mid-word** where English does not:
    Occultiste's own columns arrive as "Manifes-/tations/occultes",
    "Empla-/cements/de sort" and "Niveau des/emplace-/ments". They only
    reassemble into the declared labels because `_dehyphenate_numbered` runs
    before the label check; without it, five of the eight Occultiste columns
    would have been reported as absent from their own page.
  * **The dice column is lowercase.** French prints "d6" where English prints
    "D6" (Dé bardique, Arts martiaux, Attaque sournoise), which is why the
    cell pattern in the English module accepts both cases -- it is the same
    table read twice, not two conventions to normalise into one.
  * **Two classes elide "de" in their anchors, and not the same way in every
    phrase** -- the trap `parse_classes_fr.py` already paid for and documented:
    "Aptitudes de l'Ensorceleur" keeps the article, "Sous-classe d'Ensorceleur"
    drops it. Only the first shape is needed here, and it is reused from that
    module rather than re-derived.
"""

import re

from parse_class_progression_en import parse_pages
from parse_classes_fr import CLASSES, _ELIDED, _traits_needle
from parse_spells import _dehyphenate_numbered

# French's own cell vocabulary. The Moine's "Déplacement sans armure" column
# is printed in metres with a decimal COMMA -- "+3 m", "+4,50 m", "+7,50 m",
# "+9 m" -- where English prints "+10 ft.". Read as the source's own text
# either way; only the check that a trailing cell IS a cell differs.
CELL_RE = re.compile(r"^(?:—|\d+|\+\d+(?:,\d+)?(?: m)?|[Dd]\d+|\d+d\d+)$")

# Resource columns per class, in printed left-to-right order, then the number
# of spell-slot columns. Same shape as the English spec, independently read.
TABLES = {
    "Barbare": (["Rages", "Dégâts de Rage", "Bottes d’arme"], 0),
    "Barde": (["Dé bardique", "Sorts mineurs", "Sorts préparés"], 9),
    "Clerc": (["Conduit divin", "Sorts mineurs", "Sorts préparés"], 9),
    "Druide": (["Forme sauvage", "Sorts mineurs", "Sorts préparés"], 9),
    "Ensorceleur": (["Points de Sorcellerie", "Sorts mineurs", "Sorts préparés"], 9),
    "Guerrier": (["Second souffle", "Bottes d’arme"], 0),
    "Magicien": (["Sorts mineurs", "Sorts préparés"], 9),
    "Moine": (["Arts martiaux", "Points de Credo", "Déplacement sans armure"], 0),
    "Occultiste": (["Manifestations occultes", "Sorts mineurs", "Sorts préparés",
                    "Emplacements de sort", "Niveau des emplacements"], 0),
    "Paladin": (["Conduit divin", "Sorts préparés"], 5),
    "Rôdeur": (["Ennemi juré", "Sorts préparés"], 5),
    "Roublard": (["Attaque sournoise"], 0),
}

SLOT_BAND_LABEL = "Emplacements par niveau de sort"

SUBCLASS_PLACEHOLDER = "Aptitude de sous-classe"


def _table_needle(cls):
    return ("Aptitudes de l’%s" % cls if cls in _ELIDED
            else "Aptitudes du %s" % cls)


def needles(cls):
    """The core-traits box and the table's own title, either of which may be
    the only one present on the table's page."""
    return (_traits_needle(cls), _table_needle(cls))


def parse(pages, suspect_pages=()):
    return parse_pages(
        pages, suspect_pages, CLASSES, TABLES, needles, SLOT_BAND_LABEL,
        SUBCLASS_PLACEHOLDER, "fr", _dehyphenate_numbered, CELL_RE,
    )
