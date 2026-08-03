"""Calibration checks for the French monster (stat block) parser.

Each scenario reproduces a shape actually found in the pinned FR PDF while
calibrating parse_monsters_fr.py, plus one negative control proving the
suite can fail.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_monsters_fr  # noqa: E402

ABILITIES_BLOCK = (
    "MOD\nJS\nMOD\nJS\nMOD\nJS\n"
    "For 21 +5\n+5\nDex 9\n−1\n+3\nCon 15 +2\n+6\nInt 18 +4\n+8\nSag 15 +2\n+6\nCha 18 +4\n+4\n"
)


def page(*blocks):
    return extract.normalise("\n".join(blocks))


def wrap(*monster_blocks, suspect=()):
    pages = [page("Monstres de A à Z\n\n")] + list(monster_blocks)
    return parse_monsters_fr.parse(pages, suspect)


def main():
    # -- ordinary monster, complete stat block -------------------------------
    pages = [page(
        "Aboleth\nAboleth\n\nAberration de taille G, Loyale Mauvaise\n\n"
        "CA 17\nInitiative +7 (17)\nPv 150 (20d10 + 40)\nVitesse 3 m, nage 12 m\n\n",
        ABILITIES_BLOCK,
        "Compétences Histoire +12, Perception +10\n"
        "Sens Vision dans le noir 36 m ; Perception passive 20\n"
        "Langues profond ; télépathie 36 m\nFP 10 (5 900 PX ; BM +4)\n\n",
        "Traits\n\nAmphibie. L’aboleth peut respirer dans l’air et dans l’eau.\n\n",
        "Actions\n\nTentacule. Corps à corps : +9, allonge 3 m. Touché : 12 dégâts.\n\n",
    )]
    monsters, anomalies, conflicts = wrap(*pages)
    assert len(monsters) == 1 and not anomalies, (monsters, anomalies)
    m = monsters[0]
    assert m["size_type"] == "Aberration de taille G" and m["alignment"] == "Loyale Mauvaise"
    assert m["tags"] is None
    assert m["abilities"]["dex"] == {"score": 9, "mod": -1, "save": 3}
    print("  ok  ordinary monster: full stat block, gendered 'Loyale' alignment")

    # -- tags sit BETWEEN type and 'de taille', not at the clause's end ------
    pages = [page(
        "Fiélon (Démon)\nFiélon (Démon)\n\nFiélon (Démon) de taille P, Chaotique Mauvais\n\n"
        "CA 13\nInitiative +2 (12)\nPv 13 (6d4 -6)\nVitesse 9 m, vol 9 m\n\n",
        ABILITIES_BLOCK,
        "Sens Vision dans le noir 36 m ; Perception passive 12\n"
        "Langues comprend l’abyssal ; télépathie 36 m\nFP 1 (200 PX ; BM +2)\n\n",
        "Actions\n\nMorsure. Corps à corps : +4. Touché : 5 dégâts.\n\n",
    )]
    monsters, anomalies, conflicts = wrap(*pages)
    assert len(monsters) == 1 and not anomalies, (monsters, anomalies)
    m = monsters[0]
    assert m["tags"] == "Démon" and m["size_type"] == "Fiélon de taille P", m
    print("  ok  a parenthetical tag between type and 'de taille' is extracted")

    # -- alignment wraps across the line break --------------------------------
    pages = [page(
        "Loup-garou\nLoup-garou\n\n"
        "Monstruosité (Lycanthrope) de taille M ou P, Chaotique\nMauvaise\n\n"
        "CA 15\nInitiative +4 (14)\nPv 71 (11d8 + 22)\nVitesse 9 m\n\n",
        ABILITIES_BLOCK,
        "Sens Vision dans le noir 18 m ; Perception passive 14\n"
        "Langues commun\nFP 3 (700 PX ; BM +2)\n\n",
        "Actions\n\nMorsure. Corps à corps : +5. Touché : 7 dégâts.\n\n",
    )]
    monsters, anomalies, conflicts = wrap(*pages)
    assert len(monsters) == 1 and not anomalies, (monsters, anomalies)
    assert monsters[0]["alignment"] == "Chaotique Mauvaise", monsters[0]["alignment"]
    print("  ok  alignment clause wrapping across a line break ('Chaotique' / 'Mauvaise')")

    # -- 'Neutre' alone (true neutral) is NOT extended, unlike a wrap --------
    pages = [page(
        "Chtuul\nChtuul\n\nAberration de taille M, Neutre\n\n"
        "CA 12\nInitiative +1 (11)\nPv 22 (4d8 + 4)\nVitesse 9 m\n\n",
        ABILITIES_BLOCK,
        "Sens Perception passive 10\nLangues aucune\nFP 1/2 (100 PX ; BM +2)\n\n",
        "Actions\n\nGriffe. Corps à corps : +4. Touché : 4 dégâts.\n\n",
    )]
    monsters, anomalies, conflicts = wrap(*pages)
    assert len(monsters) == 1 and not anomalies, (monsters, anomalies)
    assert monsters[0]["alignment"] == "Neutre", monsters[0]["alignment"]
    print("  ok  standalone 'Neutre' (true neutral) is kept bare, not wrongly extended")

    # -- a trait name wraps BEFORE its own closing period ---------------------
    pages = [page(
        "Dragon bleu adulte\nDragon bleu adulte\n\n"
        "Dragon (Chromatique) de taille TG, Loyale Mauvaise\n\n"
        "CA 19\nInitiative +14 (24)\nPv 225 (18d12 + 108)\nVitesse 12 m, fouissement 9 m, vol 24 m\n\n",
        ABILITIES_BLOCK,
        "Sens Vision dans le noir 36 m ; Perception passive 23\n"
        "Langues commun, draconique\nFP 16 (15 000 PX ; BM +7)\n\n",
        "Traits\n\nRésistance légendaire (3/jour, ou 4/jour dans son\n"
        "antre). Si le dragon rate un jet de sauvegarde, il peut\n"
        "décider de le réussir tout de même.\n\n",
        "Actions\n\nMorsure. Corps à corps : +12. Touché : 16 dégâts.\n\n",
    )]
    monsters, anomalies, conflicts = wrap(*pages)
    assert len(monsters) == 1 and not anomalies, (monsters, anomalies)
    trait_names = [t["name"] for t in monsters[0]["traits"]]
    assert trait_names == ["Résistance légendaire (3/jour, ou 4/jour dans son antre)"], trait_names
    print("  ok  a trait name wrapping before its own closing period is joined")

    # -- an entry's name ends the line at its own period, description on ----
    # -- the NEXT line entirely (no trailing content on the head's own line) -
    pages = [page(
        "Vampire\nVampire\n\nMort-vivant de taille M, Neutre Mauvais\n\n"
        "CA 16\nInitiative +6 (16)\nPv 195 (26d8 + 78)\nVitesse 9 m, escalade 9 m, vol 9 m\n\n",
        ABILITIES_BLOCK,
        "Sens Vision dans le noir 36 m ; Perception passive 17\n"
        "Langues commun plus deux autres langues\nFP 15 (13 000 PX ; BM +7)\n\n",
        "Actions\n\nAttaques multiples (forme de vampire uniquement).\n"
        "Le vampire effectue deux attaques.\n\n",
    )]
    monsters, anomalies, conflicts = wrap(*pages)
    assert len(monsters) == 1 and not anomalies, (monsters, anomalies)
    action_names = [a["name"] for a in monsters[0]["actions"]]
    assert action_names == ["Attaques multiples (forme de vampire uniquement)"], action_names
    print("  ok  an entry name ending its own line at the period (description starts next line)")

    # -- a shapeshifter TRAIT's own prose is not mistaken for a monster head -
    pages = [page(
        "Guenaude nocturne\nGuenaude nocturne\n\nFée de taille M, Neutre Mauvaise\n\n"
        "CA 17\nInitiative +1 (11)\nPv 82 (11d8 + 33)\nVitesse 9 m\n\n",
        ABILITIES_BLOCK,
        "Sens Vision dans le noir 18 m ; Perception passive 12\n"
        "Langues commun, sylvestre\nFP 5 (1 800 PX ; BM +3)\n\n",
        "Traits\n\nChangement d’aspect. La guenaude se transforme en\n"
        "Humanoïde de taille P ou M, ou bien retrouve sa forme\n"
        "véritable. Hormis sa catégorie de taille, son profil reste\n"
        "le même, quelle que soit sa forme.\n\n",
        "Actions\n\nGriffe. Corps à corps : +6. Touché : 8 dégâts.\n\n",
    )]
    monsters, anomalies, conflicts = wrap(*pages)
    names = [m["name"] for m in monsters]
    assert names == ["Guenaude nocturne"], names
    assert len(monsters[0]["traits"]) == 1, monsters[0]["traits"]
    assert monsters[0]["traits"][0]["name"] == "Changement d’aspect"
    assert "Humanoïde de taille P ou M" in monsters[0]["traits"][0]["description"]
    print("  ok  a shapeshifter trait's own embedded prose is not mistaken for a new monster head")

    # -- NEGATIVE CONTROL: an ordinary, complete monster is not flagged ------
    pages = [page(
        "Zombi\nZombi\n\nMort-vivant de taille M, Neutre Mauvais\n\n"
        "CA 8\nInitiative -2 (8)\nPv 15 (2d8 + 6)\nVitesse 6 m\n\n",
        ABILITIES_BLOCK,
        "Sens Vision dans le noir 18 m ; Perception passive 8\n"
        "Langues comprend les langues de son vivant, mais ne peut pas parler\n"
        "FP 1/4 (50 PX ; BM +2)\n\n",
        "Actions\n\nCoup de poing. Corps à corps : +3. Touché : 4 dégâts.\n\n",
    )]
    monsters, anomalies, conflicts = wrap(*pages)
    assert len(monsters) == 1 and not anomalies and not conflicts, (monsters, anomalies)
    print("  ok  negative control: an ordinary complete monster is not wrongly excluded")

    print("PASS test_parse_monsters_fr")


if __name__ == "__main__":
    main()
