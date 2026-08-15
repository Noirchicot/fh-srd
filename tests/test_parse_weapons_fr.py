"""Calibration checks for the French weapons table parser."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_weapons_fr  # noqa: E402

HEADER = ("Nom\nDégâts\nPropriétés\nBotte d’arme\nPoids\nPrix\n\n"
          "Armes courantes de corps à corps\n")


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
    assert w["weapon_category"] == "simple" and w["weapon_range"] == "melee", w
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

    # -- CATEGORY: read from each label and carried onto the rows that ------
    # follow it, switching when the next label does. Javeline/Fléchette is
    # the deliberate trap: both carry "Lancer" (Thrown), and they are Simple
    # MELEE and Simple RANGED respectively -- proving the category came from
    # the label, not guessed from Propriétés (the same trap EN names for
    # Javelin/Dart).
    pages = [page(
        "Nom\nDégâts\nPropriétés\nBotte d’arme\nPoids\nPrix\n\n"
        "Armes courantes de corps à corps\n\n"
        "Javeline\n1d6 perforants\nLancer (portée 9/36)\nRalentissement\n1 kg\n5 pa\n\n"
        "Armes courantes à distance\n\n"
        "Fléchette\n1d4 perforants\nFinesse, Lancer (portée 6/18)\nOuverture\n125 g\n5 pc\n\n"
        "Armes de guerre de corps à corps\n\n"
        "Rapière\n1d8 perforants\nFinesse\nOuverture\n1 kg\n25 po\n\n"
        "Armes de guerre à distance\n\n"
        "Mousquet\n1d12 perforants\nChargement, Deux mains, Munitions (portée\n"
        "12/36 ; balles)\nRalentissement\n5 kg\n500 po\n"
    )]
    weapons, anomalies, conflicts = parse_one(*pages)
    assert len(weapons) == 4 and not anomalies and not conflicts, (weapons, anomalies)
    by_name = {w["name"]: w for w in weapons}
    assert (by_name["Javeline"]["weapon_category"], by_name["Javeline"]["weapon_range"]) == (
        "simple", "melee"), by_name["Javeline"]
    assert (by_name["Fléchette"]["weapon_category"], by_name["Fléchette"]["weapon_range"]) == (
        "simple", "ranged"), by_name["Fléchette"]
    assert (by_name["Rapière"]["weapon_category"], by_name["Rapière"]["weapon_range"]) == (
        "martial", "melee"), by_name["Rapière"]
    assert (by_name["Mousquet"]["weapon_category"], by_name["Mousquet"]["weapon_range"]) == (
        "martial", "ranged"), by_name["Mousquet"]
    print("  ok  weapon_category/weapon_range are read from each label and "
          "change when the label does (Fléchette stays Ranged despite Lancer)")

    # -- NEGATIVE CONTROL: an unrecognised label stops the parser rather ----
    # than silently leaving the rows after it uncategorised, or attributing
    # them to whichever category came before.
    pages = [page(
        "Nom\nDégâts\nPropriétés\nBotte d’arme\nPoids\nPrix\n\n"
        "Armes courantes de corps à corps\n\n"
        "Gourdin\n1d4 contondants\nLégère\nRalentissement\n1 kg\n1 pa\n\n"
        "Armes courantes de corps à corpss\n\n"
        "Dague\n1d4 perforants\nFinesse, Lancer (portée 6/18), Légère\n"
        "Coup double\n0,5 kg\n2 po\n"
    )]
    weapons, anomalies, conflicts = parse_one(*pages)
    assert len(weapons) == 1 and weapons[0]["name"] == "Gourdin", weapons
    assert anomalies and "not one of the four" in anomalies[0]["detail"], anomalies
    print("  ok  an unrecognised sub-category label stops the parser with an anomaly")

    # -- NEGATIVE CONTROL: a row before any label is refused, not guessed ---
    pages = [page(
        "Nom\nDégâts\nPropriétés\nBotte d’arme\nPoids\nPrix\n\n"
        "Gourdin\n1d4 contondants\nLégère\nRalentissement\n1 kg\n1 pa\n"
    )]
    weapons, anomalies, conflicts = parse_one(*pages)
    assert not weapons, weapons
    assert anomalies and "before any sub-category label" in anomalies[0]["detail"], anomalies
    print("  ok  a weapon row before any sub-category label is an anomaly, not a guess")

    print("PASS test_parse_weapons_fr")


if __name__ == "__main__":
    main()
