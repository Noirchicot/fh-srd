"""Magic item parser for the English SRD 5.2.1.

CALIBRATED against the pinned EN PDF on 2026-08-03, "Magic Items A-Z"
(p.209-253, inside the wider "Magic Items" chapter p.204-253). Structurally
close to a spell entry -- name, then a one-line head, then a blank line, then
description -- but the head is simpler (no four-field stat block) and messier
in a different way: it names NINE categories (Armor, Potion, Ring, Rod,
Scroll, Staff, Wand, Weapon, Wondrous Item) and a rarity clause that can
itself enumerate several rarities tied to different bonuses in one entry --
"Armor, +1, +2, or +3" heads a SINGLE record whose rarity line reads
"Rare (+1), Very Rare (+2), or Legendary (+3)". That is not decomposed into
three records: the source presents it as one entry, and so does this parser.
`rarity` is kept as the source's own text rather than forced into one enum
value, the same choice made for a spell's `components`.

The head line wraps exactly like a spell's class list does, and for the same
reason: attunement can carry a restriction ("Requires Attunement by a Bard,
Cleric, Druid, or Sorcerer") long enough to run onto a second line.

Reused from the spell parser rather than reinvented: continuous-stream
parsing across page boundaries, the page-transition-closes-a-field guard
(found calibrating spells: Duration ending a page with no blank line before
the next page's description), paragraph-break handling from
`extract.normalise()`, and the same discipline -- a block that does not parse
cleanly becomes an `unparsed` exclusion, never a half-filled record.

NOT attempted here: reconstructing the many random tables embedded inside
item descriptions (Potion Miscibility, Apparatus of the Crab's lever table,
creature-type tables for weapons of slaying). They are swept into
`description` as prose in whatever reading order the page's two-column
layout produces them, which is not necessarily row-major. That is a known,
visible limitation -- not a silent one -- and is named again in the parser's
own docstring rather than only in a commit message, since decomposing tables
is the same shape of a problem for equipment and would need its own
calibration pass to do properly.

Still true, with one thing now settled beside it: such a table is at least on
the RIGHT item. The Apparatus of the Crab's lever table is printed full-width
at the foot of EN p.210, and reading the page in printed order put it on Armor
of Resistance -- the last entry of the right column, and a different object.
`extract.float_anchors()` re-anchors it to the entry the source names as its
owner. The table is still swept in as prose; it is no longer swept into a
neighbour.
"""

import re

import canon
from parse_spells_en import _dehyphenate_numbered

CATEGORIES = {
    "Armor": "armor",
    "Potion": "potion",
    "Ring": "ring",
    "Rod": "rod",
    "Scroll": "scroll",
    "Staff": "staff",
    "Wand": "wand",
    "Weapon": "weapon",
    "Wondrous Item": "wondrous-item",
}
_CATEGORY_ALT = "|".join(re.escape(c) for c in sorted(CATEGORIES, key=len, reverse=True))

# "Armor (Any Light, Medium, or Heavy), Rare (Requires Attunement)"
# "Wondrous Item, Rare"
# "Armor, +1, +2, or +3"                      (subtype omitted, rarity list only)
TYPE_HEAD = re.compile(
    r"^(?P<category>%s)\s*(?:\((?P<subtype>[^)]*)\))?\s*,\s*(?P<rarity>.*)$"
    % _CATEGORY_ALT
)

ATTUNEMENT = re.compile(r"requires attunement", re.IGNORECASE)

CHAPTER_START = "Magic Items A–Z"
CHAPTER_END = "Monsters"


def parse_stream(text, page_of):
    lines = [l.strip("\n") for l in text.split("\n")]
    items, anomalies = [], []

    def page_at(i):
        return page_of[i] if i < len(page_of) else (page_of[-1] if page_of else 0)

    stripped = [l.strip() for l in lines]

    # UNLIKE a spell's "Level N <School> (", the head shape here -- a bare
    # category word, an optional parenthetical, a comma, more text -- is not
    # unique to this chapter. It also matches character-creation prose
    # describing starting-equipment choices ("...or (B) Studded Leather
    # Armor, Scimitar, ... and 11 GP; or (C) 155 GP") 100+ pages earlier,
    # which produced item "records" whose description was actually Fighter
    # class features. A spell's head anchors on "Level" or "Cantrip", words
    # that do not appear in ordinary prose in that exact position; a magic
    # item's head has no equivalent word, so the chapter must be bounded
    # explicitly rather than trusted to the pattern alone.
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

    # The generic "+1, +2, or +3" items name THEMSELVES in the shape of a
    # type line -- "Armor, +1, +2, or +3" reads as category "Armor" plus a
    # rarity clause, exactly like a real type line does, and it sits
    # directly (no blank line) above the REAL type line ("Armor (Any Light,
    # Medium, or Heavy), Rare (+1)..."). Left alone, both lines match as
    # heads, and the fake one steals the name from whatever text precedes
    # IT (a table row from the previous item, in the pinned PDF). A
    # candidate is not a real entry point if the VERY NEXT line is itself
    # shaped like a type line -- a real item's own type line is never
    # followed immediately by another one.
    candidates = [
        i for i, l in enumerate(stripped)
        if chapter_start < i < chapter_end and TYPE_HEAD.match(l)
    ]
    heads = [
        i for i in candidates
        if not (i + 1 < len(stripped) and stripped[i + 1] and TYPE_HEAD.match(stripped[i + 1]))
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
        head = TYPE_HEAD.match(line)

        # The rarity clause may wrap ("Rare (+1), Very\nRare (+2), or
        # Legendary (+3)"; "Requires Attunement by a Bard, Cleric,\nDruid").
        # Bounded the same way a spell's class list is: stop at the first
        # blank line, or after a few lines regardless.
        head_lines = [line]
        cursor = idx
        while cursor < idx + 3:
            nxt = cursor + 1
            if nxt >= len(stripped) or not stripped[nxt]:
                break
            head_lines.append(stripped[nxt])
            cursor = nxt
        head_text = " ".join(head_lines)

        # The name itself can wrap onto two lines when it is long enough
        # ("Amulet of Proof against Detection" / "and Location"; measured on
        # the real PDF). The signal that a line is the WRAPPED TAIL of a
        # title above it, rather than a complete name on its own, is that it
        # starts lowercase -- a real item name is always Title Case at its
        # first word. That is also what keeps this from grabbing the wrong
        # thing when a block boundary is missing elsewhere in the chapter:
        # the last row of an embedded random table ("10 Thunder") and a
        # description's leftover tail ("freed by the Greater Restoration
        # spell...") both start uppercase or with a digit, so neither is
        # mistaken for a continuation.
        name_end = idx - 1
        while name_end >= 0 and not stripped[name_end]:
            name_end -= 1
        name_start = name_end
        if name_start >= 0 and name_start - 1 >= 0 and stripped[name_start][:1].islower():
            above = stripped[name_start - 1]
            if above:
                name_start -= 1
        name = " ".join(stripped[name_start:name_end + 1]) if name_end >= 0 else ""
        if not name or len(name) > 80 or name.endswith(":") or name.endswith(","):
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "implausible item name above %r: %r"
                           % (head_text[:60], name[:80])}
            )
            continue

        # Description: from just past the head block's blank line to the
        # next entry's own name line (or the chapter boundary), exclusive.
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
                 "detail": "item %r has a type line but no description text" % name}
            )
            continue

        items.append(
            {
                "name": name,
                "category": CATEGORIES[head.group("category")],
                "subtype": (head.group("subtype") or "").strip() or None,
                "rarity": re.sub(r"\s+", " ", head.group("rarity") + " "
                                  + " ".join(head_lines[1:])).strip(),
                "attunement": bool(ATTUNEMENT.search(head_text)),
                "description": description,
                "page": page_at(name_start),
            }
        )

    return items, anomalies


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

    items, conflicts = [], []
    for item in found:
        if item["page"] in suspect:
            conflicts.append(
                {"page": item["page"], "name": item["name"],
                 "detail": "page text disputed between PyMuPDF and pdftotext"}
            )
        else:
            items.append(item)

    items.sort(key=lambda it: canon.slugify(it["name"]))
    return items, anomalies, conflicts
