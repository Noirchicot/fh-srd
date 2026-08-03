"""Feat parser for the English SRD 5.2.1.

CALIBRATED against the pinned EN PDF on 2026-08-03, "Feats" (p.87-88 -- the
whole chapter is two pages, which matches the standing expectation that most
2024 feats are NOT in the SRD subset; ATTRIBUTION.md already names several
that will land in `not-in-srd` when a Fate's Hand layer is imported: Great
Weapon Master, Sharpshooter, Spell Sniper, Observant, Keen Mind, Dual
Wielder). This importer reads only the SRD PDF, which by construction
contains only the feats that ARE in it -- there is nothing in this document
to diff against to produce a `not-in-srd` exclusion here. That bookkeeping
belongs to whoever later cross-references a fuller rulebook against this
base, not to this parser.

Grammar, close in shape to a magic item's head but not the same: the category
word comes BEFORE the word "Feat" here ("Origin Feat", "General Feat
(Prerequisite: Level 4+)"), where an item's category comes before a comma and
"Feat" never appears at all. Four categories: Origin, General, Fighting
Style, Epic Boon.

Like magic items, the head shape is not unique to this chapter on its own --
nothing stops another part of the book from writing "General Feat" in running
prose -- so the chapter is bounded by explicit start/end anchors ("Feats" /
the SECOND bare "Equipment" line, since a background's own equipment
subsection also produces one earlier in the document) rather than trusted to
the pattern alone, the same lesson learned calibrating magic items.
"""

import re

import canon
from parse_spells_en import _dehyphenate_numbered

CATEGORIES = {
    "Origin": "origin",
    "General": "general",
    "Fighting Style": "fighting-style",
    "Epic Boon": "epic-boon",
}
_CATEGORY_ALT = "|".join(re.escape(c) for c in sorted(CATEGORIES, key=len, reverse=True))

# "Origin Feat", "General Feat (Prerequisite: Level 4+)",
# "Fighting Style Feat (Prerequisite: Fighting Style\nFeature)" (wraps, and
# the closing paren is NOT on this line -- `\)?` is optional so the line
# still matches; the wrap-collector below picks up the rest).
FEAT_HEAD = re.compile(
    r"^(?P<category>%s) Feat(?:\s*\((?P<prereq>[^)]*)\)?)?\s*$" % _CATEGORY_ALT
)

CHAPTER_START = "Feats"
CHAPTER_END = "Equipment"


def parse_stream(text, page_of):
    lines = [l.strip("\n") for l in text.split("\n")]
    feats, anomalies = [], []

    def page_at(i):
        return page_of[i] if i < len(page_of) else (page_of[-1] if page_of else 0)

    stripped = [l.strip() for l in lines]

    chapter_start = 0
    for i, l in enumerate(stripped):
        if l == CHAPTER_START:
            chapter_start = i
            break

    chapter_end = len(lines)
    for i, l in enumerate(stripped):
        if i > chapter_start and l == CHAPTER_END:
            chapter_end = i
            break

    heads = [
        i for i, l in enumerate(stripped)
        if chapter_start < i < chapter_end and FEAT_HEAD.match(l)
    ]
    next_head = {}
    has_next_entry = {}
    for position, index in enumerate(heads):
        has_next = position + 1 < len(heads)
        following = heads[position + 1] if has_next else chapter_end
        next_head[index] = min(following, chapter_end)
        has_next_entry[index] = has_next and next_head[index] == following

    heads_set = set(heads)
    for idx, line in enumerate(stripped):
        if idx not in heads_set:
            continue
        head = FEAT_HEAD.match(line)

        # A prerequisite clause can wrap ("Prerequisite: Level 4+, Strength or
        # \nDexterity 13+)"), the same shape as an item's rarity clause.
        head_lines = [line]
        cursor = idx
        while cursor < idx + 3:
            nxt = cursor + 1
            if nxt >= len(stripped) or not stripped[nxt]:
                break
            head_lines.append(stripped[nxt])
            cursor = nxt

        name_at = idx - 1
        while name_at >= 0 and not stripped[name_at]:
            name_at -= 1
        name = stripped[name_at] if name_at >= 0 else ""
        if not name or len(name) > 60 or name.endswith(":") or name.endswith(","):
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "implausible feat name above %r: %r"
                           % (line[:60], name[:80])}
            )
            continue

        i = cursor + 1
        while i < len(stripped) and not stripped[i]:
            i += 1
        desc_end = next_head.get(idx, chapter_end)
        desc_lines = stripped[i:desc_end]
        end = len(desc_lines)
        while end > 0 and not desc_lines[end - 1]:
            end -= 1
        if has_next_entry.get(idx):
            if end > 0:
                end -= 1
                while end > 0 and not desc_lines[end - 1]:
                    end -= 1
        desc_lines = desc_lines[:end]
        paragraphs = []
        for chunk in "\n".join(desc_lines).split("\n\n"):
            joined = " ".join(l for l in chunk.split("\n") if l)
            if joined:
                paragraphs.append(joined)
        description = "\n\n".join(paragraphs)

        if not description:
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "feat %r has a category line but no description text" % name}
            )
            continue

        # The prerequisite clause, if present, is joined the same way a
        # wrapped item rarity is: the regex group from the head line plus
        # whatever the wrap-collector picked up after it.
        # The wrap-collector grabs whole lines, closing paren and all; the
        # regex only ever strips the close paren when it is on the HEAD's
        # own line (the common case). Strip one trailing ")" here to cover
        # the wrapped case too, matching the open paren already consumed.
        prereq_tail = " ".join(head_lines[1:])
        prereq = (head.group("prereq") or "")
        if prereq_tail:
            prereq = (prereq + " " + prereq_tail).strip()
        prereq = re.sub(r"\s+", " ", prereq).strip()
        if prereq.endswith(")"):
            prereq = prereq[:-1].strip()
        prereq = prereq or None

        feats.append(
            {
                "name": name,
                "category": CATEGORIES[head.group("category")],
                "prerequisite": prereq,
                "description": description,
                "page": page_at(name_at),
            }
        )

    return feats, anomalies


def parse(pages, suspect_pages=()):
    suspect = set(suspect_pages)

    numbered = []
    for number, raw in enumerate(pages, start=1):
        for line in raw.split("\n"):
            numbered.append((number, line))

    numbered = _dehyphenate_numbered(numbered)

    stream = "\n".join(l for _, l in numbered)
    page_of = [n for n, _ in numbered]

    found, anomalies = parse_stream(stream, page_of)

    feats, conflicts = [], []
    for feat in found:
        if feat["page"] in suspect:
            conflicts.append(
                {"page": feat["page"], "name": feat["name"],
                 "detail": "page text disputed between PyMuPDF and pdftotext"}
            )
        else:
            feats.append(feat)

    feats.sort(key=lambda f: canon.slugify(f["name"]))
    return feats, anomalies, conflicts
