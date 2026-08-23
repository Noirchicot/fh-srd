"""The SRFH layer — the numbers the book never printed.

The SRD gives 258 magic items and not one price, not one weight. That is not a
gap in our copy: the book prints none. But a character sheet with a purse and a
carried load cannot use an item that answers neither question, so two thirds of
the catalogue is unusable for anything but reading. Eric's words for what this
layer is for: *permettre a des gens de jouer sur notre systeme sans etre
amputes de la base monetaire*.

WHERE THE NUMBERS COME FROM. Almost none of them are invented. The SRD carries
its own pricing rule and its own weights for the ordinary objects that magic
items are made of, so the great majority of this layer is ARITHMETIC over the
book, not judgement:

  * `Magic Item Rarities and Values`, p.206 -- a value per rarity, half for a
    consumable, and "add that item's cost to the magic item's value" for an
    item built on a weapon or a suit of armor.
  * `Arcane Focuses`, p.96 -- what a wand, a rod and a staff weigh.
  * the ordinary equipment tables -- what a longsword, a plate armor, a healing
    potion, a book or a rope weigh.

Every value carries its own provenance, in the record, beside the number:
`tier` (the rarity table), `inherited` (a named base object), `convention` (a
category rule taken from a named table) or `chosen` (ours, and Eric ratified
it on 2026-08-23). A value nobody can trace is a value nobody can correct.

WHAT THIS LAYER DOES NOT DO. It never edits an SRD row. It adds its own rows in
its own layer and points down at the base with a `record_link`, which is the
only way one layer is allowed to touch another here.
"""

import json
import re

import canon
import db

LAYER = "srfh"

# The licence is Eric's decision and it is not made. It is written into the
# data as `undecided` rather than defaulted to `proprietary`, because
# defaulting would silently answer -- in the most restrictive direction -- a
# question whose whole point is that this layer is meant to be given away.
LICENSE = "undecided"
ATTRIBUTION = (
    "Fate's Hand (Eric). Prices and weights derived from the System Reference "
    "Document 5.2.1 by Wizards of the Coast LLC, licensed under CC-BY-4.0. "
    "The derived values are not part of the SRD."
)

# --- the book's own pricing rule, p.206 -------------------------------------
TIER_VALUE = {
    "Common": 100,
    "Uncommon": 400,
    "Rare": 4000,
    "Very Rare": 40000,
    "Legendary": 200000,
    "Artifact": None,          # "Priceless" -- not zero, not unknown
}
# Longest first: "Very Rare" must win over "Rare", and "Rarity Varies" must not
# be read as "Rare".
TIER_ORDER = ["Rarity Varies", "Very Rare", "Uncommon", "Legendary",
              "Artifact", "Common", "Rare"]

# --- `Arcane Focuses`, p.96 -------------------------------------------------
# A wand, a rod and a staff have a weight in the book. These are not category
# conventions we invented; they are the book's own line for that shape of
# object, and the staff row even says "(also a Quarterstaff)".
FOCUS_WEIGHT = {"wand": 1.0, "rod": 2.0, "staff": 4.0}

# --- the five buckets Eric ratified on 2026-08-23 ---------------------------
# For the wondrous items that have no base, no twin and no line in any table.
# These are the only values in this layer that the book does not justify, and
# they are marked `chosen` for exactly that reason.
BUCKET_WEIGHT = {
    "jewellery": None,        # negligible
    "worn-soft": 1.0,
    "held": 2.0,
    "worn-rigid": 3.0,
    "bulky": 10.0,
}
BUCKET_OF_HEAD = {}
for _head_list, _bucket in (
    (["Cloak", "Cape", "Mantle", "Boots", "Winged Boots", "Slippers",
      "Gloves", "Hat", "Belt", "Wings"], "worn-soft"),
    (["Helm", "Bracers", "Gauntlets"], "worn-rigid"),
    (["Horn", "Pipes", "Chime", "Wind Fan", "Horseshoes", "Figurine",
      "Sphere", "Dragon Orb", "Iron Bands", "Dimensional Shackles",
      "Broom", "Instant Fortress"], "held"),
    (["Apparatus", "Brazier", "Censer", "Folding Boat"], "bulky"),
):
    for _h in _head_list:
        BUCKET_OF_HEAD[_h] = _bucket

# --- wondrous items that are an everyday object, magicked ------------------
# A magic book weighs a book; a magic rope weighs a rope. The head noun of the
# name points at an ordinary equipment record, and we take its weight. Where
# the noun differs from the catalogue's spelling, it is mapped here -- and only
# where the object really is the same thing.
TWIN_OF_HEAD = {
    "Bag": "Sack", "Manual": "Book", "Tome": "Book", "Robe": "Robe",
    "Rope": "Rope", "Lantern": "Lantern, Hooded", "Mirror": "Mirror",
    "Candle": "Candle", "Quiver": "Quiver", "Efficient Quiver": "Quiver",
    "Handy Haversack": "Backpack", "Bowl": "Bucket", "Iron Flask": "Flask",
    "Efreeti Bottle": "Bottle, Glass", "Eversmoking Bottle": "Bottle, Glass",
    "Decanter": "Bottle, Glass", "Deck": "Paper", "Mysterious Deck": "Paper",
    "Carpet": "Blanket",
}
# A crystal ball is an orb, and the orb has a weight on p.96.
CRYSTAL_BALL_WEIGHT = 3.0

# --- out of scope -----------------------------------------------------------
# Not five items: five families of three upgrades each. Eric ruled on
# 2026-08-23 that a "+N" is an improvement laid on a base object, not an object,
# and that the house magic-item system will be built from them. They get no
# price and no weight here, and the build says so out loud rather than letting
# their silence pass for an oversight.
BOOSTS = (
    "Ammunition, +1, +2, or +3",
    "Armor, +1, +2, or +3",
    "Shield, +1, +2, or +3",
    "Wand of the War Mage, +1, +2, or +3",
    "Weapon, +1, +2, or +3",
)

# The scroll is the other improvement, and it took until 2026-08-23 to see it:
# a spell laid on a parchment is a boost exactly as a "+1" is. So the Spell
# Scroll record STAYS as the base object and receives no tier price; its ten
# per-level lines are the improvement's price grid and belong to the craft
# workshop, not here.
SPELL_SCROLL = "Spell Scroll"

# --- the family sheets that are not one object -----------------------------
# Seven sheets describe a whole family in a table inside their own prose. A
# single price would lie to every member but one. Eric: *pour les potions on
# cree des items, pour chaque possibilite* and *pour les trucs cor du machin on
# cree tous les objets, moins chiant qu'un gros descriptif d'item*.
#
# The members are READ FROM THE BOOK, never typed here, and each family
# declares how many it must yield. A family that comes back with a different
# count stops the build: these counts are ratified values, and drifting past
# them in silence is the one outcome that must not happen.
FAMILY_COUNT = {
    "Ioun Stone": 13,
    "Figurine of Wondrous Power": 9,
    "Feather Token": 6,
    "Belt of Giant Strength": 6,
    "Horn of Valhalla": 4,
    "Potion of Giant Strength": 6,
    "Potions of Healing": 4,
}

_TIER_RE = "Common|Uncommon|Rare|Very Rare|Legendary"
_NAMED_TIER = re.compile(r"^([A-Z][A-Za-z' ]{2,40}) \((%s)\)\." % _TIER_RE, re.M)
_D100_TIER = re.compile(r"^\d{2}[–-]\d{2} ([A-Za-z][A-Za-z ]*?) (%s)$" % _TIER_RE, re.M)
_D100_PLAIN = re.compile(r"^\d{2}[–-]\d{2} ([A-Za-z]+) \d+ ", re.M)
_GIANT_ROW = re.compile(r"^.+ \(([a-z ]+)\) \d+ (%s)$" % _TIER_RE, re.M)
_HEALING_ROW = re.compile(r"^Potion of Healing(?: \((\w+)\))? \d+d\d+ \+ \d+ (%s)$" % _TIER_RE, re.M)


# The shape Eric read and signed off on 2026-08-23. Every one of these is a
# COUNT of records this layer produces, checked against what it actually
# produced -- see the reconciliation at the end of `build_srfh`.
RATIFIED = {
    "extends": 246,      # entries that already exist and only lacked numbers
    "members": 48,       # objects lifted out of the seven family sheets
    "families": 7,       # sheets those 48 replace
    "boosts": 5,         # improvements deliberately left alone
    "twin": 35,          # wondrous items weighing what their everyday twin weighs
    "jewellery": 59,
    "worn-soft": 29,
    "held": 26,
    "worn-rigid": 7,
    "bulky": 4,
}


class SrfhError(Exception):
    """A guard in this layer refused. Never caught: the build stops."""


def _tier_of(rarity):
    for tier in TIER_ORDER:
        if rarity.startswith(tier):
            return tier
    raise SrfhError("no tier can be read from rarity %r" % rarity)


def _attunement_by(rarity):
    """The 'by whom' of an attunement, which the book keeps inside the rarity.

    Two facts in one string is two fields. The boolean already exists on the
    SRD record; what has no field anywhere is *who* may attune, and twenty
    records carry one.
    """
    match = re.search(r"Requires Attunement by ([^)]+)\)", rarity)
    return match.group(1) if match else None


def _members_of(name, description, rarity):
    """The members a family sheet holds, read from its own table.

    Six families, six table shapes -- the book is not regular here, so each is
    read by the pattern it actually prints rather than by a shape we wish it
    had.
    """
    if name in ("Ioun Stone", "Figurine of Wondrous Power"):
        return [(v, t) for v, t in _NAMED_TIER.findall(description)]

    if name == "Feather Token":
        return [(v.strip(), t) for v, t in _D100_TIER.findall(description)]

    if name == "Horn of Valhalla":
        # The only family whose tiers are not in its table but in its rarity
        # line: "Rare (Silver or Brass), Very Rare (Bronze), or Legendary
        # (Iron)". The table gives the four metals, the rarity says which tier
        # each metal carries, so the two are joined on the metal.
        tier_of_metal = {}
        for tier, metals in re.findall(r"(%s) \(([A-Za-z ]+)\)" % _TIER_RE, rarity):
            for metal in re.split(r" or ", metals):
                tier_of_metal[metal.strip()] = tier
        out = []
        for metal in _D100_PLAIN.findall(description):
            if metal not in tier_of_metal:
                raise SrfhError(
                    "Horn of Valhalla: the table prints %r, the rarity line "
                    "does not say its tier" % metal
                )
            out.append((metal, tier_of_metal[metal]))
        return out

    if name in ("Belt of Giant Strength", "Potion of Giant Strength"):
        # The book puts two giants on one line -- "(frost or stone)" -- because
        # they share a score and a tier. They are two giants, so they are two
        # possibilities, so they are two objects. Eric: *pour chaque
        # possibilite*. Splitting here is the one place this module widens what
        # the book prints, and it widens it by reading the word "or".
        out = []
        for kinds, tier in _GIANT_ROW.findall(description):
            for kind in re.split(r" or ", kinds):
                out.append((kind.strip(), tier))
        return out

    if name == "Potions of Healing":
        return [(v or "standard", t) for v, t in _HEALING_ROW.findall(description)]

    raise SrfhError("no member reader for family %r" % name)


def _member_name(family, variant):
    """The name the book itself gives a member of a family.

    `Potions of Healing` is a plural sheet heading, not an object: its members
    are printed as `Potion of Healing (greater)`, and the plain one has no
    suffix at all. Naming a member `Potions of Healing (standard)` would invent
    an object the book never prints.
    """
    if family == "Potions of Healing":
        singular = "Potion of Healing"
        return singular if variant == "standard" else "%s (%s)" % (singular, variant)
    return "%s (%s)" % (family, variant)


def _head_noun(name):
    return re.split(r" of | ,|,| the ", name)[0].strip()


def _lb(text):
    """A weight the book printed, as a number of pounds.

    Three spellings of a half live in this catalogue -- `1/2 lb.`, `58 1/2 lb.`
    with the U+00BD character, and the em dash that means "negligible". A
    reader that handles one and not the others returns a wrong number without
    raising anything, which is why this is the only place weights are read.
    """
    if text is None:
        raise SrfhError("no weight text")
    text = text.strip()
    if text == "—":
        return None                       # negligible: a value, not an absence
    body = text.replace(" lb.", "").replace("(full)", "").strip()
    body = body.replace("½", " 1/2")
    total = 0.0
    for part in body.split():
        if "/" in part:
            num, den = part.split("/")
            total += float(num) / float(den)
        else:
            total += float(part)
    return total


def _gp(text):
    """A price the book printed, in gold pieces.

    `1,000 GP` read with a naive float is 1. The thousands separator is dropped
    here, once, and silver and copper are brought to gold so a cart can add a
    single column.
    """
    match = re.match(r"^([\d,]+(?:\.\d+)?)\s+(GP|SP|CP)$", text.strip())
    if not match:
        raise SrfhError("no price can be read from %r" % text)
    value = float(match.group(1).replace(",", ""))
    return value * {"GP": 1.0, "SP": 0.1, "CP": 0.01}[match.group(2)]


def _money(value, provenance, plus_base=None):
    out = {"unit": "GP", "provenance": provenance}
    if value is None:
        out["priceless"] = True
    else:
        out["value"] = round(value, 2)
    if plus_base:
        out["plus_base"] = plus_base
    return out


def _mass(pounds, provenance):
    """Exactly one of `value` and `negligible`. Never a zero standing in for
    "light enough not to count" -- the two mean different things and a cart
    that adds them is wrong in only one of the two cases."""
    if pounds is None:
        return {"unit": "lb", "negligible": True, "provenance": provenance}
    return {"unit": "lb", "value": round(pounds, 3), "provenance": provenance}


def _catalogue(conn, kind, lang="en"):
    out = {}
    for row in conn.execute(
        "SELECT name, data FROM record WHERE layer='srd' AND kind=? AND lang=?"
        " ORDER BY slug", (kind, lang),
    ):
        out[row["name"]] = json.loads(row["data"])
    return out


def _split_bases(subtype):
    """`Glaive, Greatsword, Longsword, or Scimitar` -> the four names."""
    # `A, B, or C` -- the Oxford comma means `, or ` is ONE separator, not a
    # comma followed by a base called "or C".
    parts = re.split(r",\s*(?:or\s+)?|\s+or\s+", subtype)
    return [p.strip() for p in parts if p.strip()]


def _resolve_base(subtype, bases):
    """What the book says the magic is laid on.

    Three answers, and the difference between them is the whole point: one
    named base (the number is settled), several named bases (the number is the
    player's choice among a known list), or an open family (`Any Simple or
    Martial`) where the book itself refuses to name one.
    """
    if not subtype:
        return None
    if subtype.lower().startswith("any"):
        return {"family": subtype}
    names = _split_bases(subtype)
    unknown = [n for n in names if n not in bases]
    if unknown:
        raise SrfhError(
            "subtype %r names %s, which is in no equipment table"
            % (subtype, ", ".join(unknown))
        )
    return {"options": names}


def _base_cost_span(names, bases):
    costs = sorted({_gp(bases[n]["cost"]) for n in names})
    return costs


def build_srfh(conn, lang="en"):
    """Write the SRFH layer. Returns (count, notes) -- notes are REPORTED."""
    weapons = _catalogue(conn, "weapon", lang)
    armors = _catalogue(conn, "armor", lang)
    gear = _catalogue(conn, "gear", lang)
    bases = {}
    bases.update(weapons)
    bases.update(armors)

    potion_weight = _lb(gear["Potion of Healing"]["weight"])
    scroll_weight = _lb(gear["Spell Scroll (Cantrip)"]["weight"])

    items = []
    for row in conn.execute(
        "SELECT id, slug, name, data FROM record"
        " WHERE layer='srd' AND kind='item' AND lang=? ORDER BY slug", (lang,),
    ):
        items.append((row["id"], row["slug"], row["name"], json.loads(row["data"])))

    notes = []
    records = []          # (rec, dst_id, rel)
    tally = {"extends": 0, "members": 0, "boosts": 0, "families": 0}
    buckets = {k: 0 for k in BUCKET_WEIGHT}
    twins = 0

    def wondrous_weight(name_for_shape):
        """A wondrous item's weight: its everyday twin, or its bucket."""
        head = _head_noun(name_for_shape)
        if head == "Crystal Ball":
            return _mass(CRYSTAL_BALL_WEIGHT, "inherited:Orb (Arcane Focuses, p.96)"), "twin"
        twin = TWIN_OF_HEAD.get(head, head)
        if twin in gear:
            return _mass(_lb(gear[twin]["weight"]), "inherited:%s" % twin), "twin"
        bucket = BUCKET_OF_HEAD.get(head, "jewellery")
        return (
            _mass(BUCKET_WEIGHT[bucket], "chosen:%s (ratified 2026-08-23)" % bucket),
            bucket,
        )

    def weight_for(category, base, name_for_shape):
        if category in ("weapon", "armor"):
            if base and "options" in base:
                spans = sorted({_lb(bases[n]["weight"]) or 0.0 for n in base["options"]})
                if len(spans) == 1:
                    return _mass(spans[0], "inherited:%s" % base["options"][0]), None
                return {
                    "unit": "lb", "from_base": True,
                    "provenance": "inherited:base chosen at purchase",
                    "options": [
                        {"base": n, "value": _lb(bases[n]["weight"])}
                        for n in base["options"]
                    ],
                }, None
            return {
                "unit": "lb", "from_base": True,
                "provenance": "inherited:base chosen at purchase",
                "family": base["family"] if base else "unstated",
            }, None
        if category == "potion":
            return _mass(potion_weight, "convention:Potion of Healing"), None
        if category == "scroll":
            return _mass(scroll_weight, "convention:Spell Scroll (Cantrip)"), None
        if category in FOCUS_WEIGHT:
            return _mass(FOCUS_WEIGHT[category], "convention:Arcane Focuses, p.96"), None
        if category == "ring":
            return _mass(None, "chosen:a ring is negligible (ratified 2026-08-23)"), None
        if category == "wondrous-item":
            return wondrous_weight(name_for_shape)
        raise SrfhError("no weight rule for category %r" % category)

    def cost_for(name, tier, category, base):
        if name == SPELL_SCROLL:
            # base + improvement, and the improvement's grid is the craft
            # workshop's, not this layer's.
            return {
                "unit": "GP", "provenance": "base-plus-improvement",
                "plus_base": {"family": "Parchment"},
                "improvement": "the spell written on it",
            }
        value = TIER_VALUE[tier]
        provenance = "tier:%s (p.206)" % tier
        if value is not None and category == "potion":
            value = value / 2.0                 # p.206: halve for a consumable
            provenance = "tier:%s halved, consumable (p.206)" % tier
        plus = None
        if category in ("weapon", "armor") and base:
            if "options" in base:
                plus = {
                    "options": [
                        {"base": n, "value": round(_gp(bases[n]["cost"]), 2)}
                        for n in base["options"]
                    ]
                }
            else:
                plus = {"family": base["family"]}
        money = _money(value, provenance, plus)
        # When the book names exactly ONE base, the addition it asks for has a
        # single answer, so we do it here. A reader with a sheet of paper and
        # no builder should not have to.
        if plus and value is not None and len(plus.get("options", [])) == 1:
            money["total"] = round(value + plus["options"][0]["value"], 2)
        return money

    def emit(slug, name, data, dst_id, rel):
        rec = {
            "id": canon.record_id(LAYER, "item", lang, slug),
            "layer": LAYER,
            "kind": "item",
            "lang": lang,
            "slug": slug,
            "name": name,
            "data": canon.canonical_json(data),
            "content_hash": canon.content_hash("item", lang, name, data),
            "source_id": None,
            "source_locator": "",
            "srd_version": None,
            "license": LICENSE,
            "attribution": ATTRIBUTION,
        }
        records.append((rec, dst_id, rel))

    for srd_id, slug, name, data in items:
        if name in BOOSTS:
            tally["boosts"] += 1
            notes.append(
                "improvement left without price or weight, by Eric's ruling of "
                "2026-08-23: %s" % name
            )
            continue

        category = data["category"]
        rarity = data["rarity"]

        if name in FAMILY_COUNT:
            tally["families"] += 1
            members = _members_of(name, data["description"], rarity)
            if len(members) != FAMILY_COUNT[name]:
                raise SrfhError(
                    "family %r yielded %d member(s), %d ratified -- the book "
                    "changed under a ratified value"
                    % (name, len(members), FAMILY_COUNT[name])
                )
            for variant, tier in members:
                member_name = _member_name(name, variant)
                member_slug = canon.slugify(member_name)
                mass, bucket = weight_for(category, None, name)
                if bucket:
                    buckets[bucket] += 1
                member = {
                    "name": member_name,
                    "replaces": srd_id,
                    "variant": variant,
                    "category": category,
                    "rarity_tier": tier,
                    "attunement": data["attunement"],
                    "attunement_by": _attunement_by(rarity),
                    "cost": cost_for(member_name, tier, category, None),
                    "weight": mass,
                }
                emit(member_slug, member_name, member, srd_id, "replaces")
                tally["members"] += 1
            continue

        tier = _tier_of(rarity)
        if tier == "Rarity Varies" and name != SPELL_SCROLL:
            raise SrfhError(
                "%r says its rarity varies and is not a declared family" % name
            )
        base = _resolve_base(data["subtype"], bases)
        mass, bucket = weight_for(category, base, name)
        if bucket:
            if bucket == "twin":
                twins += 1
            else:
                buckets[bucket] += 1
        payload = {
            "name": name,
            "extends": srd_id,
            "category": category,
            "rarity_tier": None if name == SPELL_SCROLL else tier,
            "rarity_note": (
                "varies with the spell written on it; the improvement carries "
                "the tier, not the parchment"
            ) if name == SPELL_SCROLL else None,
            "attunement": data["attunement"],
            "attunement_by": _attunement_by(rarity),
            "cost": cost_for(name, tier, category, base),
            "weight": mass,
        }
        if base:
            payload["base"] = base
        emit(slug, name, payload, srd_id, "extends")
        tally["extends"] += 1

    # ---- reconciliation ---------------------------------------------------
    # These are not "expected numbers"; they are the shape Eric ratified on
    # 2026-08-23 after reading them. If the catalogue below moves, this layer
    # must not follow it in silence -- a price is a rule of the game, and a new
    # one nobody read is a rule nobody agreed to. The build stops and a human
    # re-ratifies.
    measured = {
        "extends": tally["extends"], "members": tally["members"],
        "families": tally["families"], "boosts": tally["boosts"],
        "twin": twins,
    }
    measured.update(buckets)
    drift = {k: (v, RATIFIED[k]) for k, v in sorted(measured.items())
             if RATIFIED[k] != v}
    if drift:
        raise SrfhError(
            "the catalogue moved under values Eric ratified on 2026-08-23:\n"
            + "\n".join("  %-12s measured %d, ratified %d" % (k, got, want)
                         for k, (got, want) in drift.items())
            + "\nRe-read the change, then update RATIFIED with his answer."
        )

    for rec, dst_id, rel in records:
        db.insert_record(conn, rec)
    for rec, dst_id, rel in records:
        conn.execute(
            "INSERT INTO record_link (src_id, dst_id, rel, note) VALUES (?,?,?,?)",
            (rec["id"], dst_id, rel,
             "SRFH carries the price and the weight the SRD never printed"),
        )
    conn.commit()
    return tally, buckets, twins, notes
