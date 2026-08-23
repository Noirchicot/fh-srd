"""Calibration checks for the French armor table parser."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_armor_fr  # noqa: E402

HEADER = "Armures\nClasse d’armure (CA)\nForce\nDiscrétion\nPoids\nCoût\n"

# ⚠️ The label belongs in every fixture because it belongs to the TABLE: the
# first line after the header is a sub-category label in every printing. The
# printed French carries narrow no-break spaces inside its parenthesis; they are
# reproduced here exactly, which is also what proves the parser does not depend
# on them.
LEGERES = "\nArmures légères (s’enfile ou se retire en 1\u00a0minute)\n"
LOURDES = "\nArmures lourdes (s’enfile en 10\u00a0minutes, se retire en 5\u00a0minutes)\n"
BOUCLIER = "\nBouclier (s’enfile ou se retire au prix de l’action Utilisation)\n"


def page(*blocks):
    return extract.normalise("\n".join(blocks))


def parse_one(*pages, suspect=()):
    return parse_armor_fr.parse(list(pages), suspect)


def main():
    # -- ordinary rows: no strength requirement, a strength requirement, --
    # -- and the Bouclier/Shield's own "+2" AC shape -----------------------
    pages = [page(
        HEADER, LEGERES,
        "Armure de cuir\n11 + modificateur de Dex\n—\n—\n5 kg\n10 po\n"
        "Cotte de mailles\n16\nFor 13\nDésavantage\n27,5 kg\n75 po\n"
        "Bouclier\n+2\n—\n—\n3 kg\n10 po\n",
    )]
    armors, anomalies, conflicts = parse_one(*pages)
    assert len(armors) == 3 and not anomalies, (armors, anomalies)
    by_name = {a["name"]: a for a in armors}
    cuir, mailles, bouclier = by_name["Armure de cuir"], by_name["Cotte de mailles"], by_name["Bouclier"]
    assert cuir["strength"] is None and cuir["stealth_disadvantage"] is False
    assert mailles["strength"] == "For 13" and mailles["stealth_disadvantage"] is True
    assert bouclier["armor_class"] == "+2"
    assert {a["armor_category"] for a in armors} == {"light"}, armors
    print("  ok  ordinary rows: no-requirement dash, 'For N' strength, Bouclier's '+2' AC")

    # -- the header word is 'Coût', distinct from the weapons table's -----
    # -- 'Prix' for the same currency figures -------------------------------
    pages = [page(
        "Prix\n",  # a stray 'Prix' line must not be mistaken for this header
        HEADER, LOURDES,
        "Harnois\n18\nFor 15\nDésavantage\n32,5 kg\n1 500 po\n",
    )]
    armors, anomalies, conflicts = parse_one(*pages)
    assert len(armors) == 1 and not anomalies, (armors, anomalies)
    assert armors[0]["cost"] == "1 500 po", armors[0]["cost"]
    print("  ok  'Coût' header found; space-thousands cost value read whole")

    # -- a malformed cost value stops the table, not guessed ----------------
    pages = [page(
        HEADER, LEGERES,
        "Armure matelassée\n11 + modificateur de Dex\n—\nDésavantage\n4 kg\n"
        "cinq pièces d’or\n",
    )]
    armors, anomalies, conflicts = parse_one(*pages)
    assert not armors, armors
    assert any("cost" in a["detail"] for a in anomalies), anomalies
    print("  ok  a malformed cost value stops the table with a reported anomaly")

    # -- NEGATIVE CONTROL ------------------------------------------------------
    pages = [page(
        HEADER, LEGERES,
        "Armure de peaux\n12 + modificateur de Dex (max 2)\n—\n—\n6 kg\n10 po\n",
    )]
    armors, anomalies, conflicts = parse_one(*pages)
    assert len(armors) == 1 and not anomalies and not conflicts, (armors, anomalies)
    print("  ok  negative control: an ordinary complete row is not wrongly excluded")

    # -- ⛔ the key is ENGLISH on the French side too ------------------------
    # One set of keys, in English; French lives in the labels a screen prints.
    # A French value here would rebuild the split the versatility route closed.
    pages = [page(HEADER, LOURDES,
                  "Harnois\n18\nFor 15\nDésavantage\n32,5 kg\n1 500 po\n")]
    armors, anomalies, conflicts = parse_one(*pages)
    assert armors[0]["armor_category"] == "heavy", armors[0]
    assert not anomalies, anomalies
    print("  ok  the key is 'heavy', not 'lourde': one set of keys, in English")

    # -- the Bouclier label is its own category, not a row ------------------
    pages = [page(HEADER, BOUCLIER, "Bouclier\n+2\n—\n—\n3 kg\n10 po\n")]
    armors, anomalies, conflicts = parse_one(*pages)
    assert len(armors) == 1 and not anomalies, (armors, anomalies)
    assert armors[0]["armor_category"] == "shield"
    print("  ok  'Bouclier (…)' is read as a label and 'Bouclier' as its row")

    # -- NEGATIVE CONTROL: a row before any label is refused ----------------
    pages = [page(HEADER, "Harnois\n18\nFor 15\nDésavantage\n32,5 kg\n1 500 po\n")]
    armors, anomalies, conflicts = parse_one(*pages)
    assert not armors and anomalies, (armors, anomalies)
    assert "before any sub-category label" in anomalies[0]["detail"]
    print("  ok  negative control: a row with no label above it is refused by name")

    # -- NEGATIVE CONTROL: an unknown label stops the parser ----------------
    pages = [page(HEADER, "\nArmures exotiques (une cinquième catégorie)\n",
                  "Harnois\n18\nFor 15\nDésavantage\n32,5 kg\n1 500 po\n")]
    armors, anomalies, conflicts = parse_one(*pages)
    assert not armors and anomalies, (armors, anomalies)
    assert "not one of the four" in anomalies[0]["detail"], anomalies
    print("  ok  negative control: a fifth category is an anomaly, not a guess")

    print("PASS test_parse_armor_fr")


if __name__ == "__main__":
    main()
