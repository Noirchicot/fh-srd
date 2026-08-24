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

    checked = 0
    for pair in pairs:
        if pair["en"] not in en_names or pair["fr"] not in fr_names:
            continue
        mine_en = W.PROPERTY_KEYS["en"].get(en_names[pair["en"]])
        mine_fr = W.PROPERTY_KEYS["fr"].get(fr_names[pair["fr"]])
        assert mine_en is not None and mine_en == mine_fr, (
            "the computed pairing says %s = %s; the declared table says %r and %r"
            % (en_names[pair["en"]], fr_names[pair["fr"]], mine_en, mine_fr))
        checked += 1
    assert checked >= 9, "only %d property pairs to check against" % checked
    print("  ok  %d property pairs: the hand-written table and the occurrence "
          "profile agree, with nothing in between" % checked)


def main():
    unit_the_decimal_comma()
    unit_three_kinds_of_parenthesis()
    unit_no_property_is_an_answer()
    unit_a_tenth_name_is_refused()
    acceptance_recompose_every_weapon()
    acceptance_keys_are_one_vocabulary()
    acceptance_the_declared_table_agrees_with_the_computed_pairing()
    print("PASS test_weapon_properties")


if __name__ == "__main__":
    main()
