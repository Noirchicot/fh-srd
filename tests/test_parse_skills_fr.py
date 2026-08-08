"""Calibration checks for the French Skills table parser.

The English suite already covers the shape. What is checked here is what
French does that English gives no reason to expect: a mid-word hyphenated
wrap inside an Example Uses cell, and ability keys that are French's own.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import canon  # noqa: E402
import extract  # noqa: E402
import parse_skills_fr as skills  # noqa: E402

FILLER = [
    ("Arcanes", "Intelligence"), ("Athlétisme", "Force"),
    ("Discrétion", "Dextérité"), ("Dressage", "Sagesse"),
    ("Escamotage", "Dextérité"), ("Histoire", "Intelligence"),
    ("Intimidation", "Charisme"), ("Intuition", "Sagesse"),
    ("Médecine", "Sagesse"), ("Nature", "Intelligence"),
    ("Perception", "Sagesse"), ("Persuasion", "Charisme"),
    ("Religion", "Intelligence"), ("Représentation", "Charisme"),
    ("Survie", "Sagesse"), ("Tromperie", "Charisme"),
    ("Investigation", "Intelligence"),
]


def page(*blocks):
    return extract.normalise("\n".join(blocks))


def wrap(rows, filler_from=0):
    body = "\n\n".join(rows)
    rest = "\n\n".join(
        "%s\n%s\nExemple pour %s." % (name, ability, name)
        for name, ability in FILLER[filler_from:]
    )
    return skills.parse([page(
        body + "\n\nCompétences\n\nCompétence\nCaractéristique\n"
        "Exemples d’application\n\n" + rest
    )])


def main():
    # -- an ordinary row ----------------------------------------------------
    found, anomalies, conflicts = wrap(
        ["Acrobaties\nDextérité\nRester debout lorsque l’équilibre est précaire."]
    )
    assert not anomalies and not conflicts, (anomalies, conflicts)
    assert len(found) == 18, len(found)
    assert found[0]["name"] == "Acrobaties" and found[0]["ability_key"] == "dex"
    print("  ok  une ligne ordinaire se lit proprement")

    # -- THE FRENCH TRAP: the SRD's own layout hyphenates mid-word inside an
    # Example Uses cell ("fonction-" / "nement"), which English never does in
    # this table. Left unmerged it would ship as "fonction- nement".
    found, anomalies, _ = wrap(
        ["Investigation\nIntelligence\nRetrouver des informations obscures ou "
         "déduire le fonction-\nnement des choses."],
        filler_from=0,
    )
    assert not anomalies, anomalies
    investigation = [s for s in found if s["name"] == "Investigation"][0]
    assert "fonctionnement des choses" in investigation["example_uses"], (
        investigation["example_uses"]
    )
    assert "fonction-" not in investigation["example_uses"]
    print("  ok  une coupure de mot dans la cellule d'exemples est recollée")

    # -- French ability keys, not transliterated English ones ---------------
    keys = {s["name"]: s["ability_key"] for s in found}
    assert keys["Athlétisme"] == "for", keys["Athlétisme"]
    assert keys["Survie"] == "sag" and keys["Tromperie"] == "cha"
    assert "str" not in keys.values() and "wis" not in keys.values()
    print("  ok  les clefs de caractéristique sont celles des profils français (for/sag)")

    # -- records come back in FRENCH alphabetical order, which is not the ---
    # English one: Discrétion (Stealth) sorts fourth here, fifteenth there
    names = [s["name"] for s in found]
    assert names == sorted(names, key=canon.slugify)
    assert names.index("Discrétion") < names.index("Perception")
    print("  ok  l'ordre exporté est l'ordre alphabétique français")

    # -- NEGATIVE CONTROL 1: a short table is reported ----------------------
    found, anomalies, _ = wrap(
        ["Acrobaties\nDextérité\nRester debout."], filler_from=1)
    assert anomalies and "17 lignes lues" in anomalies[0]["detail"], anomalies
    print("  ok  contrôle négatif : une table incomplète échoue bruyamment")

    # -- NEGATIVE CONTROL 2: the English header must not match a French page
    found, anomalies, _ = skills.parse([page(
        "Acrobatics\nDexterity\nStay on your feet.\n\nSkills\n\n"
        "Skill\nAbility\nExample Uses\n"
    )])
    assert not found and anomalies and "en-tête introuvable" in anomalies[0]["detail"]
    print("  ok  contrôle négatif : la grammaire anglaise ne déclenche rien ici")

    print("PASS test_parse_skills_fr")


if __name__ == "__main__":
    main()
