"""Calibration checks for the English class level-progression parser.

Every trap here is a real one, reproduced from the pinned PDF: the Bard's
two-line feature cell, the Bard's bare em dash where a feature name belongs,
the Rogue's single trailing column, the Monk's "+10 ft.", and the page
boundary that swallows a table whose first row sits at the top of its page.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_class_progression_en as prog  # noqa: E402
from parse_spells_en import _dehyphenate_numbered  # noqa: E402


def page(text):
    return extract.normalise(text)


def blocks_of(pages):
    numbered = []
    for number, raw in enumerate(pages, start=1):
        for line in raw.split("\n"):
            numbered.append((number, line))
    numbered = _dehyphenate_numbered(numbered)
    return prog.groups([l.strip() for _, l in numbered],
                       [n for n, _ in numbered])


def table_text(rows):
    return "\n\n".join("\n".join(r) for r in rows)


def full_table(row_maker):
    """Twenty rows, level 1..20, each built by `row_maker(level, bonus)`."""
    return [row_maker(level, 2 + (level - 1) // 4) for level in range(1, 21)]


def main():
    # -- SPLITTING A ROW ----------------------------------------------------
    # Bard level 1 as the extractor really emits it: the Class Features cell
    # occupies two physical lines, so the row has 16 lines for 15 columns.
    bard_l1 = ["1", "+2", "Bardic Inspiration,", "Spellcasting", "D6", "2", "4",
               "2"] + ["—"] * 8
    split, why = prog.split_row(bard_l1, 15, prog.CELL_RE)
    assert why is None, why
    level, bonus, features, trailing = split
    assert (level, bonus) == (1, 2)
    assert features == "Bardic Inspiration, Spellcasting", features
    assert trailing == ["D6", "2", "4", "2"] + ["—"] * 8, trailing
    print("  ok  a wrapped Class Features cell is rejoined by counting from both ends")

    # THE REASON the boundary is a count and not "read compact cells from the
    # end": the feature cell's own value can BE a compact cell. Bard 11.
    bard_l11 = ["11", "+4", "—", "D10", "4", "16", "4", "3", "3", "3", "2", "1",
                "—", "—", "—"]
    split, why = prog.split_row(bard_l11, 15, prog.CELL_RE)
    assert why is None, why
    assert split[2] == "—", split[2]
    assert split[3] == ["D10", "4", "16", "4", "3", "3", "3", "2", "1", "—", "—", "—"]
    print("  ok  a bare dash in the feature cell is not mistaken for a value column")

    # -- CELL TYPING --------------------------------------------------------
    assert prog.cell_value("—") is None
    assert prog.cell_value("4") == 4
    assert prog.cell_value("D6") == "D6" and prog.cell_value("1d10") == "1d10"
    assert prog.cell_value("+10 ft.") == "+10 ft."
    assert prog.cell_value("+2") == "+2"
    print("  ok  digits become integers, an em dash becomes null, dice stay printed text")

    # -- RECORD ASSEMBLY ----------------------------------------------------
    rows = [prog.split_row(
        ["%d" % lv, "+%d" % (2 + (lv - 1) // 4), "Feature", "D6", "2", "4", "2"]
        + ["—"] * 8, 15, prog.CELL_RE)[0] for lv in range(1, 21)]
    record, columns, problems = prog.build_record(
        "Bard", "en", ["Bardic Die", "Cantrips", "Prepared Spells"], 9, rows,
        31, prog.SUBCLASS_PLACEHOLDER,
    )
    assert not problems, problems
    assert columns == 15
    assert record["class"] == "srd:class:en:bard"
    assert [c["key"] for c in record["resource_columns"]] == [
        "bardic_die", "cantrips", "prepared_spells"]
    first = record["levels"][0]
    assert first["spell_slots"] == [2, 0, 0, 0, 0, 0, 0, 0, 0], first["spell_slots"]
    assert first["resources"] == {"bardic_die": "D6", "cantrips": 2,
                                  "prepared_spells": 4}
    print("  ok  em dashes in the slot band become 0, and the band is an array by level")

    # a table with no slot band carries no spell_slots key at all, rather than
    # an empty list that reads like "zero slots of zero levels"
    rows = [prog.split_row(["%d" % lv, "+%d" % (2 + (lv - 1) // 4), "Feature", "1d6"],
                           4, prog.CELL_RE)[0] for lv in range(1, 21)]
    record, columns, problems = prog.build_record(
        "Rogue", "en", ["Sneak Attack"], 0, rows, 62, prog.SUBCLASS_PLACEHOLDER)
    assert not problems and columns == 4
    assert "spell_slots" not in record["levels"][0]
    assert record["levels"][0]["resources"] == {"sneak_attack": "1d6"}
    print("  ok  a table with no slot band has no spell_slots key, not an empty one")

    # -- FEATURE NAMES ARE A LIST -------------------------------------------
    rows = [prog.split_row(
        ["1", "+2", "Rage, Unarmored Defense, Weapon Mastery", "2", "+2", "2"],
        6, prog.CELL_RE)[0]]
    record, _, _ = prog.build_record(
        "Barbarian", "en", ["Rages", "Rage Damage", "Weapon Mastery"], 0, rows,
        28, prog.SUBCLASS_PLACEHOLDER)
    assert record["levels"][0]["features"] == [
        "Rage", "Unarmored Defense", "Weapon Mastery"]
    assert record["levels"][0]["resources"]["rage_damage"] == "+2"
    print("  ok  the Class Features cell splits on ', ' into named features")

    # -- PAGE BOUNDARIES END A ROW ------------------------------------------
    # Five French tables begin on the first line of their page with no blank
    # line before them. Without the page break in `groups`, the preceding
    # paragraph swallows the level-1 row and the whole table disappears.
    blocks = blocks_of([page("A closing paragraph."), page("1\n+2\nFeature\n1d6")])
    heads = [b[2][0] for b in blocks]
    assert "1" in heads, heads
    assert blocks[-1][2] == ["1", "+2", "Feature", "1d6"], blocks[-1]
    print("  ok  a page boundary ends a group, so a table at a page top survives")

    # -- TABLE DETECTION IS SELF-ANCHORING ----------------------------------
    rows = full_table(lambda lv, pb: ["%d" % lv, "+%d" % pb, "Feature", "1d6"])
    blocks = blocks_of([page("Rogue Features\n\n" + table_text(rows))])
    found = prog.find_tables(blocks)
    assert len(found) == 1 and len(found[0]) == 20, [len(t) for t in found]
    print("  ok  a 1..20 run is found with no header, no title and no page number")

    # -- NEGATIVE CONTROL 1: a run that stops at 19 is not a table ----------
    short = full_table(lambda lv, pb: ["%d" % lv, "+%d" % pb, "Feature", "1d6"])[:19]
    assert prog.find_tables(blocks_of([page(table_text(short))])) == []
    print("  ok  negative control: a run short of level 20 is not accepted as a table")

    # -- NEGATIVE CONTROL 2: a trailing cell that is prose is refused -------
    split, why = prog.split_row(
        ["1", "+2", "Feature", "Second Wind"], 4, prog.CELL_RE)
    assert split is None and "not a count, a die or a dash" in why, why
    print("  ok  negative control: a header word in a value column is refused, not stored")

    # -- NEGATIVE CONTROL 3: a wrong proficiency bonus is reported ----------
    rows = [prog.split_row(["5", "+2", "Feature", "1d6"], 4, prog.CELL_RE)[0]]
    _, _, problems = prog.build_record(
        "Rogue", "en", ["Sneak Attack"], 0, rows, 62, prog.SUBCLASS_PLACEHOLDER)
    assert problems and "expected +3" in problems[0], problems
    print("  ok  negative control: a bonus that breaks the +2/+3/+4/+5/+6 ladder is caught")

    # -- NEGATIVE CONTROL 4: every declared class has a coherent spec -------
    for cls, (resources, slots) in prog.TABLES.items():
        assert cls in prog.CLASSES, cls
        assert len(set(resources)) == len(resources), cls
        assert slots in (0, 5, 9), (cls, slots)
    assert set(prog.TABLES) == set(prog.CLASSES)
    assert all(re.match(r"^\+\d$", "+%d" % (2 + (lv - 1) // 4)) for lv in range(1, 21))
    print("  ok  negative control: the declared spec covers all twelve classes, once each")

    print("PASS test_parse_class_progression_en")


if __name__ == "__main__":
    main()
