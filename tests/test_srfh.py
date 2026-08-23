"""The SRFH layer: the numbers are derived, traceable, and never touch the SRD.

Every rule below is checked by BREAKING it, not by watching the happy path
succeed. The failures this guards against are the ones that do not raise: a
price read as 1 instead of 1000 because of a thousands separator, a weight of
zero standing in for "negligible", a value nobody can trace back to a page.
"""

import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import canon  # noqa: E402
import db  # noqa: E402
import srfh  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "build", "srfh-test.sqlite")

CASES = []


def case(fn):
    CASES.append(fn)
    return fn


# --- a stand-in catalogue: one entry per branch the module can take ---------
WEAPONS = [
    ("Longsword", {"cost": "15 GP", "weight": "3 lb."}),
    ("Greatsword", {"cost": "50 GP", "weight": "6 lb."}),
    ("Dart", {"cost": "5 CP", "weight": "1/4 lb."}),
    ("Sling", {"cost": "1 SP", "weight": "—"}),
]
ARMORS = [("Plate Armor", {"cost": "1,500 GP", "weight": "65 lb."})]
GEAR = [
    ("Potion of Healing", {"cost": "50 GP", "weight": "1/2 lb."}),
    ("Spell Scroll (Cantrip)", {"cost": "30 GP", "weight": "—"}),
    ("Book", {"cost": "25 GP", "weight": "5 lb."}),
    ("Entertainer's Pack", {"cost": "40 GP", "weight": "58½ lb."}),
]
ITEMS = [
    # name, rarity, category, subtype, description
    ("Sun Blade", "Rare (Requires Attunement)", "weapon", "Longsword", ""),
    ("Vorpal Sword", "Legendary (Requires Attunement)", "weapon",
     "Greatsword, or Longsword", ""),
    ("Vicious Weapon", "Rare", "weapon", "Any Simple or Martial", ""),
    ("Armor of Invulnerability", "Legendary (Requires Attunement)", "armor",
     "Plate Armor", ""),
    ("Potion of Climbing", "Common", "potion", None, ""),
    ("Ring of Regeneration", "Very Rare (Requires Attunement)", "ring", None, ""),
    ("Wand of Magic Missiles", "Uncommon", "wand", None, ""),
    ("Staff of Charming", "Rare (Requires Attunement by a Bard)", "staff", None, ""),
    ("Rod of Rulership", "Rare (Requires Attunement)", "rod", None, ""),
    ("Manual of Golems", "Very Rare", "wondrous-item", None, ""),      # twin: Book
    ("Cloak of Elvenkind", "Uncommon (Requires Attunement)", "wondrous-item", None, ""),
    ("Dragon Orb", "Artifact (Requires Attunement)", "wondrous-item", None, ""),
    ("Spell Scroll", "Rarity Varies", "scroll", None, ""),
    ("Weapon, +1, +2, or +3", "Uncommon (+1), Rare (+2), or Very Rare (+3)",
     "weapon", "Any Simple or Martial", ""),
    ("Potions of Healing", "Rarity Varies", "potion", None,
     "Potion HP Regained Rarity\n\nPotion of Healing 2d4 + 2 Common\n\n"
     "Potion of Healing (greater) 4d4 + 4 Uncommon\n\n"
     "Potion of Healing (superior) 8d4 + 8 Rare\n\n"
     "Potion of Healing (supreme) 10d4 + 20 Very Rare"),
]
# The stand-in catalogue is not Eric's, so its counts are not his either.
FIXTURE_RATIFIED = {
    "extends": 13, "members": 4, "families": 1, "boosts": 1, "twin": 1,
    "jewellery": 0, "worn-soft": 1, "held": 1, "worn-rigid": 0, "bulky": 0,
}


def seed(conn):
    conn.execute(
        """INSERT INTO source (id,title,publisher,version,lang,url,sha256,bytes,
                               license,license_url,attribution)
           VALUES ('t','t','t','5.2.1','en','u','h',1,'CC-BY-4.0','u','a')"""
    )
    with db.srd_write(conn):
        for kind, rows in (("weapon", WEAPONS), ("armor", ARMORS), ("gear", GEAR)):
            for name, data in rows:
                payload = dict(data, name=name)
                _insert(conn, kind, name, payload)
        for name, rarity, category, subtype, description in ITEMS:
            _insert(conn, "item", name, {
                "name": name, "rarity": rarity, "category": category,
                "subtype": subtype, "description": description,
                "attunement": "Attunement" in rarity,
            })
    conn.commit()


def _insert(conn, kind, name, payload):
    slug = canon.slugify(name)
    db.insert_record(conn, {
        "id": canon.record_id("srd", kind, "en", slug), "layer": "srd",
        "kind": kind, "lang": "en", "slug": slug, "name": name,
        "data": canon.canonical_json(payload),
        "content_hash": canon.content_hash(kind, "en", name, payload),
        "source_id": "t", "source_locator": "p.1", "srd_version": "5.2.1",
        "license": "CC-BY-4.0", "attribution": "a",
    })


def _data(conn, name):
    row = conn.execute(
        "SELECT data FROM record WHERE layer='srfh' AND name=?", (name,)
    ).fetchone()
    return json.loads(row["data"]) if row else None


# ---------------------------------------------------------------------------
# The readers, on the spellings that actually appear in this catalogue
# ---------------------------------------------------------------------------
@case
def a_thousands_separator_is_not_a_decimal_point(conn):
    """`1,000 GP` parsed naively is 1. That is the whole failure mode."""
    assert srfh._gp("1,500 GP") == 1500.0, srfh._gp("1,500 GP")
    assert srfh._gp("50 GP") == 50.0
    assert srfh._gp("5 CP") == 0.05, srfh._gp("5 CP")
    assert srfh._gp("1 SP") == 0.1


@case
def both_spellings_of_a_half_are_read(conn):
    """`1/2 lb.` and `58½ lb.` live in the same file. A reader that handles one
    and not the other is silently wrong on the other."""
    assert srfh._lb("1/2 lb.") == 0.5
    assert srfh._lb("58½ lb.") == 58.5, srfh._lb("58½ lb.")
    assert srfh._lb("5 lb. (full)") == 5.0
    assert srfh._lb("1/4 lb.") == 0.25


@case
def the_em_dash_is_a_value_not_an_absence(conn):
    """`—` means "negligible". It is neither zero nor missing."""
    assert srfh._lb("—") is None
    mass = srfh._mass(None, "t")
    assert mass["negligible"] is True and "value" not in mass, mass
    assert srfh._mass(3.0, "t")["value"] == 3.0


@case
def the_oxford_comma_is_one_separator(conn):
    """`A, B, or C` names three bases -- not two and a base called `or C`."""
    assert srfh._split_bases("Battleaxe, Greataxe, or Halberd") == [
        "Battleaxe", "Greataxe", "Halberd"]
    assert srfh._split_bases("Maul or Warhammer") == ["Maul", "Warhammer"]


@case
def very_rare_is_not_rare(conn):
    """Reading the tier by prefix puts `Rare` before `Very Rare` unless the
    longest label wins first."""
    assert srfh._tier_of("Very Rare (Requires Attunement)") == "Very Rare"
    assert srfh._tier_of("Rare") == "Rare"
    assert srfh._tier_of("Rarity Varies") == "Rarity Varies"


@case
def the_attunement_condition_gets_its_own_field(conn):
    """Two facts in one string is two fields: the book keeps *who may attune*
    inside the rarity, where nothing can read it."""
    assert srfh._attunement_by(
        "Rare (Requires Attunement by a Bard)") == "a Bard"
    assert srfh._attunement_by("Rare (Requires Attunement)") is None


@case
def a_family_member_is_named_as_the_book_names_it(conn):
    assert srfh._member_name("Potions of Healing", "standard") == "Potion of Healing"
    assert srfh._member_name(
        "Potions of Healing", "greater") == "Potion of Healing (greater)"


# ---------------------------------------------------------------------------
# The layer, against a stand-in catalogue
# ---------------------------------------------------------------------------
@case
def the_srd_rows_are_byte_identical_afterwards(conn):
    """The layer adds rows of its own. It never edits the base."""
    before = conn.execute(
        "SELECT id, content_hash FROM record WHERE layer='srd' ORDER BY id"
    ).fetchall()
    srfh.RATIFIED, keep = FIXTURE_RATIFIED, srfh.RATIFIED
    try:
        srfh.build_srfh(conn)
    finally:
        srfh.RATIFIED = keep
    after = conn.execute(
        "SELECT id, content_hash FROM record WHERE layer='srd' ORDER BY id"
    ).fetchall()
    assert [tuple(r) for r in before] == [tuple(r) for r in after], \
        "an SRD row changed while the layer above it was written"


@case
def every_srfh_record_points_down_at_the_base(conn):
    orphans = conn.execute(
        "SELECT count(*) FROM record r WHERE r.layer='srfh'"
        " AND NOT EXISTS (SELECT 1 FROM record_link l WHERE l.src_id = r.id)"
    ).fetchone()[0]
    assert orphans == 0, "%d SRFH record(s) point at nothing" % orphans


@case
def the_improvements_are_left_alone(conn):
    """A `+1/+2/+3` entry is an improvement, not an object. Eric, 2026-08-23."""
    assert _data(conn, "Weapon, +1, +2, or +3") is None


@case
def a_replaced_family_sheet_gets_no_record_of_its_own(conn):
    assert _data(conn, "Potions of Healing") is None
    assert _data(conn, "Potion of Healing")["rarity_tier"] == "Common"
    assert _data(conn, "Potion of Healing (supreme)")["rarity_tier"] == "Very Rare"


@case
def a_consumable_costs_half_the_table(conn):
    """p.206 halves a consumable, and the book proves its own rule: it sells a
    Potion of Healing for 50 GP, which is half of Common."""
    assert _data(conn, "Potion of Healing")["cost"]["value"] == 50.0
    assert _data(conn, "Potion of Climbing")["cost"]["value"] == 50.0
    assert _data(conn, "Potion of Healing (greater)")["cost"]["value"] == 200.0
    # and a non-consumable of the same tier is NOT halved
    assert _data(conn, "Wand of Magic Missiles")["cost"]["value"] == 400


@case
def the_base_price_is_added_when_the_book_names_one_base(conn):
    """p.206: *+1 Armor (Plate Armor) has a value of 5,500 GP* -- the tier plus
    the armor. With one named base the addition has one answer, so it is done
    here rather than left to the reader."""
    cost = _data(conn, "Armor of Invulnerability")["cost"]
    assert cost["value"] == 200000, cost
    assert cost["plus_base"]["options"][0]["value"] == 1500.0, cost
    assert cost["total"] == 201500.0, cost


@case
def several_bases_are_offered_and_never_averaged(conn):
    """Two bases of different weights have no single answer. Naming both is the
    answer; picking one silently is not."""
    weight = _data(conn, "Vorpal Sword")["weight"]
    assert weight["from_base"] is True
    assert [o["base"] for o in weight["options"]] == ["Greatsword", "Longsword"]
    assert {o["value"] for o in weight["options"]} == {6.0, 3.0}
    assert "value" not in weight, weight


@case
def an_open_family_names_the_family_and_stops(conn):
    """`Any Simple or Martial` -- the book itself refuses to name a base, so
    the layer says so instead of inventing one."""
    weight = _data(conn, "Vicious Weapon")["weight"]
    assert weight["family"] == "Any Simple or Martial", weight
    assert "value" not in weight and "options" not in weight


@case
def the_focus_table_gives_the_wand_the_rod_and_the_staff(conn):
    """p.96 prints these three weights. They are inherited, not chosen."""
    assert _data(conn, "Wand of Magic Missiles")["weight"]["value"] == 1.0
    assert _data(conn, "Rod of Rulership")["weight"]["value"] == 2.0
    assert _data(conn, "Staff of Charming")["weight"]["value"] == 4.0


@case
def a_wondrous_item_with_an_everyday_twin_inherits_it(conn):
    weight = _data(conn, "Manual of Golems")["weight"]
    assert weight["value"] == 5.0 and weight["provenance"] == "inherited:Book", weight


@case
def a_chosen_weight_says_that_it_was_chosen(conn):
    """The only values here the book does not justify. They must be legible as
    decisions, not hidden among the inherited ones."""
    weight = _data(conn, "Cloak of Elvenkind")["weight"]
    assert weight["value"] == 1.0
    assert weight["provenance"].startswith("chosen:"), weight
    assert _data(conn, "Ring of Regeneration")["weight"]["provenance"].startswith("chosen:")


@case
def an_artifact_is_priceless_and_not_zero(conn):
    cost = _data(conn, "Dragon Orb")["cost"]
    assert cost["priceless"] is True and "value" not in cost, cost


@case
def the_scroll_is_a_parchment_plus_an_improvement(conn):
    """Eric, 2026-08-23: *parchemin + boost (sort) dans craft*. It keeps no tier
    price, and its null tier says why it is null."""
    scroll = _data(conn, "Spell Scroll")
    assert scroll["rarity_tier"] is None
    assert "varies with the spell" in scroll["rarity_note"], scroll
    assert scroll["cost"]["provenance"] == "base-plus-improvement"
    assert "value" not in scroll["cost"]


@case
def every_value_can_say_where_it_came_from(conn):
    """A value without a provenance is a value nobody can correct."""
    for row in conn.execute("SELECT name, data FROM record WHERE layer='srfh'"):
        payload = json.loads(row["data"])
        for field in ("cost", "weight"):
            assert payload[field].get("provenance"), \
                "%s: %s carries no provenance" % (row["name"], field)


@case
def a_weight_is_a_number_or_negligible_or_from_a_base_never_two(conn):
    for row in conn.execute("SELECT name, data FROM record WHERE layer='srfh'"):
        weight = json.loads(row["data"])["weight"]
        shape = sum(1 for k in ("value", "negligible", "from_base") if k in weight)
        assert shape == 1, "%s: weight is %r" % (row["name"], weight)


@case
def the_layer_is_not_shipped_under_the_wotc_grant(conn):
    """`cc_by_srd` answers "what may I publish under the upstream licence?".
    These values are ours; the grant does not cover them."""
    leaked = conn.execute(
        "SELECT count(*) FROM publishable_srd WHERE layer='srfh'"
    ).fetchone()[0]
    assert leaked == 0, "%d SRFH record(s) leaked into the CC-BY export" % leaked


@case
def the_licence_is_open_and_says_so(conn):
    """Eric has not decided what people may do with this layer. Defaulting it
    to `proprietary` would answer for him, in the direction he did not ask."""
    row = conn.execute("SELECT license FROM layer WHERE id='srfh'").fetchone()
    assert row["license"] == "undecided", row["license"]
    assert srfh.LICENSE == "undecided"


@case
def a_family_that_changes_size_stops_the_build(conn):
    """These counts are ratified values. Drifting past one in silence is the
    single outcome that must not happen."""
    keep = srfh.FAMILY_COUNT["Potions of Healing"]
    srfh.FAMILY_COUNT["Potions of Healing"] = 99
    try:
        conn.execute("DELETE FROM record_link")
        conn.execute("DELETE FROM record WHERE layer='srfh'")
        srfh.build_srfh(conn)
    except srfh.SrfhError as exc:
        assert "yielded" in str(exc) and "ratified" in str(exc), exc
        return
    finally:
        srfh.FAMILY_COUNT["Potions of Healing"] = keep
    raise AssertionError("a family sheet changed size and the build carried on")


@case
def a_catalogue_that_moves_stops_the_build(conn):
    """Same guard, one level up: the shape of the whole layer."""
    conn.execute("DELETE FROM record_link")
    conn.execute("DELETE FROM record WHERE layer='srfh'")
    keep = srfh.RATIFIED
    srfh.RATIFIED = dict(FIXTURE_RATIFIED, extends=999)
    try:
        srfh.build_srfh(conn)
    except srfh.SrfhError as exc:
        assert "moved under values" in str(exc), exc
        return
    finally:
        srfh.RATIFIED = keep
    raise AssertionError("the catalogue moved and the layer followed in silence")


@case
def the_ratified_shape_adds_up(conn):
    """Eric's numbers, checked against each other rather than trusted."""
    r = srfh.RATIFIED
    assert r["extends"] + r["members"] == 294, "the layer is not 294 records"
    wondrous = r["twin"] + sum(
        r[b] for b in ("jewellery", "worn-soft", "held", "worn-rigid", "bulky"))
    assert wondrous == 160, "the wondrous items do not add up to 160: %d" % wondrous


def main():
    if os.path.exists(DB):
        os.remove(DB)
    conn = db.create(DB)
    seed(conn)
    for fn in CASES:
        fn(conn)
        print("  ok  %s" % fn.__name__)
    conn.close()
    os.remove(DB)
    print("PASS test_srfh  (%d checks)" % len(CASES))


if __name__ == "__main__":
    main()
