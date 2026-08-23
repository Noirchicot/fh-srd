"""Where an object is SHELVED, and where on a body it is WORN.

The SRD prints 416 pieces of equipment and never says where to look for one.
There is no aisle, no shelf, no body location anywhere in the book — those are
Fate's Hand decisions taken on the book's own matter, which is what the `srfh`
layer is for. Eric arrested the classification by hand on the 21st and 22nd of
August 2026; this module makes it machine-readable.

TWO AXES, NEVER ONE. Eric's own words: *ou ca se range, ou ca se porte*. The
shelf answers "where do I look for it", the slot answers "where do I wear it".
Boots and cloaks share a shelf and take two different slots; an amulet and a
ring are both jewellery and go to the neck and to the fingers. Folding the two
into one field costs a second pass over the whole catalogue, so they are two
fields here and they are computed by two functions.

DERIVE FIRST, WRITE ONLY WHAT CANNOT BE DERIVED. 309 of the 416 already carry a
field that answers the shelf question — `item.category`, `weapon.weapon_range`,
`armor.armor_category`. Only the 107 mundane rows (82 adventuring gear, 25
tools) have nothing but a name, and for those, and only those, the table below
is the source. A value written in two places ends up disagreeing with itself;
the catalyst price list in this house already carries one derived tier from two
different fields, 463 records against 2, divergent before it ever had a reader.

⛔ NO NAME ANALYSER, ANYWHERE. Four "obvious" lexical rules were tested against
the 82 common items and three of them break on their first object: *ends with
"pack"* catches Backpack, which is a container; *contains "scroll"* catches
`Case, Map or Scroll`, which is a case; *contains "pouch"* catches both
`Component Pouch` (magic) and `Pouch` (a container) — one word, two shelves.
The table below is keyed by the EXACT catalogue name, never by a substring.

⚠️ AND THE ABSENCE TRAP, which has a name in this workshop. `item.subtype` has
its key present 258 times out of 258 and its VALUE is null 206 of those times:
52 real values. Anything asking `"subtype" in data` believes it holds an axis
and holds nothing. Every test below reads the VALUE.
"""

import json

import canon
import db

LAYER = "srfh"
KIND = "shelving"

# Same licence question as the rest of the SRFH layer, and it is still Eric's
# to answer. See `srfh.py`: `undecided` is a state, not a placeholder.
LICENSE = "undecided"
ATTRIBUTION = (
    "Fate's Hand (Eric). Shelving and body slots decided on 2026-08-21/22 for "
    "the System Reference Document 5.2.1 by Wizards of the Coast LLC, licensed "
    "under CC-BY-4.0. The classification is not part of the SRD."
)


class ShelvingError(Exception):
    """A guard in this module refused. Never caught: the build stops."""


# ---------------------------------------------------------------------------
# The seven aisles
# ---------------------------------------------------------------------------
# Alphabetical at both levels, and the first one is the one that opens (Eric,
# 2026-08-22). Keys are ENGLISH on both sides — repository law §0.13, *the
# engine makes identifiers, the interface makes words*. The ten French words in
# the source document are labels, not keys. The counter-example is in this same
# repository and it cost a day: `damage_type_key` holds `slashing` in English
# and `perforant` in French, a field whose name promises a key and carries a
# translation.
#
# `Arcana` and `Marvels` are PROPOSED names, never ratified. They are used here
# because the structure under them is firm, and flagged so nobody mistakes use
# for agreement.
PROVISIONAL_AISLE = ("arcana", "marvels")

SHELVES = {
    "adventuring": ("camp", "force-and-trap", "light-and-fire", "packs",
                    "ropes-and-climbing", "watch-and-signal"),
    "arcana": ("consumables-and-potions", "scrolls-foci-components",
               "wands-rods-staves"),
    "battlefield": ("armor", "magic-armor", "magic-weapons", "melee-weapons",
                    "projectiles", "thrown-weapons"),
    "companions": ("familiars", "henchmen"),
    "crafting": ("gems", "ingredients", "tools"),
    "marvels": ("rings", "wondrous"),
    "mundane": ("containers", "clothing", "writing-and-reading"),
}

# Shelves this lot ADDED rather than transcribed, and why each one exists. The
# source document assumed the magic weapons and the magic armor would stop
# being records at all — *elles se fabriquent depuis leur base mondaine* — so it
# never said where to put them. The lot's requirement is 416 out of 416 with no
# remainder, which reopens the question. Keeping them on their own two shelves
# leaves every count the document printed exactly as it printed it.
#
# `marvels/wondrous` is a HOLDING shelf, not a decision: the ratified split of
# the 149 marvels into seven shelves lives in `merveilleux-ranges.json`, which
# the document names and which exists nowhere on disk.
PROVISIONAL_SHELF = {
    ("battlefield", "magic-weapons"):
        "the document expected these to stop being records; 416/416 says they "
        "are still here, and this shelf leaves its printed counts untouched",
    ("battlefield", "magic-armor"):
        "same, for armor",
    ("marvels", "wondrous"):
        "holding shelf: the seven-shelf split of the marvels is in "
        "merveilleux-ranges.json, which is named by the source and absent from "
        "disk",
}

# ---------------------------------------------------------------------------
# The ten body slots
# ---------------------------------------------------------------------------
# Read off the 77 worn objects, 77 out of 77 with no remainder. `eyes` is kept
# apart from `head` on purpose: merged, a helm would forbid goggles, which the
# SRD does not forbid.
SLOTS = ("back", "eyes", "feet", "fingers", "forearms", "hands", "head",
         "neck", "torso", "waist")

# ⛔ THIS IS THE SILHOUETTE'S SHAPE, NOT A RULE OF THE GAME. A square on the
# doll holds one object, and `fingers` is the one square Eric left open —
# *les anneaux pas de limites, mais deux bottes, gants, capes l'une sur l'autre
# non*. It is deliberately NOT written onto the objects: a slot PLACES, it does
# not FORBID. No SRD 5.2.1 rule limits how many rings or cloaks are worn; the
# only limit in the game is attunement, and that already exists in the data.
# Emitting a per-object exclusivity here would be a second limit, drifting away
# from the first.
SLOT_CAPACITY = {slot: (None if slot == "fingers" else 1) for slot in SLOTS}

# ---------------------------------------------------------------------------
# The 309 that derive — one field already answers
# ---------------------------------------------------------------------------
# `item.category` carries nine values and every one of them names a shelf. Three
# of the counts this produces land exactly on the document's own figures without
# anything being written down: wands+rods+staves = 32, potions+9 mundane
# consumables = 33, the scroll + 6 mundane magic gear = 7. That agreement is the
# evidence that the derivation is the right one.
SHELF_OF_ITEM_CATEGORY = {
    "armor": ("battlefield", "magic-armor"),
    "potion": ("arcana", "consumables-and-potions"),
    "ring": ("marvels", "rings"),
    "rod": ("arcana", "wands-rods-staves"),
    "scroll": ("arcana", "scrolls-foci-components"),
    "staff": ("arcana", "wands-rods-staves"),
    "wand": ("arcana", "wands-rods-staves"),
    "weapon": ("battlefield", "magic-weapons"),
    "wondrous-item": ("marvels", "wondrous"),
}

SHELF_OF_WEAPON_RANGE = {
    "melee": ("battlefield", "melee-weapons"),
    "ranged": ("battlefield", "thrown-weapons"),
}

# ---------------------------------------------------------------------------
# The 107 that do not derive — transcribed from the source, 2026-08-22
# ---------------------------------------------------------------------------
#   ~/obsidian-vault/FH-WEB/FHPC/FHPCv2 rangement equipement.md
#
# Keyed by the exact catalogue name, apostrophes included (the catalogue uses
# U+2019, not U+0027). The build refuses if a key here matches no record or if
# a record matches no key, so a rename upstream cannot pass in silence.
SHELF_OF_GEAR = {}
for _names, _shelf in (
    # Containers, 16
    (("Backpack", "Barrel", "Basket", "Bottle, Glass", "Bucket",
      "Case, Crossbow Bolt", "Case, Map or Scroll", "Chest", "Flask", "Jug",
      "Pot, Iron", "Pouch", "Quiver", "Sack", "Vial", "Waterskin"),
     ("mundane", "containers")),
    # Force and trap, 10
    (("Ball Bearings", "Caltrops", "Crowbar", "Hunting Trap", "Lock",
      "Manacles", "Net", "Ram, Portable", "Shovel", "Spikes, Iron"),
     ("adventuring", "force-and-trap")),
    # Consumables, 9 — they join the potions in Arcana, as the document says
    (("Acid", "Alchemist’s Fire", "Antitoxin", "Healer’s Kit", "Holy Water",
      "Oil", "Poison, Basic", "Potion of Healing", "Rations"),
     ("arcana", "consumables-and-potions")),
    # Ropes and climbing, 8
    (("Block and Tackle", "Chain", "Climber’s Kit", "Grappling Hook", "Ladder",
      "Pole", "Rope", "String"),
     ("adventuring", "ropes-and-climbing")),
    # Packs, 7 — filed INSIDE Adventuring rather than given an aisle of their
    # own: an aisle with no shelves would empty the lower carousel on that one
    # aisle and make the page jump height, and a screen that moves under the
    # finger is a screen nobody dares touch.
    (("Burglar’s Pack", "Diplomat’s Pack", "Dungeoneer’s Pack",
      "Entertainer’s Pack", "Explorer’s Pack", "Priest’s Pack",
      "Scholar’s Pack"),
     ("adventuring", "packs")),
    # Light and fire, 6
    (("Candle", "Lamp", "Lantern, Bullseye", "Lantern, Hooded", "Tinderbox",
      "Torch"),
     ("adventuring", "light-and-fire")),
    # Writing and reading, 6
    (("Book", "Ink", "Ink Pen", "Map", "Paper", "Parchment"),
     ("mundane", "writing-and-reading")),
    # Magic, 6 — the mundane half of the Arcana scroll shelf
    (("Arcane Focus", "Component Pouch", "Druidic Focus", "Holy Symbol",
      "Spell Scroll (Cantrip)", "Spell Scroll (Level 1)"),
     ("arcana", "scrolls-foci-components")),
    # Clothing, 5
    (("Clothes, Fine", "Clothes, Traveler’s", "Costume", "Perfume", "Robe"),
     ("mundane", "clothing")),
    # Watch and signal, 5
    (("Bell", "Magnifying Glass", "Mirror", "Signal Whistle", "Spyglass"),
     ("adventuring", "watch-and-signal")),
    # Camp, 3
    (("Bedroll", "Blanket", "Tent"), ("adventuring", "camp")),
    # Ammunition, 1 — the SRD's single empty `Varies/Varies` row. The document
    # replaces it with five real records (arrows, bolts, sling bullets,
    # needles, firearm bullets); those five do not exist yet, so this shelf
    # holds one record today and will hold five.
    (("Ammunition",), ("battlefield", "projectiles")),
):
    for _n in _names:
        SHELF_OF_GEAR[_n] = _shelf

SHELF_OF_TOOL = ("crafting", "tools")

# The document's own counts, and they are a free check: if the transcription
# above drifts, these stop adding up. 16+10+9+8+7+6+6+6+5+5+3+1 = 82.
GEAR_SHELF_COUNT = {
    ("mundane", "containers"): 16,
    ("adventuring", "force-and-trap"): 10,
    ("arcana", "consumables-and-potions"): 9,
    ("adventuring", "ropes-and-climbing"): 8,
    ("adventuring", "packs"): 7,
    ("adventuring", "light-and-fire"): 6,
    ("mundane", "writing-and-reading"): 6,
    ("arcana", "scrolls-foci-components"): 6,
    ("mundane", "clothing"): 5,
    ("adventuring", "watch-and-signal"): 5,
    ("adventuring", "camp"): 3,
    ("battlefield", "projectiles"): 1,
}

# ---------------------------------------------------------------------------
# `craftable` — posed as the document poses it, and MEASURED
# ---------------------------------------------------------------------------
# A transverse label, not an aisle: an object is shelved somewhere AND carries
# `craftable`. The bases the craft lays magic onto are weapons, armor,
# projectiles and spell scrolls. The first two are a whole record kind; the last
# two are three named rows, which is why they are named here and nowhere else.
CRAFT_BASE_GEAR = ("Ammunition", "Spell Scroll (Cantrip)", "Spell Scroll (Level 1)")
CRAFT_BASE_KINDS = ("weapon", "armor")


# ---------------------------------------------------------------------------
# Axis 1 — the shelf. One entry point, two sources behind it.
# ---------------------------------------------------------------------------
def shelf_of(kind, name, data):
    """(aisle, shelf, provenance) for any of the 416. Never returns None.

    A single function answers "which shelf?" for the whole catalogue: it
    DERIVES for 309 and READS THE TABLE for 107. Two entry points would let the
    two answers drift.
    """
    if kind == "weapon":
        # `weapon_range` is melee or ranged and never absent. Note what the
        # shelf is called: the document's second battlefield shelf is *armes de
        # jet*, and its ten members are exactly the ten ranged rows.
        rng = data["weapon_range"]
        if rng not in SHELF_OF_WEAPON_RANGE:
            raise ShelvingError(
                "%r has weapon_range %r, which names no shelf" % (name, rng))
        aisle, shelf = SHELF_OF_WEAPON_RANGE[rng]
        return aisle, shelf, "derived:weapon.weapon_range"

    if kind == "armor":
        # Every armor row, shield included, sits on one shelf. `armor_category`
        # is read here only to prove it is a real value — it is what tells the
        # SLOT axis a shield goes to the hands and a breastplate to the torso.
        if data["armor_category"] not in ("light", "medium", "heavy", "shield"):
            raise ShelvingError(
                "%r has armor_category %r" % (name, data["armor_category"]))
        return "battlefield", "armor", "derived:armor.armor_category"

    if kind == "tool":
        aisle, shelf = SHELF_OF_TOOL
        return aisle, shelf, "table:rangement 2026-08-22 (all 25 tools)"

    if kind == "gear":
        if name not in SHELF_OF_GEAR:
            raise ShelvingError(
                "the catalogue has a gear row the shelving table does not "
                "name: %r.\n\nThe table is the ONLY source for these — no name "
                "rule may be invented to cover it. Add the row to the vault "
                "document first, then here." % name)
        aisle, shelf = SHELF_OF_GEAR[name]
        return aisle, shelf, "table:rangement 2026-08-22"

    if kind == "item":
        # ⚠️ The VALUE, never the key. `category` is filled 258/258; `subtype`
        # has its key filled 258/258 and its value 52/258, and it is not read
        # here at all — the shelf never needed it.
        category = data["category"]
        if category not in SHELF_OF_ITEM_CATEGORY:
            raise ShelvingError(
                "%r has category %r, which names no shelf" % (name, category))
        aisle, shelf = SHELF_OF_ITEM_CATEGORY[category]
        return aisle, shelf, "derived:item.category"

    raise ShelvingError("no shelving rule for record kind %r" % kind)


# ---------------------------------------------------------------------------
# Axis 2 — the body slot. Only what is worn, and only where a field says so.
# ---------------------------------------------------------------------------
def slot_of(kind, name, data, shelf):
    """The body slot, as one of four honest answers.

      worn=True  + slot        a field settles it
      worn=True  + from_base   a magic weapon or armor: the slot is whichever
                               base you laid the magic on, chosen at purchase
      worn=False               a field settles that it is not worn
      worn=None  + pending     nobody has answered yet, and saying "not worn"
                               would answer it in the wrong direction

    The fourth case is the whole reason this returns a dict rather than a
    string or None. An absence is never an answer: a robe that comes back
    `worn=False` because no table mentioned it is a wrong answer wearing the
    costume of a right one.
    """
    if kind == "weapon":
        return {"worn": True, "slot": "hands",
                "provenance": "derived:record kind weapon"}

    if kind == "armor":
        if data["armor_category"] == "shield":
            return {"worn": True, "slot": "hands",
                    "provenance": "derived:armor.armor_category = shield"}
        return {"worn": True, "slot": "torso",
                "provenance": "derived:armor.armor_category"}

    if kind == "item":
        category = data["category"]
        if category == "ring":
            # 22 rings, and the document's `Doigts` shelf holds 22. The two
            # numbers were arrived at independently and they match.
            return {"worn": True, "slot": "fingers",
                    "provenance": "derived:item.category = ring"}
        if category in ("weapon", "armor"):
            # The magic is laid on a base, and the base is picked when the item
            # is bought — `Any Simple or Martial` names no single one. The same
            # shape already exists one file over, where `srfh` gives these items
            # a weight `from_base` for exactly this reason.
            return {"worn": True, "from_base": True,
                    "provenance": "derived:item.category; the slot is the "
                                  "base's, chosen at purchase"}
        if category == "wondrous-item":
            return {"worn": None,
                    "pending": "merveilleux-ranges.json — the per-object "
                               "classification of the 149 marvels, named by "
                               "the source document and absent from disk. 55 "
                               "of these 127 are worn.",
                    "provenance": "table:absent"}
        return {"worn": False, "provenance": "derived:item.category = %s" % category}

    if shelf == ("mundane", "clothing"):
        # Fine clothes, traveler's clothes, a costume, a robe. Obviously worn,
        # and the source never says where: its ten slots were read off the 149
        # marvels and it never asked the question of mundane clothing. Saying
        # `worn=False` here would be inventing an answer; saying `torso` would
        # be inventing a different one.
        return {"worn": None,
                "pending": "the source's ten slots were read off the marvels "
                           "and never asked where mundane clothing goes",
                "provenance": "table:silent"}

    return {"worn": False, "provenance": "derived:record kind %s" % kind}


def craftable_of(kind, name):
    """Is this a base the craft lays magic onto? With its provenance."""
    if kind in CRAFT_BASE_KINDS:
        return {"value": True, "provenance": "derived:record kind %s" % kind}
    if name in CRAFT_BASE_GEAR:
        return {"value": True,
                "provenance": "table:rangement 2026-08-22 (craft bases)"}
    return {"value": False, "provenance": "derived:record kind %s" % kind}


# ---------------------------------------------------------------------------
# The shape Eric read. A drift here stops the build.
# ---------------------------------------------------------------------------
# Same reasoning as `srfh.RATIFIED`: these are not "expected numbers", they are
# a classification a person arrested by hand. If the catalogue moves under them,
# this layer must not follow in silence — a shelf nobody chose is a shelf nobody
# agreed to.
RATIFIED_TOTAL = 416
RATIFIED_SHELF_COUNT = {
    ("adventuring", "camp"): 3,
    ("adventuring", "force-and-trap"): 10,
    ("adventuring", "light-and-fire"): 6,
    ("adventuring", "packs"): 7,
    ("adventuring", "ropes-and-climbing"): 8,
    ("adventuring", "watch-and-signal"): 5,
    ("arcana", "consumables-and-potions"): 33,
    ("arcana", "scrolls-foci-components"): 7,
    ("arcana", "wands-rods-staves"): 32,
    ("battlefield", "armor"): 13,
    ("battlefield", "magic-armor"): 19,
    ("battlefield", "magic-weapons"): 33,
    ("battlefield", "melee-weapons"): 28,
    ("battlefield", "projectiles"): 1,
    ("battlefield", "thrown-weapons"): 10,
    ("companions", "familiars"): 0,
    ("companions", "henchmen"): 0,
    ("crafting", "gems"): 0,
    ("crafting", "ingredients"): 0,
    ("crafting", "tools"): 25,
    ("marvels", "rings"): 22,
    ("marvels", "wondrous"): 127,
    ("mundane", "clothing"): 5,
    ("mundane", "containers"): 16,
    ("mundane", "writing-and-reading"): 6,
}
RATIFIED_SLOT_COUNT = {"fingers": 22, "hands": 39, "torso": 12}
RATIFIED_SLOT_TALLY = {"decided": 73, "from_base": 52, "pending": 132,
                       "not_worn": 159}
RATIFIED_CRAFTABLE = 54

KINDS = ("armor", "gear", "item", "tool", "weapon")


def _check_table_covers_the_catalogue(names_by_kind):
    """Every table key names a record, and every gear record has a key.

    Both directions, because they fail differently. A key naming nothing is a
    typo or a rename upstream; a record naming no key is an object with no
    shelf, which is the one outcome this lot exists to prevent.
    """
    gear = names_by_kind["gear"]
    unknown = sorted(set(SHELF_OF_GEAR) - gear)
    if unknown:
        raise ShelvingError(
            "%d shelving table key(s) name no gear record:\n%s\n\nEither the "
            "catalogue renamed a row or the transcription has a typo. It is not "
            "safe to guess which."
            % (len(unknown), "\n".join("  " + n for n in unknown)))
    for name in CRAFT_BASE_GEAR:
        if name not in gear:
            raise ShelvingError(
                "the craft base %r names no gear record" % name)
    # Cross-check the document's own per-shelf counts before using the table.
    measured = {}
    for shelf in SHELF_OF_GEAR.values():
        measured[shelf] = measured.get(shelf, 0) + 1
    if measured != GEAR_SHELF_COUNT:
        drift = sorted(set(measured) | set(GEAR_SHELF_COUNT))
        raise ShelvingError(
            "the transcription does not add up to the document's counts:\n"
            + "\n".join(
                "  %-40s transcribed %d, document %d"
                % ("/".join(s), measured.get(s, 0), GEAR_SHELF_COUNT.get(s, 0))
                for s in drift
                if measured.get(s, 0) != GEAR_SHELF_COUNT.get(s, 0)))


def build_shelving(conn, lang="en"):
    """Write the shelving layer. Returns (by_shelf, by_slot, tally, notes)."""
    rows = {}
    names_by_kind = {}
    for kind in KINDS:
        rows[kind] = [
            (r["id"], r["slug"], r["name"], json.loads(r["data"]))
            for r in conn.execute(
                "SELECT id, slug, name, data FROM record"
                " WHERE layer='srd' AND kind=? AND lang=? ORDER BY slug",
                (kind, lang))
        ]
        names_by_kind[kind] = {n for _i, _s, n, _d in rows[kind]}

    _check_table_covers_the_catalogue(names_by_kind)

    by_shelf = {shelf: 0 for aisle in SHELVES for shelf in
                [(aisle, s) for s in SHELVES[aisle]]}
    by_slot = {}
    tally = {"decided": 0, "from_base": 0, "pending": 0, "not_worn": 0}
    source = {"derived": 0, "table": 0}
    craftable_count = 0
    records = []
    notes = []

    for kind in KINDS:
        for srd_id, slug, name, data in rows[kind]:
            aisle, shelf, provenance = shelf_of(kind, name, data)
            if (aisle, shelf) not in by_shelf:
                raise ShelvingError(
                    "%r was shelved on %s/%s, which is in no aisle"
                    % (name, aisle, shelf))
            by_shelf[(aisle, shelf)] += 1
            source["table" if provenance.startswith("table:") else "derived"] += 1

            worn = slot_of(kind, name, data, (aisle, shelf))
            if worn.get("slot"):
                tally["decided"] += 1
                by_slot[worn["slot"]] = by_slot.get(worn["slot"], 0) + 1
            elif worn.get("from_base"):
                tally["from_base"] += 1
            elif worn["worn"] is None:
                tally["pending"] += 1
            else:
                tally["not_worn"] += 1

            craft = craftable_of(kind, name)
            if craft["value"]:
                craftable_count += 1

            payload = {
                "name": name,
                "extends": srd_id,
                "of_kind": kind,
                "shelf": {
                    "aisle": aisle,
                    "shelf": shelf,
                    "provenance": provenance,
                    # Carried on the record, not only in this module: a reader
                    # holding one exported row must be able to see that the
                    # aisle it names has not been ratified.
                    "aisle_name_provisional": aisle in PROVISIONAL_AISLE,
                    "shelf_provisional": (aisle, shelf) in PROVISIONAL_SHELF,
                },
                "slot": worn,
                "craftable": craft,
            }
            records.append((
                {
                    "id": canon.record_id(LAYER, KIND, lang, slug),
                    "layer": LAYER,
                    "kind": KIND,
                    "lang": lang,
                    "slug": slug,
                    "name": name,
                    "data": canon.canonical_json(payload),
                    "content_hash": canon.content_hash(KIND, lang, name, payload),
                    "source_id": None,
                    "source_locator": "",
                    "srd_version": None,
                    "license": LICENSE,
                    "attribution": ATTRIBUTION,
                },
                srd_id,
            ))

    # ---- reconciliation ---------------------------------------------------
    total = sum(by_shelf.values())
    if total != RATIFIED_TOTAL or total != len(records):
        raise ShelvingError(
            "%d record(s) shelved, %d ratified, %d emitted — the requirement "
            "is every object and no remainder"
            % (total, RATIFIED_TOTAL, len(records)))

    drift = {k: (v, RATIFIED_SHELF_COUNT.get(k))
             for k, v in by_shelf.items() if RATIFIED_SHELF_COUNT.get(k) != v}
    drift.update({("slot", k): (v, RATIFIED_SLOT_COUNT.get(k))
                  for k, v in by_slot.items() if RATIFIED_SLOT_COUNT.get(k) != v})
    drift.update({("tally", k): (v, RATIFIED_SLOT_TALLY[k])
                  for k, v in tally.items() if RATIFIED_SLOT_TALLY[k] != v})
    if craftable_count != RATIFIED_CRAFTABLE:
        drift[("craftable", "")] = (craftable_count, RATIFIED_CRAFTABLE)
    if drift:
        raise ShelvingError(
            "the catalogue moved under a classification Eric arrested by hand "
            "on 2026-08-21/22:\n"
            + "\n".join("  %-46s measured %s, ratified %s"
                        % ("/".join(str(p) for p in k), got, want)
                        for k, (got, want) in sorted(drift.items(), key=str))
            + "\nRe-read the change, then update the ratified counts with his "
              "answer.")

    for rec, _dst in records:
        db.insert_record(conn, rec)
    for rec, dst_id in records:
        conn.execute(
            "INSERT INTO record_link (src_id, dst_id, rel, note) VALUES (?,?,?,?)",
            (rec["id"], dst_id, "extends",
             "SRFH carries the shelf and the body slot the SRD never printed"))
    conn.commit()

    notes.append(
        "shelf: %d derived from a field already in the record, %d read from "
        "the written table" % (source["derived"], source["table"]))
    notes.append(
        "the seven-shelf split of marvels/wondrous (127 records) and the body "
        "slot of 55 of them both wait on merveilleux-ranges.json, which the "
        "source document names and which is on no disk here")
    notes.append(
        "craftable: %d bases — %d weapons and armor, from the record kind "
        "alone, and %d named gear rows. Rarity plays NO part: all %d are "
        "mundane rows with no rarity at all, so this is not Foundry's "
        "rarity-and-days calculation wearing a different name."
        % (craftable_count, len(rows["weapon"]) + len(rows["armor"]),
           len(CRAFT_BASE_GEAR), craftable_count))
    return by_shelf, by_slot, tally, notes
