"""Shelving: every object gets a shelf, no name is analysed, no key is trusted.

Each rule below is checked by BREAKING it. The failures worth guarding against
here are the ones that do not raise:

  * a name rule that looks right and quietly mis-files an object — three of the
    four obvious ones do, measured on this very catalogue;
  * a key tested for presence instead of value — `item.subtype` is present
    258/258 and null 206 of those, so `"subtype" in data` is always true and
    always useless;
  * an object that falls through every branch and comes back with no shelf,
    which is the one outcome the lot exists to prevent;
  * a worn object answered "not worn" because nobody ever asked.
"""

import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import canon  # noqa: E402
import db  # noqa: E402
import shelving  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "build", "shelving-test.sqlite")

CASES = []


def case(fn):
    CASES.append(fn)
    return fn


# --- a stand-in catalogue --------------------------------------------------
# All 82 gear names are seeded, because the module refuses a table key that
# names no record — and rightly so. The rest is one row per branch.
WEAPONS = [("Longsword", "melee"), ("Shortbow", "ranged")]
ARMORS = [("Breastplate", "medium"), ("Shield", "shield")]
TOOLS = ["Thieves’ Tools", "Smith’s Tools"]
ITEMS = [
    # name, category, subtype  -- subtype is deliberately null on most of them
    ("Ring of Invisibility", "ring", None),
    ("Potion of Climbing", "potion", None),
    ("Wand of Magic Missiles", "wand", None),
    ("Rod of Rulership", "rod", None),
    ("Staff of Charming", "staff", None),
    ("Spell Scroll", "scroll", None),
    ("Cloak of Elvenkind", "wondrous-item", None),
    ("Sun Blade", "weapon", "Longsword"),
    ("Adamantine Armor", "armor", "Any Medium or Heavy, Except Hide Armor"),
]

# The stand-in catalogue is not Eric's, so its counts are not his either.
FIXTURE_SHELF_COUNT = dict(shelving.GEAR_SHELF_COUNT)
FIXTURE_SHELF_COUNT.update({
    ("adventuring", "camp"): 3,
    ("arcana", "consumables-and-potions"): 10,     # 9 gear + 1 potion
    ("arcana", "scrolls-foci-components"): 7,      # 6 gear + 1 scroll
    ("arcana", "wands-rods-staves"): 3,
    ("battlefield", "armor"): 2,
    ("battlefield", "magic-armor"): 1,
    ("battlefield", "magic-weapons"): 1,
    ("battlefield", "melee-weapons"): 1,
    ("battlefield", "projectiles"): 1,             # the Ammunition gear row
    ("battlefield", "thrown-weapons"): 1,
    ("companions", "familiars"): 0,
    ("companions", "henchmen"): 0,
    ("crafting", "gems"): 0,
    ("crafting", "ingredients"): 0,
    ("crafting", "tools"): 2,
    ("marvels", "rings"): 1,
    ("marvels", "wondrous"): 1,
})
FIXTURE_TOTAL = 97                                  # 82 + 2 + 2 + 2 + 9
FIXTURE_SLOT_COUNT = {"fingers": 1, "hands": 3, "torso": 1}
FIXTURE_SLOT_TALLY = {"decided": 5, "from_base": 2, "pending": 6, "not_worn": 84}
FIXTURE_CRAFTABLE = 7                               # 2 + 2 + 3 named gear rows


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


def seed(conn):
    conn.execute(
        """INSERT INTO source (id,title,publisher,version,lang,url,sha256,bytes,
                               license,license_url,attribution)
           VALUES ('t','t','t','5.2.1','en','u','h',1,'CC-BY-4.0','u','a')"""
    )
    with db.srd_write(conn):
        for name in shelving.SHELF_OF_GEAR:
            _insert(conn, "gear", name,
                    {"name": name, "cost": "1 GP", "weight": "1 lb."})
        for name in TOOLS:
            _insert(conn, "tool", name, {"name": name, "cost": "1 GP"})
        for name, rng in WEAPONS:
            _insert(conn, "weapon", name, {
                "name": name, "weapon_range": rng, "weapon_category": "martial"})
        for name, cat in ARMORS:
            _insert(conn, "armor", name, {"name": name, "armor_category": cat})
        for name, category, subtype in ITEMS:
            _insert(conn, "item", name, {
                "name": name, "category": category, "subtype": subtype,
                "rarity": "Rare", "attunement": False, "description": ""})
    conn.commit()


def _rebuild(conn):
    """Run the layer against the fixture's own ratified shape."""
    conn.execute("DELETE FROM record_link")
    conn.execute("DELETE FROM record WHERE layer='srfh'")
    keep = (shelving.RATIFIED_TOTAL, shelving.RATIFIED_SHELF_COUNT,
            shelving.RATIFIED_SLOT_COUNT, shelving.RATIFIED_SLOT_TALLY,
            shelving.RATIFIED_CRAFTABLE)
    shelving.RATIFIED_TOTAL = FIXTURE_TOTAL
    shelving.RATIFIED_SHELF_COUNT = FIXTURE_SHELF_COUNT
    shelving.RATIFIED_SLOT_COUNT = FIXTURE_SLOT_COUNT
    shelving.RATIFIED_SLOT_TALLY = FIXTURE_SLOT_TALLY
    shelving.RATIFIED_CRAFTABLE = FIXTURE_CRAFTABLE
    try:
        return shelving.build_shelving(conn)
    finally:
        (shelving.RATIFIED_TOTAL, shelving.RATIFIED_SHELF_COUNT,
         shelving.RATIFIED_SLOT_COUNT, shelving.RATIFIED_SLOT_TALLY,
         shelving.RATIFIED_CRAFTABLE) = keep


def _data(conn, name):
    row = conn.execute(
        "SELECT data FROM record WHERE layer='srfh' AND kind='shelving' AND name=?",
        (name,)).fetchone()
    return json.loads(row["data"]) if row else None


# ---------------------------------------------------------------------------
# The name lies — the four rules, measured
# ---------------------------------------------------------------------------
@case
def the_four_obvious_name_rules_are_all_wrong_here(conn):
    """Three of the four break on their first object, and the table proves it."""
    shelf = shelving.SHELF_OF_GEAR
    # "ends with pack" -> a pack. Catches Backpack, which is a container.
    assert shelf["Backpack"] == ("mundane", "containers")
    assert shelf["Burglar’s Pack"] == ("adventuring", "packs")
    # "contains scroll" -> magic. Catches a case.
    assert shelf["Case, Map or Scroll"] == ("mundane", "containers")
    assert shelf["Spell Scroll (Cantrip)"] == ("arcana", "scrolls-foci-components")
    # "contains pouch" -> a container. One word, two shelves.
    assert shelf["Pouch"] == ("mundane", "containers")
    assert shelf["Component Pouch"] == ("arcana", "scrolls-foci-components")


@case
def a_gear_row_the_table_does_not_name_stops_the_build(conn):
    """The forbidden repair is a name rule. So the absence must be loud."""
    with db.srd_write(conn):
        _insert(conn, "gear", "Bag of Nothing",
                {"name": "Bag of Nothing", "cost": "1 GP", "weight": "1 lb."})
    conn.commit()
    try:
        _rebuild(conn)
    except shelving.ShelvingError as exc:
        assert "Bag of Nothing" in str(exc), exc
        assert "no name rule may be invented" in str(exc), exc
    else:
        raise AssertionError("an unshelved object passed through in silence")
    finally:
        with db.srd_write(conn):
            conn.execute(
                "DELETE FROM record WHERE layer='srd' AND name='Bag of Nothing'")
        conn.commit()


@case
def a_table_key_that_names_nothing_stops_the_build(conn):
    """The other direction: a rename upstream must not pass unnoticed."""
    keep = dict(shelving.SHELF_OF_GEAR)
    keep_counts = dict(shelving.GEAR_SHELF_COUNT)
    shelving.SHELF_OF_GEAR["Backpacke"] = ("mundane", "containers")
    shelving.GEAR_SHELF_COUNT[("mundane", "containers")] = 17
    try:
        _rebuild(conn)
    except shelving.ShelvingError as exc:
        assert "Backpacke" in str(exc), exc
    else:
        raise AssertionError("a table key naming no record went unnoticed")
    finally:
        shelving.SHELF_OF_GEAR.clear()
        shelving.SHELF_OF_GEAR.update(keep)
        shelving.GEAR_SHELF_COUNT.clear()
        shelving.GEAR_SHELF_COUNT.update(keep_counts)


@case
def the_transcription_adds_up_to_the_documents_own_counts(conn):
    """16+10+9+8+7+6+6+6+5+5+3+1 = 82. A free check on the transcription."""
    assert sum(shelving.GEAR_SHELF_COUNT.values()) == 82
    assert len(shelving.SHELF_OF_GEAR) == 82
    measured = {}
    for shelf in shelving.SHELF_OF_GEAR.values():
        measured[shelf] = measured.get(shelf, 0) + 1
    assert measured == shelving.GEAR_SHELF_COUNT, measured


# ---------------------------------------------------------------------------
# The absence is not an answer
# ---------------------------------------------------------------------------
@case
def the_subtype_key_is_never_read_for_a_shelf(conn):
    """Present 258/258, null 206 of those. Testing the key answers nothing."""
    for subtype in (None, "", "Any Simple or Martial", "Longsword"):
        data = {"name": "x", "category": "weapon", "subtype": subtype,
                "rarity": "Rare", "attunement": False, "description": ""}
        assert shelving.shelf_of("item", "x", data) == (
            "battlefield", "magic-weapons", "derived:item.category")


@case
def an_unanswered_slot_says_so_instead_of_saying_no(conn):
    """`worn=False` for want of a table is a wrong answer in a right costume."""
    _rebuild(conn)
    cloak = _data(conn, "Cloak of Elvenkind")["slot"]
    assert cloak["worn"] is None, cloak
    assert "merveilleux-ranges.json" in cloak["pending"], cloak
    robe = _data(conn, "Robe")["slot"]
    assert robe["worn"] is None, robe
    assert robe.get("pending"), robe
    # and a thing that genuinely is not worn says THAT, positively
    barrel = _data(conn, "Barrel")["slot"]
    assert barrel["worn"] is False and "pending" not in barrel, barrel


# ---------------------------------------------------------------------------
# Two axes, not one
# ---------------------------------------------------------------------------
@case
def one_shelf_can_hold_two_different_slots(conn):
    """The whole reason these are two fields and two functions."""
    _rebuild(conn)
    shield, plate = _data(conn, "Shield"), _data(conn, "Breastplate")
    assert shield["shelf"] == plate["shelf"], (shield["shelf"], plate["shelf"])
    assert shield["slot"]["slot"] == "hands"
    assert plate["slot"]["slot"] == "torso"


@case
def a_magic_weapon_wears_whatever_base_it_was_laid_on(conn):
    """`Any Simple or Martial` names no single base, so no single slot."""
    _rebuild(conn)
    for name in ("Sun Blade", "Adamantine Armor"):
        slot = _data(conn, name)["slot"]
        assert slot["from_base"] is True and "slot" not in slot, (name, slot)


@case
def fingers_is_the_only_slot_left_open(conn):
    """And it is the silhouette's shape, not a rule of the game."""
    open_slots = [s for s, cap in shelving.SLOT_CAPACITY.items() if cap is None]
    assert open_slots == ["fingers"], open_slots
    assert len(shelving.SLOTS) == 10
    # No exclusivity is written onto an object: a slot places, it never forbids.
    _rebuild(conn)
    for row in conn.execute(
            "SELECT data FROM record WHERE layer='srfh' AND kind='shelving'"):
        assert "capacity" not in json.loads(row["data"])["slot"]


# ---------------------------------------------------------------------------
# Nothing is written down twice, and everything says where it came from
# ---------------------------------------------------------------------------
@case
def what_derives_is_never_also_written(conn):
    """A value carried in two places ends up disagreeing with itself."""
    written = set(shelving.SHELF_OF_GEAR)
    for name, _cat, _sub in ITEMS:
        assert name not in written, name
    for name, _rng in WEAPONS + ARMORS:
        assert name not in written, name
    for kind, name, data in (
        ("weapon", "Longsword", {"weapon_range": "melee"}),
        ("armor", "Shield", {"armor_category": "shield"}),
        ("item", "x", {"category": "ring", "subtype": None}),
    ):
        _a, _s, provenance = shelving.shelf_of(kind, name, data)
        assert provenance.startswith("derived:"), (kind, provenance)


@case
def every_value_carries_its_provenance(conn):
    """The form the layer below already uses. A value nobody can trace is a
    value nobody can correct."""
    _rebuild(conn)
    n = 0
    for row in conn.execute(
            "SELECT data FROM record WHERE layer='srfh' AND kind='shelving'"):
        data = json.loads(row["data"])
        for field in ("shelf", "slot", "craftable"):
            assert data[field].get("provenance"), (data["name"], field)
        n += 1
    assert n == FIXTURE_TOTAL, n


@case
def the_srd_row_is_never_touched(conn):
    """The layer adds its own rows and points down. Nothing else is allowed."""
    _rebuild(conn)
    for row in conn.execute(
            "SELECT data FROM record WHERE layer='srd' AND kind='gear'"):
        assert "shelf" not in json.loads(row["data"])
    edges = conn.execute(
        "SELECT count(*) FROM record_link rl JOIN record r ON r.id = rl.src_id"
        " WHERE r.kind='shelving'").fetchone()[0]
    assert edges == FIXTURE_TOTAL, edges


# ---------------------------------------------------------------------------
# The shape, and what happens when the catalogue moves under it
# ---------------------------------------------------------------------------
@case
def a_catalogue_that_moves_stops_the_build(conn):
    keep = shelving.RATIFIED_SHELF_COUNT
    try:
        conn.execute("DELETE FROM record_link")
        conn.execute("DELETE FROM record WHERE layer='srfh'")
        bad = dict(FIXTURE_SHELF_COUNT)
        bad[("marvels", "rings")] = 99
        shelving.RATIFIED_SHELF_COUNT = bad
        shelving.RATIFIED_TOTAL = FIXTURE_TOTAL
        try:
            shelving.build_shelving(conn)
        except shelving.ShelvingError as exc:
            assert "arrested by hand" in str(exc), exc
        else:
            raise AssertionError("the shape moved and the layer followed")
    finally:
        shelving.RATIFIED_SHELF_COUNT = keep
        shelving.RATIFIED_TOTAL = 416


@case
def erics_numbers_are_checked_against_each_other(conn):
    """Not trusted: added up. If they disagree it is the transcription that is
    wrong, and it should say so here rather than at the far end of a build."""
    assert sum(shelving.RATIFIED_SHELF_COUNT.values()) == 416
    assert sum(shelving.RATIFIED_SLOT_TALLY.values()) == 416
    # The document's own body-slot arithmetic: 22+13+10+8+7+5+4+4+2+2 = 77
    # worn marvels. 22 of them are the rings, and the rings are the only ones
    # this layer can place today; the other 55 are the pending wondrous items.
    assert shelving.RATIFIED_SLOT_COUNT["fingers"] == 22
    assert shelving.RATIFIED_SLOT_TALLY["pending"] == 127 + 5
    assert 22 + 55 == 77
    # Every shelf named in an aisle has a ratified count, and no count names a
    # shelf that is in no aisle.
    declared = {(a, s) for a in shelving.SHELVES for s in shelving.SHELVES[a]}
    assert declared == set(shelving.RATIFIED_SHELF_COUNT), (
        declared ^ set(shelving.RATIFIED_SHELF_COUNT))
    assert len(shelving.SHELVES) == 7


@case
def the_provisional_is_flagged_as_provisional(conn):
    """`Arcana` and `Marvels` are proposed names, never ratified. Using one is
    not agreeing to it, and a reader holding a single row must be able to see
    the difference."""
    _rebuild(conn)
    acid = _data(conn, "Acid")["shelf"]
    assert acid["aisle"] == "arcana" and acid["aisle_name_provisional"] is True
    book = _data(conn, "Book")["shelf"]
    assert book["aisle"] == "mundane" and book["aisle_name_provisional"] is False
    assert _data(conn, "Cloak of Elvenkind")["shelf"]["shelf_provisional"] is True
    assert _data(conn, "Longsword")["shelf"]["shelf_provisional"] is False


@case
def craftable_is_a_genre_test_and_not_a_rarity_calculation(conn):
    """Measured, because §6 asked for the measurement rather than a decision."""
    assert shelving.craftable_of("weapon", "Longsword")["value"] is True
    assert shelving.craftable_of("armor", "Shield")["value"] is True
    assert shelving.craftable_of("gear", "Ammunition")["value"] is True
    assert shelving.craftable_of("gear", "Backpack")["value"] is False
    assert shelving.craftable_of("item", "Sun Blade")["value"] is False
    # Only three rows need naming; everything else falls out of the record kind.
    assert len(shelving.CRAFT_BASE_GEAR) == 3
    assert shelving.RATIFIED_CRAFTABLE == 38 + 13 + 3


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
    print("PASS test_shelving  (%d checks)" % len(CASES))


if __name__ == "__main__":
    main()
