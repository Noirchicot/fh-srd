"""Calibration checks for the English Armor table parser."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_armor_en as armor  # noqa: E402


def page(*blocks):
    return extract.normalise("\n".join(blocks))


def wrap(table_body, suspect=()):
    pages = [
        page("Armor\nArmor Class (AC)\nStrength\nStealth\nWeight\nCost\n\n" + table_body),
        page("Armor\n\nLight Armor (1 Minute to Don or Doff)\n\nShield (Utilize Action to Don or Doff)\n"),
    ]
    return armor.parse(pages, suspect)


def main():
    # -- an ordinary row, both Strength and Stealth present -----------------
    found, anomalies, conflicts = wrap(
        "Chain Mail\n16\nStr 13\nDisadvantage\n55 lb.\n75 GP\n"
    )
    assert len(found) == 1 and not anomalies and not conflicts, (found, anomalies)
    assert found[0]["strength"] == "Str 13" and found[0]["stealth_disadvantage"] is True
    print("  ok  an ordinary row with both Strength and Stealth entries parses cleanly")

    # -- a dash in Strength/Stealth means the drawback does not apply -------
    found, anomalies, conflicts = wrap(
        "Leather Armor\n11 + Dex modifier\n—\n—\n10 lb.\n10 GP\n"
    )
    assert len(found) == 1 and not anomalies
    assert found[0]["strength"] is None and found[0]["stealth_disadvantage"] is False
    print("  ok  a dash in Strength or Stealth becomes None / False, not the literal dash")

    # -- the Shield row, whose AC is a bonus ("+2") not a base calculation --
    found, anomalies, conflicts = wrap(
        "Shield\n+2\n—\n—\n6 lb.\n10 GP\n"
    )
    assert len(found) == 1 and not anomalies
    assert found[0]["armor_class"] == "+2"
    print("  ok  the Shield's '+2' AC bonus is captured rather than rejected as malformed")

    # -- the displaced category-header trailer must not spawn a bogus row ---
    found, anomalies, conflicts = wrap(
        "Padded Armor\n11 + Dex modifier\n—\nDisadvantage\n8 lb.\n5 GP\n"
    )
    assert len(found) == 1, (
        "the page-end 'Armor / Light Armor (...) / Shield (...)' trailer must "
        "not be read as further rows: %s" % found
    )
    print("  ok  the displaced category-header trailer does not spawn bogus rows")

    # -- NEGATIVE CONTROL: two ordinary rows in sequence --------------------
    found, anomalies, conflicts = wrap(
        "Hide Armor\n12 + Dex modifier (max 2)\n—\n—\n12 lb.\n10 GP\n\n"
        "Breastplate\n14 + Dex modifier (max 2)\n—\n—\n20 lb.\n400 GP\n"
    )
    assert len(found) == 2 and not anomalies and not conflicts, (found, anomalies)
    print("  ok  negative control: two ordinary consecutive rows both parse cleanly")

    print("PASS test_parse_armor_en")


if __name__ == "__main__":
    main()
