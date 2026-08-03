"""Tool parser for the French SRD 5.2.1.

CALIBRATED against the pinned FR PDF on 2026-08-03, the "Outils" section
(p.99-100, inside the "Équipement" chapter, p.95-106). Ported from
`parse_tools_en.py`: not a table at all, each tool is its own named entry
shaped like a magic item or a feat -- "Nom (Coût)" on its own head line,
then a short fixed sequence of labelled fields. The head shape is the
SAME as an adventuring gear item's, so the anchor requires a second
signal to be trustworthy on its own: the line right after the head must
start with "Caractéristique :" -- the one field every tool has that no
other "Nom (Coût)"-shaped line in the chapter is followed by.

FIELD LABELS: "Caractéristique :" (Ability), "Poids :" (Weight),
"Utilisation :" (Utilize), "Artisanat :" (Craft, optional), "Variantes :"
(Variants, optional) -- same fixed order and same two genuinely-absent
trailing fields as EN's Ability/Weight/Utilize/[Craft]/[Variants].

CHAPTER_START = "Outils" -- a literal string that recurs (p.99, the real
chapter; p.110 and p.218, both cross-references in running prose, "La
section « Outils »..." / "Outils\n\nLa table « Outils par objet
magique »..."). Taking the FIRST occurrence lands correctly on the real
chapter, the same discipline the EN parser already uses for its own
"Tools" anchor.

CHAPTER_END = "Matériel d'aventurier" -- ALSO recurs (p.100, the section's
own heading, directly above its intro paragraph; p.101, the SAME phrase
again as the table's own caption, directly above "Objet / Poids / Prix").
The first occurrence after `chapter_start` is p.100 -- exactly where the
Outils section actually ends, right after "Outils de voleur" -- so taking
the first occurrence (not disambiguating further) is correct here; the
second occurrence is `parse_gear_fr.py`'s own concern, not this one's.
"""

import re

import canon
from parse_spells import _dehyphenate_numbered

HEAD_RE = re.compile(r"^(.+?)\s\(([^)]+)\)$")

FIELD_LABELS = ["Caractéristique", "Poids", "Utilisation", "Artisanat", "Variantes"]
_LABEL_RE = re.compile(r"^(%s)\s*:\s*(.*)$" % "|".join(FIELD_LABELS))

CHAPTER_START = "Outils"
CHAPTER_END = "Matériel d’aventurier"


def _collect_fields(stripped, start, end):
    fields = {}
    i = start
    current = None
    while i < end:
        line = stripped[i]
        m = _LABEL_RE.match(line)
        if m:
            current = m.group(1)
            if current in fields:
                return None, "label %r repeated" % current
            fields[current] = [m.group(2)] if m.group(2) else []
        elif current:
            fields[current].append(line)
        else:
            return None, "text %r before any recognised label" % line[:60]
        i += 1

    for key in fields:
        fields[key] = " ".join(p for p in fields[key] if p).strip()

    missing = [key for key in ("Caractéristique", "Poids", "Utilisation") if key not in fields]
    if missing:
        return None, "missing required field(s): %s" % ", ".join(missing)
    return fields, None


def parse_stream(lines, page_of):
    stripped = [l.strip() for l in lines]

    def page_at(i):
        return page_of[i] if i < len(page_of) else (page_of[-1] if page_of else 0)

    chapter_start = None
    for i, l in enumerate(stripped):
        if l == CHAPTER_START:
            chapter_start = i
            break

    tools, anomalies = [], []
    if chapter_start is None:
        anomalies.append({"page": 0, "line": 0, "detail": "'Outils' chapter heading not found"})
        return tools, anomalies

    chapter_end = len(stripped)
    for i in range(chapter_start + 1, len(stripped)):
        if stripped[i] == CHAPTER_END:
            chapter_end = i
            break

    heads = []
    for i in range(chapter_start, chapter_end):
        m = HEAD_RE.match(stripped[i])
        if m and i + 1 < chapter_end and stripped[i + 1].startswith("Caractéristique"):
            heads.append((i, m.group(1), m.group(2)))

    for pos, (idx, name, cost) in enumerate(heads):
        body_end = heads[pos + 1][0] if pos + 1 < len(heads) else chapter_end
        fields, err = _collect_fields(stripped, idx + 1, body_end)
        if err:
            anomalies.append(
                {"page": page_at(idx), "line": idx, "detail": "tool %r: %s" % (name, err)}
            )
            continue

        tools.append(
            {
                "name": name,
                "cost": cost,
                "ability": fields["Caractéristique"],
                "weight": fields["Poids"],
                "utilize": fields["Utilisation"],
                "craft": fields.get("Artisanat"),
                "variants": fields.get("Variantes"),
                "page": page_at(idx),
            }
        )

    return tools, anomalies


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

    tools, conflicts = [], []
    for tool in found:
        if tool["page"] in suspect:
            conflicts.append(
                {"page": tool["page"], "name": tool["name"],
                 "detail": "page text disputed between PyMuPDF and pdftotext"}
            )
        else:
            tools.append(tool)

    tools.sort(key=lambda t: canon.slugify(t["name"]))
    return tools, anomalies, conflicts
