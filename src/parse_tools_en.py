"""Tool parser for the English SRD 5.2.1.

CALIBRATED against the pinned EN PDF on 2026-08-03, the "Tools" section
(p.93-94, inside the "Equipment" chapter, p.89-103). 25 tools, 0 anomalies.

NOT A TABLE AT ALL, despite living in the same chapter as the Weapons and
Armor tables this lot also covers: each tool is its own named entry, shaped
like a magic item or a feat -- "Name (Cost)" on its own head line, then a
short fixed sequence of labelled fields. The head shape is the SAME as an
adventuring gear item's ("Backpack (2 GP)"), so the anchor requires a
second signal to be trustworthy on its own: the line right after the head
must start with "Ability:" -- the one field every tool has and no other
"Name (Cost)"-shaped line in the chapter is followed by.

FIELD ORDER IS FIXED (Ability, Weight, Utilize, then optionally Craft, then
optionally Variants) but the last two are genuinely absent for some tools
(Forgery Kit, Navigator's Tools have no Craft; sixteen of twenty-five have
no Variants) -- reported here as a fixed sequence read until either the
next known label or the entry's end, not as a strict template that would
turn a tool's honestly-missing field into a manufactured one.

Ability and Weight are always exactly one line; Utilize, Craft and
Variants wrap freely, including across a PAGE BOUNDARY with no blank line
at the seam (Smith's Tools' Craft list runs from the last line of p.93
into p.94) -- handled for free here, unlike the spell parser's page-seam
fix, because entry boundaries are anchored on the "Name (Cost)" + "Ability:"
signature rather than on counting blank lines within a stat block: a body
span runs from one confirmed head to the next confirmed head regardless of
how many pages it crosses, so a wrapped field's continuation is simply
more of the same span.
"""

import re

import canon
from parse_spells_en import _dehyphenate_numbered

HEAD_RE = re.compile(r"^(.+?)\s\(([^)]+)\)$")

FIELD_LABELS = ["Ability", "Weight", "Utilize", "Craft", "Variants"]
_LABEL_RE = re.compile(r"^(%s):\s*(.*)$" % "|".join(FIELD_LABELS))

CHAPTER_START = "Tools"
CHAPTER_END = "Adventuring Gear"


def _collect_fields(stripped, start, end):
    """Walk the fixed label sequence, tolerating the two optional trailing ones.

    Returns (fields_dict, error) -- error is None on success, a string
    naming what went wrong otherwise.
    """
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

    missing = [key for key in ("Ability", "Weight", "Utilize") if key not in fields]
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
        anomalies.append({"page": 0, "line": 0, "detail": "'Tools' chapter heading not found"})
        return tools, anomalies

    chapter_end = len(stripped)
    for i in range(chapter_start + 1, len(stripped)):
        if stripped[i] == CHAPTER_END:
            chapter_end = i
            break

    heads = []
    for i in range(chapter_start, chapter_end):
        m = HEAD_RE.match(stripped[i])
        if m and i + 1 < chapter_end and stripped[i + 1].startswith("Ability:"):
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
                "ability": fields["Ability"],
                "weight": fields["Weight"],
                "utilize": fields["Utilize"],
                "craft": fields.get("Craft"),
                "variants": fields.get("Variants"),
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
