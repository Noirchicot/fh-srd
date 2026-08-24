"""A weapon's properties as a list, and the proof the conversion lost nothing.

⭐ THE PROOF IS FREE AND IT IS THE POINT: recompose the printed sentence from
the list, and it must come back character for character on all 38 weapons in
both languages. A conversion that can be undone exactly did not lose anything
and did not invent anything.

Run: python3 tests/test_weapon_properties.py
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS = os.path.join(ROOT, "exports", "srd")

sys.path.insert(0, os.path.join(ROOT, "src"))

import french_layer  # noqa: E402

import weapon_properties as W  # noqa: E402


def load(lang, kind):
    """⭐ UNE SEULE LECTURE POUR TOUT LE DÉPÔT — `src/french_layer.py`.
    
    Depuis la transition à froid, `exports/srd/fr/*.json` ne porte plus de
    records mais des PATCHES posés sur les adresses anglaises. Lire `["records"]`
    ici casserait — et si chaque test reconstituait de son côté, les copies
    divergeraient exactement comme divergent toujours deux écritures d'une
    même liste.
    """
    return french_layer.load(EXPORTS, lang, kind)


def unit_the_decimal_comma():
    """🔴 The row that makes depth-aware splitting mandatory, not tidy.

    The French prints a range with a DECIMAL COMMA inside the parenthesis. A
    naive `split(",")` cuts it in half and invents a tenth property called
    "50/30 ; dards)". This is a real row of the real table, not a hypothetical.
    """
    printed = "Chargement, Munitions (portée 7,50/30 ; dards)"
    assert printed.split(",") != W.split_properties(printed)
    assert W.split_properties(printed) == [
        "Chargement", "Munitions (portée 7,50/30 ; dards)"]
    items = W.property_list(printed, "fr")
    assert [i["key"] for i in items] == ["loading", "ammunition"]
    assert items[1]["detail"] == "portée 7,50/30 ; dards"
    print("  ok  a decimal comma inside a parenthesis does not split a property in two")


def unit_three_kinds_of_parenthesis():
    """A die, a range plus an ammunition type, and a plain condition.

    They are not interchangeable, and none of them is the property's name. All
    three are kept verbatim: typing a range means choosing feet or metres and
    parsing a French decimal, which is the typed-field work, not this lot.
    """
    die = W.property_list("Versatile (1d10)", "en")[0]
    assert die["key"] == "versatile" and die["detail"] == "1d10"
    ammo = W.property_list("Ammunition (Range 25/100; Needle)", "en")[0]
    assert ammo["key"] == "ammunition" and ammo["detail"] == "Range 25/100; Needle"
    note = W.property_list("Two-Handed (unless mounted)", "en")[0]
    assert note["key"] == "two-handed" and note["detail"] == "unless mounted"
    bare = W.property_list("Finesse", "en")[0]
    assert bare == {"key": "finesse", "label": "Finesse"}, bare
    print("  ok  a die, a range with an ammo type, and a condition all survive whole")


def unit_no_property_is_an_answer():
    """Three weapons carry none. That is an answer, not a gap."""
    assert W.property_list(None, "en") == []
    assert W.property_list("", "fr") == []
    assert W.recompose([]) is None
    print("  ok  a weapon with no property yields an empty list and no sentence")


def unit_a_tenth_name_is_refused():
    """NEGATIVE CONTROL: the SRD prints a closed set. A name outside it stops."""
    for lang, invented in (("en", "Whirling"), ("fr", "Tournoyante")):
        try:
            W.property_list("Finesse, %s" % invented, lang)
        except W.UnknownProperty as exc:
            assert invented in str(exc), exc
            continue
        raise AssertionError("%r should have been refused in %r" % (invented, lang))
    print("  ok  negative control: a tenth property name is refused, not invented")


def acceptance_recompose_every_weapon():
    """The whole point, on the real exports: 38 and 38, word for word."""
    total = 0
    for lang in ("en", "fr"):
        weapons = load(lang, "weapon")
        assert len(weapons) == 38, (lang, len(weapons))
        for weapon in weapons:
            printed = weapon["data"]["properties"]
            items = weapon["data"]["property_list"]
            assert W.recompose(items) == printed, (lang, weapon["name"], items)
            total += 1
        assert sum(1 for w in weapons if not w["data"]["property_list"]) == 3, lang
    print("  ok  %d weapons recomposed to the exact printed sentence, both languages"
          % total)


def acceptance_keys_are_one_vocabulary():
    """Every key names a `weapon-property` record, and both languages agree.

    ⛔ Two vocabularies for the same thing is the failure this prevents: the
    genre already carries each property's DEFINITION, and a list whose keys did
    not land on it would be a second, silent naming of the same nine things.
    """
    for lang in ("en", "fr"):
        records = {r["name"] for r in load(lang, "weapon-property")}
        assert set(W.PROPERTY_KEYS[lang]) == records, (
            lang, sorted(set(W.PROPERTY_KEYS[lang]) ^ records))
        used = {i["key"] for w in load(lang, "weapon") for i in w["data"]["property_list"]}
        assert used <= set(W.PROPERTY_KEYS[lang].values()), (lang, used)

    en_keys = {i["key"] for w in load("en", "weapon") for i in w["data"]["property_list"]}
    fr_keys = {i["key"] for w in load("fr", "weapon") for i in w["data"]["property_list"]}
    assert en_keys == fr_keys, sorted(en_keys ^ fr_keys)
    assert len(en_keys) == 9, sorted(en_keys)
    print("  ok  9 keys, identical on both sides, every one a weapon-property record")


def acceptance_the_declared_table_agrees_with_the_computed_pairing():
    """⭐ The declared French table, checked against a route that never read it.

    `PROPERTY_KEYS["fr"]` is a translation written by hand, which is exactly the
    kind of thing this repository refuses to take on trust. The correspondence
    layer pairs the eleven `weapon-property` records by OCCURRENCE PROFILE --
    which weapons carry each one -- reading no name and no table. If the two
    disagree anywhere, the hand-written half is wrong.
    """
    with open(os.path.join(EXPORTS, "correspondence.json"), encoding="utf-8") as fh:
        pairs = json.load(fh)["pairs"]
    en_names = {r["id"]: r["name"] for r in load("en", "weapon-property")}
    fr_names = {r["id"]: r["name"] for r in load("fr", "weapon-property")}

    # 🔴 LA MÉCANIQUE A CHANGÉ AU LOT 105, ET ELLE S'EST RENFORCÉE. Ce bloc
    # suivait la table de correspondance pour retrouver le jumeau français.
    # Depuis la transition à froid, les deux records vivent À LA MÊME ADRESSE :
    # l'appariement n'est plus une table à consulter, c'est l'identifiant.
    # ⭐ La table déclarée `PROPERTY_KEYS` est donc vérifiée par quelque chose
    # qui ne l'a jamais lue — l'adresse partagée — au lieu de l'être par une
    # autre table.
    checked = 0
    for rid, nom_en in en_names.items():
        nom_fr = fr_names.get(rid)
        if nom_fr is None:
            continue
        mine_en = W.PROPERTY_KEYS["en"].get(nom_en)
        mine_fr = W.PROPERTY_KEYS["fr"].get(nom_fr)
        assert mine_en is not None and mine_en == mine_fr, (
            "à l'adresse %s le livre imprime %r et %r ; la table déclarée dit "
            "%r et %r" % (rid, nom_en, nom_fr, mine_en, mine_fr))
        checked += 1
    assert checked >= 9, "only %d property pairs to check against" % checked
    print("  ok  %d property pairs: the hand-written table and the occurrence "
          "profile agree, with nothing in between" % checked)


def acceptance_une_clef_de_propriete_ne_se_traduit_jamais():
    """🔴 LE CAS OÙ L'EMBRANCHEMENT POURRAIT REVENIR SANS QU'ON LE VOIE.

    `weapon.property_list` est le seul champ du corpus qui porte, DANS LE MÊME
    OBJET, une clef et un mot : `{"key": "two-handed", "label": "Deux mains"}`.
    C'est le patron que le lot 92 a posé et que le lot 98 a généralisé — et
    c'est aussi le seul endroit où une clef peut redevenir française sans
    qu'aucun compte ne bouge : la liste garderait sa longueur, ses libellés,
    son ordre.

    ➡️ À la même adresse, les `key` doivent être IDENTIQUES des deux côtés, et
    seuls `label` et `detail` ont le droit de différer. ⭐ C'est l'invariant du
    lot 104 dit sur le cas le plus fin qui existe dans la donnée.
    """
    en = {r["id"]: r["data"] for r in load("en", "weapon")}
    fr = {r["id"]: r["data"] for r in load("fr", "weapon")}
    vus = 0
    mots = 0
    for rid, a in en.items():
        b = fr.get(rid)
        if b is None:
            continue
        la, lb = a.get("property_list") or [], b.get("property_list") or []
        # 🔴 PAR LA CLEF, JAMAIS PAR LA POSITION — et j'ai écrit `zip` en
        # premier jet, dans le garde même qui existe pour attraper ça. Le
        # français imprime ses propriétés dans SON alphabet (« Chargement,
        # Munitions » là où l'anglais met « Ammunition, Loading »), donc les
        # deux listes ne se correspondent pas rang par rang. L'ORDRE MENT ;
        # l'appartenance, non. C'est la quatrième fois dans ce chantier.
        par_clef_en = {x["key"]: x for x in la}
        par_clef_fr = {y["key"]: y for y in lb}
        assert set(par_clef_en) == set(par_clef_fr), (
            "à l'adresse %s les clefs de propriété diffèrent — anglais %s, "
            "français %s. Une clef traduite ferait revenir l'embranchement là "
            "où rien ne le compterait."
            % (rid, sorted(par_clef_en), sorted(par_clef_fr)))
        assert len(par_clef_en) == len(la) == len(lb), (
            "%s : une clef de propriété est portée deux fois" % rid)
        for clef, x in par_clef_en.items():
            vus += 1
            if x.get("label") != par_clef_fr[clef].get("label"):
                mots += 1
    assert vus >= 30, vus
    assert mots >= 20, (
        "les libellés ne diffèrent presque plus (%d sur %d) — soit le français "
        "a disparu, soit ce test ne regarde plus rien" % (mots, vus))
    print("  ok  %d clefs de propriété identiques des deux côtés, %d libellés "
          "français distincts — une clef, deux mots" % (vus, mots))


def main():
    unit_the_decimal_comma()
    unit_three_kinds_of_parenthesis()
    unit_no_property_is_an_answer()
    unit_a_tenth_name_is_refused()
    acceptance_recompose_every_weapon()
    acceptance_keys_are_one_vocabulary()
    acceptance_the_declared_table_agrees_with_the_computed_pairing()
    acceptance_une_clef_de_propriete_ne_se_traduit_jamais()
    print("PASS test_weapon_properties")


if __name__ == "__main__":
    main()
