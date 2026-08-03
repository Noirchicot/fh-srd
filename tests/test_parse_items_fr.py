"""Calibration checks for the French magic item parser.

Each scenario reproduces a shape actually found in the pinned FR PDF while
calibrating parse_items_fr.py, plus one negative control proving the suite
can fail.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_items_fr  # noqa: E402


def page(*blocks):
    raw = "\n".join(blocks)
    return extract.normalise(raw)


def parse_one(*pages, suspect=()):
    return parse_items_fr.parse(list(pages), suspect)


def main():
    intro = page("Objets magiques de A à Z\n\nLes objets magiques sont présentés par ordre alphabétique.\n")

    # -- ordinary head: category, comma, rarity, restricted attunement ----
    pages = [intro, page(
        "Amulette d’antidétection\nObjet merveilleux, peu courant (Harmonisation requise)\n",
        "Tant que vous portez cette amulette, vous êtes indétectable par divination.\n",
    )]
    items, anomalies, conflicts = parse_one(*pages)
    assert len(items) == 1 and not anomalies, (items, anomalies)
    it = items[0]
    assert it["category"] == "wondrous-item" and it["attunement"] is True
    print("  ok  ordinary head: masculine 'peu courant' rarity, attunement")

    # -- BUG 1: no comma before the rarity word ----------------------------
    pages = [intro, page(
        "Armure de cuir clouté enchantée\nArmure (armure de cuir clouté) rare\n",
        "Vous recevez un bonus de +1 à la CA.\n",
    )]
    items, anomalies, conflicts = parse_one(*pages)
    assert len(items) == 1 and not anomalies, (items, anomalies)
    it = items[0]
    assert it["category"] == "armor" and it["subtype"] == "armure de cuir clouté"
    assert it["rarity"] == "rare"
    print("  ok  bare-space rarity clause (missing comma) is still read")

    # -- BUG 2: subtype parenthetical wraps before its closing paren ------
    pages = [intro, page(
        "Armure de mithral\nArmure (intermédiaire ou lourde, sauf armure de\n"
        "peaux), peu courante\n",
        "Le mithral est un métal léger et souple.\n",
    )]
    items, anomalies, conflicts = parse_one(*pages)
    assert len(items) == 1 and not anomalies, (items, anomalies)
    it = items[0]
    assert it["subtype"] == "intermédiaire ou lourde, sauf armure de peaux"
    assert "peu courante" in it["rarity"]
    print("  ok  subtype parenthetical wrapping onto a second line before ')'")

    # -- BUG 2b: rarity wraps to a THIRD line after the paren closes ------
    # cleanly and a bare comma already ends line one -- no anomaly is
    # raised for this shape (a line ending after a comma is not malformed,
    # it just isn't a complete head YET), so silently dropping it would
    # never be caught by the exclusion register.
    pages = [intro, page(
        "Armure de vulnérabilité\nArmure (légère, intermédiaire ou lourde),\n"
        "rare (Harmonisation requise)\n",
        "Vous bénéficiez de la résistance à l’un des types de dégâts suivants.\n",
    )]
    items, anomalies, conflicts = parse_one(*pages)
    assert len(items) == 1 and not anomalies, (items, anomalies)
    it = items[0]
    assert it["subtype"] == "légère, intermédiaire ou lourde"
    assert it["rarity"].startswith("rare"), it["rarity"]
    print("  ok  rarity word wrapping to a third line after a bare comma")

    # -- capitalised "Artefact" rarity (a one-off in the source) ----------
    pages = [intro, page(
        "Orbe des dragons\nObjet merveilleux, Artefact (Harmonisation requise)\n",
        "Chaque orbe est un globe de cristal gravé.\n",
    )]
    items, anomalies, conflicts = parse_one(*pages)
    assert len(items) == 1 and not anomalies, (items, anomalies)
    assert items[0]["rarity"].startswith("Artefact")
    print("  ok  capitalised 'Artefact' rarity is matched")

    # -- the "+1, +2 ou +3" generic name does NOT collide with TYPE_HEAD ---
    # the way its English translation does (no comma right after the
    # category word in French) -- confirms the false-head guard is
    # defensive here, not load-bearing.
    pages = [intro, page(
        "Arme +1, +2 ou +3\nArme (courante ou de guerre), peu courante (+1), rare\n"
        "(+2) ou très rare (+3)\n",
        "Vous recevez un bonus aux jets d’attaque et de dégâts.\n",
    )]
    items, anomalies, conflicts = parse_one(*pages)
    assert len(items) == 1 and not anomalies, (items, anomalies)
    assert items[0]["name"] == "Arme +1, +2 ou +3"
    print("  ok  the generic '+1, +2 ou +3' name is read as an ordinary name")

    # -- a genuinely empty entry (type line, no description) is excluded --
    pages = [intro, page(
        "Objet cassé\nObjet merveilleux, rare\n",
        "Objet suivant\nObjet merveilleux, rare\n",
        "Une description bien réelle.\n",
    )]
    items, anomalies, conflicts = parse_one(*pages)
    names = [i["name"] for i in items]
    assert "Objet suivant" in names, names
    assert "Objet cassé" not in names, names
    print("  ok  a type line with no description text is excluded, not borrowed")

    # -- NEGATIVE CONTROL: an ordinary, complete item is not flagged ------
    pages = [intro, page(
        "Objet complet\nAnneau, rare\n",
        "Un effet quelconque.\n",
    )]
    items, anomalies, conflicts = parse_one(*pages)
    assert len(items) == 1 and not anomalies and not conflicts, (
        "an ordinary, complete item must parse cleanly: %s / %s" % (items, anomalies)
    )
    print("  ok  negative control: an ordinary complete item is not wrongly excluded")

    print("PASS test_parse_items_fr")


if __name__ == "__main__":
    main()
