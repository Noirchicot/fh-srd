"""Spell parser for the English SRD 5.2.1.

CALIBRATED against the pinned EN PDF on 2026-08-03, by reading the actual
"Spell Descriptions" chapter (p.107-175) rather than assuming the French
grammar translates. It does not: EN puts the level FIRST ("Level 3 Evocation
(Sorcerer, Wizard)"), where FR puts the school first ("Évocation du 3e
niveau"). Cantrips read "<School> Cantrip (<classes>)".

ONE GUESS FROM THE BRIEF WAS WRONG, and it is worth recording rather than
quietly fixing: the brief expected the ritual marker to live on the level
line in English. It does not. It lives in the CASTING TIME line, exactly
where French puts it too ("Casting Time: Action or Ritual", "Casting Time: 1
minute or Ritual") — measured on Detect Magic, Alarm, Identify, Find
Familiar, Silence. Not one of the 345 "Level "/"Cantrip (" anchors in the
document carries "Ritual" on its head line.

THE PARAGRAPH-BREAK FIX THIS PARSER NEEDED, filed in extract.py rather than
here: PyMuPDF merges a spell's whole description into ONE text block and
marks the second and later paragraphs with a tab right after the newline —
not a blank line. `extract.normalise()` now promotes that into a real blank
line; without it, "Fireball"'s "Using a Higher-Level Spell Slot." paragraph
was glued to the previous sentence with no way to tell it apart from an
ordinary line wrap.

The upcast/scaling paragraph is NOT split into its own field. The brief only
asked that it not be lost, and both of the two headings the SRD actually uses
for it — "Using a Higher-Level Spell Slot." for leveled spells, "Cantrip
Upgrade." for cantrips — read fine as the tail of `description`. Splitting
them is a display decision for whoever renders this, not an import one.

THE FIELD LABEL ITSELF IS NOT CONSISTENT IN THE SOURCE. 12 of the 339 spells
print "Component:" (singular) instead of "Components:" — Barkskin, Contagion,
Divine Smite, Find Steed, Guidance, Jump, Power Word Heal, Power Word Kill,
Resistance, Searing Smite, Shining Smite, Sorcerous Burst — regardless of how
many components the spell actually has (Jump lists three: "V, S, M"). This is
a wording inconsistency in Wizards' own PDF, not a scanning artefact: it
reads the same under both extractors. Matching only the plural silently
turned these 12 into `unparsed` exclusions with a real, present components
line one word away — found by the count landing at 327 instead of 339, with
exactly 12 anomalies, all reading "missing stat line(s): components".

An embedded stat block inside a description (Find Steed's "Otherworldly
Steed" companion, p.131) is not a trap here the way it would be for the level
line: it has no "Level N <School> (" or "<School> Cantrip (" to match, so it
is swept into the description text as prose, which is exactly what it is —
you cannot cast the "Otherworldly Steed" as a spell.

The discipline is unchanged from the French parser: a block that does not
parse cleanly becomes an `unparsed` exclusion. It never becomes a half-filled
record.
"""

import re

import canon
from parse_spells import _classes

_HYPH_END = re.compile(r"[a-zà-öø-ÿ]-$")
_HYPH_START = re.compile(r"^[a-zà-öø-ÿ]")

SCHOOLS = {
    "Abjuration": "abjuration",
    "Conjuration": "conjuration",
    "Divination": "divination",
    "Enchantment": "enchantment",
    "Evocation": "evocation",
    "Illusion": "illusion",
    "Necromancy": "necromancy",
    "Transmutation": "transmutation",
}

_SCHOOL_ALT = "|".join(SCHOOLS)

# Leveled: "Level 3 Evocation (Sorcerer, Wizard)". Cantrip: "Evocation
# Cantrip (Sorcerer, Wizard)" — the school comes first for cantrips, same as
# the leveled form puts the level first. Two shapes, not one with an optional
# group, because the word order actually differs between them.
LEVEL_HEAD = re.compile(
    r"^(?:Level\s+(?P<level>\d+)\s+(?P<school>%s)|(?P<school_cantrip>%s)\s+Cantrip)\s*\("
    % (_SCHOOL_ALT, _SCHOOL_ALT)
)

FIELDS = [
    ("casting_time", re.compile(r"^Casting Time:\s*(.+)$")),
    ("range", re.compile(r"^Range:\s*(.+)$")),
    ("components", re.compile(r"^Components?:\s*(.+)$")),
    ("duration", re.compile(r"^Duration:\s*(.+)$")),
]

RITUAL = re.compile(r"\britual\b", re.IGNORECASE)

# The chapter that follows Spells. Every OTHER occurrence of these two words
# in the document is a cross-reference wrapped in curly quotes ("see
# 'Rules Glossary'"); this exact, bare, standalone line occurs exactly once
# -- the real heading. Without this bound, the alphabetically LAST spell
# (Zone of Truth) has no next head to stop at, and its "description" runs
# past the end of the chapter into the entire rest of the book: the Rules
# Glossary, Gameplay Toolbox, Magic Items and Monsters chapters, silently
# appended as if they were part of the spell's text.
CHAPTER_END = "Rules Glossary"


def parse_stream(text, page_of):
    """Return (spells, anomalies) for the whole de-hyphenated document.

    Structure mirrors the French parser: the document is read as one
    continuous stream (spells cross page boundaries here too — see the page-
    crossing check in tests), every entry's head line bounds how far the next
    one may read, and a missing field is an exclusion rather than a borrowed
    one.
    """
    lines = [l.strip("\n") for l in text.split("\n")]
    spells, anomalies = [], []

    def page_at(i):
        return page_of[i] if i < len(page_of) else (page_of[-1] if page_of else 0)

    stripped = [l.strip() for l in lines]

    chapter_end = len(lines)
    for i, l in enumerate(stripped):
        if l == CHAPTER_END:
            chapter_end = i
            break

    heads = [i for i, l in enumerate(stripped) if LEVEL_HEAD.match(l)]
    next_head = {}
    has_next_entry = {}
    for position, index in enumerate(heads):
        has_next = position + 1 < len(heads)
        following = heads[position + 1] if has_next else chapter_end
        next_head[index] = min(following, chapter_end)
        # Only a REAL following spell has a name line to strip off the end
        # of this one's description. The chapter boundary (Rules Glossary)
        # is not a spell and has no name line to confuse this one with.
        has_next_entry[index] = has_next and next_head[index] == following

    for idx, line in enumerate(stripped):
        head = LEVEL_HEAD.match(line)
        if not head:
            continue

        # The head line may wrap when the class list is long.
        level_lines = [line]
        cursor = idx
        while "(" in " ".join(level_lines) and ")" not in " ".join(level_lines):
            cursor += 1
            if cursor >= len(stripped) or cursor > idx + 3:
                break
            level_lines.append(stripped[cursor])
        level_text = " ".join(level_lines)

        if ")" not in level_text:
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "unterminated class list: %r" % level_text[:110]}
            )
            continue

        # The name sits directly above the head line (skipping blanks): the
        # two live in the same PDF text block, and a block boundary is what
        # separates this spell's name from the previous spell's description.
        name_at = idx - 1
        while name_at >= 0 and not stripped[name_at]:
            name_at -= 1
        name = stripped[name_at] if name_at >= 0 else ""
        if not name or len(name) > 60 or name.endswith(":") or name.endswith(","):
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "implausible spell name above %r: %r"
                           % (level_text[:50], name[:80])}
            )
            continue

        # Stat block: bounded by the next entry's head line, same guard as
        # the French parser — a missing field must never borrow the next
        # entry's, because that produces a complete-looking, wrong record.
        stats = {}
        limit = min(cursor + 16, max(next_head.get(idx, len(stripped)) - 1, cursor + 1))
        i = cursor + 1
        current = None
        while i < limit:
            # A page boundary is at least as strong a separator as a blank
            # line, but the text does not say so: normalise() strips each
            # page's text independently, so the blank line that would
            # normally close the stat block is not there when Duration (the
            # last field) happens to fall on the last line of a page --
            # measured on Charm Monster and Clone, whose "duration" silently
            # swallowed the whole following page's description text with no
            # blank line to stop it. Treat crossing into a new page here
            # exactly like hitting that missing blank line.
            if current and i > 0 and page_of[i] != page_of[i - 1]:
                if len(stats) == len(FIELDS):
                    break
                current = None
            wline = stripped[i]
            matched = None
            for key, pattern in FIELDS:
                m = pattern.match(wline)
                if m:
                    matched = key
                    stats[key] = m.group(1).strip()
                    current = key
                    break
            if matched:
                i += 1
                continue
            if not wline:
                if len(stats) == len(FIELDS):
                    i += 1  # consume the blank line; description starts next
                    break
                current = None
                i += 1
                continue
            if current:
                stats[current] = (stats[current] + " " + wline).strip()
            i += 1

        missing = [key for key, _ in FIELDS if key not in stats]
        if missing:
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "spell %r missing stat line(s): %s"
                           % (name, ", ".join(missing))}
            )
            continue

        # Description: everything from here to the next entry's own name
        # line, exclusive (or to the chapter boundary, for the last spell).
        # The blank line normally standing between this spell's last content
        # and the next spell's name is trimmed too.
        desc_end = next_head.get(idx, chapter_end)
        desc_lines = stripped[i:desc_end]
        end = len(desc_lines)
        while end > 0 and not desc_lines[end - 1]:
            end -= 1
        if has_next_entry.get(idx):
            # There IS a following entry: its name is the last non-blank
            # line in this slice, and it belongs to that spell, not this
            # one's description.
            if end > 0:
                end -= 1
                while end > 0 and not desc_lines[end - 1]:
                    end -= 1
        desc_lines = desc_lines[:end]
        # Blank lines (from extract.py's tab-paragraph fix) mark real
        # paragraph breaks and are kept; the plain single-newline wraps
        # WITHIN a paragraph are the PDF's line width, not the author's, and
        # are joined with a space so the text reads as prose.
        paragraphs = []
        for chunk in "\n".join(desc_lines).split("\n\n"):
            joined = " ".join(l for l in chunk.split("\n") if l)
            if joined:
                paragraphs.append(joined)
        description = "\n\n".join(paragraphs)

        if not description:
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "spell %r has a complete stat block but no description text" % name}
            )
            continue

        level = 0 if head.group("school_cantrip") else int(head.group("level"))
        school_word = head.group("school") or head.group("school_cantrip")
        spells.append(
            {
                "name": name,
                "level": level,
                "school": SCHOOLS[school_word],
                "cantrip": bool(head.group("school_cantrip")),
                "classes": _classes(level_text),
                "ritual": bool(RITUAL.search(stats["casting_time"])),
                "casting_time": stats["casting_time"],
                "range": stats["range"],
                "components": stats["components"],
                "duration": stats["duration"],
                "description": description,
                "page": page_at(name_at),
            }
        )

    return spells, anomalies


def _dehyphenate_numbered(numbered):
    """Merge a hyphenated line break WITHOUT losing the page number.

    The French parser's `dehyphenate()` joins the whole document into one
    string, substitutes, and re-splits -- then keeps the result only if the
    line count didn't change, on the theory that a changed count means the
    1:1 page mapping broke. Measured here: with 339 real spells spanning 69
    pages of the English SRD, that count changes on nearly every one of the
    document's ~57000 lines (2471 merges), so that fallback fires on every
    real run and dehyphenation never actually applies -- a wrapped field like
    Divine Smite's casting time comes back as "immedi- ately" (hyphen, space,
    and all) instead of "immediately", silently, because the record still
    looks complete.

    Fixed by merging line-by-line instead of on the whole joined string: a
    line ending in a lowercase letter then a hyphen, followed by a line
    starting with a lowercase letter, is one word split by the layout. The
    merged line takes the FIRST fragment's page number, which only matters
    when a word is split across a page boundary -- rare, and no worse than
    the alternative of not merging at all.

    Checked against the last line ALREADY WRITTEN, not against a fixed
    two-line window: "...for an-" / "other 24 hours... crea-" / "ture again"
    is two consecutive breaks (an-other, crea-ture), and a window that
    advances by 2 after each merge would consume the first pair, then
    compare the second line's tail cold against the third line and miss it.
    Re-checking the just-merged line catches a chain of any length.
    """
    out = []
    for page, line in numbered:
        if out and _HYPH_END.search(out[-1][1]) and _HYPH_START.match(line):
            prev_page, prev_line = out.pop()
            out.append((prev_page, prev_line[:-1] + line))
        else:
            out.append((page, line))
    return out


def parse(pages, suspect_pages=()):
    """Parse the document as ONE CONTINUOUS STREAM, not page by page.

    Same rationale as the French parser: an entry's stat block or
    description can straddle a page break, and parsing page by page would
    silently drop it rather than mis-read it. Page numbers are carried
    alongside each line so `source_locator` still points at the page a spell
    *starts* on.
    """
    suspect = set(suspect_pages)

    numbered = []
    for number, raw in enumerate(pages, start=1):
        for line in raw.split("\n"):
            numbered.append((number, line))

    numbered = _dehyphenate_numbered(numbered)

    stream = "\n".join(l for _, l in numbered)
    page_of = [n for n, _ in numbered]

    found, anomalies = parse_stream(stream, page_of)

    spells, conflicts = [], []
    for spell in found:
        if spell["page"] in suspect:
            conflicts.append(
                {"page": spell["page"], "name": spell["name"],
                 "detail": "page text disputed between PyMuPDF and pdftotext"}
            )
        else:
            spells.append(spell)

    spells.sort(key=lambda s: (canon.slugify(s["name"]), s["level"]))
    return spells, anomalies, conflicts
