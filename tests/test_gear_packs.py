"""The seven packs' contents: every rule checked by BREAKING it.

The failures worth guarding against here are, again, the ones that do not
raise. A pack's contents are a list of short nouns; almost any wrong reading
still produces a list of short nouns, and still exits 0:

  * a sentence cut by a COLUMN BREAK, read up to the break and no further —
    "10" and "days of Rations" become two elements, or nine become eight, and
    the pack still looks full;
  * a de-pluralising rule applied before the exact one, which mis-files "Ball
    Bearings", "Rations" and "Caltrops" onto records that do not exist and
    leaves them unresolved *for a reason that looks like the source's fault*;
  * a name rotation that shadows a real record, or that two records both
    claim, answering confidently with the wrong one;
  * an element resolved by ACCIDENT — "sac de couchage" split into a "sac" of
    "couchage" — which produces a real record id pointing at the wrong object;
  * and the one this whole lot exists to prevent: a contents sentence the
    parser began and did not finish, coming back as a pack with fewer items
    and nothing said.

The last block checks the SHIPPED exports, not a rebuild of them: the file the
FHPC actually reads, one pack at a time.

Run: python3 tests/test_gear_packs.py
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import french_layer  # noqa: E402
import gear_packs  # noqa: E402
import parse_gear_en  # noqa: E402

EXPORTS = os.path.join(ROOT, "exports", "srd")

CASES = []


def case(fn):
    CASES.append(fn)
    return fn


def rows(*names):
    """A stand-in catalogue: the table parser's own row shape, nothing more."""
    return [{"name": n, "weight": "1 lb.", "cost": "1 GP", "page": 95} for n in names]


def read(catalogue, *lines):
    """Run one pack sentence past `attach` and hand back (row, anomalies)."""
    gear = rows(*catalogue)
    anomalies = gear_packs.attach(gear, list(lines), "en")
    return {g["name"]: g for g in gear}, anomalies


# --- the sentence, and the three ways the layout cuts it --------------------

@case
def a_column_break_inside_the_list_does_not_end_it():
    """EN's Dungeoneer's Pack, verbatim from p.97: the list is cut in two by a
    blank line, mid-element, between "10" and "days of Rations"."""
    by_name, anomalies = read(
        ["Dungeoneer’s Pack", "Backpack", "Rations", "Torch"],
        "Dungeoneer’s Pack (12 GP)",
        "A Dungeoneer’s Pack contains the following items:",
        "Backpack, 10",
        "",
        "days of Rations, 10 Torches.",
    )
    contents = by_name["Dungeoneer’s Pack"]["contents"]
    assert not anomalies, anomalies
    assert [e["text"] for e in contents] == [
        "Backpack", "10 days of Rations", "10 Torches"], contents
    assert [e["quantity"] for e in contents] == [1, 10, 10], contents
    assert [e["name"] for e in contents] == ["Backpack", "Rations", "Torch"], contents


@case
def the_anchor_phrase_may_itself_be_cut_by_a_line_wrap():
    """FR's Priest's Pack wraps INSIDE the phrase ("les objets" / "suivants :").
    Checked here in the EN grammar for the same reason: a reader anchored on a
    single line finds nothing and reports nothing."""
    by_name, anomalies = read(
        ["Priest’s Pack", "Robe"],
        "A Priest’s Pack contains the following",
        "items: Robe.",
    )
    assert not anomalies, anomalies
    assert [e["name"] for e in by_name["Priest’s Pack"]["contents"]] == ["Robe"]


@case
def a_sentence_begun_and_not_finished_is_reported_not_swallowed():
    """⭐ THE GUARD THE LOT EXISTS FOR. The anchor is there, the period is not
    (here: past the 400-character bound). Returning six packs instead of seven
    with an empty anomaly list is exactly the shape of the 102 vanished
    records this repository has already paid for once."""
    filler = ", ".join(["Rope"] * 120)
    by_name, anomalies = read(
        ["Explorer’s Pack", "Rope"],
        "An Explorer’s Pack contains the following items: " + filler,
    )
    assert "contents" not in by_name["Explorer’s Pack"]
    assert len(anomalies) == 1 and "did not finish" in anomalies[0]["detail"], anomalies


@case
def a_pack_that_is_on_no_row_is_named_not_invented():
    by_name, anomalies = read(
        ["Rope"],
        "A Spelunker’s Pack contains the following items: Rope.",
    )
    assert len(anomalies) == 1 and "on no row" in anomalies[0]["detail"], anomalies
    assert all("contents" not in g for g in by_name.values())


@case
def a_source_with_no_pack_prose_is_not_an_anomaly():
    """The synthetic fixtures carry the table and none of the prose. A parser
    that complained here would make every fixture-based test carry a false
    failure, which is how a real anomaly stops being read."""
    by_name, anomalies = read(["Backpack", "Rope"], "Backpack", "5 lb.", "2 GP")
    assert not anomalies, anomalies
    assert all("contents" not in g for g in by_name.values())


# --- resolution: the two mechanical rules, and their limits -----------------

@case
def the_cited_phrase_is_tried_verbatim_before_it_is_depluralised():
    """⭐ BROKEN ON PURPOSE. Three records' own names end in "s". Strip first
    and "Ball Bearings" goes looking for "Ball Bearing", which is nothing —
    and the element comes back unresolved as if the SOURCE were at fault."""
    by_name, _ = read(
        ["Burglar’s Pack", "Ball Bearings", "Caltrops", "Rations", "Candle"],
        "A Burglar’s Pack contains the following items: "
        "Ball Bearings, Caltrops, 5 days of Rations, 10 Candles.",
    )
    got = [e["name"] for e in by_name["Burglar’s Pack"]["contents"]]
    assert got == ["Ball Bearings", "Caltrops", "Rations", "Candle"], got


@case
def exact_beats_depluralised_even_when_both_records_exist():
    """The order is not a lucky accident of this catalogue: put "Candle" AND
    "Candles" side by side and the cited "Candles" must answer "Candles"."""
    primary, alias, ambiguous = gear_packs.build_index(rows("Candle", "Candles"))
    assert not ambiguous, ambiguous
    element = gear_packs._element("10 Candles", gear_packs.LANGS["en"], "en",
                                  primary, alias)
    assert element["name"] == "Candles", element


@case
def a_record_with_one_comma_answers_to_its_rotation():
    """The table alphabetises by inversion, the prose does not."""
    by_name, anomalies = read(
        ["Diplomat’s Pack", "Lantern, Hooded", "Case, Map or Scroll", "Clothes, Fine"],
        "A Diplomat’s Pack contains the following items: "
        "Hooded Lantern, 2 Map or Scroll Cases, Fine Clothes.",
    )
    assert not anomalies, anomalies
    got = [(e["name"], e["ref"]) for e in by_name["Diplomat’s Pack"]["contents"]]
    assert got == [
        ("Lantern, Hooded", "srd:gear:en:lantern-hooded"),
        ("Case, Map or Scroll", "srd:gear:en:case-map-or-scroll"),
        ("Clothes, Fine", "srd:gear:en:clothes-fine"),
    ], got


@case
def a_rotation_never_shadows_a_record_that_really_has_that_name():
    """If some row were literally called "Hooded Lantern", it — not the
    rotation of "Lantern, Hooded" — is what "Hooded Lantern" means."""
    primary, alias, _ = gear_packs.build_index(
        rows("Lantern, Hooded", "Hooded Lantern"))
    assert "hooded-lantern" in primary and "hooded-lantern" not in alias
    element = gear_packs._element("Hooded Lantern", gear_packs.LANGS["en"], "en",
                                  primary, alias)
    assert element["name"] == "Hooded Lantern", element


@case
def a_rotation_two_records_both_claim_is_dropped_from_both():
    """⛔ A door that opens onto two rooms is not a door. "Lantern, Hooded
    Brass" and "Brass Lantern, Hooded" rotate onto the very same words;
    answering either one would be a coin toss wearing a record id."""
    primary, alias, ambiguous = gear_packs.build_index(
        rows("Lantern, Hooded Brass", "Brass Lantern, Hooded"))
    assert ambiguous == ["hooded-brass-lantern"], ambiguous
    assert "hooded-brass-lantern" not in alias
    element = gear_packs._element("Hooded Brass Lantern", gear_packs.LANGS["en"],
                                  "en", primary, alias)
    assert element["name"] is None and element["ref"] is None, element


@case
def a_record_with_a_hyphen_answers_to_that_hyphen_removed():
    """The dehyphenator joins "porte-" / "plume" into "porteplume". The damage
    is in the CITATION, so the extra door is on the RECORD."""
    primary, alias, _ = gear_packs.build_index(rows("Porte-plume", "Chausse-trappes"))
    assert alias["porteplume"] == "Porte-plume"
    assert alias["chaussetrappes"] == "Chausse-trappes"


# --- the counted word, and the accident it must not cause -------------------

@case
def a_counted_container_is_split_only_after_the_whole_phrase_fails():
    """"7 flasks of Oil" is seven flasks OF Oil; "sac de couchage" is one
    bedroll. ⭐ Broken by trying the split first: French's "de" would turn a
    record into a "sac" of "couchage" — a real id, pointing at the wrong
    thing, with nothing to show it had gone wrong."""
    by_name, _ = read(
        ["Explorer’s Pack", "Oil", "Paper", "Potion of Healing"],
        "An Explorer’s Pack contains the following items: "
        "7 flasks of Oil, 5 sheets of Paper, Potion of Healing.",
    )
    got = [(e["text"], e["quantity"], e["unit"], e["name"])
           for e in by_name["Explorer’s Pack"]["contents"]]
    assert got == [
        ("7 flasks of Oil", 7, "flasks", "Oil"),
        ("5 sheets of Paper", 5, "sheets", "Paper"),
        ("Potion of Healing", 1, None, "Potion of Healing"),
    ], got


@case
def an_element_that_resolves_to_nothing_keeps_its_text_and_says_so():
    """FR's real one: the book writes the record as "Étui à cartes OU à
    parchemins" and cites it as "étuis à cartes ET à parchemins". A trou
    déclaré, not a line filled in."""
    by_name, anomalies = read(
        ["Scholar’s Pack", "Book"],
        "A Scholar’s Pack contains the following items: Book, 2 Thingummies.",
    )
    assert not anomalies, anomalies
    contents = by_name["Scholar’s Pack"]["contents"]
    assert contents[1] == {"text": "2 Thingummies", "quantity": 2, "unit": None,
                           "name": None, "ref": None}, contents[1]
    assert gear_packs.unresolved([by_name["Scholar’s Pack"]]) == [
        ("Scholar’s Pack", "2 Thingummies")]


@case
def the_list_conjunction_is_punctuation_and_not_part_of_the_item():
    by_name, _ = read(
        ["Explorer’s Pack", "Rope", "Waterskin"],
        "An Explorer’s Pack contains the following items: Rope, and Waterskin.",
    )
    got = [e["text"] for e in by_name["Explorer’s Pack"]["contents"]]
    assert got == ["Rope", "Waterskin"], got


@case
def the_table_parser_itself_still_reports_nothing_on_a_table_without_prose():
    """A whole `parse()`, not just `attach()`: the seam is where a new pass
    usually starts inventing anomalies for the fixtures."""
    found, anomalies, conflicts = parse_gear_en.parse(
        ["Adventuring Gear\n\nItem\nWeight\nCost\n\nAcid\n1 lb.\n25 GP\n"])
    assert len(found) == 1 and not anomalies and not conflicts, (found, anomalies)
    assert "contents" not in found[0]


# --- the shipped exports, one pack at a time --------------------------------

#: Recounted off the pinned EN PDF, p.96-99, by reading the seven sentences.
#: ⛔ Not a rule and not a derivation — a transcription, and the only place in
#: this lot where a number was written by hand.
EXPECTED = {
    "burglar-s-pack": 11,
    "diplomat-s-pack": 11,
    "dungeoneer-s-pack": 9,
    "entertainer-s-pack": 10,
    "explorer-s-pack": 8,
    "priest-s-pack": 7,
    "scholar-s-pack": 8,
}


def shipped(lang):
    if lang == "en":
        with open(os.path.join(EXPORTS, "en", "gear.json"), encoding="utf-8") as fh:
            return json.load(fh)["records"]
    return french_layer.load(EXPORTS, lang, "gear")


@case
def the_committed_english_export_carries_all_seven_packs():
    got = {r["slug"]: len(r["data"]["contents"])
           for r in shipped("en") if r["data"].get("contents")}
    assert got == EXPECTED, got


@case
def every_english_element_points_at_a_gear_record_that_exists():
    records = shipped("en")
    ids = {r["id"] for r in records}
    total = 0
    for rec in records:
        for element in rec["data"].get("contents") or []:
            total += 1
            assert element["name"], (rec["slug"], element)
            assert element["ref"] in ids, (rec["slug"], element)
            assert element["quantity"] >= 1, (rec["slug"], element)
    assert total == sum(EXPECTED.values()) == 64, total


@case
def the_french_layer_describes_the_same_seven_packs_element_for_element():
    """The two books are read by two parsers with two grammars. They are not
    checked against each other's WORDS — that would be a translation — but a
    pack whose element count differs between them means one of the two reads
    stopped early, and that is worth refusing."""
    got = {r["slug"]: len(r["data"]["contents"])
           for r in shipped("fr") if r["data"].get("contents")}
    assert got == EXPECTED, got


@case
def the_one_french_element_the_book_itself_will_not_let_us_resolve():
    """⛔ Ce test EXIGE le trou. Le jour où il se comble, c'est qu'une règle
    mécanique s'est mise à deviner — et on veut l'apprendre ici."""
    holes = [(r["slug"], e["text"])
             for r in shipped("fr")
             for e in (r["data"].get("contents") or []) if not e["name"]]
    assert holes == [("diplomat-s-pack", "2 étuis à cartes et à parchemins")], holes


def main():
    for fn in CASES:
        fn()
        print("  ok  %s" % fn.__name__)
    print("PASS test_gear_packs  (%d checks)" % len(CASES))


if __name__ == "__main__":
    main()
