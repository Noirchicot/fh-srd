"""Calibration checks for the English Armor table parser."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_armor_en as armor  # noqa: E402


def page(*blocks):
    return extract.normalise("\n".join(blocks))


LIGHT = "Light Armor (1 Minute to Don or Doff)"
HEAVY = "Heavy Armor (10 Minutes to Don and 5 Minutes to Doff)"


def wrap(table_body, suspect=(), label=LIGHT):
    # ⚠️ The label is part of the fixture because it is part of the TABLE: the
    # first line after the header is always a sub-category label, in every
    # printing. A fixture that started with a bare row was testing a table that
    # does not exist, and it stopped passing the moment the parser began to
    # require what the source actually prints.
    head = "Armor\nArmor Class (AC)\nStrength\nStealth\nWeight\nCost\n\n"
    if label:
        head += label + "\n\n"
    pages = [
        page(head + table_body),
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
    assert found[0]["armor_category"] == "light", found[0]
    assert found[0]["don_doff"] == "1 Minute to Don or Doff", found[0]
    print("  ok  an ordinary row with both Strength and Stealth entries parses cleanly, "
          "carrying the category its label states")

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

    # -- the category comes from the LABEL, never from the row --------------
    # Chain Mail is heavy armor. Printed under a Light Armor label it must come
    # out `light`, because the label is what the source states and the row says
    # nothing about its own category. A parser that "corrected" this would be
    # guessing from the AC column -- exactly what this one refuses to do.
    found, anomalies, conflicts = wrap(
        "Chain Mail\n16\nStr 13\nDisadvantage\n55 lb.\n75 GP\n", label=LIGHT
    )
    assert found[0]["armor_category"] == "light", found[0]
    found, anomalies, conflicts = wrap(
        "Chain Mail\n16\nStr 13\nDisadvantage\n55 lb.\n75 GP\n", label=HEAVY
    )
    assert found[0]["armor_category"] == "heavy", found[0]
    print("  ok  the category is read from the label, never re-derived from the row")

    # -- a second label mid-table re-aims every row below it ----------------
    found, anomalies, conflicts = wrap(
        "Padded Armor\n11 + Dex modifier\n—\nDisadvantage\n8 lb.\n5 GP\n\n"
        + HEAVY + "\n\n"
        "Ring Mail\n14\n—\nDisadvantage\n40 lb.\n30 GP\n"
    )
    assert not anomalies, anomalies
    assert [(a["name"], a["armor_category"]) for a in found] == [
        ("Padded Armor", "light"), ("Ring Mail", "heavy")], found
    print("  ok  a second label mid-table re-aims the rows below it, not the ones above")

    # -- two facts from one label, and only one of them is a key ------------
    # The category is what a screen filters on; the don/doff text is what a
    # sheet prints. The shield's is not a duration at all, which is exactly why
    # it is kept as printed and not turned into a number here.
    found, _, _ = wrap("Shield\n+2\n—\n—\n6 lb.\n10 GP\n",
                       label="Shield (Utilize Action to Don or Doff)")
    assert found[0]["armor_category"] == "shield"
    assert found[0]["don_doff"] == "Utilize Action to Don or Doff", found[0]
    print("  ok  the label yields two fields: a key to filter on, a sentence to print")

    # -- a label with no parenthesis states a category and nothing else -----
    found, _, _ = wrap("Chain Mail\n16\nStr 13\nDisadvantage\n55 lb.\n75 GP\n",
                       label="Heavy Armor")
    assert found[0]["armor_category"] == "heavy"
    assert found[0]["don_doff"] is None, found[0]
    print("  ok  no parenthesis means no don/doff -- None, not an empty string")

    # -- NEGATIVE CONTROL: a row before any label is refused, not guessed ---
    found, anomalies, conflicts = wrap(
        "Chain Mail\n16\nStr 13\nDisadvantage\n55 lb.\n75 GP\n", label=None
    )
    assert found == [] and anomalies, (found, anomalies)
    assert "before any sub-category label" in anomalies[0]["detail"]
    print("  ok  negative control: a row with no label above it is refused by name")

    # -- NEGATIVE CONTROL: an unknown label stops the parser ----------------
    found, anomalies, conflicts = wrap(
        "Chain Mail\n16\nStr 13\nDisadvantage\n55 lb.\n75 GP\n",
        label="Exotic Armor (Some New Category)"
    )
    assert found == [] and anomalies, (found, anomalies)
    assert "not one of the four" in anomalies[0]["detail"], anomalies
    print("  ok  negative control: a fifth category is an anomaly, not a guess")

    print("PASS test_parse_armor_en")


if __name__ == "__main__":
    main()
