"""Calibration checks for the French weapons table parser."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_weapons_fr  # noqa: E402

HEADER = "Nom\nDégâts\nPropriétés\nBotte d’arme\nPoids\nPrix\n"


def page(*blocks):
    return extract.normalise("\n".join(blocks))


def parse_one(*pages, suspect=()):
    return parse_weapons_fr.parse(list(pages), suspect)


def main():
    # -- ordinary row, properties present -----------------------------------
    pages = [page(
        HEADER,
        "Dague\n1d4 perforants\nFinesse, Lancer (portée 6/18), Légère\n"
        "Coup double\n0,5 kg\n2 po\n",
    )]
    weapons, anomalies, conflicts = parse_one(*pages)
    assert len(weapons) == 1 and not anomalies, (weapons, anomalies)
    w = weapons[0]
    assert w["mastery"] == "Coup double", w["mastery"]
    assert w["properties"] == "Finesse, Lancer (portée 6/18), Légère"
    print("  ok  ordinary row, two-word mastery name ('Coup double')")

    # -- properties is a bare em-dash (no properties) -------------------------
    pages = [page(
        HEADER,
        "Masse d’armes\n1d6 contondants\n—\nSape\n2 kg\n5 po\n",
    )]
    weapons, anomalies, conflicts = parse_one(*pages)
    assert len(weapons) == 1 and not anomalies, (weapons, anomalies)
    assert weapons[0]["properties"] is None
    print("  ok  bare em-dash properties becomes None")

    # -- name and damage share ONE physical line (Hache à deux mains) --------
    pages = [page(
        HEADER,
        "Hache à deux mains 1d12 tranchants\nDeux mains, Lourde\n"
        "Enchaînement\n3,5 kg\n30 po\n",
    )]
    weapons, anomalies, conflicts = parse_one(*pages)
    assert len(weapons) == 1 and not anomalies, (weapons, anomalies)
    w = weapons[0]
    assert w["name"] == "Hache à deux mains", w["name"]
    assert w["damage"] == "1d12 tranchants", w["damage"]
    print("  ok  name and damage merged onto one physical line (Hache à deux mains)")

    # -- flat, non-dice damage (Sarbacane / Blowgun) --------------------------
    pages = [page(
        HEADER,
        "Sarbacane\n1 perforant\nChargement, Munitions (portée 7,50/30 ; "
        "dards)\nOuverture\n0,5 kg\n10 po\n",
    )]
    weapons, anomalies, conflicts = parse_one(*pages)
    assert len(weapons) == 1 and not anomalies, (weapons, anomalies)
    assert weapons[0]["damage"] == "1 perforant"
    print("  ok  flat non-dice damage (Sarbacane's '1 perforant')")

    # -- properties wrap across a line break ----------------------------------
    pages = [page(
        HEADER,
        "Arbalète lourde\n1d10 perforants\nChargement, Deux mains, Lourde, "
        "Munitions\n(portée 30/120 ; carreaux)\nPoussée\n9 kg\n50 po\n",
    )]
    weapons, anomalies, conflicts = parse_one(*pages)
    assert len(weapons) == 1 and not anomalies, (weapons, anomalies)
    assert "portée 30/120" in weapons[0]["properties"], weapons[0]["properties"]
    print("  ok  wrapped properties clause collected across the line break")

    # -- NEGATIVE CONTROL ------------------------------------------------------
    pages = [page(
        HEADER,
        "Gourdin\n1d4 contondants\nLégère\nRalentissement\n1 kg\n1 pa\n",
    )]
    weapons, anomalies, conflicts = parse_one(*pages)
    assert len(weapons) == 1 and not anomalies and not conflicts, (weapons, anomalies)
    print("  ok  negative control: an ordinary complete row is not wrongly excluded")

    print("PASS test_parse_weapons_fr")


if __name__ == "__main__":
    main()
