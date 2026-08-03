"""Calibration checks for the French adventuring gear table parser."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_gear_fr  # noqa: E402

INTRO = "Matériel d’aventurier\n\nObjet\nPoids\nPrix\n\n"


def page(*blocks):
    return extract.normalise("\n".join(blocks))


def parse_one(*pages, suspect=()):
    return parse_gear_fr.parse(list(pages), suspect)


def main():
    # -- ordinary row ---------------------------------------------------------
    pages = [page(INTRO, "Acide\n0,5 kg\n25 po\n")]
    gear, anomalies, conflicts = parse_one(*pages)
    assert len(gear) == 1 and not anomalies, (gear, anomalies)
    assert gear[0] == {"name": "Acide", "weight": "0,5 kg", "cost": "25 po", "page": 1}
    print("  ok  ordinary three-line row")

    # -- weight carries a parenthetical annotation (Outre / waterskin) ------
    pages = [page(INTRO, "Outre\n2,5 kg\n(pleine)\n2 pa\n")]
    gear, anomalies, conflicts = parse_one(*pages)
    assert len(gear) == 1 and not anomalies, (gear, anomalies)
    assert gear[0]["weight"] == "2,5 kg (pleine)", gear[0]["weight"]
    assert gear[0]["cost"] == "2 pa"
    print("  ok  weight with a parenthetical annotation line ('(pleine)')")

    # -- name wraps onto a second physical line ------------------------------
    pages = [page(INTRO, "Paquetage d’exploration\nsouterraine\n27,5 kg\n12 po\n")]
    gear, anomalies, conflicts = parse_one(*pages)
    assert len(gear) == 1 and not anomalies, (gear, anomalies)
    assert gear[0]["name"] == "Paquetage d’exploration souterraine", gear[0]["name"]
    print("  ok  name wrapping across a second physical line")

    # -- 'Variable' weight and cost (Focaliseur arcanique) -------------------
    pages = [page(INTRO, "Focaliseur arcanique\nVariable\nVariable\n")]
    gear, anomalies, conflicts = parse_one(*pages)
    assert len(gear) == 1 and not anomalies, (gear, anomalies)
    assert gear[0]["weight"] == "Variable" and gear[0]["cost"] == "Variable"
    print("  ok  'Variable' weight and cost")

    # -- the mid-table header repeat is skipped, not treated as the end -----
    pages = [page(
        INTRO, "Acide\n0,5 kg\n25 po\n", "Objet\nPoids\nPrix\n", "Miroir\n250 g\n5 po\n",
    )]
    gear, anomalies, conflicts = parse_one(*pages)
    names = [g["name"] for g in gear]
    assert names == ["Acide", "Miroir"], names
    print("  ok  mid-table header repeat is skipped, not mistaken for the table's end")

    # -- NEGATIVE CONTROL ------------------------------------------------------
    pages = [page(INTRO, "Billes\n1 kg\n1 po\n")]
    gear, anomalies, conflicts = parse_one(*pages)
    assert len(gear) == 1 and not anomalies and not conflicts, (gear, anomalies)
    print("  ok  negative control: an ordinary complete row is not wrongly excluded")

    print("PASS test_parse_gear_fr")


if __name__ == "__main__":
    main()
