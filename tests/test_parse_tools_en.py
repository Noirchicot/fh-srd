"""Calibration checks for the English Tools parser."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_tools_en as tools  # noqa: E402


def page(*blocks):
    return extract.normalise("\n".join(blocks))


def wrap(*tool_pages, suspect=()):
    pages = (
        [page("Tools\nA tool helps you make specialized ability checks.\n\n" + tool_pages[0])]
        + [page(p) for p in tool_pages[1:]]
        + [page("Adventuring Gear\n\nAcid (25 GP)\n")]
    )
    return tools.parse(pages, suspect)


def main():
    # -- an ordinary tool, all five fields present ---------------------------
    found, anomalies, conflicts = wrap(
        "Alchemist’s Supplies (50 GP)\n"
        "Ability: Intelligence\n"
        "Weight: 8 lb.\n"
        "Utilize: Identify a substance (DC 15), or start a fire (DC 15)\n"
        "Craft: Acid, Alchemist’s Fire, Component Pouch\n"
    )
    assert len(found) == 1 and not anomalies and not conflicts, (found, anomalies)
    t = found[0]
    assert t["cost"] == "50 GP" and t["ability"] == "Intelligence"
    assert t["craft"] == "Acid, Alchemist’s Fire, Component Pouch"
    assert t["variants"] is None
    print("  ok  an ordinary tool with Craft but no Variants parses cleanly")

    # -- a tool with neither Craft nor Variants: both fields are genuinely --
    # absent, not an anomaly (reproduces Navigator's Tools)
    found, anomalies, conflicts = wrap(
        "Navigator’s Tools (25 GP)\n"
        "Ability: Wisdom\n"
        "Weight: 2 lb.\n"
        "Utilize: Plot a course (DC 10), or determine position by stargazing (DC 15)\n"
    )
    assert len(found) == 1 and not anomalies
    assert found[0]["craft"] is None and found[0]["variants"] is None
    print("  ok  a tool missing both optional fields is not treated as an anomaly")

    # -- a tool with Variants but no Craft -----------------------------------
    found, anomalies, conflicts = wrap(
        "Gaming Set (Varies)\n"
        "Ability: Wisdom\n"
        "Weight: —\n"
        "Utilize: Discern whether someone is cheating (DC 10)\n"
        "Variants: Dice (1 SP), dragonchess (1 GP)\n"
    )
    assert len(found) == 1 and not anomalies
    assert found[0]["craft"] is None and found[0]["variants"] == "Dice (1 SP), dragonchess (1 GP)"
    print("  ok  Variants without Craft is captured correctly")

    # -- THE PAGE-SEAM TRAP: Craft's list wraps across a page with no blank -
    # line at the seam (reproduces Smith's Tools exactly)
    found, anomalies, conflicts = wrap(
        "Smith’s Tools (20 GP)\n"
        "Ability: Strength\n"
        "Weight: 8 lb.\n"
        "Utilize: Pry open a door or container (DC 20)\n"
        "Craft: Any Melee weapon (except Club, Greatclub,",
        "Quarterstaff, and Whip), Medium armor\n",
    )
    assert len(found) == 1 and not anomalies, (found, anomalies)
    assert found[0]["craft"] == (
        "Any Melee weapon (except Club, Greatclub, Quarterstaff, and Whip), Medium armor"
    ), found[0]["craft"]
    print("  ok  a Craft list that wraps across a page boundary is joined, not truncated")

    # -- NEGATIVE CONTROL: an ordinary, complete tool is not wrongly excluded
    found, anomalies, conflicts = wrap(
        "Thieves’ Tools (25 GP)\n"
        "Ability: Dexterity\n"
        "Weight: 1 lb.\n"
        "Utilize: Pick a lock (DC 15), or disarm a trap (DC 15)\n"
    )
    assert len(found) == 1 and not anomalies and not conflicts, (
        "an ordinary, complete tool must parse cleanly: %s / %s" % (found, anomalies)
    )
    print("  ok  negative control: an ordinary complete tool is not wrongly excluded")

    print("PASS test_parse_tools_en")


if __name__ == "__main__":
    main()
