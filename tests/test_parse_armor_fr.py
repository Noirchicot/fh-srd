"""Calibration checks for the French armor table parser."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_armor_fr  # noqa: E402

HEADER = "Armures\nClasse d’armure (CA)\nForce\nDiscrétion\nPoids\nCoût\n"


def page(*blocks):
    return extract.normalise("\n".join(blocks))


def parse_one(*pages, suspect=()):
    return parse_armor_fr.parse(list(pages), suspect)


def main():
    # -- ordinary rows: no strength requirement, a strength requirement, --
    # -- and the Bouclier/Shield's own "+2" AC shape -----------------------
    pages = [page(
        HEADER,
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
    print("  ok  ordinary rows: no-requirement dash, 'For N' strength, Bouclier's '+2' AC")

    # -- the header word is 'Coût', distinct from the weapons table's -----
    # -- 'Prix' for the same currency figures -------------------------------
    pages = [page(
        "Prix\n",  # a stray 'Prix' line must not be mistaken for this header
        HEADER,
        "Harnois\n18\nFor 15\nDésavantage\n32,5 kg\n1 500 po\n",
    )]
    armors, anomalies, conflicts = parse_one(*pages)
    assert len(armors) == 1 and not anomalies, (armors, anomalies)
    assert armors[0]["cost"] == "1 500 po", armors[0]["cost"]
    print("  ok  'Coût' header found; space-thousands cost value read whole")

    # -- a malformed cost value stops the table, not guessed ----------------
    pages = [page(
        HEADER,
        "Armure matelassée\n11 + modificateur de Dex\n—\nDésavantage\n4 kg\n"
        "cinq pièces d’or\n",
    )]
    armors, anomalies, conflicts = parse_one(*pages)
    assert not armors, armors
    assert any("cost" in a["detail"] for a in anomalies), anomalies
    print("  ok  a malformed cost value stops the table with a reported anomaly")

    # -- NEGATIVE CONTROL ------------------------------------------------------
    pages = [page(
        HEADER,
        "Armure de peaux\n12 + modificateur de Dex (max 2)\n—\n—\n6 kg\n10 po\n",
    )]
    armors, anomalies, conflicts = parse_one(*pages)
    assert len(armors) == 1 and not anomalies and not conflicts, (armors, anomalies)
    print("  ok  negative control: an ordinary complete row is not wrongly excluded")

    print("PASS test_parse_armor_fr")


if __name__ == "__main__":
    main()
