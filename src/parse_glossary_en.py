"""Rules Glossary parser for the English SRD 5.2.1.

CALIBRATED against the pinned EN PDF on 2026-08-03, "Rules Glossary"
(p.176-191, bounded by the "Rules Definitions" sub-heading that follows the
abbreviations table -- see below -- and the "Gameplay Toolbox" chapter that
follows). 152 entries: skills, conditions, actions, areas of effect,
attitudes, hazards, and every other rules term the SRD defines by name.

THE ABBREVIATIONS TABLE (p.176, "AC / Armor Class", "GM / Game Master", ...)
IS NOT PART OF THIS CATALOGUE. It is a distinct sub-section ("Glossary
Conventions") that precedes "Rules Definitions", answering a different
question (what does this two-letter code stand for) from what an entry
answers (what does this rule do). The chapter is entered at the "Rules
Definitions" heading, one line past the abbreviations table, not at the
chapter's own "Rules Glossary" title line.

THE CENTRAL PROBLEM, AND WHY A SPELL/FEAT/ITEM-STYLE HEAD REGEX DOES NOT
WORK HERE: every other calibrated grammar in this pipeline has a mechanical
head shape to anchor on -- "Level 3 Evocation (", "Armor, +1", "Origin
Feat". A glossary entry has none: the name IS the whole signal, e.g.
"Ability Check" directly followed by its own prose, no delimiter, no
tag word, most entries not even bracketed. Two facts make this genuinely
hard rather than merely tedious:

  1. BLANK LINES DO NOT RELIABLY MARK ENTRY BOUNDARIES. They mark
     paragraph breaks WITHIN a multi-paragraph entry too (Armor Class,
     Concentration, Breaking Objects all have an internal blank line from
     extract.normalise()'s tab-continuation promotion) -- and, worse, a
     multi-column bulleted list embedded INSIDE one entry's body renders
     as several PDF blocks, each separated by a blank line purely as a
     column-layout artefact, with no relation to entry boundaries at all.
     The "Action" entry lists twelve other action names (Attack, Dash,
     Disengage / Dodge, Help, Hide / ...) in a 3-row x 4-column grid; the
     extracted text carries a blank line after every group of three,
     making "Dodge" look exactly as blank-line-preceded as a real entry.
  2. THOSE LIST ITEMS ARE THEMSELVES REAL GLOSSARY TERMS, just referenced
     early, out of their own alphabetical position -- "attention aux
     entrees qui se referencent". "Dodge" IS a genuine entry, five pages
     later, with its own full definition; naively accepting the early
     mention would create a duplicate record with a one-word "description"
     stolen from the next list item.

WHAT DISTINGUISHES A REAL ENTRY, measured rather than assumed:
  a. NAME SHAPE. A real entry's name line is short, Title Case (every
     content word capitalised; "of"/"and"/"the"/... exempted), contains no
     ". " (which would mean it is a run-in sub-heading fused with its own
     body on one physical line, e.g. "Hit Points. An object is destroyed
     when..."), and does not end in sentence punctuation.
  b. WHAT FOLLOWS IS ACTUAL PROSE. A table row or a bare-word list item
     has almost no alphabetic content before the next break ("Dash
     Disengage" for the fake "Attack" candidate inside the Action list;
     "Str 15 lb Str 30 lb" for a Carrying Capacity table row). A genuine
     definition runs to a full sentence. Measured threshold: at least 10
     alphabetic words in the text between this candidate and the next
     blank line/page break. An early attempt used "contains a period"
     instead of a word count and was fooled twice: by "Str." (the
     glossary's own abbreviation for Strength, carrying a real period) and
     by "lb." -- both survive a naive period check, neither survives a
     word-count floor, because a table cell is short no matter what
     punctuation happens to sit inside it.
  c. GLOBAL ALPHABETICAL ORDER. The whole chapter is one A-to-Z list. A
     candidate whose name sorts BEFORE the most recently accepted entry is
     rejected outright -- this is what actually protects against a false
     positive slipping through (a). Checked end to end: the 152 accepted
     names are in strict non-decreasing order with zero exceptions, and
     the five bracketed tags this parser found (12 Action, 15 Condition,
     6 Area of Effect, 5 Hazard, 3 Attitude) match the glossary's own
     "Rules Definitions" cross-reference lists exactly (Action's own list
     of 12 named actions, Condition's own list of 15 named conditions,
     Area of Effect's own list of 6 shapes) -- an independent count
     agreeing with the parse, the same cross-check discipline already used
     for the spell/class catalogues.

THE PAGE SEAM, HANDLED DIFFERENTLY HERE THAN FOR SPELLS: a page boundary
carries no blank line of its own (each page is normalised independently),
so an entry whose name happens to be a page's very first line -- "Area of
Effect" opens p.177 clean, right after "Ally" closes p.176 -- has NO
separator at all in the raw stream between the previous entry's last body
line and this one's name. Treating a page transition as EXACTLY AS STRONG
A SEPARATOR AS A BLANK LINE (same rule already ported into the FR spell
parser) is necessary for detecting where a candidate STARTS. But unlike the
spell parser's single stat-block field, this grammar's final BODY TEXT must
not gain a synthetic paragraph break every time an accepted entry's own
prose happens to run across a page with no natural blank line at the seam.
So the two jobs are kept separate: `_find_heads` scans with page transitions
counted as boundaries (for deciding what is a head), but each entry's own
description is sliced from the plain original stream between one accepted
head and the next -- only REAL blank lines (genuine paragraph breaks)
survive into the text, and a same-sentence page crossing joins with a
space exactly as an ordinary line wrap would.

TAGS ARE KEPT AS THE SOURCE'S OWN WORD, slugified (canon.slugify), rather
than mapped through a hand-written category table the way a feat's four
categories are -- there is no reason to invent a closed enum here when the
glossary's own five words are already unambiguous and exhaustively
verified above.

"See also" cross-references are left inside `description` as running
prose, the same choice already made for a spell's "Using a Higher-Level
Spell Slot" tail: splitting them into a structured link field is a display
decision, not an import one, and every target is a bare name a consumer can
already re-slug if it wants to link.
"""

import re

import canon
from parse_spells_en import _dehyphenate_numbered

CHAPTER_ENTRY_HEADING = "Rules Definitions"
CHAPTER_END = "Gameplay Toolbox"

TAG_RE = re.compile(r"^(.*?)\s\[([A-Za-z /]+)\]$")
_MINOR_WORDS = {"of", "and", "the", "a", "an", "or", "to", "in", "at", "for", "per", "vs", "with"}
_WORD_RE = re.compile(r"[A-Za-z']+")
_ALPHA_WORD_RE = re.compile(r"[A-Za-z]+")

# Measured across the whole chapter: the longest real entry name
# ("Ability Score and Modifier") is 27 characters; 60 gives headroom
# without admitting a wrapped sentence fragment.
_NAME_MAX_LEN = 60

# The floor that separates a genuine definition from a table row or a
# bare-word list item -- see the module docstring's point (b).
_PROSE_WORD_FLOOR = 10


def _looks_titlecase(line):
    words = _WORD_RE.findall(line)
    content = [w for w in words if w.lower() not in _MINOR_WORDS]
    if not content:
        return False
    return all(w[0].isupper() for w in content)


def _is_name_candidate(line):
    if not line or not line[0].isupper():
        return False
    if len(line) > _NAME_MAX_LEN:
        return False
    if ". " in line:
        return False
    if line.endswith((".", ",", ":", ";")):
        return False
    m = TAG_RE.match(line)
    base = m.group(1) if m else line
    return _looks_titlecase(base)


def _looks_like_prose(text):
    return len(_ALPHA_WORD_RE.findall(text)) >= _PROSE_WORD_FLOOR


def _preview_end(stripped, page_of, i, limit):
    """End of the local run used only to JUDGE candidate i, not to bound its body.

    Stops at the first real blank line or page transition after i -- enough
    text to tell a definition from a table row without needing the entry's
    full span (which is not known until the NEXT accepted head is found).
    """
    j = i + 1
    while j < limit and stripped[j] and not (page_of[j] != page_of[j - 1]):
        j += 1
    return j


def _find_heads(stripped, page_of, start, end):
    """Indices of accepted entry name-lines within [start, end).

    A page transition counts as a boundary for deciding what MAY be a head
    (see module docstring); it does not affect body text, which is sliced
    later from the plain stream between two accepted heads.
    """
    heads = []
    last_key = ""
    at_boundary = True
    i = start
    while i < end:
        line = stripped[i]
        if not line:
            at_boundary = True
            i += 1
            continue
        page_changed = i > start and page_of[i] != page_of[i - 1]
        if at_boundary or page_changed:
            preview_end = _preview_end(stripped, page_of, i, end)
            preview = " ".join(stripped[i + 1 : preview_end])
            m = TAG_RE.match(line)
            base_name = m.group(1) if m else line
            key = base_name.strip().lower()
            if _is_name_candidate(line) and _looks_like_prose(preview) and key >= last_key:
                heads.append(i)
                last_key = key
                at_boundary = False
                i += 1
                continue
        at_boundary = False
        i += 1
    return heads


def _paragraphs(lines):
    end = len(lines)
    while end > 0 and not lines[end - 1]:
        end -= 1
    lines = lines[:end]
    paragraphs = []
    for chunk in "\n".join(lines).split("\n\n"):
        joined = " ".join(l for l in chunk.split("\n") if l)
        if joined:
            paragraphs.append(joined)
    return "\n\n".join(paragraphs)


def parse_stream(text, page_of):
    lines = [l.strip("\n") for l in text.split("\n")]
    stripped = [l.strip() for l in lines]
    entries, anomalies = [], []

    def page_at(i):
        return page_of[i] if i < len(page_of) else (page_of[-1] if page_of else 0)

    entry_start = None
    for i, l in enumerate(stripped):
        if l == CHAPTER_ENTRY_HEADING:
            entry_start = i
            break
    if entry_start is None:
        anomalies.append({"page": 0, "line": 0, "detail": "'Rules Definitions' heading not found"})
        return entries, anomalies

    # Skip the one-line intro ("Here are definitions of various rules.")
    # and the blank line that closes it -- the abbreviations table above
    # this point is deliberately out of scope (see module docstring).
    i = entry_start + 1
    while i < len(stripped) and stripped[i]:
        i += 1
    i += 1
    chapter_start = i

    chapter_end = len(lines)
    for j, l in enumerate(stripped):
        if j > chapter_start and l == CHAPTER_END:
            chapter_end = j
            break

    heads = _find_heads(stripped, page_of, chapter_start, chapter_end)

    for pos, idx in enumerate(heads):
        head_line = stripped[idx]
        body_end = heads[pos + 1] if pos + 1 < len(heads) else chapter_end

        m = TAG_RE.match(head_line)
        name = (m.group(1) if m else head_line).strip()
        tag = canon.slugify(m.group(2)) if m else None

        description = _paragraphs(stripped[idx + 1 : body_end])
        if not description:
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "glossary entry %r has a name line but no body text" % name}
            )
            continue

        entries.append(
            {
                "name": name,
                "tag": tag,
                "description": description,
                "page": page_at(idx),
            }
        )

    return entries, anomalies


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

    entries, conflicts = [], []
    for entry in found:
        if entry["page"] in suspect:
            conflicts.append(
                {"page": entry["page"], "name": entry["name"],
                 "detail": "page text disputed between PyMuPDF and pdftotext"}
            )
        else:
            entries.append(entry)

    entries.sort(key=lambda e: canon.slugify(e["name"]))
    return entries, anomalies, conflicts
