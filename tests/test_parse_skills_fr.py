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

    # -- CANONICAL ability keys, in French as in English --------------------
    # REWRITTEN
    # (2026-08-08, arbitrage de l'architecte, lot 8-srd-mecanique.) Cette
    # assertion exigeait l'inverse : `for` pour Athlétisme, `sag` pour Survie,
    # et l'absence de `str`/`wis`. Elle était juste sur le code d'alors et
    # fausse sur la règle : `resolved.abilities` de `fh-char/1` impose
    # `str dex con int wis cha` DANS LES DEUX LANGUES, donc une compétence
    # française qui disait `sag` ne pouvait pas adresser les caractéristiques
    # de son propre document français. Le mot affichable, lui, n'a pas bougé —
    # c'est ce que la ligne `ability` vérifie juste en dessous.
    keys = {s["name"]: s["ability_key"] for s in found}
    assert keys["Athlétisme"] == "str", keys["Athlétisme"]
    assert keys["Survie"] == "wis" and keys["Tromperie"] == "cha"
    assert "for" not in keys.values() and "sag" not in keys.values()
    words = {s["name"]: s["ability"] for s in found}
    assert words["Athlétisme"] == "Force" and words["Survie"] == "Sagesse", words
    print("  ok  les clefs sont canoniques (str/wis) et le mot affiché reste "
          "français (Force/Sagesse)")

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
