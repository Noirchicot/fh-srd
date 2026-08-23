"""The magic item value scale, and the two rules that keep it from lying.

⛔ THE FOOTNOTES ARE NOT DECORATION. A consumable is worth HALF the tier price,
and a Spell Scroll is worth twice its scribing cost instead. Potions and scrolls
are the bulk of the SRD's magic items, so a scale published without its notes is
wrong on most of the corpus — and it would be applied anyway: another lot
already stamps `halved, consumable (p.206)` on 32 records, using a rule whose
source had never been extracted. That is what this genre repairs.

Run: python3 tests/test_item_values.py
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS = os.path.join(ROOT, "exports", "srd")

sys.path.insert(0, os.path.join(ROOT, "src"))

import parse_item_values as P  # noqa: E402

EXPECTED = {"common": 100, "uncommon": 400, "rare": 4000,
            "very-rare": 40000, "legendary": 200000, "artifact": None}


def load(lang):
    with open(os.path.join(EXPORTS, lang, "item-value.json"), encoding="utf-8") as fh:
        return json.load(fh)["records"]


def unit_priceless_is_a_value():
    """⚠️ An artifact the book calls priceless, and one whose price we failed to
    read, are two different facts. `priced` says which, so nobody has to guess
    what a null means."""
    assert P._value_of("Priceless", "en") is None
    assert P._value_of("Inestimable", "fr") is None
    assert P._value_of("40,000 GP", "en") == 40000
    assert P._value_of("40 000 po", "fr") == 40000
    assert P._value_of("100 GP", "en") == 100
    print("  ok  'Priceless' parses as a value, and a thousands separator "
          "survives in both spellings")


def unit_an_unreadable_value_refuses():
    """NEGATIVE CONTROL: a price that is neither an amount nor the word stops."""
    for lang, junk in (("en", "about 4000"), ("fr", "quelques pièces")):
        try:
            P._value_of(junk, lang)
        except P.ValueTableError as exc:
            assert junk in str(exc), exc
            continue
        raise AssertionError("%r should have been refused in %r" % (junk, lang))
    print("  ok  negative control: a price in prose is refused, not guessed at")


def unit_a_short_table_refuses():
    """⛔ A partial scale is worse than none — half the corpus gets priced from
    it. Five tiers must not ship as if they were six."""
    lines = ["Magic Item Rarities and Values", "Rarity", "Value*",
             "Common", "100 GP", "Uncommon", "400 GP", "Rare", "4,000 GP"]
    records, anomalies = P.parse_stream(lines, [1] * len(lines), "en")
    assert records == []
    assert anomalies and "came back short" in anomalies[0]["detail"]
    assert "Legendary" in anomalies[0]["detail"], anomalies
    print("  ok  negative control: a table missing tiers is refused, and names them")


def acceptance_both_languages():
    """The six tiers, the same numbers on both sides, and both rules present."""
    for lang in ("en", "fr"):
        records = load(lang)
        assert len(records) == 1, (lang, len(records))
        data = records[0]["data"]
        tiers = {t["rarity_key"]: t for t in data["tiers"]}
        assert set(tiers) == set(EXPECTED), (lang, sorted(tiers))
        for key, amount in EXPECTED.items():
            assert tiers[key]["value_gp"] == amount, (lang, key, tiers[key])
            assert tiers[key]["priced"] is (amount is not None), (lang, key)
        # ⛔ Neither rule may be missing: the scale is wrong for most magic
        # items without them.
        assert data["add_base_cost_rule"], lang
        assert data["value_footnote"], lang
        assert "5,500" in data["add_base_cost_rule"] or \
               "5 500" in data["add_base_cost_rule"], data["add_base_cost_rule"]
    print("  ok  6 tiers in both languages, identical amounts, both rules present")


def acceptance_the_numbers_join_the_two_catalogues():
    """⭐ The words differ and the numbers do not, so the scale identifies
    itself across the two catalogues with nothing declared."""
    en = {t["rarity_key"]: t["value_gp"] for t in load("en")[0]["data"]["tiers"]}
    fr = {t["rarity_key"]: t["value_gp"] for t in load("fr")[0]["data"]["tiers"]}
    assert en == fr, (en, fr)
    en_labels = {t["rarity_label"] for t in load("en")[0]["data"]["tiers"]}
    fr_labels = {t["rarity_label"] for t in load("fr")[0]["data"]["tiers"]}
    assert en_labels != fr_labels, "the labels should differ; only the keys align"

    with open(os.path.join(EXPORTS, "correspondence.json"), encoding="utf-8") as fh:
        pairs = [p for p in json.load(fh)["pairs"] if ":item-value:" in p["en"]]
    assert len(pairs) == 1, pairs
    assert pairs[0]["by"].startswith("structured-fingerprint/"), pairs[0]
    print("  ok  the two tables pair by their numbers alone, with no table to declare")


def main():
    unit_priceless_is_a_value()
    unit_an_unreadable_value_refuses()
    unit_a_short_table_refuses()
    acceptance_both_languages()
    acceptance_the_numbers_join_the_two_catalogues()
    print("PASS test_item_values")


if __name__ == "__main__":
    main()
