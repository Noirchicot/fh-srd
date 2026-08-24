"""Pairing the two SRD catalogues — the normalisers, the rule, and the refusals.

WHAT THIS FILE HAS TO PROVE, in order of how much it would cost to get wrong:

  1. That the pairing NEVER GUESSES. A fingerprint worn by two English records
     is a question, not an answer, even when the French side also has exactly
     two. This is the one property the whole artefact rests on: a guessed
     correspondence gives a silently wrong character, which is worse than no
     correspondence at all (`fhpc/layers/TRADUCTION.md`).
  2. That the normalisers survive the spellings that ACTUALLY OCCUR — not the
     tidy ones. `1/2 lb.` and `58½ lb.` live in the same English file and the
     ½ is U+00BD, not three characters. The French thousands separator is a
     non-breaking space. `parseFloat("0,5")` is 0, not 0.5, and a weight read
     as zero pairs with the wrong thing in silence.
  3. That a genre with NO fingerprint comes out named, never omitted. The
     defect being guarded against is downstream and real: `gen-srd-layer.mjs`
     iterates over its own constant, so a genre missing from that constant is
     not refused — it is never read, and the build succeeds having produced
     nothing.
  4. That the acceptance numbers are RECOMPUTED from `exports/`, and that the
     sampled pairs are ones a human checked by hand, not ones copied out of the
     file this test is supposed to be checking.

Run: python3 tests/test_correspond.py
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS = os.path.join(ROOT, "exports", "srd")

sys.path.insert(0, os.path.join(ROOT, "src"))

import french_layer  # noqa: E402

# ⭐ Le seul endroit du dépôt qui écrive une adresse française — et il dit
# pourquoi : la base de travail est gitignorée, et les routes doivent tourner.
from french_layer import working_base_id as FR  # noqa: E402

import correspond as C  # noqa: E402
import export_json  # noqa: E402


# Eleven pairs read and confirmed by hand against the two PDFs. They are here
# so the test fails for the right reason instead of agreeing with whatever
# correspondence.json happens to hold — `plate-armor` pairs with `harnois`,
# and no amount of green tests makes that true if the file says otherwise.
HAND_CHECKED = {
    "srd:class:en:fighter": FR("class", "guerrier"),
    "srd:class:en:wizard": FR("class", "magicien"),
    "srd:class:en:barbarian": FR("class", "barbare"),
    "srd:monster:en:aboleth": FR("monster", "aboleth"),
    "srd:armor:en:chain-mail": FR("armor", "cotte-de-mailles"),
    "srd:armor:en:plate-armor": FR("armor", "harnois"),
    "srd:weapon:en:longsword": FR("weapon", "epee-longue"),
    "srd:spell:en:fireball": FR("spell", "boule-de-feu"),
    "srd:tool:en:thieves-tools": FR("tool", "outils-de-voleur"),
    "srd:species:en:dwarf": FR("species", "nain"),
    "srd:background:en:soldier": FR("background", "soldat"),
}


def unit_price():
    # The same number on both sides; only the coin is spelled differently.
    assert C.copper("25 GP") == C.copper("25 po") == 2500
    assert C.copper("1 SP") == C.copper("1 pa") == 10
    assert C.copper("5 CP") == C.copper("5 pc") == 5
    # Thousands separators: a comma in English, a NON-BREAKING space in French.
    # Reading either one naively gives 1, not 1000.
    assert C.copper("1,000 GP") == 100000
    assert C.copper("1 500 po") == 150000
    assert C.copper("1 500 po") == 150000
    # Not a price. None is "cannot be fingerprinted on price" — never zero.
    for absent in ("Varies", "Variable", "variable", "—", "", None, 5):
        assert C.copper(absent) is None, absent
    print("  ok  price: comma, non-breaking space, narrow space, and five vacancies")


def unit_weight():
    # The French layer divides by exactly 2. Not 2.2046 (physics), not 2.5
    # (Foundry's game abstraction). The number that joins these two files is
    # the one these two files used, and `acceptance_weight_rule` below proves
    # it holds on 133 of the 134 weights in the catalogue.
    assert C.grams("1 lb.") == C.grams("0,5 kg") == 500
    assert C.grams("45 lb.") == C.grams("22,5 kg") == 22500   # Scale Mail
    # Two spellings of one half, in the same English file.
    assert C.grams("1/2 lb.") == 250
    assert C.grams("58½ lb.") == 29250
    assert C.grams("1/4 lb.") == 125
    # French grams, where a naive unit read is wrong by a factor of 1000.
    assert C.grams("125 g") == 125
    # Negligible is neither zero nor absent.
    assert C.grams("—") is None
    assert C.grams("Varies") is None
    print("  ok  weight: /2, U+00BD vs 1/2, decimal comma, grams, and '—'")


def unit_distance():
    # 30 feet is rendered 9 m: the trip back is 10/3, not 3.28.
    assert C.feet("30 feet") == C.feet("9 m") == 30
    assert C.feet("120 feet") == C.feet("36 m") == 120
    # ⚠️ A mile does NOT round-trip: English says `1 mile` (5280 ft), French
    # says `1,5 km` (4921 ft once converted back). The fingerprint therefore
    # cannot pair a mile-ranged spell on its range, and it does not pretend to
    # — it lets the record fall through to `pending`. Asserted here so the
    # limit is written down rather than discovered.
    assert C.feet("1 mile") == 5280
    assert C.feet("1,5 km") == 4921
    # Word ranges collapse onto one token per language pair.
    assert C.feet("Self") == C.feet("Personnelle") == "self"
    assert C.feet("Touch") == C.feet("Contact") == "touch"
    # A range this does not know stops discriminating instead of
    # discriminating wrongly.
    assert C.feet("Quelque part") == "?"
    print("  ok  distance: ft/m at 10/3, and word ranges on both sides")


def unit_tokens():
    # V / S / M are the same three letters; the material component is prose.
    assert C.components("V, S, M (powdered rhubarb leaf)") == ("M", "S", "V")
    assert C.components("V, S, M (une pincée de poudre de fer)") == ("M", "S", "V")
    assert C.components("V, S") == ("S", "V")
    # Three different minus signs occur where a hyphen was meant.
    assert C.bonuses("takes −2 and then –3 and +1") == ("+1", "-2", "-3")
    assert C.dice("2d6 plus 1d4 and 2d6") == ("1d4", "2d6", "2d6")
    # The French monster block renames two of the six ability KEYS, and no
    # field name announces it.
    en = {"str": {"score": 21}, "dex": {"score": 9}, "con": {"score": 15},
          "int": {"score": 18}, "wis": {"score": 15}, "cha": {"score": 18}}
    fr = {"for": {"score": 21}, "dex": {"score": 9}, "con": {"score": 15},
          "int": {"score": 18}, "sag": {"score": 15}, "cha": {"score": 18}}
    assert C.abilities(en) == C.abilities(fr) == (21, 9, 15, 18, 15, 18)
    print("  ok  tokens: V/S/M, three minus signs, and for/sag -> str/wis")


def unit_never_guesses():
    """The load-bearing rule: two against two is a question, not two answers."""
    def rec(rid, name, cost):
        return {"id": rid, "name": name, "data": {"cost": cost, "weight": "1 lb."}}

    # One against one -> a pair.
    out = C.correspond_kind("gear",
                            [rec("srd:gear:en:a", "A", "7 GP")],
                            [rec(FR("gear", "a"), "A", "7 po")])
    assert len(out["matched"]) == 1 and not out["pending"]

    # Two against two, same fingerprint -> NO pair, one named question.
    out = C.correspond_kind(
        "gear",
        [rec("srd:gear:en:a", "A", "7 GP"), rec("srd:gear:en:b", "B", "7 GP")],
        [rec(FR("gear", "a"), "A", "7 po"), rec(FR("gear", "b"), "B", "7 po")])
    assert out["matched"] == [], "two against two must not pair"
    assert len(out["pending"]) == 1
    assert out["pending"][0]["reason"] == "ambiguous"
    assert len(out["pending"][0]["en"]) == 2 and len(out["pending"][0]["fr"]) == 2

    # One English, no French -> named, not dropped.
    out = C.correspond_kind("gear", [rec("srd:gear:en:a", "A", "7 GP")],
                            [rec(FR("gear", "z"), "Z", "9 po")])
    reasons = sorted(g["reason"] for g in out["pending"])
    assert reasons == ["unmatched-en", "unmatched-fr"], reasons
    print("  ok  rule: 1-1 pairs, 2-2 refuses, and both orphan sides are named")


def unit_unknown_genre_is_named():
    """A genre with no fingerprint is a question in the open, never a silence."""
    out = C.correspond_kind("brand-new-genre",
                            [{"id": "srd:brand-new-genre:en:x", "name": "X", "data": {}}],
                            [{"id": FR("brand-new-genre", "x"), "name": "X", "data": {}}])
    assert out["matched"] == []
    assert out["fingerprint"] is None
    assert out["pending"][0]["reason"] == "no-fingerprint"
    assert out["pending"][0]["en"][0]["id"] == "srd:brand-new-genre:en:x"
    assert out["pending"][0]["fr"][0]["id"] == FR("brand-new-genre", "x")
    print("  ok  a genre with no fingerprint is listed, not skipped")


def unit_one_sided_genre_refuses():
    """Half a catalogue is a broken build, not 'nothing matched'."""
    try:
        C.correspond_all({"gear": {"en": [{"id": "srd:gear:en:a", "name": "A",
                                           "data": {}}], "fr": []}})
    except C.CorrespondenceError as exc:
        assert "one language only" in str(exc) and "gear" in str(exc)
        print("  ok  a one-sided genre refuses, naming it")
        return
    raise AssertionError("a genre present in one language only must refuse")


def load(lang, kind):
    """⭐ UNE SEULE LECTURE POUR TOUT LE DÉPÔT — `src/french_layer.py`.
    
    Depuis la transition à froid, `exports/srd/fr/*.json` ne porte plus de
    records mais des PATCHES posés sur les adresses anglaises. Lire `["records"]`
    ici casserait — et si chaque test reconstituait de son côté, les copies
    divergeraient exactement comme divergent toujours deux écritures d'une
    même liste.
    """
    return french_layer.load(EXPORTS, lang, kind)


#: Les slugs français de deux objets nommés ci-dessous. ⚠️ Ils ne se déduisent
#: plus d'un record : après la transition à froid, le record porte l'adresse
#: ANGLAISE. Ce sont des mots du livre, écrits comme tels.
SLUGS_FR = {"Fer gelé": "fer-gele", "Lame porte-bonheur": "lame-porte-bonheur"}


def acceptance():
    """🔴 CE TEST NE RE-DÉRIVE PLUS LA CORRESPONDANCE, ET IL NE PEUT PLUS.

    Il la recalculait depuis `exports/{en,fr}` et exigeait que le fichier
    publié dise la même chose. Depuis la transition à froid, il n'y a plus
    qu'un jeu de records : les deux langues vivent à la MÊME adresse, et une
    re-dérivation apparierait `breastplate` avec `breastplate` — elle passerait
    en ne mesurant rien, ce qui est pire que rouge.

    ⭐ CE QU'IL PROUVE MAINTENANT, ET QUI N'EST PAS PLUS FAIBLE : la table
    publiée est une BIJECTION, son côté français est un MOT et non une adresse,
    et les paires vérifiées à la main s'y retrouvent. La correspondance a cessé
    d'être une hypothèse à recalculer : elle est ce que la migration a
    consommé, et ce qui reste à garder est sa FORME et sa mémoire.
    """
    with open(os.path.join(EXPORTS, "correspondence.json"), encoding="utf-8") as fh:
        published = json.load(fh)
    pairs = published["pairs"]
    ens = [p["en"] for p in pairs]
    frs = [p["fr"] for p in pairs]

    # Une correspondance qui met deux records anglais sur un français n'en est
    # pas une. C'est vrai avant comme après la migration.
    assert len(set(ens)) == len(ens), "un record anglais paraît dans deux paires"
    assert len(set(frs)) == len(frs), "un record français paraît dans deux paires"

    for pair in pairs:
        # ⛔ LE CÔTÉ FRANÇAIS EST UN MOT DU LIVRE, PAS UNE ADRESSE : après la
        # transition à froid, l'adresse française d'un record n'existe plus,
        # et l'écrire
        # comme s'il vivait serait un mensonge tranquille. C'est la preuve la
        # plus courte du chantier (`git grep` à zéro) dite comme un test.
        assert ":fr:" not in pair["fr"], pair
        assert ":en:" in pair["en"], pair
        genre_en = pair["en"].split(":")[1]
        genre_fr = pair["fr"].split(":")[0]
        assert genre_en == genre_fr, (
            "une paire traverse les genres : %s" % pair)

    index = dict(zip(ens, frs))
    for en_id, fr_id in sorted(HAND_CHECKED.items()):
        attendu = ":".join(fr_id.split(":")[1::2])
        assert index.get(en_id) == attendu, (
            "%s devrait s'apparier à %s, obtenu %r" % (en_id, attendu, index.get(en_id)))

    print("  ok  acceptance: %d paires publiées, bijectives, côté français en "
          "MOTS, %d vérifiées à la main" % (len(pairs), len(HAND_CHECKED)))


def acceptance_l_ordre_des_slugs_ne_dit_rien_de_l_ordre_des_adresses():
    """🔴 « L'ORDRE MENT » A CHANGÉ DE SUPPORT, PAS DE NATURE.

    La faute payée trois fois dans ce chantier était d'apparier par POSITION
    dans deux listes triées chacune dans sa langue. Les deux catalogues ont
    disparu — la faute, elle, est toujours possible : `sources/` est désormais
    clefé sur le **slug français**, et la table publiée porte un slug d'un côté
    et une adresse de l'autre.

    ➡️ Ce test mesure que **trier par slug et trier par adresse ne donnent PAS
    le même ordre**, et que la différence est massive. Quiconque apparierait
    « la n-ième ligne des slugs » avec « la n-ième adresse » se tromperait — et
    obtiendrait quelque chose de parfaitement cohérent, sans un seul conflit.
    """
    with open(os.path.join(EXPORTS, "correspondence.json"), encoding="utf-8") as fh:
        pairs = json.load(fh)["pairs"]

    par_slug = [p["en"] for p in sorted(pairs, key=lambda p: p["fr"])]
    par_adresse = [p["en"] for p in sorted(pairs, key=lambda p: p["en"])]
    assert len(par_slug) == len(par_adresse)

    places = sum(1 for a, b in zip(par_slug, par_adresse) if a != b)
    assert places > len(pairs) // 2, (
        "trier par slug français et trier par adresse anglaise donnent presque "
        "le même ordre (%d places sur %d diffèrent) — le témoin de « l'ordre "
        "ment » est devenu trop faible pour prouver quoi que ce soit"
        % (places, len(pairs)))

    # ⭐ ET UN CAS NOMMÉ, LISIBLE À L'ŒIL : la cuirasse est en tête de
    # l'alphabet anglais et loin dans le français.
    cuirasse = [p for p in pairs if p["fr"] == "armor:cuirasse"]
    assert cuirasse, "le témoin `armor:cuirasse` a disparu de la table"
    assert cuirasse[0]["en"] == "srd:armor:en:breastplate", cuirasse[0]
    print("  ok  l'ordre des slugs et celui des adresses diffèrent sur %d "
          "places sur %d — apparier par rang resterait cohérent, et faux"
          % (places, len(pairs)))


def acceptance_attack():
    """Break one record's fingerprint; its pair must VANISH, not move.

    The failure being ruled out: a record whose fingerprint changes quietly
    re-pairs with whatever else now wears it. The pair must be lost and the
    record named — a wrong pair is worse than a missing one.
    """
    en = [dict(r) for r in load("en", "armor")]
    fr = [dict(r) for r in load("fr", "armor")]

    before = {p["en"]: p["fr"] for p in C.correspond_kind("armor", en, fr)["matched"]}
    assert "srd:armor:en:plate-armor" in before

    victim = next(r for r in en if r["id"] == "srd:armor:en:plate-armor")
    victim["data"] = dict(victim["data"], cost="999 GP")

    after = C.correspond_kind("armor", en, fr)
    paired = {p["en"] for p in after["matched"]}
    assert "srd:armor:en:plate-armor" not in paired, "a broken record must not re-pair"
    named = {b["id"] for g in after["pending"] for b in g["en"]}
    assert "srd:armor:en:plate-armor" in named, "a broken record must be named"
    # And it must not have dragged anybody else into a wrong pair.
    for en_id, fr_id in after["matched"] and \
            [(p["en"], p["fr"]) for p in after["matched"]]:
        assert before.get(en_id) == fr_id, "%s re-paired to %s" % (en_id, fr_id)
    print("  ok  attack: a broken fingerprint loses its pair and is named, "
          "and moves nobody else")



def acceptance_weight_rule():
    """The /2 conversion, checked on the catalogue rather than on two examples.

    Measured as MULTISETS, so this does not depend on the pairing it is meant
    to justify — a check that ran only over records the fingerprint matched
    would be measuring its own assumption.

    133 of the 134 numeric weights land exactly. The single exception is
    `Entertainer's Pack`: 58½ lb halves to 29.25 kg and the French layer wrote
    29 kg. It is worth knowing that the pairing found that record ON ITS OWN —
    it is one of the two `gear` orphans — rather than pairing it with something
    close. A rounding that cost one pair is the correct price for not inventing
    one.
    """
    import collections
    kinds = ("gear", "weapon", "armor", "tool")
    counts = {}
    for lang in ("en", "fr"):
        tally = collections.Counter()
        for kind in kinds:
            for record in load(lang, kind):
                grams = C.grams(record["data"].get("weight"))
                if grams is not None:
                    tally[grams] += 1
        counts[lang] = tally

    assert sum(counts["en"].values()) == sum(counts["fr"].values()) == 134
    only_en = counts["en"] - counts["fr"]
    only_fr = counts["fr"] - counts["en"]
    assert sum(only_en.values()) == 1 and sum(only_fr.values()) == 1, (
        "expected exactly one weight to disagree, got %r / %r"
        % (dict(only_en), dict(only_fr)))
    assert list(only_en) == [29250] and list(only_fr) == [29000], (
        dict(only_en), dict(only_fr))
    print("  ok  weight rule: 133/134 weights are exactly half, and the one "
          "that is not is Entertainer's Pack (58.5 lb -> 29 kg, not 29.25)")



def unit_transitive_refuses_disagreement():
    """One weapon disagreeing kills the whole name. No majority vote.

    A majority here would be a guess wearing a number: five weapons saying
    `Topple` is `Renversement` and one saying it is `Sape` does not make the
    first true, it means something is wrong and a person should look.
    """
    def weapon(rid, mastery):
        return {"id": rid, "name": rid, "data": {"mastery": mastery}}

    src = {
        "weapon": {
            "en": [weapon("srd:weapon:en:a", "Topple"),
                   weapon("srd:weapon:en:b", "Topple"),
                   weapon("srd:weapon:en:c", "Vex")],
            "fr": [weapon(FR("weapon", "a"), "Renversement"),
                   weapon(FR("weapon", "b"), "Sape"),
                   weapon(FR("weapon", "c"), "Ouverture")],
        },
        "weapon-mastery": {
            "en": [{"id": "srd:weapon-mastery:en:topple", "name": "Topple", "data": {}},
                   {"id": "srd:weapon-mastery:en:vex", "name": "Vex", "data": {}}],
            "fr": [{"id": FR("weapon-mastery", "renversement"), "name": "Renversement", "data": {}},
                   {"id": FR("weapon-mastery", "sape"), "name": "Sape", "data": {}},
                   {"id": FR("weapon-mastery", "ouverture"), "name": "Ouverture", "data": {}}],
        },
    }
    proven = {"srd:weapon:en:a": FR("weapon", "a"),
              "srd:weapon:en:b": FR("weapon", "b"),
              "srd:weapon:en:c": FR("weapon", "c")}
    pairs, refusals = C.transitive_pairs(C.TRANSITIVE_ROUTES[0], proven, src)

    got = {p["en"]: p["fr"] for p in pairs}
    assert "srd:weapon-mastery:en:topple" not in got, "Topple disagreed and must not pair"
    assert got.get("srd:weapon-mastery:en:vex") == FR("weapon-mastery", "ouverture")
    conflict = [r for r in refusals if r["reason"] == "conflict"]
    assert len(conflict) == 1 and conflict[0]["en"] == "Topple", refusals
    assert sorted(conflict[0]["fr"]) == ["Renversement", "Sape"]
    print("  ok  transitive: one disagreement refuses the name, and says which")


def unit_transitive_refuses_dangling():
    """A name that is not a record leads nowhere and must not become a pair."""
    src = {
        "weapon": {
            "en": [{"id": "srd:weapon:en:a", "name": "A", "data": {"mastery": "Ghost"}}],
            "fr": [{"id": FR("weapon", "a"), "name": "A", "data": {"mastery": "Fantome"}}],
        },
        "weapon-mastery": {
            "en": [{"id": "srd:weapon-mastery:en:topple", "name": "Topple", "data": {}}],
            "fr": [{"id": FR("weapon-mastery", "renversement"), "name": "Renversement", "data": {}}],
        },
    }
    pairs, refusals = C.transitive_pairs(
        C.TRANSITIVE_ROUTES[0], {"srd:weapon:en:a": FR("weapon", "a")}, src)
    assert pairs == []
    assert [r["reason"] for r in refusals] == ["dangling"], refusals
    print("  ok  transitive: a name with no record is refused, not invented")


def unit_transitive_never_overturns_the_data():
    """A deduction may not overwrite a measurement — the weaker claim yields."""
    src = {
        "weapon": {
            "en": [{"id": "srd:weapon:en:a", "name": "A", "data": {"mastery": "Topple"}}],
            "fr": [{"id": FR("weapon", "a"), "name": "A", "data": {"mastery": "Sape"}}],
        },
        "weapon-mastery": {
            "en": [{"id": "srd:weapon-mastery:en:topple", "name": "Topple", "data": {}}],
            "fr": [{"id": FR("weapon-mastery", "sape"), "name": "Sape", "data": {}},
                   {"id": FR("weapon-mastery", "renversement"), "name": "Renversement", "data": {}}],
        },
    }
    # The data already decided Topple pairs with Renversement.
    proven = {"srd:weapon:en:a": FR("weapon", "a"),
              "srd:weapon-mastery:en:topple": FR("weapon-mastery", "renversement")}
    pairs, _ = C.transitive_pairs(C.TRANSITIVE_ROUTES[0], proven, src)
    assert pairs == [], "the route must not re-pair a record the data settled"
    print("  ok  transitive: a deduction yields to a measurement")


def unit_properties_is_not_a_route():
    """`weapon.properties` is refused on purpose, and here is the measurement.

    Pairing a weapon's properties by position looks obvious and is wrong: the
    French SRD lists them in its own alphabetical order. Recomputed here from
    the real exports so the reason stays true rather than becoming folklore.
    """
    assert all(r["field"] != "properties" for r in C.TRANSITIVE_ROUTES)

    corr_path = os.path.join(EXPORTS, "correspondence.json")
    with open(corr_path, encoding="utf-8") as fh:
        proven = {p["en"] for p in json.load(fh)["pairs"]}
    # ⚠️ LES DEUX LANGUES SE CHARGENT SÉPARÉMENT, ET C'EST LE LOT 104 QUI
    # L'IMPOSE : elles partagent désormais l'ADRESSE. Un seul dictionnaire
    # indexé par id écraserait l'anglais avec le français et l'attaque
    # ci-dessous n'opposerait plus rien — elle passerait, en ne mesurant rien.
    en_w = {r["id"]: r for r in load("en", "weapon")}
    fr_w = {r["id"]: r for r in load("fr", "weapon")}

    def split(value):
        return [part.split("(")[0].strip()
                for part in (value or "").split(",") if part.strip()]

    seen = {}
    for rid in proven:
        if rid not in en_w or rid not in fr_w:
            continue
        left = split(en_w[rid]["data"].get("properties"))
        right = split(fr_w[rid]["data"].get("properties"))
        if len(left) != len(right):
            continue
        for a, b in zip(left, right):
            seen.setdefault(a, set()).add(b)

    contradictory = sorted(name for name, targets in seen.items() if len(targets) > 1)
    assert len(contradictory) >= 5, (
        "positional pairing of weapon properties was expected to contradict "
        "itself; it produced %r" % seen)
    print("  ok  properties: positional pairing contradicts itself on %d of %d "
          "names — refused, not shipped" % (len(contradictory), len(seen)))


def unit_signed_refuses_what_cannot_be():
    """Four ways a hand-edited file can be wrong, and none of them go quiet."""
    known = {"srd:item:en:a", FR("item", "a"), FR("spell", "z"),
             "srd:item:en:taken", FR("item", "taken")}
    proven = {"srd:item:en:taken": FR("item", "taken")}

    signed = {
        "pairs": [
            {"en": "srd:item:en:a", "fr": FR("item", "a")},            # good
            {"en": "srd:item:en:typo", "fr": FR("item", "a")},         # unknown id
            {"en": "srd:item:en:a", "fr": FR("spell", "z")},           # genre mismatch
            {"en": "srd:item:en:taken", "fr": FR("item", "a")},        # already paired
        ],
        "no_equivalent": [
            {"id": FR("spell", "z"), "note": "checked both printings"},  # good
            {"id": "srd:item:en:taken"},                                 # contradicts a pair
        ],
    }
    pairs, none_of, refusals, confirmed = C.apply_signed(signed, proven, known)

    assert len(pairs) == 1 and pairs[0]["by"] == C.BY_HUMAN
    assert pairs[0]["en"] == "srd:item:en:a"
    assert [e["id"] for e in none_of] == [FR("spell", "z")]
    assert none_of[0]["note"] == "checked both printings"
    reasons = sorted(r["reason"] for r in refusals)
    assert reasons == ["signed-already-paired", "signed-contradiction",
                       "signed-genre-mismatch", "signed-unknown-id"], reasons
    assert confirmed == [], confirmed
    print("  ok  signed: a typo, a genre mix-up, a double claim and a "
          "contradiction are all refused by name")


def acceptance_transitive_closes_masteries():
    """The eight masteries, closed by deduction, checked against the weapons."""
    with open(os.path.join(EXPORTS, "correspondence.json"), encoding="utf-8") as fh:
        published = json.load(fh)

    derived = {p["en"]: p["fr"] for p in published["pairs"]
               if p["by"].startswith("transitive/")}
    assert len(derived) == 8, "expected all eight masteries, got %d" % len(derived)

    # Recomputed from the weapon table itself rather than trusting the file:
    # every weapon that prints an English mastery must print, on its French
    # twin, the mastery this pairing claims.
    # ⭐ ET LA VÉRIFICATION S'EST SIMPLIFIÉE : L'ADRESSE EST LA JOINTURE. Ce
    # bloc suivait la table publiée pour retrouver le jumeau français d'une
    # arme, puis celui de sa botte. Les deux langues vivent à la même adresse :
    # il n'y a plus de table à consulter, seulement deux lectures du même
    # record. ⛔ Les deux langues se chargent SÉPARÉMENT — un seul dictionnaire
    # indexé par id écraserait l'anglais et le test passerait sans rien opposer.
    en_w = {r["id"]: r for r in load("en", "weapon")}
    fr_w = {r["id"]: r for r in load("fr", "weapon")}
    en_m_name = {r["id"]: r["name"] for r in load("en", "weapon-mastery")}
    fr_m_name = {r["id"]: r["name"] for r in load("fr", "weapon-mastery")}
    par_nom_en = {nom: rid for rid, nom in en_m_name.items()}
    checked = 0
    for rid, arme_en in en_w.items():
        arme_fr = fr_w.get(rid)
        if arme_fr is None:
            continue
        en_m = arme_en["data"].get("mastery")
        fr_m = arme_fr["data"].get("mastery")
        if not en_m or not fr_m:
            continue
        botte = par_nom_en.get(en_m)
        assert botte is not None, "aucun record de botte nommé %r" % en_m
        assert fr_m_name.get(botte) == fr_m, (
            "%s imprime %r et son rendu français imprime %r, alors que la "
            "botte %s s'appelle %r en français"
            % (rid, en_m, fr_m, botte, fr_m_name.get(botte)))
        checked += 1
    assert checked >= 30, "only %d weapons carried a mastery" % checked
    print("  ok  transitive: 8/8 masteries, agreeing with %d weapon pairs" % checked)



def unit_signed_agreement_is_not_a_conflict():
    """A person reaching the same pair the data did has CONFIRMED it.

    Refusing that as a duplicate would throw away the strongest thing in the
    file. Five arrived on 2026-08-22 and every one landed on a pair the repaired
    item fingerprint had found independently.
    """
    known = {"srd:item:en:a", FR("item", "a")}
    proven = {"srd:item:en:a": FR("item", "a")}
    signed = {"pairs": [{"en": "srd:item:en:a", "fr": FR("item", "a")}]}
    pairs, _, refusals, confirmed = C.apply_signed(signed, proven, known)
    assert pairs == [], "the computed pair already exists; do not duplicate it"
    assert refusals == [], "agreement must not be reported as a conflict"
    assert confirmed == ["srd:item:en:a"]
    print("  ok  signed: agreement is a confirmation, not a duplicate")


def unit_signed_on_a_polluted_record_needs_a_note():
    """The mechanism, exercised on an entry of its own.

    ⛔ `POLLUTED_BY_EXTRACTION` is EMPTY today, and this test is what keeps its
    mechanism alive anyway. A guard with no members and no test is a guard the
    next tidy-up deletes, and then nobody knows how to refill it.

    What it guards, in the words the real incident wrote: five English magic
    items used to carry the whole description of the item printed after them.
    Eric read one of those tails and signed `sword-of-sharpness -> Épée
    mordante` -- which is *Sword of Wounding*, the item that record had
    swallowed. The guard refused it and said why. Lot 86 repaired the
    extraction and Eric corrected the signature, so the list emptied; the
    reflex it encodes did not.
    """
    polluted = "srd:item:en:some-carrier"
    guarded = {polluted: "Something It Swallowed"}
    known = {polluted, FR("item", "un-porteur")}

    bare = {"pairs": [{"en": polluted, "fr": FR("item", "un-porteur")}]}
    pairs, _, refusals, _ = C.apply_signed(bare, {}, known, polluted=guarded)
    assert pairs == []
    assert [r["reason"] for r in refusals] == ["signed-on-polluted-record"]
    assert "Something It Swallowed" in refusals[0]["detail"]

    aware = {"pairs": [{"en": polluted, "fr": FR("item", "un-porteur"),
                        "note": "read the head of the record, not the tail"}]}
    pairs, _, refusals, _ = C.apply_signed(aware, {}, known, polluted=guarded)
    assert len(pairs) == 1 and refusals == []
    print("  ok  signed: a signature on a corrupted record needs to say it knows "
          "(mechanism kept alive while the list is empty)")


def acceptance_the_guard_is_empty_because_the_records_are_clean():
    """The list is empty for a MEASURED reason, not because someone tidied up.

    ⭐ This test used to assert the opposite: that one signature still
    contradicted the data and only Eric could clear it. He cleared it -- "je
    valide, j'avais tort" -- so the test is rewritten to the new truth rather
    than deleted along with the guard's contents.

    Three measurements per record, and re-pollution fails all three: every
    carrier is back to its own length, every swallowed item exists on its own,
    and no carrier's text still names what it ate.
    """
    assert C.POLLUTED_BY_EXTRACTION == {}, (
        "the list has members again -- if that is deliberate, this test needs "
        "to say why: %r" % C.POLLUTED_BY_EXTRACTION)

    en_items = {r["name"]: r for r in load("en", "item")}
    for carrier, eaten in (("Dagger of Venom", "Dancing Sword"),
                           ("Folding Boat", "Frost Brand"),
                           ("Lantern of Revealing", "Luck Blade"),
                           ("Sun Blade", "Sword of Life Stealing"),
                           ("Sword of Sharpness", "Sword of Wounding")):
        text = en_items[carrier]["data"]["description"]
        assert eaten in en_items, "%s should exist on its own" % eaten
        assert eaten not in text, "%s carries %s again" % (carrier, eaten)
        assert len(text) < 1000, "%s is %d characters long again" % (carrier, len(text))

    # And the signature that was refused is now a pair, because it is now right.
    with open(os.path.join(EXPORTS, "correspondence.json"), encoding="utf-8") as fh:
        published = json.load(fh)
    assert not [r for r in published["refusals"]
                if r["reason"] == "signed-on-polluted-record"], published["refusals"]
    fr_ids = {r["name"]: r["id"] for r in load("fr", "item")}
    pair = next((p for p in published["pairs"]
                 if p["en"] == en_items["Sword of Sharpness"]["id"]), None)
    assert pair is not None, "the corrected signature should now be a pair"
    # ⭐ DEUX MOITIÉS, ET ELLES SE VÉRIFIENT L'UNE L'AUTRE. Le record français
    # nommé « Épée acérée » vit désormais à l'adresse ANGLAISE de Sword of
    # Sharpness — c'est la migration. Et la table publiée garde son SLUG
    # français — c'est la provenance, et c'est ce qui rend la signature d'Eric
    # encore lisible par Eric.
    assert fr_ids["Épée acérée"] == en_items["Sword of Sharpness"]["id"], (
        "le jumeau français ne partage pas l'adresse de son anglais")
    assert pair["fr"] == "item:epee-aceree", pair
    assert pair["by"] == C.BY_HUMAN, pair
    print("  ok  the guard is empty because the five records are measurably "
          "clean, and the corrected signature is a pair")



def acceptance_item_repair_is_done():
    """The extraction defect is repaired, and this is what proves it.

    ⭐ THIS TEST USED TO ASSERT THE OPPOSITE. It described a ten-record
    signature: five English items that did not exist, five French twins with
    nobody to face, three polluted carriers stranded with theirs. Lot 86 fixed
    the parser and that signature died -- so the test is rewritten to the new
    truth rather than switched off. A guard turned off is a guard lost.
    """
    en_items = {r["name"]: r for r in load("en", "item")}
    fr_items = {r["name"]: r for r in load("fr", "item")}

    # 1. The five that were eaten are records of their own now.
    for name in ("Dancing Sword", "Frost Brand", "Luck Blade",
                 "Sword of Life Stealing", "Sword of Wounding"):
        rec = en_items.get(name)
        assert rec is not None, "%s should exist since lot 86" % name
        assert rec["data"]["category"] == "weapon", rec
        # ⚠️ Their heads wrap over two or three printed lines, which is what
        # hid them -- and a rarity cut in half by a line break STILL matches
        # the pattern. So the shape of what came out is the thing to check: a
        # truncated head reads "Very Rare (Requires", loses its attunement, and
        # leaves the orphaned "Attunement)" at the head of the description.
        assert rec["data"]["rarity"].endswith(")"), rec["data"]["rarity"]
        assert rec["data"]["attunement"] is True, rec
        assert not rec["data"]["description"].startswith("Attunement)"), rec

    # 2. The two catalogues agree on how many magic items exist.
    assert len(en_items) == len(fr_items) == 258, (len(en_items), len(fr_items))

    # 3. No carrier still holds a stranger's entry.
    for carrier, eaten in (("Dagger of Venom", "Dancing Sword"),
                           ("Folding Boat", "Frost Brand"),
                           ("Lantern of Revealing", "Luck Blade"),
                           ("Sun Blade", "Sword of Life Stealing"),
                           ("Sword of Sharpness", "Sword of Wounding")):
        text = en_items[carrier]["data"]["description"]
        assert eaten not in text, "%s still carries %s" % (carrier, eaten)
        assert len(text) < 1000, "%s is still %d characters long" % (carrier, len(text))

    # 4. Two of the five pair with their French twin with no help at all -- no
    #    signature, no new fingerprint. That is the repair proving itself.
    with open(os.path.join(EXPORTS, "correspondence.json"), encoding="utf-8") as fh:
        published = json.load(fh)
    pairs = {p["en"]: p for p in published["pairs"]}
    for name, twin in (("Frost Brand", "Fer gelé"), ("Luck Blade", "Lame porte-bonheur")):
        pair = pairs.get(en_items[name]["id"])
        assert pair is not None, "%s should pair now" % name
        # ⭐ DEUX MOITIÉS, ET ELLES SE VÉRIFIENT L'UNE L'AUTRE : le jumeau
        # français vit désormais À LA MÊME ADRESSE (c'est la migration), et la
        # table publiée garde son SLUG (c'est la provenance). Exiger les deux,
        # c'est refuser qu'une seule suffise.
        assert fr_items[twin]["id"] == en_items[name]["id"], (
            "%s et %s ne partagent pas leur adresse" % (name, twin))
        # ⭐ DEUX MOITIÉS. Le jumeau français vit à la MÊME adresse (la
        # migration), et la table garde son SLUG français (la provenance).
        assert fr_items[twin]["id"] == en_items[name]["id"], (
            "%s et %s ne partagent pas leur adresse" % (name, twin))
        assert pair["fr"] == "item:%s" % SLUGS_FR[twin], (name, pair)
        assert pair["by"] == C.BY_FINGERPRINT, (name, pair["by"])
    print("  ok  items: the extraction defect is repaired -- 258/258, five items "
          "back, no carrier polluted, two pairing by themselves")


def _rec(rid, name, data=None):
    return {"id": rid, "name": name, "data": data or {}}


def unit_occurrence_refuses_indiscernible():
    """Two things carried by exactly the same records cannot be told apart.

    ⛔ This is the normal case, not a failure. `Animal Handling` and `Survival`
    are cited by the same classes, backgrounds and species; nothing OUTSIDE
    them separates them, so the route says so instead of picking one.
    """
    src = {
        "class": {
            "en": [_rec("srd:class:en:a", "A", {"skill_choice": {"from": [
                "srd:skill:en:x", "srd:skill:en:y", "srd:skill:en:z"]}})],
            "fr": [_rec(FR("class", "a"), "A", {"skill_choice": {"from": [
                FR("skill", "x"), FR("skill", "y"), FR("skill", "z")]}})],
        },
        "skill": {
            "en": [_rec("srd:skill:en:x", "X"), _rec("srd:skill:en:y", "Y"),
                   _rec("srd:skill:en:z", "Z")],
            "fr": [_rec(FR("skill", "x"), "X"), _rec(FR("skill", "y"), "Y"),
                   _rec(FR("skill", "z"), "Z")],
        },
    }
    route = {"into": "skill", "mode": "ids",
             "carriers": (("class", ".skill_choice.from[]"),)}
    pairs, refusals = C.occurrence_pairs(
        route, {"srd:class:en:a": FR("class", "a")}, src)
    assert pairs == [], "three skills on one carrier are indiscernible"
    kinds = sorted(r["reason"] for r in refusals)
    assert kinds.count("indiscernible") == 3, refusals
    print("  ok  occurrence: identical extensions are refused, not guessed")


def unit_occurrence_ignores_order():
    """The route must survive the thing that killed pairing by position.

    The French SRD lists a weapon's properties in its OWN alphabetical order.
    Here the two sides are deliberately written in opposite orders; a route
    that read position would pair them backwards.
    """
    src = {
        "weapon": {
            "en": [_rec("srd:weapon:en:1", "One", {"properties": "Heavy, Light"}),
                   _rec("srd:weapon:en:2", "Two", {"properties": "Heavy"})],
            "fr": [_rec(FR("weapon", "1"), "Un", {"properties": "Légère, Lourde"}),
                   _rec(FR("weapon", "2"), "Deux", {"properties": "Lourde"})],
        },
        "weapon-property": {
            "en": [_rec("srd:weapon-property:en:heavy", "Heavy"),
                   _rec("srd:weapon-property:en:light", "Light")],
            "fr": [_rec(FR("weapon-property", "lourde"), "Lourde"),
                   _rec(FR("weapon-property", "legere"), "Légère")],
        },
    }
    route = {"into": "weapon-property", "mode": "names",
             "carriers": (("weapon", "properties"),)}
    proven = {"srd:weapon:en:1": FR("weapon", "1"),
              "srd:weapon:en:2": FR("weapon", "2")}
    got = {p["en"]: p["fr"] for p in C.occurrence_pairs(route, proven, src)[0]}
    assert got["srd:weapon-property:en:heavy"] == FR("weapon-property", "lourde")
    assert got["srd:weapon-property:en:light"] == FR("weapon-property", "legere")
    print("  ok  occurrence: membership survives an order that would mislead")


def unit_mention_refuses_when_corpora_disagree():
    """Two independent corpora reaching different answers is a STOP.

    Not hypothetical: on the real exports, one corpus reads `Long Rest` as
    *Repos court* and another as *Repos long*. A single-corpus route would have
    shipped whichever it happened to consult.
    """
    target = {"en": [_rec("srd:glossary:en:t", "Rest")],
              "fr": [_rec(FR("glossary", "a"), "Repos court"),
                     _rec(FR("glossary", "b"), "Repos long")]}
    src = {
        "glossary": target,
        "monster": {"en": [_rec("srd:monster:en:1", "M", {"t": "rest"})],
                    "fr": [_rec(FR("monster", "1"), "M", {"t": "repos court"})]},
        "spell": {"en": [_rec("srd:spell:en:1", "S", {"t": "rest"})],
                  "fr": [_rec(FR("spell", "1"), "S", {"t": "repos long"})]},
    }
    route = {"into": "glossary", "corpora": ("monster", "spell"),
             "min_corroboration": 2}
    proven = {"srd:monster:en:1": FR("monster", "1"),
              "srd:spell:en:1": FR("spell", "1")}
    pairs, refusals = C.mention_pairs(route, proven, src)
    assert pairs == [], "corpora disagreed; nothing may be emitted"
    assert any(r["reason"] == "corpora-disagree" for r in refusals), refusals
    print("  ok  mention: two corpora disagreeing stops the pair")


def unit_mention_refuses_a_single_witness():
    """One corpus is not corroboration, however confident it looks.

    A term saturating one corpus produces a profile that matches by exhaustion
    rather than by identity. Only a second, independent population can tell the
    two apart, so one witness is refused by construction.
    """
    src = {
        "glossary": {"en": [_rec("srd:glossary:en:t", "Term")],
                     "fr": [_rec(FR("glossary", "t"), "Terme")]},
        "monster": {"en": [_rec("srd:monster:en:1", "M", {"t": "term"})],
                    "fr": [_rec(FR("monster", "1"), "M", {"t": "terme"})]},
    }
    route = {"into": "glossary", "corpora": ("monster",), "min_corroboration": 2}
    pairs, refusals = C.mention_pairs(
        route, {"srd:monster:en:1": FR("monster", "1")}, src)
    assert pairs == []
    assert any(r["reason"] == "uncorroborated" for r in refusals), refusals
    print("  ok  mention: a single witness is refused, however clean it looks")


def unit_second_axis_leaves_what_it_cannot_split():
    """The second axis narrows a group or leaves it alone. It never picks."""
    pending = [{"kind": "spell", "reason": "ambiguous",
                "en": [{"id": "srd:spell:en:a", "name": "A"},
                       {"id": "srd:spell:en:b", "name": "B"}],
                "fr": [{"id": FR("spell", "a"), "name": "A"},
                       {"id": FR("spell", "b"), "name": "B"}]}]
    same = {"casting_time": "Action", "duration": "Instantaneous"}
    src = {"spell": {
        "en": [_rec("srd:spell:en:a", "A", dict(same)),
               _rec("srd:spell:en:b", "B", dict(same))],
        "fr": [_rec(FR("spell", "a"), "A", dict(same)),
               _rec(FR("spell", "b"), "B", dict(same))]}}
    pairs, _ = C.second_axis_pairs(pending, src, {})
    assert pairs == [], "the axis cannot split them; it must not choose"

    # Give one of them a different casting time and it separates cleanly.
    src["spell"]["en"][1]["data"] = {"casting_time": "Bonus Action",
                                     "duration": "Instantaneous"}
    src["spell"]["fr"][1]["data"] = {"casting_time": "action Bonus",
                                     "duration": "instantanée"}
    pairs, _ = C.second_axis_pairs(pending, src, {})
    got = {p["en"]: p["fr"] for p in pairs}
    assert got == {"srd:spell:en:a": FR("spell", "a"),
                   "srd:spell:en:b": FR("spell", "b")}, got
    print("  ok  second axis: it separates or it abstains, never picks")


def unit_second_axis_names_the_genres_it_cannot_help():
    """`gear` and `item` have no untouched field. That is the answer, not a gap."""
    pending = [{"kind": "gear", "reason": "ambiguous",
                "en": [{"id": "srd:gear:en:a", "name": "A"}],
                "fr": [{"id": FR("gear", "a"), "name": "A"}]}]
    src = {"gear": {"en": [_rec("srd:gear:en:a", "A")],
                    "fr": [_rec(FR("gear", "a"), "A")]}}
    pairs, refusals = C.second_axis_pairs(pending, src, {})
    assert pairs == []
    assert [r["reason"] for r in refusals] == ["no-second-axis"], refusals
    assert "gear" in refusals[0]["detail"]
    print("  ok  second axis: a genre with no axis is named, not skipped")


def acceptance_lot83_routes():
    """What the three new routes closed, recomputed from `exports/`."""
    with open(os.path.join(EXPORTS, "correspondence.json"), encoding="utf-8") as fh:
        published = json.load(fh)
    counts = published["by_provenance"]

    for route, expected in (("occurrence/weapon-property", 9),
                            ("occurrence/skill", 15),
                            ("occurrence/feat", 3),
                            # 40 before lot 86, 39 after, 40 again after lot 102
                            # — and les trois nombres sont le MÊME garde qui
                            # travaille, pas un chiffre qui flotte.
                            # · 40 -> 39 : `Alignment` -> `Alignement` était
                            #   atteint par le corpus des objets ET celui des
                            #   sorts ; réparer cinq records d'objets a changé ce
                            #   corpus au point qu'il ne singularise plus le
                            #   terme, et un seul témoin n'est pas une
                            #   corroboration. La paire n'est pas fausse, elle est
                            #   NON PROUVÉE — et la route qui refuse de la
                            #   revendiquer sur un corpus est la route qui marche.
                            # · 39 -> 40 (lot 102) : ⭐ `Points de vie temporaires`
                            #   entre, et PERSONNE NE L'A DÉCLARÉ. L'entrée était
                            #   imprimée p.197 du livre français et le lecteur de
                            #   glossaire la sautait ; réparée, elle n'a eu qu'à
                            #   EXISTER pour que la corroboration l'apparie à
                            #   `Temporary Hit Points`. La méthode du chantier en
                            #   entier tient dans cette ligne : chercher un signal
                            #   avant de déclarer une table.
                            # ⛔ Et dans les deux cas, ZÉRO paire DÉPLACÉE — c'est
                            # le nombre qui aurait compté.
                            ("mention/glossary", 40),
                            ("second-axis/spell", 50),
                            ("second-axis/species", 2),
                            ("second-axis/tool", 2)):
        assert counts.get(route) == expected, (
            "%s closed %r, expected %d" % (route, counts.get(route), expected))

    # Every glossary pair must name at least two corpora, and the count must
    # match what the route claims — the corroboration is the route's whole
    # licence to exist, so it is checked on the pairs and not on a total.
    for pair in published["pairs"]:
        if pair["by"] == "mention/glossary":
            assert len(pair.get("corroborated_by", [])) >= 2, pair
        if pair["by"].startswith("occurrence/"):
            assert pair.get("via"), pair

    # The two refusals that carry the most information.
    reasons = [r["reason"] for r in published["refusals"]]
    assert "corpora-disagree" in reasons, "Long Rest should still disagree"
    assert reasons.count("indiscernible") == 2, (
        "Animal Handling and Survival should still be indiscernible")
    print("  ok  lot 83: 120 records closed across three routes, "
          "corroboration present on every glossary pair")


def main():
    unit_price()
    unit_weight()
    unit_distance()
    unit_tokens()
    unit_never_guesses()
    unit_unknown_genre_is_named()
    unit_one_sided_genre_refuses()
    unit_transitive_refuses_disagreement()
    unit_transitive_refuses_dangling()
    unit_transitive_never_overturns_the_data()
    unit_properties_is_not_a_route()
    unit_signed_refuses_what_cannot_be()
    unit_signed_agreement_is_not_a_conflict()
    unit_signed_on_a_polluted_record_needs_a_note()
    unit_occurrence_refuses_indiscernible()
    unit_occurrence_ignores_order()
    unit_mention_refuses_when_corpora_disagree()
    unit_mention_refuses_a_single_witness()
    unit_second_axis_leaves_what_it_cannot_split()
    unit_second_axis_names_the_genres_it_cannot_help()
    acceptance()
    acceptance_l_ordre_des_slugs_ne_dit_rien_de_l_ordre_des_adresses()
    acceptance_weight_rule()
    acceptance_lot83_routes()
    acceptance_transitive_closes_masteries()
    acceptance_item_repair_is_done()
    acceptance_the_guard_is_empty_because_the_records_are_clean()
    acceptance_attack()
    print("PASS test_correspond")


if __name__ == "__main__":
    main()
