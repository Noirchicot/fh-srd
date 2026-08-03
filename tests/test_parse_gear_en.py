"""Calibration checks for the English Adventuring Gear table parser."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_gear_en as gear  # noqa: E402


def page(*blocks):
    return extract.normalise("\n".join(blocks))


def wrap(table_body, suspect=()):
    pages = [page("Adventuring Gear\n\nItem\nWeight\nCost\n\n" + table_body)]
    return gear.parse(pages, suspect)


def main():
    # -- an ordinary row --------------------------------------------------
    found, anomalies, conflicts = wrap("Acid\n1 lb.\n25 GP\n")
    assert len(found) == 1 and not anomalies and not conflicts, (found, anomalies)
    assert found[0] == {"name": "Acid", "weight": "1 lb.", "cost": "25 GP", "page": 1}
    print("  ok  an ordinary row parses cleanly")

    # -- "Varies" in both Weight and Cost (Ammunition, Arcane Focus, ...) ---
    found, anomalies, conflicts = wrap("Ammunition\nVaries\nVaries\n")
    assert len(found) == 1 and not anomalies
    assert found[0]["weight"] == "Varies" and found[0]["cost"] == "Varies"
    print("  ok  'Varies' in Weight and Cost is accepted, not rejected as malformed")

    # -- a fractional weight with a unicode fraction character --------------
    found, anomalies, conflicts = wrap("Entertainer’s Pack\n58½ lb.\n40 GP\n")
    assert len(found) == 1 and not anomalies, (found, anomalies)
    assert found[0]["weight"] == "58½ lb."
    print("  ok  a unicode-fraction weight (58½ lb.) is accepted")

    # -- THE TRAP: the table's own "Item / Weight / Cost" header reappears --
    # verbatim mid-table (between Ink and Ink Pen in the real document);
    # skipping it must not be mistaken for the table's end.
    found, anomalies, conflicts = wrap(
        "Ink\n—\n10 GP\n\nItem\nWeight\nCost\n\nInk Pen\n—\n2 CP\n"
    )
    names = [g["name"] for g in found]
    assert names == ["Ink", "Ink Pen"], (
        "a repeated column-header block mid-table must be skipped, not read "
        "as data or mistaken for the table's end: %s / %s" % (names, anomalies)
    )
    print("  ok  a repeated column header mid-table is skipped, not read as a row or an end marker")

    # -- the table's real end (the "Ammunition" sub-table that follows has --
    # a different column count and must not be swallowed as more rows)
    found, anomalies, conflicts = wrap(
        "Waterskin\n5 lb. (full)\n2 SP\n\nType\nAmount\nStorage\nWeight\nCost\n\nArrows\n20\n"
    )
    names = [g["name"] for g in found]
    assert names == ["Waterskin"], (
        "a differently-shaped sub-table immediately after must end this table, "
        "not be swallowed as more rows: %s" % names
    )
    print("  ok  a differently-shaped table right after correctly ends this one")

    # -- NEGATIVE CONTROL: two ordinary rows in sequence --------------------
    found, anomalies, conflicts = wrap("Backpack\n5 lb.\n2 GP\n\nBall Bearings\n2 lb.\n1 GP\n")
    assert len(found) == 2 and not anomalies and not conflicts, (found, anomalies)
    print("  ok  negative control: two ordinary consecutive rows both parse cleanly")

    print("PASS test_parse_gear_en")


if __name__ == "__main__":
    main()
