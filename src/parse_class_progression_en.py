"""Class level-progression table parser for the English SRD 5.2.1.

CALIBRATED against the pinned EN PDF on 2026-08-08, one table per class
chapter (p.28-77). Twelve tables, 240 level rows, 0 anomalies.

WHY THIS EXISTS: the level-progression table was deferred twice on purpose --
once by the Equipment lot, once by the class-grammar lot -- and the second
deferral left its measurement to whoever came next, in `parse_classes_en.py`'s
own docstring: "row-coherent in the extracted text (a blank-line-separated
group of N lines per level, matching the column count) ... a meaningfully
easier starting point than Equipment's tables were." That measurement is
correct and this parser is built on it. Until now the base could say a Wizard
has a Spellcasting feature at level 1 and could not say how many spell slots
it buys -- "Spell Slots per Spell Level" existed in the catalogue only as a
fragment of prose inside a feature's description. A builder cannot make a
level 3 Wizard out of that.

THE ROWS ARE CLEAN. THE HEADER IS NOT. This is the one thing the earlier
measurement did not go on to check, and it decides the whole design.

A row is a blank-line-separated group whose first line is the level number and
whose second is the proficiency bonus -- always, in all twelve tables, both
languages. The header is a different story: it is made of narrow one- and
two-line cells, and extract.py's columns_of() classifies a block by width, so
the header cells are scattered by the same rule that correctly keeps body text
in two columns. Measured, not feared:

  * Barbarian's header survives in true left-to-right order (p.28);
  * Bard's does not -- "Proficiency Bonus / Bardic Die / Prepared Spells /
    ——Spell Slots per Spell Level—— / Level / Class Features / Cantrips /
    1..9" (p.31), which is neither printed order nor column order;
  * Sorcerer's is split across the page, half before the rows and half after
    them (p.65), as are Cleric's, Druid's, Wizard's and Ranger's;
  * the French Cleric table (FR p.38) has NO header text before its rows at
    all -- every cell of it lands after the last row.

So the column NAMES cannot be read in order from the extracted text, and a
parser that tried would silently mis-key Sorcery Points as Cantrips. What the
rows do give, reliably, is column POSITION. The columns are therefore declared
here per class (TABLES below), the same way `parse_classes_en.py` declares the
fixed field order of the core-traits table rather than pattern-matching a
colon that is not there -- and then checked three ways, because a declared
constant that nothing verifies is just a guess with better manners:

  1. every row must yield exactly the declared number of cells;
  2. every declared column label must actually appear in that table's own page
     text (a typo'd or invented label fails loudly);
  3. `tests/test_class_progression_witness.py` re-reads all 24 tables from the
     PDFs with poppler's `pdftotext -layout`, which renders the header ALIGNED
     over its column, and asserts the numbers and their order agree with what
     this parser produced. That is an independent extractor reading an
     independent rendering -- the same "two witnesses" rule the pipeline
     already applies page by page, applied to column order.

WHERE A ROW ENDS AND THE FEATURE CELL BEGINS. Only one cell in the table can
wrap: Class Features. Every other cell is a level number, a bonus, a count, a
die or an em dash, and never occupies two lines (asserted). So a row of L
lines with K declared columns splits as: line 0 is the level, line 1 the
proficiency bonus, the LAST K-3 lines are the trailing cells, and everything
between is the feature cell joined with spaces. Counting from both ends is
what makes it exact -- the feature cell is the only variable-length part, and
it is also the only cell whose own value can be a bare "—" (Bard 11, Wizard 7,
Sorcerer 9), which is why "read compact-looking lines from the end" is used
only as a check and never as the boundary rule.

TWO FIELDS ARE DECOMPOSED, and the line is the same one the class grammar drew
between a grant and a choice. `proficiency_bonus` becomes an integer: it is
printed "+2", it is uniform across all twenty-four tables, and it is
arithmetic a builder performs, not text it displays. Spell slots become an
array of integers with 0 where the source prints an em dash -- "—" in that
column means "no slots of this level", which is 0, and an array indexed by
spell level is the shape the rule is used in. Everything else in a resource
column stays the source's own text unless it is entirely digits, because
"1d6", "D8" and "+10 ft." are not counts and coercing them would invent a
type: digits -> int, "—" -> null, anything else -> the printed string.

CLASS FEATURES ARE SPLIT ON ", " and that is measured, not assumed: every one
of the 507 resulting names in the two languages matches a "Level N: <Name>"
heading already captured in the class record, or is the table's own
"Subclass feature" / "Aptitude de sous-classe" placeholder. No SRD feature
name contains a comma. The check runs in the test suite against the exported
class records, so a future SRD printing that adds one fails visibly instead of
splitting a feature in half.

WHAT IS DELIBERATELY NOT A RECORD HERE: the "Multiclass Spellcaster: Spell
Slots per Spell Level" table (p.26). It is the same grammar and it parses
cleanly -- and it is used, in the tests, as a third independent witness that
the five full-caster slot grids are right, since the SRD prints the same
numbers twice in two unrelated chapters. But it is not a class's progression,
it belongs to the multiclassing rules, and inventing a `class: null` record to
hold it inside a kind named `class-progression` would be a shape the source
does not ask for. Flagged for the architect rather than smuggled in.
"""

import re

import canon
from parse_classes_en import CLASSES
from parse_spells_en import _dehyphenate_numbered

MAX_LEVEL = 20
DASH = "—"

# Resource columns per class, in PRINTED left-to-right order, followed by the
# number of spell-slot columns (0 = the table has no slot band). The slot band
# is always the rightmost part of the table where it exists; Warlock has none
# because Pact Magic prints its slots as two ordinary columns instead of a
# grid, and that difference is the rule, not a formatting accident.
TABLES = {
    "Barbarian": (["Rages", "Rage Damage", "Weapon Mastery"], 0),
    "Bard": (["Bardic Die", "Cantrips", "Prepared Spells"], 9),
    "Cleric": (["Channel Divinity", "Cantrips", "Prepared Spells"], 9),
    "Druid": (["Wild Shape", "Cantrips", "Prepared Spells"], 9),
    "Fighter": (["Second Wind", "Weapon Mastery"], 0),
    "Monk": (["Martial Arts", "Focus Points", "Unarmored Movement"], 0),
    "Paladin": (["Channel Divinity", "Prepared Spells"], 5),
    "Ranger": (["Favored Enemy", "Prepared Spells"], 5),
    "Rogue": (["Sneak Attack"], 0),
    "Sorcerer": (["Sorcery Points", "Cantrips", "Prepared Spells"], 9),
    "Warlock": (["Eldritch Invocations", "Cantrips", "Prepared Spells",
                 "Spell Slots", "Slot Level"], 0),
    "Wizard": (["Cantrips", "Prepared Spells"], 9),
}

SLOT_BAND_LABEL = "Spell Slots per Spell Level"

# The table's own placeholder for "your subclass gives you something at this
# level" -- a pointer, not a feature name, and it has no "Level N:" heading.
SUBCLASS_PLACEHOLDER = "Subclass feature"

_PB_RE = re.compile(r"^\+(\d)$")
# Every cell that is not the Class Features cell: a count, a die, a bonus, a
# distance, or an em dash. Used to CHECK the split, never to find it -- and
# it is per-language, because the unit in it is: English's Unarmored Movement
# column reads "+10 ft.", French's reads "+3 m" and "+4,50 m", decimal comma
# and all. A shared pattern loose enough to swallow both would have stopped
# checking anything.
CELL_RE = re.compile(r"^(?:—|\d+|\+\d+(?: ft\.)?|[Dd]\d+|\d+d\d+)$")


def needles(cls):
    """Text that identifies which class a table belongs to.

    Two of them, because neither is present on every page: the core-traits
    box ("Core Monk Traits") sits on the previous page for Monk, Ranger,
    Rogue, Sorcerer and Warlock, and the table's own title ("Monk Features")
    is what is left there instead.
    """
    return ("Core %s Traits" % cls, "%s Features" % cls)


# ---------------------------------------------------------------------------
# Mechanics — shared with the French grammar, which imports them. Splitting a
# blank-line-separated row into cells is arithmetic on line counts; it has no
# language in it. The French module declares its own classes, its own column
# labels and its own anchors, which is where the two grammars actually differ.
# ---------------------------------------------------------------------------

def groups(stripped, page_of):
    """Blank-line-separated groups, as (page, first line index, [lines]).

    A PAGE BOUNDARY ENDS A GROUP TOO, and that is not tidiness. Five of the
    twelve French tables (Clerc, Druide, Ensorceleur, Magicien, Occultiste)
    begin on the very first line of their page, with no blank line before
    them -- the preceding page's last paragraph and the table's level-1 row
    are adjacent in a flattened stream. Without this break the level-1 row is
    swallowed by that paragraph, the 1..20 run never starts, and exactly
    those five tables vanish. Measured: 7 of 12 found before, 12 after. No
    row of any table in either language spans a page boundary.
    """
    out, cur, start = [], [], None
    for i, line in enumerate(stripped):
        if line and (not cur or page_of[i] == page_of[start]):
            if not cur:
                start = i
            cur.append(line)
            continue
        if cur:
            out.append((page_of[start], start, cur))
            cur = []
        if line:
            start = i
            cur.append(line)
    if cur:
        out.append((page_of[start], start, cur))
    return out


def find_tables(blocks):
    """Runs of exactly MAX_LEVEL groups whose heads are 1..20 with a bonus.

    Self-anchoring: it needs no header, no title and no page number, which is
    what makes it survive the header scattering described in the docstring.
    A run that stops short of 20 is not a table and is not reported -- the
    caller checks the COUNT of tables found against the twelve classes, so a
    table lost entirely is caught, loudly, one level up.
    """
    tables = []
    i = 0
    while i < len(blocks):
        lines = blocks[i][2]
        if lines[0] == "1" and len(lines) > 1 and _PB_RE.match(lines[1]):
            run, level, j = [blocks[i]], 2, i + 1
            while (level <= MAX_LEVEL and j < len(blocks)
                   and blocks[j][2][0] == str(level)
                   and len(blocks[j][2]) > 1 and _PB_RE.match(blocks[j][2][1])):
                run.append(blocks[j])
                level += 1
                j += 1
            if level == MAX_LEVEL + 1:
                tables.append(run)
                i = j
                continue
        i += 1
    return tables


def split_row(lines, columns, cell_re):
    """(level, bonus, features cell, [trailing cells]) or a reason it failed."""
    trailing_count = columns - 3
    if len(lines) < columns:
        return None, "row has %d lines, fewer than the %d declared columns" % (
            len(lines), columns)
    cut = len(lines) - trailing_count
    trailing = lines[cut:] if trailing_count else []
    features = " ".join(lines[2:cut]).strip()
    bad = [c for c in trailing if not cell_re.match(c)]
    if bad:
        return None, "cell(s) %r are not a count, a die or a dash" % bad
    if not features:
        return None, "no Class Features cell between the bonus and the values"
    return (int(lines[0]), int(_PB_RE.match(lines[1]).group(1)), features,
            trailing), None


def cell_value(text):
    """digits -> int, em dash -> None, anything else -> the printed string."""
    if text == DASH:
        return None
    if text.isdigit():
        return int(text)
    return text


def build_record(cls, lang, resource_labels, slot_levels, rows, page,
                 subclass_placeholder):
    """Assemble one class-progression record from its twenty split rows."""
    columns = 3 + len(resource_labels) + slot_levels
    keys = [canon.slugify(label).replace("-", "_") for label in resource_labels]
    levels, anomalies = [], []

    for level, bonus, features, trailing in rows:
        expected_bonus = 2 + (level - 1) // 4
        if bonus != expected_bonus:
            anomalies.append(
                "level %d: proficiency bonus +%d, expected +%d"
                % (level, bonus, expected_bonus))
        resources = {}
        for key, raw in zip(keys, trailing[:len(keys)]):
            resources[key] = cell_value(raw)
        slots = []
        for spell_level, raw in enumerate(trailing[len(keys):], start=1):
            if raw == DASH:
                slots.append(0)
            elif raw.isdigit():
                slots.append(int(raw))
            else:
                anomalies.append(
                    "level %d: spell-slot cell for level %d is %r, not a count"
                    % (level, spell_level, raw))
                slots.append(0)
        entry = {
            "level": level,
            "proficiency_bonus": bonus,
            "features": ([] if features == DASH
                         else [f.strip() for f in features.split(", ") if f.strip()]),
            "resources": resources,
        }
        if slot_levels:
            entry["spell_slots"] = slots
        levels.append(entry)

    record = {
        "name": cls,
        "class": canon.record_id("srd", "class", lang, canon.slugify(cls)),
        "resource_columns": [
            {"key": key, "label": label}
            for key, label in zip(keys, resource_labels)
        ],
        "spell_slot_levels": slot_levels,
        "subclass_placeholder": subclass_placeholder,
        "levels": levels,
        "page": page,
    }
    return record, columns, anomalies


def page_texts(numbered):
    """Page number -> its whole text as one whitespace-collapsed string.

    Built from the DEHYPHENATED stream, not from the raw pages, and that is
    load-bearing rather than incidental: French breaks its own header cells
    mid-word, so Occultiste's "Niveau des emplacements" column is printed
    "Niveau des / emplace- / ments". Checked against the raw page it is
    absent, and the parser would refuse a table whose column is really there.
    """
    texts = {}
    for page, line in numbered:
        texts.setdefault(page, []).append(line)
    return {page: " ".join(" ".join(lines).split())
            for page, lines in texts.items()}


def parse_pages(pages, suspect_pages, classes, tables_spec, needles_for,
                slot_band_label, subclass_placeholder, lang, dehyphenate,
                cell_re):
    suspect = set(suspect_pages)

    numbered = []
    for number, raw in enumerate(pages, start=1):
        for line in raw.split("\n"):
            numbered.append((number, line))
    numbered = dehyphenate(numbered)
    stripped = [l.strip() for _, l in numbered]
    page_of = [n for n, _ in numbered]
    texts = page_texts(numbered)

    blocks = groups(stripped, page_of)
    found = find_tables(blocks)

    records, anomalies, conflicts = [], [], []

    if len(found) != len(classes):
        anomalies.append(
            {"page": 0, "line": 0,
             "detail": "found %d level-progression tables, expected %d (one per class)"
                       % (len(found), len(classes))}
        )
        return records, anomalies, conflicts

    for cls, run in zip(classes, found):
        page = run[0][0]
        line_no = run[0][1]
        text = texts.get(page, "")

        if not any(needle in text for needle in needles_for(cls)):
            anomalies.append(
                {"page": page, "line": line_no,
                 "detail": "table %d is in document order the %s table, but p.%d "
                           "carries none of %r -- refusing to attribute it"
                           % (classes.index(cls) + 1, cls, page, needles_for(cls))}
            )
            continue

        resource_labels, slot_levels = tables_spec[cls]
        columns = 3 + len(resource_labels) + slot_levels

        missing = [label for label in resource_labels if label not in text]
        if slot_levels and slot_band_label not in text:
            missing.append(slot_band_label)
        if missing:
            anomalies.append(
                {"page": page, "line": line_no,
                 "detail": "%s: declared column(s) %r do not appear on p.%d"
                           % (cls, missing, page)}
            )
            continue

        rows, failed = [], None
        for _, row_line, lines in run:
            split, why = split_row(lines, columns, cell_re)
            if why:
                failed = {"page": page, "line": row_line,
                          "detail": "%s level %s: %s" % (cls, lines[0], why)}
                break
            rows.append(split)
        if failed:
            anomalies.append(failed)
            continue

        record, _, problems = build_record(
            cls, lang, resource_labels, slot_levels, rows, page,
            subclass_placeholder,
        )
        if problems:
            for problem in problems:
                anomalies.append({"page": page, "line": line_no,
                                  "detail": "%s: %s" % (cls, problem)})
            continue

        if page in suspect:
            conflicts.append(
                {"page": page, "name": cls,
                 "detail": "page text disputed between PyMuPDF and pdftotext"}
            )
            continue
        records.append(record)

    records.sort(key=lambda r: canon.slugify(r["name"]))
    return records, anomalies, conflicts


def parse(pages, suspect_pages=()):
    return parse_pages(
        pages, suspect_pages, CLASSES, TABLES, needles, SLOT_BAND_LABEL,
        SUBCLASS_PLACEHOLDER, "en", _dehyphenate_numbered, CELL_RE,
    )
