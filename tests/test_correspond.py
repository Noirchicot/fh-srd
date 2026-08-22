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

import correspond as C  # noqa: E402


# Eleven pairs read and confirmed by hand against the two PDFs. They are here
# so the test fails for the right reason instead of agreeing with whatever
# correspondence.json happens to hold — `plate-armor` pairs with `harnois`,
# and no amount of green tests makes that true if the file says otherwise.
HAND_CHECKED = {
    "srd:class:en:fighter": "srd:class:fr:guerrier",
    "srd:class:en:wizard": "srd:class:fr:magicien",
    "srd:class:en:barbarian": "srd:class:fr:barbare",
    "srd:monster:en:aboleth": "srd:monster:fr:aboleth",
    "srd:armor:en:chain-mail": "srd:armor:fr:cotte-de-mailles",
    "srd:armor:en:plate-armor": "srd:armor:fr:harnois",
    "srd:weapon:en:longsword": "srd:weapon:fr:epee-longue",
    "srd:spell:en:fireball": "srd:spell:fr:boule-de-feu",
    "srd:tool:en:thieves-tools": "srd:tool:fr:outils-de-voleur",
    "srd:species:en:dwarf": "srd:species:fr:nain",
    "srd:background:en:soldier": "srd:background:fr:soldat",
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
                            [rec("srd:gear:fr:a", "A", "7 po")])
    assert len(out["matched"]) == 1 and not out["pending"]

    # Two against two, same fingerprint -> NO pair, one named question.
    out = C.correspond_kind(
        "gear",
        [rec("srd:gear:en:a", "A", "7 GP"), rec("srd:gear:en:b", "B", "7 GP")],
        [rec("srd:gear:fr:a", "A", "7 po"), rec("srd:gear:fr:b", "B", "7 po")])
    assert out["matched"] == [], "two against two must not pair"
    assert len(out["pending"]) == 1
    assert out["pending"][0]["reason"] == "ambiguous"
    assert len(out["pending"][0]["en"]) == 2 and len(out["pending"][0]["fr"]) == 2

    # One English, no French -> named, not dropped.
    out = C.correspond_kind("gear", [rec("srd:gear:en:a", "A", "7 GP")],
                            [rec("srd:gear:fr:z", "Z", "9 po")])
    reasons = sorted(g["reason"] for g in out["pending"])
    assert reasons == ["unmatched-en", "unmatched-fr"], reasons
    print("  ok  rule: 1-1 pairs, 2-2 refuses, and both orphan sides are named")


def unit_unknown_genre_is_named():
    """A genre with no fingerprint is a question in the open, never a silence."""
    out = C.correspond_kind("brand-new-genre",
                            [{"id": "srd:brand-new-genre:en:x", "name": "X", "data": {}}],
                            [{"id": "srd:brand-new-genre:fr:x", "name": "X", "data": {}}])
    assert out["matched"] == []
    assert out["fingerprint"] is None
    assert out["pending"][0]["reason"] == "no-fingerprint"
    assert out["pending"][0]["en"][0]["id"] == "srd:brand-new-genre:en:x"
    assert out["pending"][0]["fr"][0]["id"] == "srd:brand-new-genre:fr:x"
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
    with open(os.path.join(EXPORTS, lang, kind + ".json"), encoding="utf-8") as fh:
        return json.load(fh)["records"]


def acceptance():
    """Recompute the whole pairing from `exports/` and check what it claims."""
    kinds = sorted(f[:-5] for f in os.listdir(os.path.join(EXPORTS, "en"))
                   if f.endswith(".json"))
    by_kind = {k: {lang: load(lang, k) for lang in ("en", "fr")} for k in kinds}
    result = C.correspond_all(by_kind)

    pairs = result["pairs"]
    ens = [p["en"] for p in pairs]
    frs = [p["fr"] for p in pairs]

    # A correspondence that maps two English records onto one French record is
    # not a correspondence. This is checked on the recomputed result, not read
    # out of the published file.
    assert len(set(ens)) == len(ens), "an English record appears in two pairs"
    assert len(set(frs)) == len(frs), "a French record appears in two pairs"
    for pair in pairs:
        assert pair["en"].split(":")[1] == pair["fr"].split(":")[1], pair
        assert ":en:" in pair["en"] and ":fr:" in pair["fr"], pair

    index = dict(zip(ens, frs))
    for en_id, fr_id in sorted(HAND_CHECKED.items()):
        assert index.get(en_id) == fr_id, (
            "%s should pair with %s, got %r" % (en_id, fr_id, index.get(en_id)))

    # Every record of every genre is accounted for exactly once: paired, or
    # named in `pending`. A record in neither would be a silent loss, which is
    # the shape of failure this whole artefact exists to refuse.
    for kind in kinds:
        for lang, key in (("en", "en"), ("fr", "fr")):
            catalogue = {r["id"] for r in by_kind[kind][lang]}
            paired = {p[key] for p in pairs if p["en"].split(":")[1] == kind}
            listed = {b["id"] for g in result["pending"] if g["kind"] == kind
                      for b in g[key]}
            missing = catalogue - paired - listed
            assert not missing, "%s/%s: %d record(s) neither paired nor named: %s" % (
                kind, lang, len(missing), sorted(missing)[:5])
            assert not (paired & listed), "%s/%s: a record is both paired and pending" % (
                kind, lang)

    # The published file must say what a fresh recomputation says.
    with open(os.path.join(EXPORTS, "correspondence.json"), encoding="utf-8") as fh:
        published = json.load(fh)
    assert published["totals"] == result["totals"], (
        "correspondence.json is stale: %r against %r"
        % (published["totals"], result["totals"]))
    assert published["pairs"] == pairs, "correspondence.json pairs are stale"

    print("  ok  acceptance: %d pairs, bijective, %d record(s) named, "
          "11/11 hand-checked, published file current"
          % (len(pairs), result["totals"]["pending_records"]))


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


def main():
    unit_price()
    unit_weight()
    unit_distance()
    unit_tokens()
    unit_never_guesses()
    unit_unknown_genre_is_named()
    unit_one_sided_genre_refuses()
    acceptance()
    acceptance_weight_rule()
    acceptance_attack()
    print("PASS test_correspond")


if __name__ == "__main__":
    main()
