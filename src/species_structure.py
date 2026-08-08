"""Traits and lineages, from the page's geometry rather than from its prose.

WHY THIS IS SHARED BETWEEN THE EN AND FR PARSERS when nothing else in this
repository is. The eleven other genres keep two independently calibrated
grammars on purpose, and every one of them earned that: the French SRD wraps,
elides, capitalises and abbreviates differently, and a shared grammar would
have hidden those differences instead of finding them.

This is not a grammar. It reads two things the *typesetter* states and the
*language* does not: that a trait name is set in bold italic, and that a
lineage table's cells sit at four fixed left edges. Neither fact has a French
form and an English form. Measured: 33 bold-italic runs in the EN species
chapter and 33 in FR, all of them trait names in both; and the same four-column
table shape in `Elven Lineages` / `Lignages elfiques` and `Fiendish Legacies` /
`Héritages fiélons`. Duplicating that into two files would be two copies of one
measurement, which is the failure mode the separate grammars exist to avoid,
not an instance of it.

WHAT IT REFUSES. Nothing here infers a trait from a sentence shape, and nothing
infers a lineage from a spell name. If the emphasis phrase is not found in the
description, or the table the description names is not on the pages the record
spans, or that table came back with a defect, the species gets NO `traits` /
`lineages` and an anomaly is raised. An absent field means "not stated in a form
this could read", which is the only meaning it is allowed to have.
"""

import re

import canon

# "Level 1" / "Niveau 1" — the number is the only part of a column label this
# reads, and it is read rather than assumed: a header that carries no number is
# a defect, not a column silently keyed by its position.
_LEVEL = re.compile(r"(\d+)")


def _strip_label(phrase):
    """"Darkvision." -> "Darkvision". The printed name keeps everything else."""
    return phrase.rstrip().rstrip(".").strip()


def claim(description, phrases, start):
    """Take this description's run of emphasis phrases off the chapter's stream.

    THE PHRASE STREAM IS CONSUMED ONCE, IN DOCUMENT ORDER, AND THAT IS LOAD-
    BEARING RATHER THAN TIDY. Matching each species against every phrase on its
    own pages looks equivalent and is not: "Vision dans le noir." is printed for
    six of the nine French species, and the FIRST one on a page belongs to
    whichever entry the page opened with. Searching the Elf's description for
    the page's phrases in page order found the Dwarf's "Vision dans le noir."
    at the END of the Elf's text, moved the cursor there, and lost the four
    traits before it — the Elf came back with one trait instead of five, and so
    did the Gnome and the Orc. Measured before and after: 25 French traits that
    way, 33 this way, against 33 in English.

    Returns `(cuts, next_start)`. A phrase that is not found ends this
    description's run: it belongs to the next species.
    """
    cuts = []
    cursor = 0
    index = start
    while index < len(phrases):
        at = description.find(phrases[index], cursor)
        if at < 0:
            break
        cuts.append((at, at + len(phrases[index]), _strip_label(phrases[index])))
        cursor = at + len(phrases[index])
        index += 1
    return cuts, index


def traits_from(description, cuts, drop=None):
    """Build `{id, name, text}` from the cuts `claim` returned.

    `drop` is a (start, end) character span to remove from the trait text it
    falls in — the lineage table, which is printed inside a trait's own
    paragraph flow and is carried separately as `lineages`.
    """
    traits, dropped = [], False
    for index, (start, after, name) in enumerate(cuts):
        end = cuts[index + 1][0] if index + 1 < len(cuts) else len(description)
        text = description[after:end]
        if drop:
            drop_start, drop_end = drop
            if after <= drop_start and drop_end <= end:
                text = description[after:drop_start] + description[drop_end:end]
                dropped = True
        text = re.sub(r"\s*\n\s*\n\s*", "\n\n", text).strip()
        traits.append({"id": canon.slugify(name), "name": name, "text": text})
    return traits, dropped


def find_table(description, tables):
    """The lineage table this description names, or None.

    The link is the table's own caption appearing in the description — the
    printed page puts the caption there, and the trait text says so in words
    ("Choose a lineage from the Elven Lineages table"). Nothing is matched on a
    species name or on a hard-coded caption, so a chapter that gained a tenth
    species with a table would be read, and one whose caption moved would fail
    loudly instead of attaching to the wrong record.
    """
    found = None
    for table in tables:
        caption = table.get("caption")
        if not caption or caption not in description:
            continue
        if found is not None:
            return {"defect": "two tables claim this description: %r and %r"
                             % (found.get("caption"), caption)}
        found = table
    return found


def lineages_from(table):
    """`[{id, name, levels}]` from a cell-separated table, or (None, reason).

    `levels` is keyed by the level number the column header prints, as a
    string, because a JSON object has no integer keys and the alternative — an
    array indexed by position — would silently renumber if the SRD ever printed
    a fourth level column.
    """
    if "defect" in table:
        return None, table["defect"]
    columns = table.get("columns") or []
    if len(columns) < 2:
        return None, "table %r has fewer than two columns" % table.get("caption")

    levels = []
    for column in columns[1:]:
        match = _LEVEL.search(column)
        if not match:
            return None, "column header %r carries no level number" % column
        levels.append(match.group(1))
    if len(set(levels)) != len(levels):
        return None, "table %r repeats a level number in its headers" % table.get("caption")

    out = []
    for row in table.get("rows") or []:
        if len(row) != len(columns):
            return None, "row %r has %d cells for %d columns" % (row[0], len(row), len(columns))
        name = row[0].strip()
        if not name:
            return None, "a row of table %r has no name cell" % table.get("caption")
        out.append({
            "id": canon.slugify(name),
            "name": name,
            "levels": {level: row[i + 1].strip() for i, level in enumerate(levels)},
        })
    if not out:
        return None, "table %r has a header and no rows" % table.get("caption")
    return out, None


def attach_all(species_list, layout, anomalies):
    """Add `traits`, and `lineages` where the source prints a table.

    Takes the whole chapter at once, in document order, because the phrase
    stream is consumed once — see `claim`. Each species carries
    `first_page`/`last_page`, which this consumes: the table search is confined
    to the pages a record actually spans.
    """
    layout = list(layout)
    spans = [(s["first_page"], s["last_page"]) for s in species_list]
    if not species_list or not layout:
        for species in species_list:
            species.pop("first_page", None)
            species.pop("last_page", None)
            anomalies.append(
                {"page": species["page"], "line": 0,
                 "detail": "species %r: no page geometry was supplied, so neither "
                           "its traits nor its lineages could be read" % species["name"]}
            )
        return

    # THE STREAM IS THE CHAPTER'S, NOT THE DOCUMENT'S. Bold italic is used all
    # over this PDF — every spell's own "Using a Higher-Level Spell Slot", every
    # monster trait — so a cursor starting at page 1 arrives at the first
    # species some thousands of phrases too late and claims nothing.
    chapter_first = min(first for first, _ in spans)
    chapter_last = max(last for _, last in spans)
    phrases = [p for page in layout[max(0, chapter_first - 1):chapter_last]
               for p in page.get("emphasis", ())]
    cursor = 0

    for species in species_list:
        first = species.pop("first_page")
        last = species.pop("last_page")
        name = species["name"]
        description = species["description"]

        drop = None
        tables = [t for page in layout[max(0, first - 1):last]
                  for t in page.get("tables", ())]
        table = find_table(description, tables)
        if table is not None:
            if "defect" in table:
                anomalies.append(
                    {"page": species["page"], "line": 0,
                     "detail": "species %r: its lineage table was not read as cells (%s)"
                               % (name, table["defect"])}
                )
            else:
                lineages, reason = lineages_from(table)
                if reason:
                    anomalies.append(
                        {"page": species["page"], "line": 0,
                         "detail": "species %r: %s" % (name, reason)}
                    )
                else:
                    species["lineages"] = lineages
                    drop = table_span(description, table)

        cuts, cursor = claim(description, phrases, cursor)
        if cuts:
            traits, dropped = traits_from(description, cuts, drop)
            species["traits"] = traits
            if drop and not dropped:
                anomalies.append(
                    {"page": species["page"], "line": 0,
                     "detail": "species %r: its lineage table straddles two traits, so "
                               "the table prose was left inside a trait's text" % name}
                )
            continue
        if not cuts:
            anomalies.append(
                {"page": species["page"], "line": 0,
                 "detail": "species %r: the chapter's emphasis stream reached it at "
                           "phrase %d (%r) and that phrase is not in its description, "
                           "so no trait could be named"
                           % (name, cursor,
                              phrases[cursor] if cursor < len(phrases) else None)}
            )


def table_span(description, table):
    """Where the table's own text sits inside the description, or None.

    THE CAPTION ALONE IS THE WRONG ANCHOR, and cheaply so: the Elf's own prose
    says "Choose a lineage from the Elven Lineages table", which contains the
    caption verbatim and is not the table. Cutting there deleted three real
    sentences of the Elven Lineage trait — "…table. You gain the level 1 benefit
    of that lineage. When you reach character levels 3 and 5…" — and the loss
    was invisible in the record, which still looked like a sentence.

    So the anchor is the caption IMMEDIATELY FOLLOWED BY ITS OWN HEADER ROW,
    which is what the repaired reading order prints and what no sentence
    contains. The span ends at the last cell of the last row: a table is emitted
    contiguously, caption then header then each row's cells in order. If either
    end is missing, this returns None and the trait keeps the table prose rather
    than being cut at a guess.
    """
    caption = table.get("caption")
    columns = table.get("columns") or []
    rows = table.get("rows") or []
    if not caption or not columns or not rows:
        return None
    head = "%s\n\n%s" % (caption, " ".join(columns))
    start = description.find(head)
    if start < 0:
        return None
    last = rows[-1][-1].strip()
    if not last:
        return None
    at = description.find(last, start + len(head))
    if at < 0:
        return None
    return start, at + len(last)
