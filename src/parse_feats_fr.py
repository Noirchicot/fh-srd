"""Feat parser for the French SRD 5.2.1.

CALIBRATED against the pinned FR PDF on 2026-08-03, "Dons" (p.92-94). Ported
from `parse_feats_en.py` -- same continuous-stream approach, same explicit
chapter bound (a bare category+"Don" line is not unique to this chapter any
more than "General Feat" was in English), same discipline that an unparsed
block becomes an `unparsed` exclusion, never a half-filled record.

THE HEAD PUTS THE WORD "Don" FIRST, where English puts the category first
("Origin Feat") -- "Don d'origines" (note the PLURAL "origines", matching
the section heading "Dons d'origines" two lines above it, not the singular
"Origine" the category table uses), "Don général", "Don de Style de combat",
"Don de faveur épique". Four categories, the same four EN has: Origine
(plural in the head), Général, Style de combat, Faveur épique.

The prerequisite clause reads "(prérequis : ...)", lowercase "p" -- unlike
EN's capitalised "(Prerequisite: ...)" -- and wraps across a line break the
same way ("Don général (prérequis : niveau 4 ou\nsupérieur, Force ou
Dextérité 13 ou plus)"), collected the same way EN's is.

CHAPTER_START = "Dons" (a single, literal occurrence in the whole document,
p.92). CHAPTER_END = "Équipement" -- but that bare string ALSO appears
repeatedly earlier in the document (the Classes chapter's own "Équipement
de départ" starting-equipment label wraps onto two lines per class, p.30-87,
each instance a category label, not a chapter title). Searching only AFTER
`chapter_start` (which is already past all of those, p.92 > p.87) lands on
the real Equipment chapter heading at p.95 with nothing in between -- the
same discipline already used for EN's "Equipment" bound.
"""

import re

import canon
from parse_spells import _dehyphenate_numbered

CATEGORIES = {
    "d’origines": "origin",
    "général": "general",
    "de Style de combat": "fighting-style",
    "de faveur épique": "epic-boon",
}
_CATEGORY_ALT = "|".join(re.escape(c) for c in sorted(CATEGORIES, key=len, reverse=True))

FEAT_HEAD = re.compile(
    r"^Don (?P<category>%s)(?:\s*\((?:[Pp]r[ée]requis)\s*:\s*(?P<prereq>[^)]*)\)?)?\s*$"
    % _CATEGORY_ALT
)

CHAPTER_START = "Dons"
CHAPTER_END = "Équipement"


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
