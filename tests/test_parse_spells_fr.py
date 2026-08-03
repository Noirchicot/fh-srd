"""Calibration checks for the French spell parser (v2: description text).

Each scenario here reproduces a shape actually found in the pinned FR PDF
while calibrating parse_spells.py's v2 pass, plus one negative control
proving the suite can fail. Fixtures are built with `extract.normalise()`
so the paragraph-break behaviour they depend on matches what the real
pipeline hands the parser. See test_parse_spells_fr_seam.py for the
dedicated page-seam regression (v1 finding, still pinned against the
committed export).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_spells  # noqa: E402


def page(*blocks):
    raw = "\n".join(blocks)
    return extract.normalise(raw)


def parse_one(*pages, suspect=()):
    return parse_spells.parse(list(pages), suspect)


def main():
    # -- school-first grammar, ritual in the CASTING TIME line ------------
    pages = [page(
        "Alarme\nAbjuration du 1er niveau (Rôdeur, Magicien)\n",
        "Temps d’incantation : 1 minute ou rituel\nPortée : 9 m\n"
        "Composantes : V, S, M (une clochette et du fil d’argent)\n"
        "Durée : 8 heures\n",
        "Vous placez une alarme contre les intrusions.\n\t Il ne se passe rien d’autre.\n",
    )]
    spells, anomalies, conflicts = parse_one(*pages)
    assert len(spells) == 1 and not anomalies and not conflicts, (spells, anomalies)
    s = spells[0]
    assert s["level"] == 1 and s["school"] == "abjuration" and not s["cantrip"]
    assert s["ritual"] is True, "ritual must be read off the casting-time line"
    print("  ok  school-first head, ritual detected in Temps d'incantation")

    # -- cantrip gender agreement: feminine school -> "mineure" ------------
    pages = [page(
        "Éclaboussure d’acide\nÉvocation mineure (Ensorceleur, Magicien)\n",
        "Temps d’incantation : action\nPortée : 18 m\nComposantes : V, S\n"
        "Durée : instantanée\n",
        "Vous créez une bulle acide.\n",
    )]
    spells, anomalies, conflicts = parse_one(*pages)
    assert len(spells) == 1 and not anomalies
    assert spells[0]["cantrip"] is True and spells[0]["level"] == 0
    print("  ok  feminine cantrip head ('mineure')")

    # -- cantrip gender agreement: masculine school -> "mineur" ------------
    # Enchantement is the one masculine school with a real cantrip in the
    # SRD (Moquerie cruelle, p.161) -- hard-coding "mineure" loses it.
    pages = [page(
        "Moquerie cruelle\nEnchantement mineur (Barde)\n",
        "Temps d’incantation : action\nPortée : 18 m\nComposantes : V\n"
        "Durée : 1 round\n",
        "Vous humiliez votre cible.\n",
    )]
    spells, anomalies, conflicts = parse_one(*pages)
    assert len(spells) == 1 and not anomalies
    assert spells[0]["cantrip"] is True and spells[0]["school"] == "enchantement"
    print("  ok  masculine cantrip head ('mineur', Enchantement)")

    # -- wrapped class list on the level line ------------------------------
    pages = [page(
        "Détection de la magie\nDivination du 1er niveau (Barde, Clerc, Druide, Paladin,\n"
        "Rôdeur, Ensorceleur, Occultiste, Magicien)\n",
        "Temps d’incantation : action ou rituel\nPortée : personnelle\n"
        "Composantes : V, S\nDurée : Concentration, jusqu’à 10 minutes\n",
        "Vous détectez la présence de magie.\n",
    )]
    spells, anomalies, conflicts = parse_one(*pages)
    assert len(spells) == 1 and not anomalies
    s = spells[0]
    assert s["classes"] == ["Barde", "Clerc", "Druide", "Paladin", "Rôdeur",
                             "Ensorceleur", "Occultiste", "Magicien"], s["classes"]
    assert s["ritual"] is True
    print("  ok  wrapped class list collected across the line break")

    # -- a genuinely missing field is excluded, never borrowed -------------
    pages = [page(
        "Sort cassé\nÉvocation du 1er niveau (Magicien)\n",
        "Temps d’incantation : action\nPortée : contact\nDurée : instantanée\n",
        # no Composantes line at all
        "Un effet se produit.\n",
        "Sort suivant\nÉvocation du 1er niveau (Magicien)\n",
        "Temps d’incantation : action\nPortée : contact\nComposantes : V\n"
        "Durée : instantanée\n",
        "Un effet différent.\n",
    )]
    spells, anomalies, conflicts = parse_one(*pages)
    names = [s["name"] for s in spells]
    assert "Sort suivant" in names, names
    assert "Sort cassé" not in names, names
    assert any("Sort cassé" in a["detail"] and "components" in a["detail"] for a in anomalies), anomalies
    print("  ok  a missing field is an exclusion, not borrowed from the next entry")

    # -- description keeps the upcast paragraph, does not overrun the ------
    # -- chapter boundary for the LAST spell in the stream ------------------
    pages = [page(
        "Boule de feu\nÉvocation du 3e niveau (Ensorceleur, Magicien)\n",
        "Temps d’incantation : action\nPortée : 45 m\n"
        "Composantes : V, S, M (une boulette de guano de chauve-souris)\n"
        "Durée : instantanée\n",
        "Une déflagration embrase la zone.\n"
        "\t Les objets inflammables s’enflamment.\n"
        "\t Emplacement de niveau supérieur. Les dégâts augmentent de 1d6.\n",
        "Glossaire de règles\n\nConventions du glossaire\nLe glossaire utilise des balises.\n",
    )]
    spells, anomalies, conflicts = parse_one(*pages)
    assert len(spells) == 1 and not anomalies
    desc = spells[0]["description"]
    assert desc.endswith("Les dégâts augmentent de 1d6."), repr(desc)
    assert "Conventions du glossaire" not in desc, (
        "the last spell's description ran past the chapter boundary: %r" % desc
    )
    print("  ok  upcast paragraph kept; last spell does not swallow the Glossaire")

    # -- page-crossing entry: stat block starts on one page, ends on the ---
    # -- next, exactly like Arrêt du temps in the real PDF ------------------
    pages = [
        page("Long sort\nNécromancie du 5e niveau (Magicien)\n",
             "Temps d’incantation : action\nPortée : contact\n"),
        page("Composantes : V, S\nDurée : instantanée\n",
             "Un effet funeste se produit.\n"),
    ]
    spells, anomalies, conflicts = parse_one(*pages)
    assert len(spells) == 1 and not anomalies, (spells, anomalies)
    s = spells[0]
    assert s["duration"] == "instantanée" and s["components"] == "V, S"
    assert s["page"] == 1, "source_locator must point at the page the spell STARTS on"
    print("  ok  an entry whose stat block crosses a page boundary is not lost")

    # -- embedded companion stat block inside a description is prose, not --
    # -- a new spell head (Objet animé inside Animation des objets, etc.) --
    pages = [page(
        "Appel de destrier\nInvocation du 2e niveau (Paladin)\n",
        "Temps d’incantation : action\nPortée : 9 m\nComposantes : V, S\n"
        "Durée : instantanée\n",
        "Vous convoquez une monture.\n\t Monture d’outre-monde\n"
        "Céleste, Fée ou Fiélon de taille G, Neutre\n"
        "CA 10 + niveau du sort\n",
        "Détection de la magie\nDivination du 1er niveau (Barde)\n",
        "Temps d’incantation : action\nPortée : personnelle\nComposantes : V, S\n"
        "Durée : Concentration, jusqu’à 10 minutes\n",
        "Vous détectez la magie environnante.\n",
    )]
    spells, anomalies, conflicts = parse_one(*pages)
    names = [s["name"] for s in spells]
    assert names == ["Appel de destrier", "Détection de la magie"], names
    assert "Monture d’outre-monde" in spells[0]["description"]
    assert "CA 10 + niveau du sort" in spells[0]["description"]
    print("  ok  a companion stat block inside a description is not a new spell head")

    # -- NEGATIVE CONTROL: an ordinary, complete spell must not be flagged -
    pages = [page(
        "Sort complet\nÉvocation du 1er niveau (Magicien)\n",
        "Temps d’incantation : action\nPortée : contact\nComposantes : V\n"
        "Durée : instantanée\n",
        "Un effet.\n",
    )]
    spells, anomalies, conflicts = parse_one(*pages)
    assert len(spells) == 1 and not anomalies and not conflicts, (
        "an ordinary, complete spell must parse cleanly: %s / %s" % (spells, anomalies)
    )
    print("  ok  negative control: an ordinary complete spell is not wrongly excluded")

    print("PASS test_parse_spells_fr")


if __name__ == "__main__":
    main()
