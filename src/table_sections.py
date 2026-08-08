"""One rule, stated once: a table's own sub-category label is not a row.

Before 2026-08-08 the Weapons and Armor tables' sub-category labels ("Simple
Melee Weapons", "Light Armor (1 Minute to Don or Doff)", "Armures lourdes…")
never reached the row parsers at all. `extract.columns_of()` classified a block
by width, the labels are narrow one-liners, and they were swept to the end of
their page as a group -- a limitation `parse_weapons_en.py` and
`parse_armor_en.py` both documented and neither could act on, because by the
time the parser saw the text the labels had lost their position.

Repairing the two-column extraction put them back where they are printed:
between the rows they introduce. That is strictly better text and it broke both
parsers, in the worst possible way -- the row loop met a line that is not a row,
stopped, and returned **zero weapons and zero armors with zero anomalies**.
The build exited 0.

So the labels now have to be stepped over deliberately. Two ways were available:

  * **Declare them.** The four weapon labels and four armor labels are a closed
    set printed in the source, and this pipeline already declares closed sets
    (the eight Mastery words, the six ability names). Rejected here: the set is
    closed *per table per language*, so it is eight constants that must be kept
    in step with the PDF's exact punctuation and spacing -- "Armures légères
    (s'enfile ou se retire en 1 minute)" has a narrow no-break space in it --
    and a label whose wording drifted upstream would fail as a missing row, not
    as a mismatched constant.

  * **Read the shape.** A row's fields are consecutive lines with no blank
    between them. A sub-category label is a single line with a blank line on
    each side, and the next non-blank line after it starts a valid row. That is
    a structural fact about the table, it needs no vocabulary, and it is the
    same kind of rule the rest of this repository uses to find field boundaries.

The second one, with a deliberately tight guard: exactly ONE line is stepped
over, only when a blank line separates it from what follows, and only when the
caller's own row test says a real row begins there. Anything looser would let a
parser walk out of its table and into the prose after it, which is the failure
this repository has paid for twice (the phantom hag "monster", the
"Success: Half damage." false entry).
"""


def skip_subheading(stripped, index, starts_row):
    """Return the index past a sub-category label at `index`, or None.

    `stripped` is the whitespace-stripped line list, `index` the position the
    row loop is stuck on, and `starts_row(j)` the caller's own test for "a real
    row begins at line j". None means "this is not a label" -- the table has
    ended and the caller should stop, exactly as it did before.
    """
    if index >= len(stripped) or not stripped[index]:
        return None
    j = index + 1
    while j < len(stripped) and not stripped[j]:
        j += 1
    if j == index + 1:
        # No blank line after it: this is a row's own field, not a label.
        return None
    if j >= len(stripped) or not starts_row(j):
        return None
    return j
