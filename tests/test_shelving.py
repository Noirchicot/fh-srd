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
    ("Potion of Climbing", "potion", None),
    ("Wand of Magic Missiles", "wand", None),
    ("Rod of Rulership", "rod", None),
    ("Staff of Charming", "staff", None),
    ("Spell Scroll", "scroll", None),
    ("Sun Blade", "weapon", "Longsword"),
    ("Adamantine Armor", "armor", "Any Medium or Heavy, Except Hide Armor"),
]
# The 22 rings and the 127 marvels are not a choice the fixture gets to make.
# The layer refuses a marvel it cannot name and refuses a name that is on no
# record, so the stand-in catalogue has to carry all 149 — and the rings are
# there because `marvels/rings` is one of Eric's seven counts and a guard that
# checks a constant against itself checks nothing.
ITEMS += [("Ring %02d" % i, "ring", None) for i in range(1, 23)]
ITEMS += [(name, "wondrous-item", None) for name in sorted(shelving.MARVEL)]

# The stand-in catalogue is not Eric's, so its counts are not his either.
FIXTURE_SHELF_COUNT = dict(shelving.GEAR_SHELF_COUNT)
FIXTURE_SHELF_COUNT.update({
    ("adventuring", "camp"): 3,
    ("arcana", "consumables-and-potions"): 10,     # 9 gear + 1 potion
    ("arcana", "scrolls-foci-components"): 7,      # 6 gear + 1 scroll
    ("arcana", "wands-rods-staves"): 3,
    ("armory", "armor"): 2,
    ("armory", "magic-armor"): 1,
    ("armory", "magic-weapons"): 1,
    ("armory", "melee-weapons"): 1,
    ("armory", "ranged-weapons"): 2,          # 1 ranged weapon + the Ammunition gear row
    # ✅ Les QUATRE entrées de `companions`, ratifiées par Eric le 2026-08-24.
    ("companions", "bespoke"): 0,
    ("companions", "familiars"): 0,
    ("companions", "henchmen"): 0,
    ("companions", "monster-search"): 0,
    # ✅ ERIC, 2026-09-24 : une seule etagere `blueprints` pour les quatre plans
    # du Soulforging. `gems` et `ingredients` sont RETIREES -- la premiere est
    # morte le 23/09 (les pierres sont chez `trade-goods`), la seconde ne sera
    # jamais peuplee (un ingredient se fait SUR MESURE, il naît dans l'inventaire
    # d'un personnage, pas dans le catalogue).
    ("crafting", "blueprints"): 0,
    ("crafting", "tools"): 2,
    # ✅ Le rayon `trade-goods` d'Eric (23/09), déclaré et VIDE des deux côtés :
    # le SRD ne porte ni gemme ni marchandise, et le catalogue fabriqué de ce
    # fichier n'en porte pas davantage. ⭐ C'est le cas que le garde doit tenir :
    # une étagère à zéro EXISTE dans la structure et ne paraît PAS au tambour.
    ("trade-goods", "commodities"): 0,
    ("trade-goods", "gems"): 0,
})
# The marvel half of the fixture IS Eric's, because it has to be.
FIXTURE_SHELF_COUNT.update({
    ("marvels", shelf): n for shelf, n in shelving.MARVEL_SHELF_COUNT.items()})
FIXTURE_TOTAL = 244                                 # 82 + 2 + 2 + 2 + 156
FIXTURE_SLOT_COUNT = {
    "back": 10, "eyes": 4, "feet": 7, "fingers": 22, "forearms": 2,
    "hands": 7,        # 4 marvels + Longsword + Shortbow + the Shield
    "head": 8, "neck": 13,
    "torso": 6,        # 5 robes + the Breastplate
    "waist": 2,
}
FIXTURE_SLOT_TALLY = {"decided": 81, "from_base": 2, "pending": 5,
                      "not_worn": 156}
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
            # A marvel's description is its own justification: the layer checks
            # that the sentence it files an object on is REALLY IN that
            # object's text, so a fixture with an empty description would be a
            # fixture that cannot exercise the guard at all.
            description = ""
            if category == "wondrous-item":
                description = shelving.MARVEL[name][2]
            _insert(conn, "item", name, {
                "name": name, "category": category, "subtype": subtype,
                "rarity": "Rare", "attunement": False,
                "description": description})
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
            "armory", "magic-weapons", "derived:item.category")


@case
def an_unanswered_slot_says_so_instead_of_saying_no(conn):
    """`worn=False` for want of a table is a wrong answer in a right costume."""
    _rebuild(conn)
    # A mundane robe: obviously worn, and the source never said where. Neither
    # `torso` nor `not worn` may be invented for it.
    robe = _data(conn, "Robe")["slot"]
    assert robe["state"] == "unanswered" and robe["worn"] is None, robe
    assert robe.get("pending"), robe
    # A thing that genuinely is not worn says THAT, positively, and says why.
    barrel = _data(conn, "Barrel")["slot"]
    assert barrel["state"] == "not_worn" and barrel["worn"] is False, barrel
    assert "pending" not in barrel, barrel
    # And a marvel refused a slot is refused on its own sentence, never on a
    # missing table: the hat is a hat and the SRD still never says wear.
    hat = _data(conn, "Hat of Many Spells")["slot"]
    assert hat["state"] == "not_worn", hat
    assert hat["provenance"].startswith("srd:While holding the hat"), hat


@case
def the_four_states_are_four_and_each_one_names_itself(conn):
    """🔴 The distinction this lot exists for. `not_worn` is a measurement and
    `unanswered` is the lack of one; a reader must never have to tell them apart
    by looking at a null, because two readers consume this — the silhouette and
    the Soulforge — and neither should have to guess."""
    _rebuild(conn)
    seen = {}
    for row in conn.execute(
            "SELECT data FROM record WHERE layer='srfh' AND kind='shelving'"):
        slot = json.loads(row["data"])["slot"]
        assert "state" in slot, slot
        seen[slot["state"]] = seen.get(slot["state"], 0) + 1
        assert slot.get("provenance"), slot
        if slot["state"] == "worn":
            assert slot["slot"] in shelving.SLOTS and slot["worn"] is True, slot
        elif slot["state"] == "from_base":
            assert slot["from_base"] is True and "slot" not in slot, slot
        elif slot["state"] == "not_worn":
            assert slot["worn"] is False and "pending" not in slot, slot
        elif slot["state"] == "unanswered":
            assert slot["worn"] is None and slot["pending"], slot
        else:
            raise AssertionError(slot["state"])
    assert set(seen) == {"worn", "from_base", "not_worn", "unanswered"}, seen
    assert seen == {"worn": FIXTURE_SLOT_TALLY["decided"],
                    "from_base": FIXTURE_SLOT_TALLY["from_base"],
                    "not_worn": FIXTURE_SLOT_TALLY["not_worn"],
                    "unanswered": FIXTURE_SLOT_TALLY["pending"]}, seen


# ---------------------------------------------------------------------------
# The 149 marvels
# ---------------------------------------------------------------------------
@case
def the_seven_counts_eric_arrested_all_land(conn):
    """⭐ The verification that costs nothing. He printed seven numbers on
    2026-08-21 from a classification he made by hand; landing on all seven is
    what says the table is his and not a second opinion in his labels."""
    assert sum(shelving.MARVEL_SHELF_COUNT.values()) == 149
    assert len(shelving.MARVEL) == 127            # 149 less the 22 rings
    measured = {}
    for shelf, _slot, _why in shelving.MARVEL.values():
        measured[shelf] = measured.get(shelf, 0) + 1
    measured["rings"] = 22
    assert measured == shelving.MARVEL_SHELF_COUNT, measured
    # And no shelf is a drawer of 127 any more: the screen is aimed at 35.
    # 33 → 34 le 2026-08-24 : la Perle de puissance rejoint `foci-and-curios`,
    # ratifié par Eric. ⭐ ET LE CRITÈRE EST DIT À CÔTÉ DU CHIFFRE, parce que
    # c'est lui qui compte : Eric a écrit « moins de 35 items sur la dernière
    # catégorie, c'est l'idée ». Le chiffre exact attrape une dérive muette ; la
    # borne dit à un lecteur POURQUOI on la surveille.
    assert max(shelving.RATIFIED_SHELF_COUNT.values()) == 34
    assert max(shelving.RATIFIED_SHELF_COUNT.values()) < 35, (
        "une étagère atteint la cible d'Eric — c'est le découpage qu'on refait, "
        "jamais la donnée qu'on refuse")
    # The ten slots, as the source read them off the marvels: 77, no remainder.
    worn = {}
    for _shelf, slot, _why in shelving.MARVEL.values():
        if slot:
            worn[slot] = worn.get(slot, 0) + 1
    worn["fingers"] = 22
    assert sum(worn.values()) == 77, worn
    assert worn == {"fingers": 22, "neck": 13, "back": 10, "head": 8,
                    "feet": 7, "torso": 5, "eyes": 4, "hands": 4,
                    "forearms": 2, "waist": 2}, worn


@case
def a_reason_the_srd_does_not_contain_stops_the_build(conn):
    """⭐ The guard that separates evidence from prose. Every one of the 149
    rows carries the sentence that decides it, and the sentence is checked to be
    really in the record it justifies."""
    keep = shelving.MARVEL["Broom of Flying"]
    shelving.MARVEL["Broom of Flying"] = (
        keep[0], keep[1], "This broom is obviously a container.")
    try:
        _rebuild(conn)
    except shelving.ShelvingError as exc:
        assert "Broom of Flying" in str(exc), exc
        assert "not a justification" in str(exc), exc
    else:
        raise AssertionError("an invented reason passed through in silence")
    finally:
        shelving.MARVEL["Broom of Flying"] = keep


@case
def a_marvel_with_no_shelf_stops_the_build(conn):
    """Both directions, because they fail differently — and neither may be
    repaired by putting the object back in a drawer of 127."""
    with db.srd_write(conn):
        _insert(conn, "item", "Cloak of Nothing",
                {"name": "Cloak of Nothing", "category": "wondrous-item",
                 "subtype": None, "rarity": "Rare", "attunement": False,
                 "description": ""})
    conn.commit()
    try:
        _rebuild(conn)
    except shelving.ShelvingError as exc:
        assert "Cloak of Nothing" in str(exc), exc
    else:
        raise AssertionError("a marvel with no shelf passed through")
    finally:
        with db.srd_write(conn):
            conn.execute(
                "DELETE FROM record WHERE layer='srd' AND name='Cloak of Nothing'")
        conn.commit()

    keep = shelving.MARVEL.pop("Wind Fan")
    try:
        _rebuild(conn)
    except shelving.ShelvingError as exc:
        assert "Wind Fan" in str(exc) and "no shelf" in str(exc), exc
    else:
        raise AssertionError("a record naming no table row passed through")
    finally:
        shelving.MARVEL["Wind Fan"] = keep


@case
def the_doubts_are_named_and_counted(conn):
    """⭐ What Eric reads first. The source document announced 33 without listing
    them; this reconstruction finds 11, and the gap is said out loud rather than
    padded to match a number."""
    assert len(shelving.MARVEL_DOUBT) == 11
    for name, why in shelving.MARVEL_DOUBT.items():
        assert name in shelving.MARVEL, name
        assert len(why) > 60, name
    # The three arbitrations Eric made himself are among them, carried forward
    # as his and not re-decided here.
    for name in ("Hat of Many Spells", "Horseshoes of a Zephyr",
                 "Horseshoes of Speed", "Scarab of Protection"):
        assert name in shelving.MARVEL_DOUBT, name
    # The hat is shelved as a focus and NOT worn; the scarab is a consumable and
    # NOT worn. Both are his calls, and both are what keep the counts landing.
    assert shelving.MARVEL["Hat of Many Spells"][:2] == ("foci-and-curios", None)
    assert shelving.MARVEL["Scarab of Protection"][:2] == ("consumables", None)
    assert shelving.MARVEL["Horseshoes of Speed"][1] is None


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
    assert sum(shelving.RATIFIED_SLOT_COUNT.values()) == \
        shelving.RATIFIED_SLOT_TALLY["decided"]
    # The document's own body-slot arithmetic: 22+13+10+8+7+5+4+4+2+2 = 77 worn
    # marvels — 22 rings and 55 of the 127 wondrous rows. The two slots the
    # source says are SHARED are where its reading and this measurement meet:
    # `torso` also carries body armor, `hands` also carries weapons and the
    # shield. Eric counts the shield among his 13 armures; measured, it is in
    # the hands, which leaves 12 body armors on the torso.
    assert shelving.RATIFIED_SLOT_COUNT["fingers"] == 22
    assert shelving.RATIFIED_SLOT_COUNT["torso"] == 5 + 12
    assert shelving.RATIFIED_SLOT_COUNT["hands"] == 4 + 38 + 1
    # 🔴 Two numbers, never one. 5 unanswered is the mundane clothing and
    # nothing else; everything else that is not worn was MEASURED not worn.
    assert shelving.RATIFIED_SLOT_TALLY["pending"] == 5
    assert shelving.RATIFIED_SLOT_TALLY["not_worn"] == 231
    # Every shelf named in an aisle has a ratified count, and no count names a
    # shelf that is in no aisle.
    declared = {(a, s) for a in shelving.SHELVES for s in shelving.SHELVES[a]}
    assert declared == set(shelving.RATIFIED_SHELF_COUNT), (
        declared ^ set(shelving.RATIFIED_SHELF_COUNT))
    # 7 -> 8 le 2026-09-23 : `trade-goods`, categorie SRFH d'Eric, declaree
    # et vide du cote SRD (le livre ne porte ni gemme ni marchandise).
    assert len(shelving.SHELVES) == 8


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
    assert _data(conn, "Sun Blade")["shelf"]["shelf_provisional"] is True
    assert _data(conn, "Longsword")["shelf"]["shelf_provisional"] is False
    # `marvels/wondrous` was the last provisional shelf inside Marvels and it is
    # gone: the seven that replaced it are Eric's own, not a holding pen.
    cloak = _data(conn, "Cloak of Elvenkind")["shelf"]
    assert cloak["shelf"] == "clothing", cloak
    assert cloak["shelf_provisional"] is False, cloak
    assert cloak["aisle_name_provisional"] is True, cloak   # the NAME still is


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


# ---------------------------------------------------------------------------
# The DECLARED structure — the four shelves and the aisle that hold nothing
# ---------------------------------------------------------------------------
# ⛔ AN ABSENCE IS NOT AN ANSWER. Everything below breaks the same rule from a
# different side: a count obtained by GROUPING records can never produce a zero,
# so an empty shelf disappears and nothing anywhere says it did.


def _exported_records(conn):
    """The shelving records as the export ships them — same objects, one read."""
    _rebuild(conn)
    return [
        {"name": r["name"], "data": json.loads(r["data"])}
        for r in conn.execute(
            "SELECT name, data FROM record WHERE layer='srfh' AND kind='shelving'"
            " ORDER BY id")
    ]


@case
def the_structure_publishes_what_is_declared_not_what_is_populated(conn):
    """8 aisles and 32 shelves, where grouping the records yields 6 and 25."""
    records = _exported_records(conn)
    populated = {(r["data"]["shelf"]["aisle"], r["data"]["shelf"]["shelf"])
                 for r in records}
    assert len(set(a for a, _s in populated)) == 6, sorted(populated)
    # 26 -> 25 on 2026-09-23: Eric merged `projectiles` into `ranged-weapons`
    # ("donc ammo et les autres projectiles, a mettre dans ranged weapons"), and
    # the shelf was REMOVED from SHELVES rather than left declared at zero -- it
    # will never be filled again, unlike `companions` and `crafting`.
    assert len(populated) == 25, len(populated)

    block = shelving.declared_structure(records)["structure"]
    assert block["aisle_count"] == 8, block["aisle_count"]
    # 30 → 32 le 2026-08-24 : `companions` reçoit ses deux entrées manquantes.
    # 32 → 31 le 2026-09-23 : `armory/projectiles` fusionne dans `ranged-weapons`.
    assert block["shelf_count"] == 32, block["shelf_count"]
    # 6 -> 8 le 2026-09-23 : les deux etageres de `trade-goods`, declarees et
    # vides du cote SRD. ⭐ Eric, ce jour-la : « si elle est vide on l'affiche
    # pas, mais elle existe » -- et c'est exactement ce que cette liste dit.
    # Le tambour ne montre que les combinaisons PEUPLEES ; la STRUCTURE, elle,
    # publie ce qui est declare, y compris a zero. Les deux lectures repondent
    # a deux questions differentes, et aucune ne ment.
    assert block["empty_shelves"] == [
        "companions/bespoke", "companions/familiars", "companions/henchmen",
        "companions/monster-search",
        "crafting/blueprints",
        "trade-goods/commodities", "trade-goods/gems"], block["empty_shelves"]
    # The aisle nobody can see today is a whole aisle, and it is here at zero.
    companions = [a for a in block["aisles"] if a["aisle"] == "companions"][0]
    assert companions["count"] == 0
    # ⭐ QUATRE, ET PAS DEUX — c'est ce qui sort le rayon du cas « court » que
    # le tambour rend quand une roue a moins de trois crans. Les quatre viennent
    # du document d'Eric, ratifiées le 2026-08-24 ; elles ne sont pas inventées.
    assert [s["shelf"] for s in companions["shelves"]] == [
        "bespoke", "familiars", "henchmen", "monster-search"]
    assert len(companions["shelves"]) >= 3, (
        "un rayon sous trois crans est rendu « court » par le tambour")


@case
def emptying_a_shelf_leaves_it_published_at_zero(conn):
    """The defect, reproduced: take every record off a shelf and see it survive.

    ⭐ This is the one check that cannot pass by accident. A structure derived
    from the records would lose `mundane/writing-and-reading` the moment the
    last book left it; a structure derived from the DECLARATION keeps it and
    says 0."""
    records = _exported_records(conn)
    kept = [r for r in records
            if r["data"]["shelf"]["shelf"] != "writing-and-reading"]
    assert len(kept) < len(records), "the fixture shelves nothing there"

    block = shelving.declared_structure(kept)["structure"]
    # 30 → 32 le 2026-08-24 : `companions` reçoit ses deux entrées manquantes.
    # 32 → 31 le 2026-09-23 : `armory/projectiles` fusionne dans `ranged-weapons`.
    assert block["shelf_count"] == 32, block["shelf_count"]
    mundane = [a for a in block["aisles"] if a["aisle"] == "mundane"][0]
    writing = [s for s in mundane["shelves"]
               if s["shelf"] == "writing-and-reading"][0]
    assert writing["count"] == 0, writing
    assert "mundane/writing-and-reading" in block["empty_shelves"]


@case
def every_published_count_is_recounted_off_the_records_beside_it(conn):
    """🔴 A TOTAL THAT ADDS UP SAYS NOTHING ABOUT WHAT IT ADDED.

    416 = 416 would still hold if two shelves had swapped ten objects. So each
    of the thirty counts is compared against a SECOND, independent tally of the
    very records the block ships with — never against the ratified constants,
    which is a table checking itself."""
    records = _exported_records(conn)
    block = shelving.declared_structure(records)["structure"]

    tally = {}
    for r in records:
        s = r["data"]["shelf"]
        tally[(s["aisle"], s["shelf"])] = tally.get((s["aisle"], s["shelf"]), 0) + 1

    seen = 0
    for aisle in block["aisles"]:
        assert aisle["count"] == sum(s["count"] for s in aisle["shelves"]), aisle
        for shelf in aisle["shelves"]:
            key = (aisle["aisle"], shelf["shelf"])
            assert shelf["count"] == tally.get(key, 0), (key, shelf["count"])
            seen += 1
    # 30 → 32 le 2026-08-24 : les deux entrées rendues à `companions`.
    assert seen == 32, seen  # 32 → 31 le 2026-09-23 : `armory/projectiles` a fusionné
    assert block["shelved_total"] == len(records) == sum(tally.values())


@case
def a_record_on_an_undeclared_shelf_stops_the_export(conn):
    """The two readings can disagree, and then neither is safe to assume right."""
    records = _exported_records(conn)
    stray = json.loads(json.dumps(records[0]))
    stray["data"]["shelf"]["shelf"] = "nowhere"
    try:
        shelving.declared_structure(records + [stray])
    except shelving.ShelvingError as exc:
        assert "nowhere" in str(exc), exc
    else:
        raise AssertionError("a shelf no aisle holds was published in silence")


@case
def the_declared_order_survives_the_canonical_writer(conn):
    """⛔ THE ORDER LIVES IN LISTS, NEVER IN DICT KEYS.

    `canon.canonical_json` writes with `sort_keys=True`. A mapping of aisle ->
    shelves would come back out of the writer re-alphabetised, and the declared
    order would have been replaced by an accident of spelling with nothing
    raised. `mundane` is the witness that makes this measurable: it is the one
    aisle whose declared shelf order is NOT alphabetical."""
    records = _exported_records(conn)
    block = shelving.declared_structure(records)
    written = json.loads(canon.canonical_json(block, indent=2))["structure"]

    assert [a["aisle"] for a in written["aisles"]] == list(shelving.SHELVES)
    for aisle in written["aisles"]:
        assert [s["shelf"] for s in aisle["shelves"]] == \
            list(shelving.SHELVES[aisle["aisle"]]), aisle["aisle"]

    mundane = [a for a in written["aisles"] if a["aisle"] == "mundane"][0]
    order = [s["shelf"] for s in mundane["shelves"]]
    assert order == ["clothing", "containers", "writing-and-reading"], order

    # 🔴 ET L'ARBITRAGE DU 2026-08-24 A DÉTRUIT LE TÉMOIN DE CE TEST — il faut le
    # dire, et le remplacer.
    #
    # `mundane` était la SEULE des sept rangées hors alphabet, et c'est
    # précisément ce qui faisait de lui une preuve : si l'ordre publié était
    # celui de `SHELVES`, il ne pouvait pas être le fruit d'un tri. Eric a
    # tranché (« Je valide », §Q19 fermée) et `mundane` est trié : les sept
    # rayons sont désormais alphabétiques, et « l'ordre déclaré survit » ne se
    # distingue plus de « quelque chose l'a trié en chemin ».
    #
    # ⭐ ON FABRIQUE DONC LE TÉMOIN au lieu de l'emprunter à la donnée : une
    # structure dont l'ordre est délibérément l'INVERSE de l'alphabet doit
    # traverser la sérialisation telle quelle. Un garde qui ne peut plus
    # échouer ne prouve rien.
    faux = {"zzz": ("gamma", "beta", "alpha")}
    vrai = shelving.SHELVES
    try:
        shelving.SHELVES = faux
        temoin = shelving.declared_structure([])["structure"]
    finally:
        shelving.SHELVES = vrai
    ecrit = json.loads(canon.canonical_json(temoin, indent=2))
    assert [a["aisle"] for a in ecrit["aisles"]] == ["zzz"], ecrit
    assert [s["shelf"] for s in ecrit["aisles"][0]["shelves"]] == [
        "gamma", "beta", "alpha"], (
        "l'ordre DÉCLARÉ n'a pas survécu à la sérialisation — quelque chose "
        "trie en chemin, et sur la vraie donnée ça ne se verrait plus depuis "
        "que les sept rayons sont alphabétiques")
    # ⛔ ET LA PREUVE QUE LE TÉMOIN PEUT ACCUSER : son ordre n'est pas
    # l'alphabet, donc un tri en chemin le casserait. C'est cette ligne qui
    # échouait sur `mundane` depuis qu'il est trié — elle vit maintenant sur la
    # structure fabriquée, où elle peut encore dire quelque chose.
    fabrique = [s["shelf"] for s in ecrit["aisles"][0]["shelves"]]
    assert fabrique != sorted(fabrique)


@case
def the_provisional_name_travels_with_the_structure_too(conn):
    """A reader holding the structure block alone must see what a record shows.

    `Arcana` and `Marvels` are proposed names; the aisles under them are firm.
    The flag says exactly that, and it says it in both places or in neither."""
    records = _exported_records(conn)
    block = shelving.declared_structure(records)["structure"]
    flagged = {a["aisle"] for a in block["aisles"] if a["name_provisional"]}
    assert flagged == set(shelving.PROVISIONAL_AISLE), flagged
    on_records = {r["data"]["shelf"]["aisle"] for r in records
                  if r["data"]["shelf"]["aisle_name_provisional"]}
    assert on_records == flagged, (on_records, flagged)

    magic_weapons = [s for a in block["aisles"] if a["aisle"] == "armory"
                     for s in a["shelves"] if s["shelf"] == "magic-weapons"][0]
    assert magic_weapons["provisional"] is True
    assert magic_weapons["provisional_because"], magic_weapons


@case
def the_committed_export_carries_the_block_beside_its_records(conn):
    """The file the FHPC actually reads, not a rebuild of it in a scratch dir."""
    path = os.path.join(ROOT, "exports", "srfh", "en", "shelving.json")
    with open(path, encoding="utf-8") as fh:
        payload = json.load(fh)
    block = payload["structure"]
    # 30 → 32 le 2026-08-24 : les deux entrées rendues à `companions`.
    assert (block["aisle_count"], block["shelf_count"]) == (8, 32), block
    assert block["shelved_total"] == payload["count"] == len(payload["records"])
    # Recounted off the shipped records, one shelf at a time.
    tally = {}
    for r in payload["records"]:
        s = r["data"]["shelf"]
        tally[(s["aisle"], s["shelf"])] = tally.get((s["aisle"], s["shelf"]), 0) + 1
    for aisle in block["aisles"]:
        for shelf in aisle["shelves"]:
            key = (aisle["aisle"], shelf["shelf"])
            assert shelf["count"] == tally.get(key, 0), key
    assert len(tally) == 25, len(tally)   # what grouping alone could recover


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
