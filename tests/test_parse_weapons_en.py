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
        page("Name\nDamage\nProperties\nMastery\nWeight\nCost\n\n" + table_body),
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

    print("PASS test_parse_weapons_en")


if __name__ == "__main__":
    main()
