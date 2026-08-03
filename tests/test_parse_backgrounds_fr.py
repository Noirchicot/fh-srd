"""Calibration checks for the French background parser."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_backgrounds_fr  # noqa: E402


def page(*blocks):
    raw = "\n".join(blocks)
    return extract.normalise(raw)


def parse_one(*pages, suspect=()):
    return parse_backgrounds_fr.parse(list(pages), suspect)


def main():
    intro = page("Description des historiques\n\n")

    # -- ordinary background, all five fields, wrapped ability scores ------
    pages = [intro, page(
        "Acolyte\nValeurs de caractéristique : Intelligence, Sagesse,\n"
        "Charisme\nDon : Initié à la magie (Clerc) (cf. « Dons »)\n"
        "Maîtrises de compétence : Intuition et Religion\n"
        "Maîtrise d’outils : matériel de calligraphe\n"
        "Équipement : Choisissez A ou B : (A) Matériel, 8 po ; ou (B) 50 po\n",
        "Espèces des personnages\n",
    )]
    bgs, anomalies, conflicts = parse_one(*pages)
    assert len(bgs) == 1 and not anomalies, (bgs, anomalies)
    b = bgs[0]
    assert b["ability_scores"] == ["Intelligence", "Sagesse", "Charisme"], b["ability_scores"]
    assert b["skill_proficiencies"] == ["Intuition", "Religion"], b["skill_proficiencies"]
    print("  ok  ordinary background: wrapped ability-score list, 'et'-joined skills")

    # -- a missing field is an exclusion, not borrowed from the next -------
    pages = [intro, page(
        "Criminel\nValeurs de caractéristique : Dextérité, Constitution,\n"
        "Intelligence\nDon : Vigilant (cf. « Dons »)\n"
        # no "Maîtrises de compétence :" line
        "Maîtrise d’outils : outils de voleur\n"
        "Équipement : 50 po\n",
        "Sage\nValeurs de caractéristique : Constitution, Intelligence,\n"
        "Sagesse\nDon : Initié à la magie (Magicien) (cf. « Dons »)\n"
        "Maîtrises de compétence : Arcanes et Histoire\n"
        "Maîtrise d’outils : matériel de calligraphe\n"
        "Équipement : 50 po\n",
        "Espèces des personnages\n",
    )]
    bgs, anomalies, conflicts = parse_one(*pages)
    names = [b["name"] for b in bgs]
    assert "Sage" in names and "Criminel" not in names, names
    assert any("Criminel" in a["detail"] for a in anomalies), anomalies
    print("  ok  a missing field is an exclusion, not borrowed from the next entry")

    # -- NEGATIVE CONTROL ----------------------------------------------------
    pages = [intro, page(
        "Soldat\nValeurs de caractéristique : Force, Dextérité,\n"
        "Constitution\nDon : Sauvagerie martiale (cf. « Dons »)\n"
        "Maîtrises de compétence : Athlétisme et Intimidation\n"
        "Maîtrise d’outils : Choisissez un type de boîte de jeux\n"
        "Équipement : 50 po\n",
        "Espèces des personnages\n",
    )]
    bgs, anomalies, conflicts = parse_one(*pages)
    assert len(bgs) == 1 and not anomalies and not conflicts, (bgs, anomalies)
    print("  ok  negative control: an ordinary complete background is not wrongly excluded")

    print("PASS test_parse_backgrounds_fr")


if __name__ == "__main__":
    main()
