"""La conversion est une FONCTION, et c'est ce qui autorise l'option 4.

🔴 TOUTE LA DÉCISION D'ERIC REPOSE SUR CE FICHIER. Il a tranché que les nombres
convertis sortent de la donnée et se dérivent au rendu — ce qui n'est possible
QUE si une valeur anglaise rend toujours la même valeur française. Si une seule
en rendait deux, le site français deviendrait faux **sans que rien d'autre
casse** : les records seraient intacts, les paires justes, les comptes verts, et
une valeur sur deux serait tirée au sort.

⭐ MESURÉ SUR TOUT LE CORPUS le 2026-08-24 : 85 entrées, ZÉRO ambiguïté. Et la
mesure du siège portait sur 58 sorts — forte, pas exhaustive. Celle-ci porte sur
les 1 366 paires et sur TOUS les champs porteurs d'unité.

⛔ CE FICHIER NE COMPTE PAS LES ENTRÉES. Un compte figé se périmerait au premier
objet ajouté au livre ; ce qu'on garde, c'est la PROPRIÉTÉ.

Run: python3 tests/test_convert_units.py
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

import convert_units  # noqa: E402

EXPORTS = os.path.join(HERE, "..", "exports", "srd")


def _records(lang):
    out = {}
    directory = os.path.join(EXPORTS, lang)
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(directory, name), encoding="utf-8") as fh:
            for rec in json.load(fh)["records"]:
                out[rec["id"]] = rec
    return out


def _pairs():
    with open(os.path.join(EXPORTS, "correspondence.json"), encoding="utf-8") as fh:
        return [(p["fr"], p["en"]) for p in json.load(fh)["pairs"]]


def unit_la_coupure_est_par_valeur_jamais_par_champ():
    """⚠️ LE PIÈGE DE CE MODULE, et il est réel dans la donnée.

    `monster.speed` vaut TANTÔT `20 ft.` — une conversion pure — TANTÔT
    `30 ft., Fly 60 ft.`, qui est une PHRASE. Décider « le champ speed se
    convertit » perdrait les phrases françaises ; décider « il se traduit »
    ferait entrer des conversions dans le patch. On regarde la valeur.
    """
    assert convert_units.is_pure_conversion("30 feet")
    assert convert_units.is_pure_conversion("20 ft.")
    assert convert_units.is_pure_conversion("1/2 lb.")
    assert convert_units.is_pure_conversion("1,000 GP")
    assert convert_units.is_pure_conversion("30/120 feet")
    # ⛔ Une phrase qui CONTIENT une unité n'est pas une conversion.
    assert not convert_units.is_pure_conversion("30 ft., Fly 60 ft.")
    assert not convert_units.is_pure_conversion("Darkvision 60 ft.; Passive Perception 9")
    assert not convert_units.is_pure_conversion("Self")
    assert not convert_units.is_pure_conversion(None)


def unit_la_table_refuse_de_cesser_d_etre_une_fonction():
    """⭐ LE GARDE, ÉPROUVÉ EN LE FAISANT MORDRE — un garde qu'on n'a pas vu
    mordre ne mord pas. Deux paires fabriquées donnent à la même valeur
    anglaise deux valeurs françaises : `derive` doit REFUSER, pas arbitrer.
    """
    faux = {
        "fr": {"f1": {"data": {"weight": "1,5 kg"}},
               "f2": {"data": {"weight": "1,4 kg"}}},
        "en": {"e1": {"data": {"weight": "3 lb."}},
               "e2": {"data": {"weight": "3 lb."}}},
    }
    try:
        convert_units.derive([("f1", "e1"), ("f2", "e2")], faux)
    except convert_units.ConversionError as err:
        assert "FONCTION" in str(err), err
        assert "1,4 kg" in str(err) and "1,5 kg" in str(err), (
            "le refus doit NOMMER les deux valeurs : « une valeur anglaise en "
            "rend deux » sans dire lesquelles n'aide personne")
        return
    raise AssertionError("la table a accepté deux françaises pour une anglaise")


def unit_une_valeur_absente_crie_au_lieu_de_se_replier():
    """⛔ PAS DE REPLI SILENCIEUX SUR L'ANGLAIS. Une valeur manquante afficherait
    `30 feet` au lecteur français ; le garde de reconstruction verrait bien un
    mot changé, mais il ne dirait pas POURQUOI. C'est ici que ça doit crier.
    """
    try:
        convert_units.apply({}, "weight", "3 lb.")
    except convert_units.ConversionError as err:
        assert "3 lb." in str(err) and "weight" in str(err), err
        return
    raise AssertionError("une conversion inconnue a été rendue en silence")


def acceptance_la_vraie_table_est_une_fonction():
    """La propriété, sur les 1 366 paires réelles et tous les champs.

    ⛔ Aucun compte n'est figé : c'est la PROPRIÉTÉ qui est gardée, pas le
    nombre d'entrées. Un objet ajouté au livre ne doit pas rougir ce test.
    """
    table = convert_units.derive(_pairs(), {"fr": _records("fr"), "en": _records("en")})
    assert table, "la table est vide — la dérivation ne lit plus rien"
    # `derive` jette sur ambiguïté ; qu'elle ait rendu quelque chose EST la preuve.
    champs = sorted({champ for champ, _ in table})
    assert champs == ["cost", "range", "speed", "weight"], champs


def acceptance_la_table_publiee_est_celle_qui_se_derive():
    """⭐ LE FICHIER COMMITÉ N'EST PAS UNE COPIE À LA MAIN. Il se re-dérive ici
    et doit tomber au même octet — sinon quelqu'un l'a édité en passant, et la
    passe suivante l'écraserait en silence.
    """
    with open(os.path.join(EXPORTS, "conversions.json"), encoding="utf-8") as fh:
        publie = json.load(fh)
    table = convert_units.derive(_pairs(), {"fr": _records("fr"), "en": _records("en")})
    assert publie["fields"] == convert_units.as_export(table), (
        "exports/srd/conversions.json a divergé de sa dérivation — édité à la "
        "main, ou produit par une autre passe")
    assert publie["count"] == len(table)


def acceptance_les_arrondis_sont_ceux_du_livre():
    """📌 LA TABLE NE MULTIPLIE RIEN, ELLE LIT.

    30 pieds font 9,144 m et le livre écrit `9 m` ; un mille fait 1,609 km et
    le livre écrit `1,5 km`. ⭐ Une table recalculée serait un AUTRE livre — et
    elle aurait l'air juste, ce qui est pire.
    """
    with open(os.path.join(EXPORTS, "conversions.json"), encoding="utf-8") as fh:
        champs = json.load(fh)["fields"]
    assert champs["range"]["30 feet"] == "9 m", champs["range"]["30 feet"]
    assert champs["range"]["1 mile"] == "1,5 km", champs["range"]["1 mile"]
    # ⭐ Et le livre change d'unité quand ça l'arrange : une demi-livre passe en
    # GRAMMES, pas en kilos. Un convertisseur générique aurait écrit `0,25 kg`.
    assert champs["weight"]["1/2 lb."] == "250 g", champs["weight"]["1/2 lb."]
    assert champs["weight"]["3 lb."] == "1,5 kg", champs["weight"]["3 lb."]


def main():
    unit_la_coupure_est_par_valeur_jamais_par_champ()
    unit_la_table_refuse_de_cesser_d_etre_une_fonction()
    unit_une_valeur_absente_crie_au_lieu_de_se_replier()
    acceptance_la_vraie_table_est_une_fonction()
    acceptance_la_table_publiee_est_celle_qui_se_derive()
    acceptance_les_arrondis_sont_ceux_du_livre()
    print("PASS test_convert_units")


if __name__ == "__main__":
    main()
