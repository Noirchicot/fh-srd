"""Weapon table parser for the French SRD 5.2.1.

CALIBRATED against the pinned FR PDF on 2026-08-03, the "Armes" table
(p.97, inside the "Équipement" chapter, p.95-106). Ported from
`parse_weapons_en.py` -- the table is row-coherent for the same reason
EN's is (wide enough to read as a single spanning PDF block per row,
re-measured rather than assumed per the brief's own warning that FR table
geometry is not guaranteed to match EN's), and the same sub-category
labels ("Armes courantes de corps à corps", etc.) are displaced as a group
to the page's end by the same `columns_of()` span-ratio artefact, and are
NOT captured here for the same reason.

THE HEADER WORD FOR "COST" DIFFERS BETWEEN THIS TABLE AND THE ARMOR TABLE
RIGHT AFTER IT -- "Prix" here, "Coût" there (parse_armor_fr.py) -- despite
both meaning the same thing and using the same currency units. Checked
rather than assumed identical: translating one table's header word onto
the other would have missed both tables' real header text.

WEAPON MASTERY ("Botte d'arme" -- the table's own sixth column header,
distinct from the word "Botte" used alone in the surrounding prose) has
the SAME field-boundary trap as EN's Mastery column: Properties is read
as "every line up to the first line that IS one of the eight known
mastery words". The eight, read off the table's own rows (not the EN
mastery names translated): Coup double, Écorchure, Enchaînement,
Ouverture, Poussée, Ralentissement, Renversement, Sape. ONE of them,
"Coup double", is TWO WORDS on a single physical line -- unlike every
EN mastery name, which is one word -- but that does not complicate
matching, since the whole line is still compared as one unit.

FIELD BOUNDARIES: Nom and Dégâts are always exactly one line each.
Propriétés can be the literal "—" (no properties: Masse d'armes, Fléau
d'armes, Morgenstern) and wraps across more than one physical line for
weapons whose Munitions range note pushes past the column width (Arbalète
légère, lourde, de poing; Arc long; Mousquet) -- the same shape as EN's
four wrapping Ammunition weapons, just not the identical four.

WEIGHT AND COST USE FRENCH UNITS AND PUNCTUATION, not a translation of
EN's regex: weight in kg or g with a comma decimal separator ("0,5 kg",
"125 g"), cost in French coin abbreviations (pc/pa/pe/po/pp for
cuivre/argent/électrum/or/platine) with a SPACE thousands separator
("1 500 po" -- checked on the armor table's Harnois row), rather than
EN's lb/GP-etc. and comma thousands separator. Weight can also be the
literal "—" (Fronde has none).

SARBACANE (Blowgun) DEALS A FLAT "1 perforant" INSTEAD OF A DICE
EXPRESSION -- the same fixed-damage exception EN's own `_DAMAGE_RE` already
carries (`^1\s+\S+$` alongside the `NdN` pattern), ported here rather than
re-derived, since it is the same weapon and the same rules text either
language just translates the damage type word for.

ONE ROW HAS NO NAME/DAMAGE LINE BREAK AT ALL, found by the parser
stopping dead at 21 weapons instead of 38 with zero anomalies (the "table
ended naturally" exit, not a caught error): "Hache à deux mains
1d12 tranchants" -- name and damage share ONE physical line, the only
weapon in the table where this happens, a PyMuPDF block-merge quirk tied
to this specific name's width rather than anything the source's own
layout intends differently for it. `_NAME_DAMAGE_RE` is tried only when
the ordinary two-line shape does not match at that position, so it does
not risk mis-splitting a normal name that is followed by its own damage
line one row down.
"""

import re

import canon
from parse_spells import _dehyphenate_numbered

MASTERY_PROPERTIES = {
    "Coup double", "Écorchure", "Enchaînement", "Ouverture", "Poussée",
    "Ralentissement", "Renversement", "Sape",
}

TABLE_HEADER = ["Nom", "Dégâts", "Propriétés", "Botte d’arme", "Poids", "Prix"]

_DAMAGE_RE = re.compile(r"^\d+d\d+(?:\s*\+\s*\d+)?\s+\S+$|^1\s+\S+$")
_NAME_DAMAGE_RE = re.compile(r"^(.+?)\s+(\d+d\d+(?:\s*\+\s*\d+)?\s+\S+|1\s+\S+)$")
_WEIGHT_RE = re.compile(r"^[\d,.\s]+\s?(?:kg|g)\.?$|^—$")
_COST_RE = re.compile(r"^[\d\s]+(?:pc|pa|pe|po|pp)$")

CHAPTER_START = "Équipement"


def _find_seq(stripped, seq, after=0):
    for i in range(after, len(stripped) - len(seq) + 1):
        if all(stripped[i + k] == seq[k] for k in range(len(seq))):
            return i
    return None


def parse_stream(lines, page_of):
    stripped = [l.strip() for l in lines]

    def page_at(i):
        return page_of[i] if i < len(page_of) else (page_of[-1] if page_of else 0)

    header = _find_seq(stripped, TABLE_HEADER)
    weapons, anomalies = [], []
    if header is None:
        anomalies.append({"page": 0, "line": 0, "detail": "Armes table header not found"})
        return weapons, anomalies

    i = header + len(TABLE_HEADER)
    while i < len(stripped) and not stripped[i]:
        i += 1

    while i < len(stripped):
        line = stripped[i]
        next_line = stripped[i + 1] if i + 1 < len(stripped) else ""
        combined = _NAME_DAMAGE_RE.match(line) if line else None
        if line and _DAMAGE_RE.match(next_line):
            name = line
            row_start = i
            i += 1
            damage = stripped[i]
            i += 1
        elif combined:
            name = combined.group(1)
            damage = combined.group(2)
            row_start = i
            i += 1
        else:
            break

        properties_lines = []
        guard_start = i
        while i < len(stripped) and stripped[i] not in MASTERY_PROPERTIES:
            properties_lines.append(stripped[i])
            i += 1
            if i - guard_start > 6:
                anomalies.append(
                    {"page": page_at(row_start), "line": row_start,
                     "detail": "weapon %r: no Botte d'arme word found within 6 lines" % name}
                )
                return weapons, anomalies
        if i >= len(stripped):
            anomalies.append(
                {"page": page_at(row_start), "line": row_start,
                 "detail": "weapon %r: table ended before a Botte d'arme value was found" % name}
            )
            break
        mastery = stripped[i]
        i += 1

        if i >= len(stripped) or not _WEIGHT_RE.match(stripped[i]):
            anomalies.append(
                {"page": page_at(row_start), "line": row_start,
                 "detail": "weapon %r: expected a weight value, found %r"
                           % (name, stripped[i] if i < len(stripped) else None)}
            )
            break
        weight = stripped[i]
        i += 1

        if i >= len(stripped) or not _COST_RE.match(stripped[i]):
            anomalies.append(
                {"page": page_at(row_start), "line": row_start,
                 "detail": "weapon %r: expected a cost value, found %r"
                           % (name, stripped[i] if i < len(stripped) else None)}
            )
            break
        cost = stripped[i]
        i += 1

        properties = " ".join(properties_lines).strip()
        weapons.append(
            {
                "name": name,
                "damage": damage,
                "properties": None if properties in ("", "—") else properties,
                "mastery": mastery,
                "weight": weight,
                "cost": cost,
                "page": page_at(row_start),
            }
        )

        if i < len(stripped) and not stripped[i]:
            i += 1

    return weapons, anomalies


def parse(pages, suspect_pages=()):
    suspect = set(suspect_pages)

    numbered = []
    for number, raw in enumerate(pages, start=1):
        for line in raw.split("\n"):
            numbered.append((number, line))

    numbered = _dehyphenate_numbered(numbered)
    lines = [l for _, l in numbered]
    page_of = [n for n, _ in numbered]

    found, anomalies = parse_stream(lines, page_of)

    weapons, conflicts = [], []
    for weapon in found:
        if weapon["page"] in suspect:
            conflicts.append(
                {"page": weapon["page"], "name": weapon["name"],
                 "detail": "page text disputed between PyMuPDF and pdftotext"}
            )
        else:
            weapons.append(weapon)

    weapons.sort(key=lambda w: canon.slugify(w["name"]))
    return weapons, anomalies, conflicts
