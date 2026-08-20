"""Calibration checks for the French weapon-property / botte parsers.

🔴 THE TRAP THIS FILE EXISTS FOR: French does not say "maîtrise" for a weapon
mastery. It says **botte**. And `Maîtrise des armes` DOES exist, on the same
spread, for the *proficiency* rule. The fixture below prints both sections,
in the order the pinned PDF prints them, so an anchor that drifts onto
"maîtrise" fails here instead of failing silently in production.

The other traps are the English ones read in French: `Armes improvisées` is a
sidebar landing inside the botte block, `Lourde` is the first line of a page,
and `Propriétés` is also the weapons table's column header.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_weapon_mastery_fr as botte  # noqa: E402
import parse_weapon_property_fr as prop  # noqa: E402
import weapon_sections  # noqa: E402

PAGE_BEFORE = (
    "Équipement\n"
    "\n"
    "Armes\n"
    "\n"
    "Bottes d’arme. Chaque arme est dotée d’une propriété botte, qui est\n"
    "définie en section « Propriétés botte ».\n"
    # THE NEIGHBOUR: weapon *proficiency*, which French calls "maîtrise".
    # It is not this genre and must not be read as one.
    "Maîtrise des armes\n"
    "\n"
    "N’importe qui peut tenir une arme, mais vous devez en avoir la maîtrise\n"
    "pour ajouter votre bonus de maîtrise aux jets d’attaque correspondants.\n"
    "Propriétés\n"
    "\n"
    "Ci-après figurent les définitions des propriétés de la colonne\n"
    "Propriétés du tableau « Armes ».\n"
    "\n"
    "Allonge\n"
    "Une arme avec la propriété Allonge ajoute 1,50 m à votre allonge lorsque\n"
    "vous attaquez avec elle.\n"
    "\n"
    "Chargement\n"
    "Vous ne pouvez tirer qu’un seul projectile lorsque vous consacrez une\n"
    "action à attaquer avec une arme dotée de la propriété Chargement.\n"
    "\n"
    "Deux mains\n"
    "Une arme à Deux mains requiert vos deux mains lorsque vous l’utilisez\n"
    "pour attaquer.\n"
    "\n"
    "Finesse\n"
    "Lorsque effectuez une attaque avec une arme dotée de la propriété\n"
    "Finesse, vous choisissez le modificateur qui s’applique.\n"
    "\n"
    "Lancer\n"
    "Quand une arme est dotée de la propriété Lancer, vous pouvez la lancer\n"
    "pour effectuer une attaque à distance.\n"
    "\n"
    "Légère\n"
    "Lorsque vous effectuez l’action Attaque à votre tour et attaquez avec\n"
    "une arme Légère, vous pouvez effectuer une attaque supplémentaire.\n"
)

# THE PAGE-BOUNDARY TRAP: `Lourde` opens this page, straight after the last
# body line of `Légère`, with no blank line between them in the stream.
PAGE_MAIN = (
    "Lourde\n"
    "Vous subissez le Désavantage aux jets d’attaque avec une arme Lourde\n"
    "s’il s’agit d’une arme de corps à corps.\n"
    "\n"
    "Munitions\n"
    "Vous pouvez utiliser une arme dotée de la propriété Munitions pour\n"
    "effectuer une attaque à distance.\n"
    "\n"
    "Polyvalente\n"
    "Une arme dite Polyvalente peut s’utiliser à une ou deux mains.\n"
    "\n"
    "Portée\n"
    "La portée d’une arme à distance figure entre parenthèses après la\n"
    "propriété Munitions ou Lancer.\n"
    "Propriétés botte\n"
    "\n"
    "Chaque arme est dotée d’une botte, qui n’est utilisable que par un\n"
    "personnage disposant d’une aptitude, comme Bottes d’arme.\n"
    "\n"
    # THE SIDEBAR TRAP, in French.
    "Armes improvisées\n"
    "\n"
    "Si vous utilisez un objet (pied de table, poêle à frire, bouteille)\n"
    "comme arme improvisée, veuillez vous référer au « Glossaire de règles ».\n"
    "\n"
    "Coup double\n"
    "Lorsque vous effectuez l’attaque supplémentaire de la propriété Légère\n"
    "de l’arme, vous pouvez l’effectuer dans le cadre de l’action Attaque.\n"
    "\n"
    "Écorchure\n"
    "Si votre jet d’attaque avec cette arme rate une créature, vous pouvez\n"
    "lui infliger des dégâts.\n"
    "\n"
    "Enchaînement\n"
    "Si vous touchez une créature avec un jet d’attaque de corps à corps avec\n"
    "cette arme, vous pouvez attaquer une deuxième créature.\n"
    "\n"
    "Ouverture\n"
    "Si vous touchez une créature avec cette arme et lui infligez des dégâts,\n"
    "vous avez l’Avantage à votre prochain jet d’attaque.\n"
    "\n"
    "Poussée\n"
    "Si vous touchez une créature avec cette arme, vous pouvez la repousser\n"
    "d’un maximum de 3 m en ligne droite.\n"
    "\n"
    "Ralentissement\n"
    "Si vous touchez une créature avec cette arme et lui infligez des dégâts,\n"
    "vous pouvez réduire sa Vitesse de 3 m.\n"
    "\n"
    "Renversement\n"
    "Si vous touchez une créature avec cette arme, vous pouvez la contraindre\n"
    "à effectuer un jet de sauvegarde de Constitution.\n"
    "\n"
    "Sape\n"
    "Si vous touchez une créature avec cette arme, cette créature subit le\n"
    "Désavantage à son prochain jet d’attaque.\n"
)

PAGE_TABLE = (
    "Armes\n"
    "\n"
    "Nom\n"
    "Dégâts\n"
    "Propriétés\n"
    "Botte d’arme\n"
    "Poids\n"
    "Prix\n"
    "\n"
    "Bâton de combat\n"
    "1d6 contondants\n"
    "Polyvalente (1d8)\n"
    "Renversement\n"
    "2 kg\n"
    "2 pa\n"
)


def pages(before=PAGE_BEFORE, main=PAGE_MAIN, table=PAGE_TABLE):
    return [extract.normalise(p) for p in (before, main, table)]


def names(records):
    return [r["name"] for r in records]


def main():
    # -- the eleven properties ---------------------------------------------
    found, anomalies, conflicts = prop.parse(pages())
    assert not anomalies and not conflicts, (anomalies, conflicts)
    assert names(found) == [
        "Allonge", "Armes improvisées", "Chargement", "Deux mains", "Finesse",
        "Lancer", "Légère", "Lourde", "Munitions", "Polyvalente", "Portée",
    ], names(found)
    print("  ok  11 propriétés, French's own alphabet, sidebar included")

    by_name = {r["name"]: r for r in found}
    assert by_name["Lourde"]["page"] == 2
    print("  ok  `Lourde`, first line of its page, is still a head")

    # -- ⚠️ THE `maîtrise` TRAP --------------------------------------------
    # `Maîtrise des armes` is weapon PROFICIENCY and is printed on the page
    # before. Nothing from it may appear in either genre.
    all_names = set(names(found))
    found_m, anomalies_m, conflicts_m = botte.parse(pages())
    all_names |= set(names(found_m))
    assert "Maîtrise des armes" not in all_names
    for record in list(found) + list(found_m):
        assert "bonus de maîtrise aux jets d’attaque" not in record["description"], (
            "the weapon-PROFICIENCY section leaked into %r" % record["name"])
    print("  ok  `Maîtrise des armes` (proficiency) leaked into neither genre")

    # -- the eight bottes --------------------------------------------------
    assert not anomalies_m and not conflicts_m, (anomalies_m, conflicts_m)
    assert names(found_m) == [
        "Coup double", "Écorchure", "Enchaînement", "Ouverture", "Poussée",
        "Ralentissement", "Renversement", "Sape",
    ], names(found_m)
    assert "Armes improvisées" not in names(found_m)
    print("  ok  8 bottes, sidebar excluded, none of them named from English")

    # The names really are the unguessable ones.
    assert "Enchaînement" in names(found_m)   # = Cleave
    assert "Coup double" in names(found_m)    # = Nick, NOT Cleave
    assert "Renversement" in names(found_m)   # = Topple
    print("  ok  Enchaînement/Coup double/Renversement are read, not derived")

    # -- an unknown head is NAMED ------------------------------------------
    intruder = PAGE_MAIN.replace(
        "Sape\n",
        "Estoc\n"
        "Une tête qui n’appartient à aucun des deux ensembles.\n"
        "\n"
        "Sape\n",
    )
    found_i, anomalies_i, _ = botte.parse(pages(main=intruder))
    assert len(found_i) == 8, names(found_i)
    assert len(anomalies_i) == 1 and "Estoc" in anomalies_i[0]["detail"], anomalies_i
    print("  ok  a head in neither closed set is excluded and named")

    # -- a MISSING property refuses ----------------------------------------
    lost = PAGE_MAIN.replace(
        "Polyvalente\n"
        "Une arme dite Polyvalente peut s’utiliser à une ou deux mains.\n"
        "\n",
        "",
    )
    try:
        prop.parse(pages(main=lost))
    except weapon_sections.SectionCountError as exc:
        assert "Polyvalente" in str(exc) and "10 of the 11" in str(exc), exc
        print("  ok  a section short of one entry REFUSES, naming it")
    else:
        raise AssertionError("a missing property must stop the build, not export 10")

    print("PASS test_parse_weapon_sections_fr")


if __name__ == "__main__":
    main()
