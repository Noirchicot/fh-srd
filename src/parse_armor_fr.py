"""Armor table parser for the French SRD 5.2.1.

CALIBRATED against the pinned FR PDF on 2026-08-03, the "Armures" table
(p.98, inside the "Équipement" chapter, p.95-106). 13 rows (12 armors plus
the Bouclier/Shield), 0 anomalies. Ported from `parse_armor_en.py` -- row-
coherent for the same reason the weapons table is, re-measured rather than
assumed per the brief's own warning that FR geometry is not guaranteed to
match EN's.

THE HEADER WORD FOR "COST" HERE IS "Coût", NOT "Prix" -- the word the
Armes table right before it uses for the exact same currency figures.
Checked directly rather than assumed identical to the weapons table's own
header: `TABLE_HEADER` names this table's actual printed words, not a
shared constant.

Simpler than the Armes table it sits right after: every field is exactly
one line for all 13 rows, no wrapping (the AC column's longest value,
"15 + modificateur de Dex (max 2)", still fits one physical line). Strength
reads "For 13"/"For 15" or "—" (no requirement) -- French puts the
abbreviation before the number, the same order EN's "Str 13" uses.
Stealth reads "Désavantage" or "—", not EN's "Disadvantage".

WEIGHT AND COST use French units and punctuation, the same regexes
`parse_weapons_fr.py` calibrated for the same table family: kg/g with a
comma decimal separator, French coin abbreviations with a space thousands
separator (checked directly on Harnois: "1 500 po").
"""

import re

import canon
from parse_spells import _dehyphenate_numbered

TABLE_HEADER = ["Armures", "Classe d’armure (CA)", "Force", "Discrétion", "Poids", "Coût"]

_AC_RE = re.compile(r"^\d|^\+\d")
_WEIGHT_RE = re.compile(r"^[\d,.\s]+\s?(?:kg|g)\.?$|^—$")
_COST_RE = re.compile(r"^[\d\s]+(?:pc|pa|pe|po|pp)$")


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
    armors, anomalies = [], []
    if header is None:
        anomalies.append({"page": 0, "line": 0, "detail": "Armures table header not found"})
        return armors, anomalies

    i = header + len(TABLE_HEADER)
    while i < len(stripped) and not stripped[i]:
        i += 1

    while i + 5 < len(stripped) and _AC_RE.match(stripped[i + 1]):
        row_start = i
        name = stripped[i]
        armor_class = stripped[i + 1]
        strength = stripped[i + 2]
        stealth = stripped[i + 3]
        weight = stripped[i + 4]
        cost = stripped[i + 5]

        if not _WEIGHT_RE.match(weight):
            anomalies.append(
                {"page": page_at(row_start), "line": row_start,
                 "detail": "armor %r: expected a weight value, found %r" % (name, weight)}
            )
            break
        if not _COST_RE.match(cost):
            anomalies.append(
                {"page": page_at(row_start), "line": row_start,
                 "detail": "armor %r: expected a cost value, found %r" % (name, cost)}
            )
            break

        armors.append(
            {
                "name": name,
                "armor_class": armor_class,
                "strength": None if strength == "—" else strength,
                "stealth_disadvantage": stealth == "Désavantage",
                "weight": weight,
                "cost": cost,
                "page": page_at(row_start),
            }
        )

        i += 6
        if i < len(stripped) and not stripped[i]:
            i += 1

    return armors, anomalies


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

    armors, conflicts = [], []
    for armor in found:
        if armor["page"] in suspect:
            conflicts.append(
                {"page": armor["page"], "name": armor["name"],
                 "detail": "page text disputed between PyMuPDF and pdftotext"}
            )
        else:
            armors.append(armor)

    armors.sort(key=lambda a: canon.slugify(a["name"]))
    return armors, anomalies, conflicts
