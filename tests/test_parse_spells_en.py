"""Calibration checks for the English spell parser.

Each scenario here reproduces a shape actually found in the pinned EN PDF
while calibrating parse_spells_en.py, plus one negative control proving the
suite can fail. Fixtures are built with `extract.normalise()` so that the
paragraph-break behaviour they depend on (a blank line for a real paragraph
start, a plain "\\n" for a mid-sentence wrap) matches what the real pipeline
hands the parser -- not a hand-simplified version of it.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_spells_en  # noqa: E402


def page(*blocks):
    """Join text blocks the way `columns_of` would, then normalise.

    Each block already ends with its own content; blocks are separated the
    way PyMuPDF blocks are -- which is what makes a real blank line appear
    between them once normalised.
    """
    raw = "\n".join(blocks)
    return extract.normalise(raw)


def parse_one(*pages, suspect=()):
    spells, anomalies, conflicts = parse_spells_en.parse(list(pages), suspect)
    return spells, anomalies, conflicts


def main():
    # -- level-first grammar, ritual in the CASTING TIME line -------------
    pages = [page(
        "Alarm\nLevel 1 Abjuration (Ranger, Wizard)\n",
        "Casting Time: 1 minute or Ritual\nRange: 30 feet\n"
        "Components: V, S, M (a bell and silver wire)\nDuration: 8 hours\n",
        "You set an alarm against intrusion.\n\t Nothing else happens.\n",
    )]
    spells, anomalies, conflicts = parse_one(*pages)
    assert len(spells) == 1 and not anomalies and not conflicts, (spells, anomalies)
    s = spells[0]
    assert s["level"] == 1 and s["school"] == "abjuration" and not s["cantrip"]
    assert s["ritual"] is True, "ritual must be read off the casting-time line"
    assert "Ritual" not in s["casting_time"] or "or Ritual" in s["casting_time"]
    print("  ok  level-first head, ritual detected in Casting Time (not the level line)")

    # -- cantrip line: school first, then the word "Cantrip" --------------
    pages = [page(
        "Acid Splash\nEvocation Cantrip (Sorcerer, Wizard)\n",
        "Casting Time: Action\nRange: 60 feet\nComponents: V, S\n"
        "Duration: Instantaneous\n",
        "You create an acidic bubble.\n\t Cantrip Upgrade. It gets worse.\n",
    )]
    spells, anomalies, conflicts = parse_one(*pages)
    assert len(spells) == 1 and not anomalies
    s = spells[0]
    assert s["cantrip"] is True and s["level"] == 0
    assert "Cantrip Upgrade." in s["description"]
    print("  ok  cantrip head (school before the word 'Cantrip')")

    # -- wrapped class list on the head line -------------------------------
    pages = [page(
        "Detect Magic\nLevel 1 Divination (Bard, Cleric, Druid, Paladin,\n"
        "Ranger, Sorcerer, Warlock, Wizard)\n",
        "Casting Time: Action or Ritual\nRange: Self\nComponents: V, S\n"
        "Duration: Concentration, up to 10 minutes\n",
        "You sense the presence of magic.\n",
    )]
    spells, anomalies, conflicts = parse_one(*pages)
    assert len(spells) == 1 and not anomalies
    s = spells[0]
    assert s["classes"] == ["Bard", "Cleric", "Druid", "Paladin", "Ranger",
                             "Sorcerer", "Warlock", "Wizard"], s["classes"]
    assert s["ritual"] is True
    print("  ok  wrapped class list collected across the line break")

    # -- wrapped field value (components run onto the next line) ----------
    pages = [page(
        "Find the Path\nLevel 6 Divination (Bard, Cleric, Druid)\n",
        "Casting Time: 1 minute\nRange: Self\n"
        "Components: V, S, M (a set of divination tools worth\n"
        "100+ GP)\nDuration: Concentration, up to 1 day\n",
        "You sense the most direct physical route to a location.\n",
    )]
    spells, anomalies, conflicts = parse_one(*pages)
    assert len(spells) == 1 and not anomalies
    s = spells[0]
    assert s["components"] == "V, S, M (a set of divination tools worth 100+ GP)", s["components"]
    print("  ok  a wrapped field value is not truncated mid-parenthesis")

    # -- the singular "Component:" label (found on 12 real spells) --------
    pages = [page(
        "Barkskin\nLevel 2 Transmutation (Druid, Ranger)\n",
        "Casting Time: Bonus Action\nRange: Touch\n"
        "Component: V, S, M (a handful of bark)\nDuration: 1 hour\n",
        "The target's skin turns bark-like.\n",
    )]
    spells, anomalies, conflicts = parse_one(*pages)
    assert len(spells) == 1 and not anomalies, (
        "the singular 'Component:' label must not be read as a missing field: %s" % anomalies
    )
    assert spells[0]["components"] == "V, S, M (a handful of bark)"
    print("  ok  singular 'Component:' label is accepted like the plural")

    # -- a genuinely missing field is excluded, never borrowed -------------
    pages = [page(
        "Broken Spell\nLevel 1 Evocation (Wizard)\n",
        "Casting Time: Action\nRange: Touch\nDuration: Instantaneous\n",
        # no Components line at all
        "Some effect happens.\n",
        "Next Spell\nLevel 1 Evocation (Wizard)\n",
        "Casting Time: Action\nRange: Touch\nComponents: V\nDuration: Instantaneous\n",
        "A different effect.\n",
    )]
    spells, anomalies, conflicts = parse_one(*pages)
    names = [s["name"] for s in spells]
    assert "Next Spell" in names, names
    assert "Broken Spell" not in names, names
    assert any("Broken Spell" in a["detail"] and "components" in a["detail"] for a in anomalies), anomalies
    # THE TRAP: "Broken Spell" must not silently pick up "Next Spell"'s
    # Components line -- that would produce a complete-looking, wrong record.
    assert not any(s["name"] == "Broken Spell" for s in spells)
    print("  ok  a missing field is an exclusion, not borrowed from the next entry")

    # -- page-crossing entry: stat block starts on one page, ends on the --
    # -- next, exactly like Time Stop / Arret du temps in the French PDF --
    pages = [
        page("Long Spell\nLevel 5 Necromancy (Wizard)\n",
             "Casting Time: Action\nRange: Touch\n"),
        page("Components: V, S\nDuration: Instantaneous\n",
             "A grim effect occurs.\n"),
    ]
    spells, anomalies, conflicts = parse_one(*pages)
    assert len(spells) == 1 and not anomalies, (spells, anomalies)
    s = spells[0]
    assert s["duration"] == "Instantaneous" and s["components"] == "V, S"
    assert s["page"] == 1, "source_locator must point at the page the spell STARTS on"
    print("  ok  an entry whose stat block crosses a page boundary is not lost")

    # -- THE BUG FOUND BY MANUAL VERIFICATION: Duration is the very last ---
    # line on a page, and the description starts on the next page with NO
    # blank line between them (normalise() strips each page independently,
    # so the blank line that would normally close the stat block is not
    # there). Reproduces Charm Monster / Clone exactly: both had their
    # "duration" silently swallow the whole next page's description text.
    pages = [
        page("Charm Monster\nLevel 4 Enchantment (Bard, Wizard)\n",
             "Casting Time: Action\nRange: 30 feet\nComponents: V, S\nDuration: 1 hour"),
        page("One creature you can see within range makes a save.\n"),
    ]
    spells, anomalies, conflicts = parse_one(*pages)
    assert len(spells) == 1 and not anomalies, (spells, anomalies)
    s = spells[0]
    assert s["duration"] == "1 hour", (
        "duration swallowed the next page's description: %r" % s["duration"]
    )
    assert s["description"] == "One creature you can see within range makes a save."
    print("  ok  Duration ending a page does not swallow the next page's description")

    # -- embedded stat block inside a description is prose, not a new head -
    pages = [page(
        "Find Steed\nLevel 2 Conjuration (Paladin)\n",
        "Casting Time: Action\nRange: 30 feet\nComponents: V, S\n"
        "Duration: Instantaneous\n",
        "You summon a steed.\n\t Otherworldly Steed\n"
        "Large Celestial, Fey, or Fiend, Neutral\n"
        "AC 10 + 1 per spell level\n",
        "Find the Path\nLevel 6 Divination (Bard, Cleric, Druid)\n",
        "Casting Time: 1 minute\nRange: Self\nComponents: V, S\n"
        "Duration: Concentration, up to 1 day\n",
        "You sense the route.\n",
    )]
    spells, anomalies, conflicts = parse_one(*pages)
    names = [s["name"] for s in spells]
    assert names == ["Find Steed", "Find the Path"], names
    assert "Otherworldly Steed" in spells[0]["description"]
    assert "AC 10 + 1 per spell level" in spells[0]["description"]
    print("  ok  a companion stat block inside a description is not a new spell head")

    # -- description keeps the Higher-Level paragraph, does not overrun ----
    # -- the chapter boundary for the LAST spell in the stream -------------
    pages = [page(
        "Fireball\nLevel 3 Evocation (Sorcerer, Wizard)\n",
        "Casting Time: Action\nRange: 150 feet\n"
        "Components: V, S, M (a ball of bat guano and sulfur)\n"
        "Duration: Instantaneous\n",
        "A bright streak flashes from you.\n"
        "\t Flammable objects start burning.\n"
        "\t Using a Higher-Level Spell Slot. The damage increases by 1d6.\n",
        "Rules Glossary\n\nGlossary Conventions\nThe glossary uses tags.\n",
    )]
    spells, anomalies, conflicts = parse_one(*pages)
    assert len(spells) == 1 and not anomalies
    desc = spells[0]["description"]
    assert desc.count("\n\n") == 2, "expected 3 paragraphs: %r" % desc
    assert desc.endswith("The damage increases by 1d6."), repr(desc)
    assert "Glossary Conventions" not in desc, (
        "the last spell's description ran past the chapter boundary: %r" % desc
    )
    print("  ok  Higher-Level paragraph kept; last spell does not swallow the next chapter")

    # -- NEGATIVE CONTROL: a complete, ordinary spell must NOT be flagged --
    # by any of the checks above. Paired with "Broken Spell" earlier, this is
    # what proves those checks discriminate rather than always firing (or
    # never firing): one deliberately broken input got excluded, this
    # deliberately unremarkable one does not.
    pages = [page(
        "Complete Spell\nLevel 1 Evocation (Wizard)\n",
        "Casting Time: Action\nRange: Touch\nComponents: V\nDuration: Instantaneous\n",
        "An effect.\n",
    )]
    spells, anomalies, conflicts = parse_one(*pages)
    assert len(spells) == 1 and not anomalies and not conflicts, (
        "an ordinary, complete spell must parse cleanly: %s / %s" % (spells, anomalies)
    )
    print("  ok  negative control: an ordinary complete spell is not wrongly excluded")

    # -- and the implausible-name check can fire on its own, distinctly ---
    # from the missing-field check: a stray fragment left above a head line
    # (e.g. a running list item, not a spell name) is excluded for THAT
    # reason, with a real stat block sitting right there unused.
    pages = [page(
        "some trailing fragment:\nLevel 1 Evocation (Wizard)\n",
        "Casting Time: Action\nRange: Touch\nComponents: V\nDuration: Instantaneous\n",
        "An effect.\n",
    )]
    spells, anomalies, conflicts = parse_one(*pages)
    assert not spells, spells
    assert any("implausible spell name" in a["detail"] for a in anomalies), anomalies
    print("  ok  a name line ending in ':' is rejected as implausible, not accepted")

    print("PASS test_parse_spells_en")


if __name__ == "__main__":
    main()
