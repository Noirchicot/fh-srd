"""Calibration checks for the English Weapons table parser."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_weapons_en as weapons  # noqa: E402


def page(*blocks):
    return extract.normalise("\n".join(blocks))


def wrap(table_body, suspect=()):
    pages = [
        page("Name\nDamage\nProperties\nMastery\nWeight\nCost\n\n"
             "Simple Melee Weapons\n\n" + table_body),
        page("Weapons\n\nSimple Melee Weapons\n\nMartial Ranged Weapons\n"),
    ]
    return weapons.parse(pages, suspect)


def main():
    # -- an ordinary row, single-line properties ----------------------------
    found, anomalies, conflicts = wrap(
        "Club\n1d4 Bludgeoning\nLight\nSlow\n2 lb.\n1 SP\n"
    )
    assert len(found) == 1 and not anomalies and not conflicts, (found, anomalies)
    w = found[0]
    assert w["properties"] == "Light" and w["mastery"] == "Slow" and w["cost"] == "1 SP"
    assert w["weapon_category"] == "simple" and w["weapon_range"] == "melee", w
    print("  ok  an ordinary single-line-properties row parses cleanly")

    # -- THE TRAP: Properties wraps to a second physical line with no ------
    # delimiter of its own; only the fact that Mastery is a closed, known
    # set of eight words tells the parser where Properties actually ends
    # (reproduces Light Crossbow exactly).
    found, anomalies, conflicts = wrap(
        "Light Crossbow\n1d8 Piercing\nAmmunition (Range 80/320; Bolt), Loading,\n"
        "Two-Handed\nSlow\n5 lb.\n25 GP\n"
    )
    assert len(found) == 1 and not anomalies, (found, anomalies)
    assert found[0]["properties"] == "Ammunition (Range 80/320; Bolt), Loading, Two-Handed"
    assert found[0]["mastery"] == "Slow"
    print("  ok  wrapped properties are joined up to the Mastery word, not before")

    # -- a weapon with no properties at all ("—") must not be mistaken for -
    # the Mastery word sitting in the Properties slot
    found, anomalies, conflicts = wrap(
        "Mace\n1d6 Bludgeoning\n—\nSap\n4 lb.\n5 GP\n"
    )
    assert len(found) == 1 and not anomalies, (found, anomalies)
    assert found[0]["properties"] is None and found[0]["mastery"] == "Sap"
    print("  ok  a bare dash in the Properties column is not confused with Mastery")

    # -- the displaced category-header trailer must not become a bogus row -
    found, anomalies, conflicts = wrap(
        "Whip\n1d4 Slashing\nFinesse, Reach\nSlow\n3 lb.\n2 GP\n"
    )
    assert len(found) == 1, (
        "the page-end 'Weapons / Simple Melee Weapons / ...' trailer must not "
        "be read as further rows: %s" % found
    )
    print("  ok  the displaced category-header trailer does not spawn bogus rows")

    # -- NEGATIVE CONTROL: two ordinary rows in sequence --------------------
    found, anomalies, conflicts = wrap(
        "Dagger\n1d4 Piercing\nFinesse, Light, Thrown (Range 20/60)\nNick\n1 lb.\n2 GP\n\n"
        "Handaxe\n1d6 Slashing\nLight, Thrown (Range 20/60)\nVex\n2 lb.\n5 GP\n"
    )
    assert len(found) == 2 and not anomalies and not conflicts, (found, anomalies)
    print("  ok  negative control: two ordinary consecutive rows both parse cleanly")

    # -- CATEGORY: read from each label and carried onto the rows that ------
    # follow it, switching when the next label does -- not a static default.
    # Dart is the deliberate trap named in the module docstring: it carries
    # "Thrown", the same property Javelin (a MELEE weapon) also carries, so
    # a correct result here proves the category came from the label and not
    # from a guess based on Properties.
    pages = [page(
        "Name\nDamage\nProperties\nMastery\nWeight\nCost\n\n"
        "Simple Melee Weapons\n\n"
        "Club\n1d4 Bludgeoning\nLight\nSlow\n2 lb.\n1 SP\n\n"
        "Simple Ranged Weapons\n\n"
        "Dart\n1d4 Piercing\nFinesse, Thrown (Range 20/60)\nVex\n1/4 lb.\n5 CP\n\n"
        "Martial Melee Weapons\n\n"
        "Greatsword\n2d6 Slashing\nHeavy, Two-Handed\nGraze\n6 lb.\n50 GP\n\n"
        "Martial Ranged Weapons\n\n"
        "Longbow\n1d8 Piercing\nAmmunition (Range 150/600; Arrow), Heavy,\n"
        "Two-Handed\nSlow\n2 lb.\n50 GP\n"
    )]
    found, anomalies, conflicts = weapons.parse(pages)
    assert len(found) == 4 and not anomalies and not conflicts, (found, anomalies)
    by_name = {w["name"]: w for w in found}
    assert (by_name["Club"]["weapon_category"], by_name["Club"]["weapon_range"]) == (
        "simple", "melee"), by_name["Club"]
    assert (by_name["Dart"]["weapon_category"], by_name["Dart"]["weapon_range"]) == (
        "simple", "ranged"), by_name["Dart"]
    assert (by_name["Greatsword"]["weapon_category"], by_name["Greatsword"]["weapon_range"]) == (
        "martial", "melee"), by_name["Greatsword"]
    assert (by_name["Longbow"]["weapon_category"], by_name["Longbow"]["weapon_range"]) == (
        "martial", "ranged"), by_name["Longbow"]
    print("  ok  weapon_category/weapon_range are read from each label and "
          "change when the label does (Dart stays Ranged despite Thrown)")

    # -- NEGATIVE CONTROL: an unrecognised label stops the parser rather ----
    # than silently leaving the rows after it uncategorised, or attributing
    # them to whichever category came before.
    pages = [page(
        "Name\nDamage\nProperties\nMastery\nWeight\nCost\n\n"
        "Simple Melee Weapons\n\n"
        "Club\n1d4 Bludgeoning\nLight\nSlow\n2 lb.\n1 SP\n\n"
        "Simple Melee Weaponss\n\n"
        "Dagger\n1d4 Piercing\nFinesse, Light, Thrown (Range 20/60)\nNick\n1 lb.\n2 GP\n"
    )]
    found, anomalies, conflicts = weapons.parse(pages)
    assert len(found) == 1 and found[0]["name"] == "Club", found
    assert anomalies and "not one of the four" in anomalies[0]["detail"], anomalies
    print("  ok  an unrecognised sub-category label stops the parser with an anomaly")

    # -- NEGATIVE CONTROL: a row before any label is refused, not guessed ---
    pages = [page(
        "Name\nDamage\nProperties\nMastery\nWeight\nCost\n\n"
        "Club\n1d4 Bludgeoning\nLight\nSlow\n2 lb.\n1 SP\n"
    )]
    found, anomalies, conflicts = weapons.parse(pages)
    assert not found, found
    assert anomalies and "before any sub-category label" in anomalies[0]["detail"], anomalies
    print("  ok  a weapon row before any sub-category label is an anomaly, not a guess")

    print("PASS test_parse_weapons_en")


if __name__ == "__main__":
    main()
