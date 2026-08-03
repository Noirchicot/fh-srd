"""Calibration checks for the English Rules Glossary parser.

Each scenario reproduces a shape found calibrating parse_glossary_en.py
against the pinned EN PDF, plus a negative control.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_glossary_en as glossary  # noqa: E402


def page(*blocks):
    return extract.normalise("\n".join(blocks))


_INTRO = (
    "Rules Glossary\n\nGlossary Conventions\nSome intro text.\n\n"
    "Rules Definitions\nHere are definitions of various rules.\n\n"
)


def wrap(*raw_pages, suspect=()):
    """Each arg is ONE page's raw text (not yet normalised).

    The intro block is prefixed onto the FIRST page rather than given its
    own page: in the real PDF, "Rules Definitions" and the first entry
    ("Ability Check") sit on the same page 176, separated by a plain blank
    line -- putting the intro on its own page here would introduce a page
    transition the real document does not have, at exactly the point the
    parser is not built to expect one (see the "chapter_start" skip in
    parse_stream, which only looks for a blank line, not a page seam).
    """
    if not raw_pages:
        raw_pages = ("",)
    first = _INTRO + raw_pages[0]
    pages = (
        [page(first)]
        + [page(p) for p in raw_pages[1:]]
        + [page("Gameplay Toolbox\n\nTravel Pace\n")]
    )
    return glossary.parse(pages, suspect)


def main():
    # -- an ordinary entry, no tag -------------------------------------------
    entries, anomalies, conflicts = wrap(
        "Ally\n"
        "A creature is your ally if it is a member of your adventuring "
        "party, your friend, on your side in combat, or a creature that "
        "the rules or the GM designates as your ally.\n"
    )
    assert len(entries) == 1 and not anomalies and not conflicts, (entries, anomalies)
    assert entries[0]["name"] == "Ally" and entries[0]["tag"] is None
    print("  ok  an ordinary entry with no tag parses cleanly")

    # -- a tagged entry: the tag lives in brackets AFTER the name, the -------
    # opposite position from a feat's category word before "Feat" -----------
    entries, anomalies, conflicts = wrap(
        "Blinded [Condition]\n"
        "While you have the Blinded condition, you experience the "
        "following effects. Can't See. You automatically fail any "
        "ability check that requires sight.\n"
    )
    assert len(entries) == 1 and not anomalies
    assert entries[0]["name"] == "Blinded" and entries[0]["tag"] == "condition"
    print("  ok  a bracketed tag is captured and stripped from the name")

    # -- THE TRAP: a multi-column bulleted list embedded INSIDE one entry's -
    # body renders as several blank-line-separated blocks, each looking as
    # blank-line-preceded as a real entry. "Dodge" here is a real glossary
    # term elsewhere in the alphabet, referenced early by "Action" -- it
    # must NOT become its own record with a one-word stolen description.
    entries, anomalies, conflicts = wrap(
        "Action\n"
        "On your turn, you can take one action, chosen from the actions "
        "below or from your own features. These actions are defined "
        "elsewhere in this glossary:\n"
        "\n"
        "Attack\nDash\nDisengage\n"
        "\n"
        "Dodge\nHelp\nHide\n"
        "\n"
        "Advantage\n"
        "If you have Advantage on a D20 Test, roll two d20s and use the "
        "higher roll, a rule explained further in Playing the Game.\n"
    )
    names = [e["name"] for e in entries]
    assert names == ["Action", "Advantage"], (
        "the embedded action list must fold into 'Action', not spawn its own "
        "entries: %s / %s" % (names, anomalies)
    )
    assert "Dodge" in entries[0]["description"] and "Attack" in entries[0]["description"]
    print("  ok  a bare-word list embedded in an entry's body is not mistaken for new entries")

    # -- a multi-paragraph entry (extract.normalise's tab-continuation fix --
    # promotes the second paragraph's leading tab to a blank line): the
    # internal blank line must not split it into two entries.
    entries, anomalies, conflicts = wrap(
        "Armor Class\n"
        "An Armor Class (AC) is the target number for an attack roll "
        "against a creature or an object.\n"
        "\n"
        "Your base AC calculation is 10 plus your Dexterity modifier "
        "unless a rule gives you another calculation to use instead.\n"
    )
    assert len(entries) == 1 and not anomalies, (entries, anomalies)
    assert "Your base AC calculation" in entries[0]["description"]
    assert entries[0]["description"].count("\n\n") == 1
    print("  ok  a genuine internal paragraph break does not split one entry into two")

    # -- THE PAGE-SEAM TRAP: an entry's name is the very first line of a ----
    # new page, with NO blank line at the seam (each page is normalised
    # independently) between the previous entry's last body line and this
    # one's name -- reproduces Ally (p.176) / Area of Effect (p.177) exactly.
    entries, anomalies, conflicts = wrap(
        "Alignment\n"
        "A creature's alignment broadly describes its ethical "
        "attitudes and ideals, a combination of two factors.\n",
        "Ally\n"
        "A creature is your ally if it is a member of your "
        "adventuring party or on your side in combat.\n",
    )
    names = [e["name"] for e in entries]
    assert names == ["Alignment", "Ally"], (
        "an entry name landing on a fresh page with no blank line at the "
        "seam must still be recognised, not glued to the previous entry: "
        "%s / %s" % (names, anomalies)
    )
    assert "adventuring party" in entries[1]["description"]
    assert "adventuring party" not in entries[0]["description"]
    print("  ok  a page transition with no blank line still separates two entries")

    # -- and the reverse must also hold: a genuine paragraph that happens to
    # be split across a page (no blank line, mid-sentence) must NOT gain a
    # synthetic paragraph break in the reconstructed description -----------
    entries, anomalies, conflicts = wrap(
        "Bloodied\nA creature is Bloodied while it has half its Hit",
        "Points or fewer remaining, a state that matters for several features.\n",
    )
    assert len(entries) == 1 and not anomalies
    assert "\n\n" not in entries[0]["description"], (
        "a same-sentence page crossing must join with a space, not a "
        "synthetic paragraph break: %r" % entries[0]["description"]
    )
    assert entries[0]["description"] == (
        "A creature is Bloodied while it has half its Hit Points or fewer "
        "remaining, a state that matters for several features."
    )
    print("  ok  a same-sentence page crossing does not gain a synthetic paragraph break")

    # -- NEGATIVE CONTROL: an ordinary entry is not wrongly excluded --------
    entries, anomalies, conflicts = wrap(
        "Bonus Action\n"
        "A Bonus Action is a special action you can take on the same turn "
        "you take an action, only if a rule explicitly grants you one.\n"
    )
    assert len(entries) == 1 and not anomalies and not conflicts, (
        "an ordinary, complete entry must parse cleanly: %s / %s" % (entries, anomalies)
    )
    print("  ok  negative control: an ordinary complete entry is not wrongly excluded")

    print("PASS test_parse_glossary_en")


if __name__ == "__main__":
    main()
