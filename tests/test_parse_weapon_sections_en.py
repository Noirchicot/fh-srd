"""Calibration checks for the English weapon-property / weapon-mastery parsers.

Both genres come out of ONE region (`weapon_sections.py`), so one fixture
exercises both and the traps are checked where they actually live:

  * the eleventh property, `Improvised Weapons`, sits INSIDE the mastery block
    in reading order — a sidebar, not an entry of the section it lands in;
  * `Loading` is the first line of a page, with no blank line before it;
  * `Properties` is not a unique line: the Weapons table's column header is
    the same word, on a later page;
  * a head belonging to neither closed set is named, not skipped;
  * a closed set that comes back short REFUSES.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_weapon_mastery_en as mastery  # noqa: E402
import parse_weapon_property_en as prop  # noqa: E402
import weapon_sections  # noqa: E402

# A decoy: the word alone on a line, BEFORE the real section heading. The
# region opens on the LAST such line before `Mastery Properties`, so this one
# must be ignored — as must the Weapons table's own column header, after it.
PAGE_BEFORE = (
    "Equipment\n"
    "\n"
    "Properties\n"
    "\n"
    "Weapon Proficiency\n"
    "\n"
    "Anyone can wield a weapon, but you must have proficiency with it to add\n"
    "your Proficiency Bonus to an attack roll you make with it.\n"
    "Properties\n"
    "\n"
    "Here are definitions of the properties in the Properties column of the\n"
    "Weapons table.\n"
    "\n"
    "Ammunition\n"
    "You can use a weapon that has the Ammunition property to make a ranged\n"
    "attack only if you have ammunition to fire from it.\n"
    "\n"
    "Finesse\n"
    "When making an attack with a Finesse weapon, use your choice of your\n"
    "Strength or Dexterity modifier.\n"
    "\n"
    "Heavy\n"
    "You have Disadvantage on attack rolls with a Heavy weapon if it’s a\n"
    "Melee weapon and your Strength score isn’t at least 13.\n"
    "\n"
    "Light\n"
    "When you take the Attack action on your turn and attack with a Light\n"
    "weapon, you can make one extra attack as a Bonus Action.\n"
)

# THE PAGE-BOUNDARY TRAP: `Loading` opens this page. In the joined stream the
# line before it is the last body line of `Light`, with no blank between them.
PAGE_MAIN = (
    "Loading\n"
    "You can fire only one piece of ammunition from a Loading weapon when you\n"
    "use an action, a Bonus Action, or a Reaction to fire it.\n"
    "\n"
    "Range\n"
    "A Range weapon has a range in parentheses after the Ammunition or Thrown\n"
    "property.\n"
    "\n"
    "Reach\n"
    "A Reach weapon adds 5 feet to your reach when you attack with it.\n"
    "\n"
    "Thrown\n"
    "If a weapon has the Thrown property, you can throw the weapon to make a\n"
    "ranged attack.\n"
    "\n"
    "Two-Handed\n"
    "A Two-Handed weapon requires two hands when you attack with it.\n"
    "\n"
    "Versatile\n"
    "A Versatile weapon can be used with one or two hands.\n"
    # No blank line: the section heading runs straight on from the last body
    # line, exactly as the pinned PDF prints it.
    "Mastery Properties\n"
    "\n"
    "Each weapon has a mastery property, which is usable only by a character\n"
    "who has a feature, such as Weapon Mastery, that unlocks the property.\n"
    "\n"
    # THE SIDEBAR TRAP: a weapon PROPERTY, landing inside the mastery block.
    "Improvised Weapons\n"
    "\n"
    "If you use an object—such as a table leg, frying pan, or bottle—as a\n"
    "makeshift weapon, see “Improvised Weapons” in “Rules Glossary.”\n"
    "\n"
    "Cleave\n"
    "If you hit a creature with a melee attack roll using this weapon, you can\n"
    "make a melee attack roll with the weapon against a second creature.\n"
    "\n"
    "Graze\n"
    "If your attack roll with this weapon misses a creature, you can deal\n"
    "damage to that creature equal to the ability modifier you used.\n"
    "\n"
    "Nick\n"
    "When you make the extra attack of the Light property, you can make it as\n"
    "part of the Attack action instead of as a Bonus Action.\n"
    "\n"
    "Push\n"
    "If you hit a creature with this weapon, you can push the creature up to\n"
    "10 feet straight away from yourself if it is Large or smaller.\n"
    "\n"
    "Sap\n"
    "If you hit a creature with this weapon, that creature has Disadvantage on\n"
    "its next attack roll before the start of your next turn.\n"
    "\n"
    "Slow\n"
    "If you hit a creature with this weapon and deal damage to it, you can\n"
    "reduce its Speed by 10 feet until the start of your next turn.\n"
    "\n"
    "Topple\n"
    "If you hit a creature with this weapon, you can force the creature to\n"
    "make a Constitution saving throw.\n"
    "\n"
    "Vex\n"
    "If you hit a creature with this weapon and deal damage to the creature,\n"
    "you have Advantage on your next attack roll against that creature.\n"
)

# The Weapons table. Its own column header is the word `Properties` again, and
# its `Mastery` column repeats every one of the eight mastery words.
PAGE_TABLE = (
    "Weapons\n"
    "\n"
    "Name\n"
    "Damage\n"
    "Properties\n"
    "Mastery\n"
    "Weight\n"
    "Cost\n"
    "\n"
    "Club\n"
    "1d4 Bludgeoning\n"
    "Light\n"
    "Slow\n"
    "2 lb.\n"
    "1 SP\n"
)


def pages(before=PAGE_BEFORE, main=PAGE_MAIN, table=PAGE_TABLE):
    return [extract.normalise(p) for p in (before, main, table)]


def names(records):
    return [r["name"] for r in records]


def main():
    # -- the eleven properties, sidebar included ----------------------------
    found, anomalies, conflicts = prop.parse(pages())
    assert not anomalies and not conflicts, (anomalies, conflicts)
    assert names(found) == [
        "Ammunition", "Finesse", "Heavy", "Improvised Weapons", "Light",
        "Loading", "Range", "Reach", "Thrown", "Two-Handed", "Versatile",
    ], names(found)
    print("  ok  11 properties, sorted by slug, sidebar included")

    by_name = {r["name"]: r for r in found}

    # `Loading` opens a page with no blank line before it.
    assert by_name["Loading"]["page"] == 2
    assert by_name["Loading"]["description"].startswith(
        "You can fire only one piece of ammunition")
    print("  ok  a property that is the FIRST LINE of a page is still a head")

    # The sidebar is a property, and it is read from inside the mastery block.
    assert by_name["Improvised Weapons"]["page"] == 2
    assert "makeshift weapon" in by_name["Improvised Weapons"]["description"]
    print("  ok  `Improvised Weapons` is claimed by the property genre, "
          "not by the block it physically sits in")

    # The mastery heading is not an entry of either genre.
    assert "Mastery Properties" not in by_name
    assert "Properties" not in by_name
    print("  ok  neither section heading became a record")

    # -- the eight masteries ------------------------------------------------
    found, anomalies, conflicts = mastery.parse(pages())
    assert not anomalies and not conflicts, (anomalies, conflicts)
    assert names(found) == ["Cleave", "Graze", "Nick", "Push", "Sap", "Slow",
                            "Topple", "Vex"], names(found)
    assert "Improvised Weapons" not in names(found)
    print("  ok  8 masteries, and the sidebar is NOT among them")

    # The body is the whole paragraph, dehyphenated and space-joined.
    topple = {r["name"]: r for r in found}["Topple"]
    assert topple["description"] == (
        "If you hit a creature with this weapon, you can force the creature "
        "to make a Constitution saving throw."), topple["description"]
    print("  ok  a wrapped definition comes back as one joined paragraph")

    # -- THE DOUBLE `Properties`: the table's header must not open the region
    # A region opened on the table's column header would start after the
    # mastery heading and find nothing at all.
    assert len(names(found)) == 8
    print("  ok  the Weapons table's own `Properties` header did not open "
          "the region")

    # -- an unknown head is NAMED, not swallowed ----------------------------
    intruder = PAGE_MAIN.replace(
        "Cleave\n",
        "Riposte\n"
        "A head that belongs to neither closed set.\n"
        "\n"
        "Cleave\n",
    )
    found, anomalies, conflicts = mastery.parse(pages(main=intruder))
    assert len(found) == 8, names(found)
    assert len(anomalies) == 1, anomalies
    assert "Riposte" in anomalies[0]["detail"], anomalies[0]
    print("  ok  a head in neither closed set is excluded and named: %r"
          % anomalies[0]["detail"][:60])

    # -- a MISSING head refuses -------------------------------------------
    lost = PAGE_MAIN.replace(
        "Topple\n"
        "If you hit a creature with this weapon, you can force the creature to\n"
        "make a Constitution saving throw.\n"
        "\n",
        "",
    )
    try:
        mastery.parse(pages(main=lost))
    except weapon_sections.SectionCountError as exc:
        assert "Topple" in str(exc), exc
        assert "7 of the 8" in str(exc), exc
        print("  ok  a section short of one entry REFUSES, naming it")
    else:
        raise AssertionError("a missing mastery must stop the build, not export 7")

    # -- the region absent altogether is an anomaly, not a crash ------------
    found, anomalies, conflicts = prop.parse([extract.normalise(PAGE_TABLE)])
    assert not found and len(anomalies) == 1, (found, anomalies)
    assert "was not found" in anomalies[0]["detail"], anomalies[0]
    print("  ok  a source without the region reports it instead of guessing")

    # -- a disputed page sends its records to the exclusion register --------
    found, anomalies, conflicts = mastery.parse(pages(), suspect_pages=[2])
    assert not found and len(conflicts) == 8, (found, conflicts)
    print("  ok  an extractor-disputed page yields conflicts, not records")

    print("PASS test_parse_weapon_sections_en")


if __name__ == "__main__":
    main()
