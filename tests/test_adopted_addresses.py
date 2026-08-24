"""Les trois adresses du français seul : adoptées du livre anglais, pas inventées.

🔴 ERIC A AUTORISÉ D'INVENTER, ET LA MESURE A TROUVÉ QU'ON N'A PAS À LE FAIRE.
Le livre anglais imprime `Fly Speed`, `Swim Speed` et `Climb Speed` — 74 fois au
total — sans leur donner d'entrée de glossaire. Ce fichier garde les deux moitiés
de cette preuve : que le livre les imprime, et que ce sont bien CES formes-là.

Run: python3 tests/test_adopted_addresses.py
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

import adopted_addresses as A  # noqa: E402

EXPORTS = os.path.join(HERE, "..", "exports", "srd")


def _all(lang):
    out = {}
    d = os.path.join(EXPORTS, lang)
    for name in sorted(os.listdir(d)):
        if name.endswith(".json"):
            with open(os.path.join(d, name), encoding="utf-8") as fh:
                for r in json.load(fh)["records"]:
                    out[r["id"]] = r
    return out


def acceptance_le_livre_anglais_imprime_bien_ces_termes():
    """⭐ LA PREUVE QUE CE N'EST PAS UNE INVENTION — comptée sur le corpus.

    ⛔ Et le contrôle NÉGATIF compte autant : `Climbing Speed` n'existe PAS.
    Sans lui, on ne saurait pas que `Climb Speed` a été choisi par le livre
    plutôt que par nous. Le premier réflexe était `climbing-speed`, calqué sur
    l'entrée `Climbing` qui existe — il aurait été faux, et muet.
    """
    corpus = json.dumps([r["data"] for r in _all("en").values()], ensure_ascii=False)
    for terme in ("Fly Speed", "Swim Speed", "Climb Speed", "Burrow Speed"):
        assert corpus.count(terme) > 0, (
            "« %s » n'est plus imprimé nulle part dans le livre anglais — "
            "l'adresse adoptée qui en descend n'a plus de preuve" % terme)
    for absent in ("Flying Speed", "Swimming Speed", "Climbing Speed"):
        assert corpus.count(absent) == 0, (
            "« %s » est apparu dans le livre anglais : la forme adoptée "
            "(`%s`) doit être remesurée, ce n'est plus la seule attestée"
            % (absent, absent.split()[0].lower()))


def acceptance_le_temoin_de_la_famille_existe_des_deux_cotes():
    """⭐ `Burrow Speed` est le quatrième membre, et LUI a son entrée.

    C'est lui qui donne la forme du slug (`<X> Speed` → `<x>-speed`) et il est
    APPARIÉ à `Vitesse de fouissement`. Sans ce témoin, les trois adresses
    seraient dérivées d'un patron que rien n'atteste.
    """
    en = _all("en")
    assert A.WITNESS in en, A.WITNESS
    with open(os.path.join(EXPORTS, "correspondence.json"), encoding="utf-8") as fh:
        pairs = {p["en"]: p["fr"] for p in json.load(fh)["pairs"]}
    assert pairs.get(A.WITNESS) == "srd:glossary:fr:vitesse-de-fouissement", (
        "le témoin n'est plus apparié à son jumeau français — le patron "
        "`<X> Speed` ↔ `Vitesse de <x>` n'est plus prouvé des deux côtés")


def acceptance_aucune_adresse_adoptee_n_ecrase_une_entree_existante():
    """🔴 LE VRAI PIÈGE, ET ARCHI L'AVAIT NOMMÉ.

    L'anglais porte DÉJÀ `Climbing`, `Swimming`, `Flying`. Ce sont des entrées
    DISTINCTES : le mode de déplacement (« chaque mètre coûte un mètre de
    plus ») n'est pas la vitesse (« remplace la Vitesse pour traverser une
    surface verticale »). Écraser l'une des trois serait un défaut, pas un
    raccourci.
    """
    en = _all("en")
    assert A.assert_no_collision(en) is True
    # ⭐ Et on prouve la DISTINCTION, pas seulement l'absence de collision :
    # les deux textes ne disent pas la même chose.
    mode = en["srd:glossary:en:climbing"]["data"]["description"]
    assert "extra foot" in mode, mode[:120]
    assert "srd:glossary:en:climb-speed" not in en, (
        "l'adresse adoptée existe désormais comme record anglais : le français "
        "a un vrai vis-à-vis et doit se PAIRER, pas s'adopter")


def acceptance_les_trois_francaises_sont_bien_les_seules_sans_paire():
    """⛔ TROIS, ET SEULEMENT TROIS. Eric a tranché sur un cas connu, pas sur
    une catégorie. Une quatrième orpheline ne s'adopte pas : elle se nomme.
    """
    with open(os.path.join(EXPORTS, "correspondence.json"), encoding="utf-8") as fh:
        appariés = {p["fr"] for p in json.load(fh)["pairs"]}
    sans = sorted(rid for rid in _all("fr") if rid not in appariés)
    assert sans == sorted(A.ADOPTED), (
        "les records français sans paire ne sont plus exactement les trois "
        "déclarées — mesuré %s, déclaré %s. Une orpheline neuve se NOMME et "
        "s'arrête ; elle ne prend pas une adresse au passage."
        % (sans, sorted(A.ADOPTED)))


def main():
    acceptance_le_livre_anglais_imprime_bien_ces_termes()
    acceptance_le_temoin_de_la_famille_existe_des_deux_cotes()
    acceptance_aucune_adresse_adoptee_n_ecrase_une_entree_existante()
    acceptance_les_trois_francaises_sont_bien_les_seules_sans_paire()
    print("PASS test_adopted_addresses")


if __name__ == "__main__":
    main()
