"""Which French record is which English record — computed, never guessed.

WHAT THIS CLOSES. The two SRD catalogues have no join key. Every identifier
carries its own language (`srd:species:fr:drakeide` against
`srd:species:en:dragonborn`), the slugs are transliterations of translated
names, and no export carries a `translation_of` field. Matching by rank in the
document fails on the second element: both catalogues are sorted
alphabetically, each in its own language, so *Elfe* lands opposite *Dwarf*.
That was established on 2026-08-08 and is still true; what was never tested is
whether the DATA can do what the names cannot.

It can. A price is the same number in both languages — only the coin changes
(`25 GP` / `25 po`). A weight in the French layer is the English one divided by
exactly 2 (`1 lb.` -> `0,5 kg`), so it is reversible. Spell components are the
same three letters, V / S / M. And everything that was already a number — an
armour class, a hit point total, a damage die, six ability scores — never
passed through a translator at all.

THE RULE THIS MODULE OBEYS, and it is the whole design: a fingerprint counts
only when it is UNIQUE ON BOTH SIDES. One English record, one French record,
nothing else wearing the same fingerprint. Anything else is not a match, it is
a question, and it leaves here NAMED rather than resolved. `layers/TRADUCTION.md`
put it plainly and it has not been abrogated: *"une correspondance devinée
serait pire que l'absence de correspondance : elle donnerait silencieusement un
personnage faux."*

WHAT THIS MODULE IS NOT. It does not touch the SRD exports. The correspondence
is a THIRD artefact, produced beside them and never merged into them, so that
what was extracted verbatim under CC-BY stays distinguishable from what was
computed here. That separation is the same law, one level up: the 117 pairs a
human still has to arbitrate must never become indistinguishable from the 711
the data decided.

⛔ NO HARDCODED LIST OF GENRES. This module iterates over the kinds it is
GIVEN, and a kind with no fingerprint registered comes out marked
`no-fingerprint` with all of its records listed. The failure being avoided is
concrete and cost this project a lot two lots ago: `gen-srd-layer.mjs` iterates
over its own constant, so a genre absent from that constant is not refused, it
is simply never read — a build that succeeds and produces nothing. A catalogue
that grows must show up here as an unanswered question, never as a silence.

Nothing here reads the clock, the environment, the filesystem or a random
source: two runs over the same exports produce the same bytes.
"""

import re

# Every pair says HOW it was obtained, and the three ways are not equally
# strong. A pair the data decided, a pair deduced from another pair, and a pair
# a person signed are three different claims; a file that mixes them without
# saying which is which loses the only thing that made the artefact honest.
BY_FINGERPRINT = "structured-fingerprint/2"
BY_HUMAN = "human"
METHOD = BY_FINGERPRINT

# ---------------------------------------------------------------------------
# Normalisers — every one of them turns a localised string into a number or a
# token that survives the trip across languages.
# ---------------------------------------------------------------------------

_INT = re.compile(r"\d+")
_DICE = re.compile(r"\b(\d+d\d+)\b")
_BONUS = re.compile(r"(?<![\w.])([+\-−–]\s?\d+)(?![\d])")
_COMPONENT = re.compile(r"\b([VSM])\b")

# ` ` and ` ` are the non-breaking spaces the French layer uses as a
# thousands separator: "1 500 po". Stripping them is not cosmetic — leaving
# them in makes `1 500` and `1,500` two different prices.
_SPACES = (" ", " ", " ")


def _despace(text):
    for ch in _SPACES:
        text = text.replace(ch, "")
    return text


def ints(value):
    """Every integer in a string, thousands separators removed.

    `cr` reads `10 (XP 5,900, or 7,200 in lair; PB +4)` in English and
    `1/2 (100 PX ; BM +2)` in French: the same fact, wrapped in two different
    sentences. Only the numbers survive that, and only the first one is the
    challenge rating.
    """
    if value is None:
        return ()
    return tuple(int(m) for m in _INT.findall(_despace(str(value)).replace(",", "")))


def first_int(value):
    found = ints(value)
    return found[0] if found else None


# Copper is the common base because it is the only one both languages agree on
# by construction: the NUMBER is identical across the two layers, only the coin
# is spelled differently. `ep`/`pe` is carried although the SRD layer uses
# neither — a coin that appears later must not fall through as None in silence.
COINS = {"gp": 100, "po": 100, "sp": 10, "pa": 10, "cp": 1, "pc": 1,
         "ep": 50, "pe": 50}

_PRICE = re.compile(r"^\s*([\d.,\s]+)\s*([A-Za-z]{2})\s*$")


def copper(value):
    """A price in copper, or None when the string does not carry one.

    None is returned for `Varies` / `Variable` / `variable` and for anything
    else this does not understand. ⚠️ None is NOT zero and not "free": it means
    *this record cannot be fingerprinted on price*, which is why a fingerprint
    that contains it can still be unique on the other components — and why it
    must never be compared as if it were a value.
    """
    if not isinstance(value, str):
        return None
    match = _PRICE.match(_despace(value))
    if not match:
        return None
    digits = match.group(1).replace(",", "").replace(".", "").strip()
    coin = COINS.get(match.group(2).lower())
    if not digits.isdigit() or coin is None:
        return None
    return int(digits) * coin


_WEIGHT_FRAC = re.compile(r"^(\d+)/(\d+)(lb|kg|g)\.?$")
_WEIGHT = re.compile(r"^([\d.]+)(lb|kg|g)\.?$")
# 1 lb -> 500 g. That is the FRENCH LAYER's own conversion, measured: `1 lb.`
# is rendered `0,5 kg` and `50 lb.` is rendered `22,5 kg`. It is NOT the
# physical 453.6 g, and it is NOT Foundry's 400 g (their kg is 2.5 lb). Using
# the physical value here would break every match; using Foundry's would break
# them differently. The number that joins these two files is the one these two
# files used.
_GRAMS_PER = {"lb": 500, "kg": 1000, "g": 1}


def grams(value):
    """A weight in grams, or None.

    Handles the four spellings that actually occur: `4 lb.`, `1/2 lb.`,
    `58½ lb.` (½ is U+00BD, and it is NOT the same character as the `1/2`
    three lines above — both live in the same English file), and the French
    decimal comma `0,5 kg`. Returns None for `—` (U+2014, "negligible") and
    for `Varies`: negligible is not zero, and a fingerprint must not pretend
    otherwise.
    """
    if not isinstance(value, str):
        return None
    text = _despace(value.strip()).replace("½", ".5").replace(",", ".")
    match = _WEIGHT_FRAC.match(text)
    if match:
        amount = int(match.group(1)) / int(match.group(2))
        unit = match.group(3)
    else:
        match = _WEIGHT.match(text)
        if not match:
            return None
        amount, unit = float(match.group(1)), match.group(2)
    return round(amount * _GRAMS_PER[unit])


# The French layer converts feet to metres at 0.3 exactly (30 feet -> 9 m), so
# the trip back is 10/3. Everything is normalised to FEET because that is the
# side the numbers were written in.
_DISTANCE = re.compile(r"([\d.]+)\s*(km|m|mile|miles|feet|foot|ft)\b")
_FEET_PER = {"km": 3280.84, "m": 10 / 3, "mile": 5280, "miles": 5280,
             "feet": 1, "foot": 1, "ft": 1}
# The ranges that are words rather than distances. Each language's spellings
# collapse onto one token; a range this does not know becomes `?`, which is
# honest — it stops discriminating instead of discriminating wrongly.
_WORD_RANGE = (
    ("self", ("self", "personnelle", "personnel")),
    ("touch", ("touch", "contact")),
    ("sight", ("sight", "vue")),
    ("unlimited", ("unlimited", "illimitee", "illimitée")),
    ("special", ("special", "spéciale", "speciale")),
)


def feet(value):
    if not isinstance(value, str):
        return None
    text = _despace(value.replace(",", ".")).lower()
    match = _DISTANCE.search(text)
    if match:
        return round(_FEET_PER[match.group(2)] * float(match.group(1)))
    for token, spellings in _WORD_RANGE:
        if any(word in text for word in spellings):
            return token
    return "?"


def components(value):
    """V / S / M — the same three letters in both languages.

    Only the part before the first parenthesis is read: the material component
    itself is prose and is translated.
    """
    if not isinstance(value, str):
        return ()
    return tuple(sorted(set(_COMPONENT.findall(value.split("(")[0]))))


def dice(text):
    return tuple(sorted(_DICE.findall(text or "")))


def bonuses(text):
    """`+1`, `-2`... normalised, because three different minus signs occur.

    U+2212 (true minus) and U+2013 (en dash) both appear where a hyphen was
    meant; the English monster block uses one and the French another.
    """
    out = []
    for raw in _BONUS.findall(text or ""):
        out.append(_despace(raw).replace("−", "-").replace("–", "-"))
    return tuple(sorted(out))


# The French monster block localises the KEYS of its ability dictionary, which
# no field name announces: `for` for Strength, `sag` for Wisdom. Nothing else
# in the six is renamed.
_ABILITY_ALIAS = {"for": "str", "sag": "wis"}


def abilities(block):
    if not isinstance(block, dict):
        return ()
    scores = {}
    for key, entry in block.items():
        canonical = _ABILITY_ALIAS.get(key, key)
        if isinstance(entry, dict) and "score" in entry:
            scores[canonical] = entry["score"]
    return tuple(scores.get(k) for k in ("str", "dex", "con", "int", "wis", "cha"))


def _properties_count(value):
    if not value:
        return 0
    return len([part for part in str(value).split(",") if part.strip()])


def _versatile_die(value):
    """The die hiding inside `Versatile (1d10)` / `Polyvalente (1d10)`.

    The property NAME is translated; the die is not. Reading the die is what
    separates a Glaive from a Halberd without reading a word of either.
    """
    match = re.search(r"\((\d+d\d+)\)", value or "")
    return match.group(1) if match else None


# ---------------------------------------------------------------------------
# The fingerprints, one per kind.
# ---------------------------------------------------------------------------

def _fp_monster(data):
    return (abilities(data.get("abilities")), first_int(data.get("ac")),
            first_int(data.get("hp")), ints(data.get("cr"))[:1])


def _fp_weapon(data):
    return (data.get("damage_dice"), data.get("weapon_category"),
            data.get("weapon_range"), copper(data.get("cost")),
            grams(data.get("weight")),
            _properties_count(data.get("properties")),
            _versatile_die(data.get("properties")))


def _fp_armor(data):
    return (data.get("ac_base"), data.get("ac_dex_cap"),
            data.get("stealth_disadvantage"), copper(data.get("cost")),
            grams(data.get("weight")))


def _fp_gear(data):
    return (copper(data.get("cost")), grams(data.get("weight")))


def _fp_tool(data):
    return (data.get("ability_key"), copper(data.get("cost")),
            grams(data.get("weight")))


def _fp_spell(data):
    return (data.get("level"), data.get("ritual"), data.get("concentration"),
            data.get("cantrip"), components(data.get("components")),
            feet(data.get("range")), len(data.get("classes") or []))


def _fp_species(data):
    return (data.get("size_key"), feet(data.get("speed")),
            len(data.get("traits") or []), len(data.get("senses") or []))


# A magic bonus is small. `-18` is a temperature: the French *Anneau de chaleur
# constante* says the wearer is comfortable down to −18 °C where the English
# *Ring of Warmth* words it differently, and that stray number was enough to
# stop the two from pairing.
_BONUS_CEILING = 10


def _fp_item_value(data):
    """The six tiers and their prices — the same numbers in both languages.

    ⭐ A free join: the book prints `100 GP` and `100 po`, `40,000 GP` and
    `40 000 po`. The WORDS differ and the NUMBERS do not, so the scale
    identifies itself across the two catalogues without anything being declared.
    """
    tiers = sorted(data.get("tiers") or [], key=lambda t: t["rarity_key"])
    return (tuple(t["rarity_key"] for t in tiers),
            tuple(t["value_gp"] for t in tiers))


def _fp_item(data):
    """Magic items carry no numeric field at all — everything is in the prose.

    So the prose is mined for the two things a translator does not touch: dice
    expressions and small signed bonuses. It is still the weakest fingerprint
    here and it is reported as such.

    ⚠️ SET, NOT MULTISET, and the correction is worth writing down because the
    first version got it wrong in the way this repository keeps getting things
    wrong: it counted a pattern narrower than the thing it claimed to count.
    English prose says `1d100` one more time than French prose does — same
    table, same roll, one extra mention — and counting occurrences made five
    items look like orphans that are word-for-word translations of each other
    (*Deck of Illusions* / *Tarot fantasmagorique*, *Ring of Warmth* /
    *Anneau de chaleur constante*, and three more). How MANY times a die is
    mentioned is a fact about the prose; WHICH dice appear is a fact about the
    item.

    Loosening a fingerprint cannot create a wrong pair — only unique-on-both-
    sides emits — so the trade is pairs against ambiguity, never against
    correctness. Measured: 82 pairs to 85, seven English orphans down to two,
    two pairs lost to ambiguity, and **no pair moved**.
    """
    text = data.get("description") or ""
    small = tuple(sorted({b for b in bonuses(text)
                          if abs(int(b)) <= _BONUS_CEILING}))
    return (data.get("category"), data.get("attunement"),
            tuple(sorted(set(dice(text)))), small)


def _fp_class(data):
    """The class is fingerprinted on what a translator never touched.

    `saving_throw_keys` is one of the seven sites that already carry a stable
    key in both languages — it holds `["str", "con"]` on the French Barbarian
    too. Two saves out of six, plus a hit die and a mastery count, separate
    twelve classes without reading a word.
    """
    return (tuple(data.get("saving_throw_keys") or ()), data.get("hit_die"),
            data.get("weapon_mastery_count"),
            data.get("spellcasting_ability_key"),
            len(data.get("features") or ()))


def _fp_class_progression(data):
    """Twenty rows of numbers. The KEYS of `resources` are translated
    (`de_bardique` against `bardic_die`) — the VALUES are not, so the values
    are what is read, sorted, with the keys discarded.
    """
    rows = []
    for level in data.get("levels") or ():
        values = tuple(sorted(str(v) for v in (level.get("resources") or {}).values()))
        rows.append((level.get("level"), level.get("proficiency_bonus"),
                     len(level.get("features") or ()), values))
    return (tuple(rows), data.get("spell_slot_levels"))


def _fp_background(data):
    """`ability_keys` is stable across both layers; three of six, four
    backgrounds. That is enough and nothing else here is language-free.
    """
    return (tuple(data.get("ability_keys") or ()),
            len(data.get("skill_ids") or ()),
            bool(data.get("feat_option")))


FINGERPRINTS = {
    "monster": (_fp_monster, "six ability scores + AC + HP + CR"),
    "armor": (_fp_armor, "AC + Dex cap + stealth + price + weight"),
    "weapon": (_fp_weapon,
               "damage die + category + range + price + weight "
               "+ property count + versatile die"),
    "tool": (_fp_tool, "ability + price + weight"),
    "gear": (_fp_gear, "price + weight"),
    "spell": (_fp_spell,
              "level + ritual + concentration + cantrip + components "
              "+ range + class count"),
    "species": (_fp_species, "size + speed + trait count + sense count"),
    "item": (_fp_item,
             "category + attunement + which dice appear + small bonuses "
             "(mined from the prose; the weakest here)"),
    "class": (_fp_class,
              "saving throw keys + hit die + mastery count "
              "+ spellcasting ability + feature count"),
    "class-progression": (_fp_class_progression,
                          "the twenty rows: level + proficiency bonus "
                          "+ feature count + resource VALUES + slot levels"),
    "item-value": (_fp_item_value,
                   "the six rarity keys and their gold-piece values, which are "
                   "the same numbers in both languages"),
    "background": (_fp_background,
                   "ability keys + skill count + feat option"),
}


# ---------------------------------------------------------------------------
# The pairing itself.
# ---------------------------------------------------------------------------

class CorrespondenceError(RuntimeError):
    """A correspondence run that cannot be trusted to mean what it says."""


def _index(records, fingerprint):
    buckets = {}
    for record in records:
        buckets.setdefault(fingerprint(record["data"]), []).append(record)
    return buckets


def _brief(record):
    return {"id": record["id"], "name": record["name"]}


def correspond_kind(kind, en_records, fr_records):
    """Pair one genre. Returns matched pairs and, separately, the questions.

    A pair is emitted ONLY when exactly one English and exactly one French
    record share a fingerprint. Two English records wearing the same
    fingerprint are ambiguous even if the French side has exactly two as well:
    the data says these four go together, it does not say which goes with
    which, and that distinction is the entire point.
    """
    entry = FINGERPRINTS.get(kind)
    if entry is None:
        # Not an error. An unanswered question, carried in the open.
        return {
            "kind": kind,
            "fingerprint": None,
            "matched": [],
            "pending": [{
                "kind": kind,
                "reason": "no-fingerprint",
                "en": [_brief(r) for r in sorted(en_records, key=lambda r: r["id"])],
                "fr": [_brief(r) for r in sorted(fr_records, key=lambda r: r["id"])],
            }],
        }

    fingerprint, label = entry
    en_buckets = _index(en_records, fingerprint)
    fr_buckets = _index(fr_records, fingerprint)

    matched, pending = [], []
    for key in sorted(en_buckets, key=repr):
        here = en_buckets[key]
        there = fr_buckets.get(key, [])
        if len(here) == 1 and len(there) == 1:
            matched.append({"en": here[0]["id"], "fr": there[0]["id"],
                            "by": BY_FINGERPRINT})
        elif not there:
            pending.append({
                "kind": kind, "reason": "unmatched-en",
                "en": [_brief(r) for r in sorted(here, key=lambda r: r["id"])],
                "fr": [],
            })
        else:
            pending.append({
                "kind": kind, "reason": "ambiguous",
                "en": [_brief(r) for r in sorted(here, key=lambda r: r["id"])],
                "fr": [_brief(r) for r in sorted(there, key=lambda r: r["id"])],
            })

    # The French records no English fingerprint reached. Walking only the
    # English side would have hidden them — and the French catalogue is the
    # LONGER of the two (258 magic items against 253), so the records missing
    # from this direction are exactly the ones worth seeing.
    for key in sorted(fr_buckets, key=repr):
        if key not in en_buckets:
            pending.append({
                "kind": kind, "reason": "unmatched-fr",
                "en": [],
                "fr": [_brief(r) for r in
                       sorted(fr_buckets[key], key=lambda r: r["id"])],
            })

    matched.sort(key=lambda pair: pair["en"])
    pending.sort(key=lambda group: (group["reason"],
                                    group["en"][0]["id"] if group["en"]
                                    else group["fr"][0]["id"]))
    return {"kind": kind, "fingerprint": label,
            "matched": matched, "pending": pending}



# ---------------------------------------------------------------------------
# Second pass: pairs deduced from pairs.
# ---------------------------------------------------------------------------

# A route says: these records are already paired, they NAME something, so the
# things they name are paired too. 35 of the 38 weapons are paired and each one
# prints the name of its mastery — `Topple` on one side, `Renversement` on the
# other — so the eight mastery records fall out without a single new guess.
#
# ⛔ `weapon.properties` is NOT a route, and the reason is measured rather than
# assumed. A weapon's properties are one prose string; splitting it and pairing
# by position looks obvious and is wrong — the French SRD lists them in its own
# alphabetical order, so `Ammunition` came out mapping to `Chargement`,
# `Deux mains` AND `Munitions` depending on the weapon. The consistency guard
# below caught it: 8 conflicts out of 9 names, and nothing was emitted. That
# refusal is the route's result, not its failure.
TRANSITIVE_ROUTES = (
    {"through": "weapon", "field": "mastery", "into": "weapon-mastery"},
)


def _route_label(route):
    return "transitive/%s.%s" % (route["through"], route["field"])


def transitive_pairs(route, proven, records_by_kind):
    """Follow proven pairs through a named field. Returns (pairs, refusals).

    Four things have to hold before a pair is emitted, and each one is a way
    this could quietly go wrong:

      1. **Consistency.** Every weapon carrying `Topple` must point at the same
         French name. One disagreement anywhere and the whole name is refused —
         not resolved by majority. A majority vote here would be a guess wearing
         a number.
      2. **Existence.** Both names must actually be records of the target genre.
         A name that leads nowhere is a dangling reference, not a pair.
      3. **No contradiction.** A route may not produce a pair that disagrees
         with one the data already decided.
      4. **No double claim.** A record already paired is not paired again.

    Everything refused comes back named, with the reason, exactly as the direct
    pass does. A deduced pair is a weaker claim than a measured one, so it
    carries its own provenance and never borrows the fingerprint's.
    """
    through, field, into = route["through"], route["field"], route["into"]
    source = records_by_kind.get(through)
    target = records_by_kind.get(into)
    if not source or not target:
        return [], [{"route": _route_label(route), "reason": "genre-absent",
                     "detail": "%s or %s is not in this build" % (through, into)}]

    by_id = {r["id"]: r for lang in ("en", "fr") for r in source[lang]}
    observed = {}          # English name -> {French name: how many weapons said so}
    for en_id, fr_id in proven.items():
        en_rec, fr_rec = by_id.get(en_id), by_id.get(fr_id)
        if not en_rec or not fr_rec:
            continue       # a pair from another genre
        en_value = en_rec["data"].get(field)
        fr_value = fr_rec["data"].get(field)
        # ⚠️ One side naming something and the other naming nothing is a
        # DISAGREEMENT, not a shrug: it says the two records do not carry the
        # same fact, and a route must not step over that.
        if en_value is None and fr_value is None:
            continue
        if en_value is None or fr_value is None:
            observed.setdefault(en_value, {}).setdefault(fr_value, 0)
            observed[en_value][fr_value] += 1
            continue
        observed.setdefault(en_value, {}).setdefault(fr_value, 0)
        observed[en_value][fr_value] += 1

    index = {lang: {r["name"]: r for r in target[lang]} for lang in ("en", "fr")}
    pairs, refusals = [], []
    claimed_en = set(proven)
    claimed_fr = set(proven.values())

    for en_name in sorted(observed, key=repr):
        seen = observed[en_name]
        if len(seen) > 1:
            refusals.append({
                "route": _route_label(route), "reason": "conflict",
                "en": en_name,
                "fr": sorted((str(k) for k in seen), key=str),
                "detail": "%d weapons disagree on what %r translates to"
                          % (sum(seen.values()), en_name),
            })
            continue
        fr_name = next(iter(seen))
        if en_name is None or fr_name is None:
            refusals.append({
                "route": _route_label(route), "reason": "one-sided",
                "en": en_name, "fr": [fr_name],
                "detail": "one language names a %s here and the other does not"
                          % into,
            })
            continue
        en_rec = index["en"].get(en_name)
        fr_rec = index["fr"].get(fr_name)
        if not en_rec or not fr_rec:
            refusals.append({
                "route": _route_label(route), "reason": "dangling",
                "en": en_name, "fr": [fr_name],
                "detail": "no %s record named %r on the %s side"
                          % (into, en_name if not en_rec else fr_name,
                             "en" if not en_rec else "fr"),
            })
            continue
        if en_rec["id"] in claimed_en or fr_rec["id"] in claimed_fr:
            continue       # the data already decided this one; it wins
        pairs.append({"en": en_rec["id"], "fr": fr_rec["id"],
                      "by": _route_label(route)})
        claimed_en.add(en_rec["id"])
        claimed_fr.add(fr_rec["id"])

    pairs.sort(key=lambda pair: pair["en"])
    return pairs, refusals


# ---------------------------------------------------------------------------
# Third pass: what a person signed.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# A defect that makes human signatures unsafe on five specific records.
# ---------------------------------------------------------------------------

# ⛔ EMPTY, AND ON PURPOSE. The mechanism stays; its members are gone.
#
# WHAT IT IS FOR, which is not what its name suggests: it never meant "these
# records are broken". It means "a human signature made against one of these
# must say, in its note, that it knows what it was reading". A signature CLOSES
# a question, and closing one on a record that shows two items in one is the
# worst outcome available here.
#
# WHY IT EARNED ITS PLACE. Five English magic items used to carry the full
# description of the item printed after them, glued to their own. Eric read one
# of those tails and signed `sword-of-sharpness -> Épée mordante` in good faith
# -- *Épée mordante* is *Sword of Wounding*, the item that record had
# swallowed. This guard refused the signature and named why.
#
# WHY IT IS EMPTY NOW. Lot 86 repaired the extraction on 2026-08-23, and Eric
# corrected his signature to `srd:item:fr:epee-aceree` -- his words, "j'avais
# tort". Measured on all five before emptying, three ways each: every carrier is
# back to its own length, every swallowed item exists as its own record, and no
# carrier's text still contains the name of what it ate.
# `acceptance_the_guard_is_empty_because_the_records_are_clean` re-measures
# exactly that, so re-pollution turns this list's emptiness back into a failure.
#
# ⛔ HOW TO RE-ARM IT, written down so a future tidy-up does not delete a
# mechanism nobody knows how to refill: add `"<record id>": "<name of what it
# swallowed>"` for any record whose extracted text is found to contain another
# entry's prose. Every signature touching it then has to carry a note.
# `unit_signed_on_a_polluted_record_needs_a_note` exercises the mechanism with
# an entry of its own, so it keeps being tested while this stays empty.
POLLUTED_BY_EXTRACTION = {}

SIGNED_TEMPLATE = {"pairs": [], "no_equivalent": []}


def apply_signed(signed, proven, known_ids, polluted=None):
    """Fold in the decisions a human made, and refuse the ones that cannot be.

    `signed` is a hand-edited file, so every identifier in it is checked against
    the catalogue. A typo must not become a pair, and it must not vanish either:
    it comes back named.

    ⭐ `no_equivalent` is a THIRD STATE and it is not a tidier way of saying
    "pending". A record nobody has looked at yet and a record a person examined
    and declared to have no counterpart are different facts, and collapsing them
    means searching forever for something that was already established not to
    exist. It is also the state that must be hardest to enter: it is the only
    one that closes a question rather than opening it.
    """
    # The list is a PARAMETER so the guard's mechanism stays testable while the
    # module-level one is empty. Callers pass nothing; the test passes an entry
    # of its own.
    polluted = POLLUTED_BY_EXTRACTION if polluted is None else polluted
    pairs, no_equivalent, refusals, confirmed = [], [], [], []
    claimed_en, claimed_fr = set(proven), set(proven.values())

    for entry in signed.get("pairs", []):
        en_id, fr_id = entry.get("en"), entry.get("fr")
        missing = [i for i in (en_id, fr_id) if i not in known_ids]
        if missing:
            refusals.append({"reason": "signed-unknown-id", "ids": missing,
                             "detail": "signed pair names a record that is not "
                                       "in the catalogue"})
            continue
        if en_id.split(":")[1] != fr_id.split(":")[1]:
            refusals.append({"reason": "signed-genre-mismatch",
                             "ids": [en_id, fr_id],
                             "detail": "a pair must join two records of one genre"})
            continue
        if proven.get(en_id) == fr_id:
            # ⭐ NOT a conflict — an AGREEMENT, and it is the strongest thing in
            # the file. A person who reached the same pair independently has
            # confirmed the measurement rather than duplicated it. Five of these
            # arrived on 2026-08-22 and every one landed on a pair the repaired
            # item fingerprint had found on its own.
            confirmed.append(en_id)
            continue
        if en_id in claimed_en or fr_id in claimed_fr:
            refusals.append({"reason": "signed-already-paired",
                             "ids": [en_id, fr_id],
                             "detail": "one of these is already paired with "
                                       "something else; remove the signature or "
                                       "fix the pairing"})
            continue
        if en_id in polluted and not entry.get("note"):
            refusals.append({
                "reason": "signed-on-polluted-record", "ids": [en_id, fr_id],
                "detail": "%s carries the whole description of %r glued to the "
                          "end of its own, so a reader can pair on the wrong "
                          "half — and this signature has no note saying it knows "
                          "that. Check which item the French record actually "
                          "translates, then sign again with a note."
                          % (en_id, polluted[en_id])})
            continue
        pairs.append({"en": en_id, "fr": fr_id, "by": BY_HUMAN,
                      **({"note": entry["note"]} if entry.get("note") else {})})
        claimed_en.add(en_id)
        claimed_fr.add(fr_id)

    for entry in signed.get("no_equivalent", []):
        rid = entry.get("id")
        if rid not in known_ids:
            refusals.append({"reason": "signed-unknown-id", "ids": [rid],
                             "detail": "signed 'no equivalent' names a record "
                                       "that is not in the catalogue"})
            continue
        if rid in claimed_en or rid in claimed_fr:
            refusals.append({"reason": "signed-contradiction", "ids": [rid],
                             "detail": "declared to have no counterpart, but it "
                                       "is paired with one"})
            continue
        no_equivalent.append({"id": rid, "by": BY_HUMAN,
                              **({"note": entry["note"]} if entry.get("note") else {})})

    pairs.sort(key=lambda pair: pair["en"])
    no_equivalent.sort(key=lambda e: e["id"])
    confirmed.sort()
    return pairs, no_equivalent, refusals, confirmed


def correspond_all(records_by_kind, signed=None):
    """`records_by_kind` maps kind -> {"en": [...], "fr": [...]}.

    Three passes, in strictly decreasing order of strength, and each one only
    ever fills gaps the one before it left:

      1. **the data**   — a fingerprint unique on both sides;
      2. **deduction**  — a pair reached by following an already-proven pair;
      3. **a person**   — what somebody looked at and signed.

    Order matters and is not a preference. A deduction may not overturn a
    measurement, because the measurement is the stronger claim; a signature may
    not silently overturn either, because a person contradicting the data is a
    thing to LOOK AT, not to apply — so it is refused and named. Every pair
    carries which pass produced it.

    Refuses a kind present in one language and absent from the other: that is
    not a correspondence problem, it is a broken build, and it must not be
    reported as "nothing matched".
    """
    signed = signed or SIGNED_TEMPLATE

    kinds, one_sided = [], []
    for kind in sorted(records_by_kind):
        sides = records_by_kind[kind]
        if not sides.get("en") or not sides.get("fr"):
            one_sided.append(kind)
        else:
            kinds.append(kind)

    if one_sided:
        raise CorrespondenceError(
            "%d genre(s) exist in one language only: %s\n\n"
            "A genre with no counterpart cannot be paired, and reporting it as "
            "zero matches would read as 'the fingerprint failed' when the real "
            "answer is that half the catalogue is missing. Nothing was written."
            % (len(one_sided), ", ".join(one_sided))
        )

    # --- pass 1: the data -------------------------------------------------
    fingerprints, pairs, pending = {}, [], []
    for kind in kinds:
        result = correspond_kind(kind, records_by_kind[kind]["en"],
                                 records_by_kind[kind]["fr"])
        fingerprints[kind] = result["fingerprint"]
        pairs.extend(result["matched"])
        pending.extend(result["pending"])

    # --- pass 2: deduction ------------------------------------------------
    proven = {pair["en"]: pair["fr"] for pair in pairs}
    refusals = []
    for route in TRANSITIVE_ROUTES:
        derived, route_refusals = transitive_pairs(route, proven, records_by_kind)
        pairs.extend(derived)
        refusals.extend(route_refusals)
        proven.update({pair["en"]: pair["fr"] for pair in derived})

    # --- pass 2b: routes that do not read a number ------------------------
    for route in OCCURRENCE_ROUTES:
        derived, route_refusals = occurrence_pairs(route, proven, records_by_kind)
        pairs.extend(derived)
        refusals.extend(route_refusals)
        proven.update({pair["en"]: pair["fr"] for pair in derived})

    for route in MENTION_ROUTES:
        derived, route_refusals = mention_pairs(route, proven, records_by_kind)
        pairs.extend(derived)
        refusals.extend(route_refusals)
        proven.update({pair["en"]: pair["fr"] for pair in derived})

    # --- pass 2c: a second axis inside the groups the first one isolated ---
    derived, route_refusals = second_axis_pairs(pending, records_by_kind, proven)
    pairs.extend(derived)
    refusals.extend(route_refusals)
    proven.update({pair["en"]: pair["fr"] for pair in derived})

    # --- pass 3: a person -------------------------------------------------
    known_ids = {r["id"] for kind in kinds for lang in ("en", "fr")
                 for r in records_by_kind[kind][lang]}
    human_pairs, no_equivalent, signed_refusals, confirmed = apply_signed(
        signed, proven, known_ids)
    pairs.extend(human_pairs)
    refusals.extend(signed_refusals)
    proven.update({pair["en"]: pair["fr"] for pair in human_pairs})

    # --- what is still open ----------------------------------------------
    # A record paired by pass 2 or 3 must leave `pending`, and one declared to
    # have no counterpart must leave it too — otherwise the list grows a tail of
    # questions that were already answered, and nobody trusts it a second time.
    settled = set(proven) | set(proven.values()) | {e["id"] for e in no_equivalent}
    trimmed = []
    for group in pending:
        en_left = [b for b in group["en"] if b["id"] not in settled]
        fr_left = [b for b in group["fr"] if b["id"] not in settled]
        if not en_left and not fr_left:
            continue
        trimmed.append({**group, "en": en_left, "fr": fr_left})
    pending = trimmed

    by_kind = {}
    for kind in kinds:
        kind_pending = [g for g in pending if g["kind"] == kind]
        by_kind[kind] = {
            "fingerprint": fingerprints[kind],
            "en_records": len(records_by_kind[kind]["en"]),
            "fr_records": len(records_by_kind[kind]["fr"]),
            "matched": sum(1 for p in pairs if p["en"].split(":")[1] == kind),
            "no_equivalent": sum(1 for e in no_equivalent
                                 if e["id"].split(":")[1] == kind),
            "pending_groups": len(kind_pending),
            "pending_records": sum(max(len(g["en"]), len(g["fr"]))
                                   for g in kind_pending),
        }

    pairs.sort(key=lambda pair: pair["en"])
    # Smallest groups first: a two-against-two is decided at a glance, a
    # hundred-against-a-hundred is a different job. Whoever signs this list
    # should meet the cheap questions first and stop when it stops being cheap.
    pending.sort(key=lambda g: (max(len(g["en"]), len(g["fr"])), g["kind"],
                                g["en"][0]["id"] if g["en"] else g["fr"][0]["id"]))
    refusals.sort(key=repr)

    # A computed pair a person independently reached too is stronger than
    # either on its own; it says so on the pair rather than in a footnote.
    confirmed_set = set(confirmed)
    for pair in pairs:
        if pair["en"] in confirmed_set:
            pair["confirmed_by"] = BY_HUMAN

    by_provenance = {}
    for pair in pairs:
        by_provenance[pair["by"]] = by_provenance.get(pair["by"], 0) + 1

    return {
        "method": METHOD,
        "langs": ["en", "fr"],
        "by_kind": by_kind,
        "by_provenance": by_provenance,
        "totals": {
            "matched": len(pairs),
            "confirmed_by_human": len(confirmed),
            "no_equivalent": len(no_equivalent),
            "pending_groups": len(pending),
            "pending_records": sum(max(len(g["en"]), len(g["fr"]))
                                   for g in pending),
            "refused": len(refusals),
        },
        "pairs": pairs,
        "no_equivalent": no_equivalent,
        "refusals": refusals,
        "pending": pending,
    }


# ---------------------------------------------------------------------------
# Lot 83 — three more routes, for records the fingerprint cannot reach.
# ---------------------------------------------------------------------------
#
# 198 records carry no number at all (`glossary` 152, `skill` 18, `feat` 17,
# `weapon-property` 11): a name and prose, nothing to measure. Tightening the
# fingerprint will never reach them. 211 more have a fingerprint that matches
# too many candidates. Two problems, two routes — plus a third for the second
# population.
#
# ⛔ NONE OF THEM COMPARES TWO NAMES. Every route below uses each name only to
# find that name's own occurrences in its own language, then compares the
# resulting SETS. A French name and an English name are never put side by side
# and judged to look alike; that is the one move this repository refuses in
# every genre, and `skill` and `glossary` are exactly where a near-miss name is
# a trap (`Animal Handling` and `Survival`; `Attack Roll` and `Reach`).

import json as _json
import re as _re
import unicodedata as _ud


def _fold(text):
    """Lowercase, accents removed. For finding a term, never for comparing two."""
    return "".join(c for c in _ud.normalize("NFD", text.lower())
                   if not _ud.combining(c))


def _dig(data, path):
    """Follow a dotted path, returning the ids found there and nothing else.

    ⚠️ `any` is not an identifier. A class whose skill choice is "any" cites no
    skill in particular, and counting it as a citation would give every skill
    the same profile.
    """
    node = data
    for part in path.strip(".").replace("[]", "").split("."):
        node = node.get(part) if isinstance(node, dict) else None
        if node is None:
            return []
    values = node if isinstance(node, list) else [node]
    return [v for v in values if isinstance(v, str) and v.startswith("srd:")]


# ---------------------------------------------------------------------------
# Route 1 — occurrence profile.
# ---------------------------------------------------------------------------
#
# ⭐ THE IDEA THAT UNLOCKS THIS, and it comes from correcting an earlier refusal
# rather than reversing it. Lot 3 refused `weapon.properties` because pairing
# them BY POSITION contradicted itself on 8 names out of 9 — the French SRD
# lists properties in its own alphabetical order. That refusal was right, and it
# only ever condemned the POSITION.
#
# **The order lies; the membership does not.** Take the set of proven weapons
# carrying an English property, map it through the weapon pairs, and ask which
# French property is carried by exactly those weapons and no others. No order is
# read. No name is compared.
#
# ⛔ EXACT EXTENSION ONLY. Two things carried by exactly the same records are
# INDISCERNIBLE and go back to `pending` saying so — `Animal Handling` and
# `Survival` are cited by the same classes and backgrounds, and no amount of
# staring separates them from the outside. That is the normal case, not a
# failure.
OCCURRENCE_ROUTES = (
    {"into": "weapon-property", "mode": "names",
     "carriers": (("weapon", "properties"),)},
    {"into": "skill", "mode": "ids",
     "carriers": (("class", ".skill_choice.from[]"),
                  ("background", ".skill_ids[]"),
                  ("species", ".granted_skill_choice.from[]"))},
    {"into": "feat", "mode": "ids",
     "carriers": (("background", ".feat_id"),)},
)


def _property_names(value):
    """`Loading, Light, Ammunition (Range 30/120; Bolts)` -> the three names.

    The parenthetical is dropped: it carries a range and an ammunition type,
    both of which are translated and neither of which is the property's name.
    """
    return {part.split("(")[0].strip()
            for part in (value or "").split(",") if part.strip()}


def occurrence_pairs(route, proven, records_by_kind):
    into = route["into"]
    target = records_by_kind.get(into)
    if not target:
        return [], [{"route": "occurrence/%s" % into, "reason": "genre-absent",
                     "detail": "%s is not in this build" % into}]

    label = "occurrence/%s" % into
    via = ["%s.%s" % (kind, field.strip(".").replace("[]", ""))
           for kind, field in route["carriers"]]

    # Both sides are read over the SAME proven carriers, in the same order, so
    # the two profiles are comparable by construction. A carrier that is not
    # paired contributes to neither side — otherwise one profile would carry
    # evidence the other cannot have, and every extension would miss by one.
    profile_en, profile_fr = {}, {}
    slot = 0
    carriers_used = 0
    for kind, field in route["carriers"]:
        source = records_by_kind.get(kind)
        if not source:
            continue
        en_by_id = {r["id"]: r for r in source["en"]}
        fr_by_id = {r["id"]: r for r in source["fr"]}
        couples = [(e, f) for e, f in sorted(proven.items())
                   if e in en_by_id and f in fr_by_id]
        carriers_used += len(couples)
        for en_id, fr_id in couples:
            if route["mode"] == "ids":
                keys_en = _dig(en_by_id[en_id]["data"], field)
                keys_fr = _dig(fr_by_id[fr_id]["data"], field)
            else:
                keys_en = _property_names(en_by_id[en_id]["data"].get(field))
                keys_fr = _property_names(fr_by_id[fr_id]["data"].get(field))
            for key in keys_en:
                profile_en.setdefault(key, set()).add(slot)
            for key in keys_fr:
                profile_fr.setdefault(key, set()).add(slot)
            slot += 1

    if route["mode"] == "ids":
        en_index = {r["id"]: r for r in target["en"]}
        fr_index = {r["id"]: r for r in target["fr"]}
    else:
        en_index = {r["name"]: r for r in target["en"]}
        fr_index = {r["name"]: r for r in target["fr"]}

    pairs, refusals = [], []
    claimed_en, claimed_fr = set(proven), set(proven.values())
    for key in sorted(profile_en):
        record = en_index.get(key)
        if record is None or not profile_en[key]:
            continue
        wanted = profile_en[key]
        candidates = [k for k, prof in profile_fr.items()
                      if prof == wanted and k in fr_index]
        if len(candidates) > 1:
            refusals.append({
                "route": label, "reason": "indiscernible",
                "en": record["name"],
                "fr": sorted(fr_index[k]["name"] for k in candidates),
                "detail": "carried by exactly the same %d record(s); nothing "
                          "outside them separates these" % len(wanted)})
            continue
        if not candidates:
            refusals.append({
                "route": label, "reason": "no-exact-extension",
                "en": record["name"], "fr": [],
                "detail": "no %s is carried by exactly those %d record(s)"
                          % (into, len(wanted))})
            continue
        twin = fr_index[candidates[0]]
        if record["id"] in claimed_en or twin["id"] in claimed_fr:
            continue
        pairs.append({"en": record["id"], "fr": twin["id"], "by": label,
                      "via": via})
        claimed_en.add(record["id"])
        claimed_fr.add(twin["id"])

    # Anything the carriers never mention has NO profile — and an empty profile
    # is not weak evidence, it is none. `Improvised Weapons` and `Range` are
    # weapon properties no weapon in the table carries; `Performance` is a skill
    # no proven carrier cites.
    silent = sorted(k for k in en_index if k not in profile_en)
    if silent:
        refusals.append({
            "route": label, "reason": "never-carried",
            "en": None, "fr": [],
            "detail": "%d %s record(s) are cited by no proven carrier, so they "
                      "have no profile at all: %s"
                      % (len(silent), into,
                         ", ".join(en_index[k]["name"] for k in silent))})

    pairs.sort(key=lambda pair: pair["en"])
    return pairs, refusals


# ---------------------------------------------------------------------------
# Route 2 — mention profile, corroborated across independent corpora.
# ---------------------------------------------------------------------------
#
# `glossary` is cited by NOBODY: no record anywhere carries a glossary id. But
# the terms are USED — a monster is Frightened, a spell creates a Cone, an item
# grants Advantage — so each term has a footprint in the prose of records that
# are already paired.
#
# 🔴 AND THAT FOOTPRINT LIES IF YOU TRUST IT ALONE. Measured: matching on the
# monster corpus by itself proposed `Attack Roll -> Allonge` and
# `Damage -> Allonge`. Both English terms appear in nearly every English stat
# block; `allonge` appears in nearly every French one. Their profiles coincide
# by SATURATION, not by identity, and the same French term was claimed twice.
#
# Two guards, and the second is what makes the route sound:
#
#   * **bijection** — the English term's profile must single out one French
#     term, and that French term's profile must single out the same English
#     term. This alone kills the saturation pairs above.
#   * **corroboration** — the same pair must be reached in at least two
#     INDEPENDENT corpora (monsters, spells, items, classes), and no corpus may
#     disagree. Two populations that share no records cannot both be fooled by
#     the same coincidence of phrasing.
#
# ⭐ Corroboration replaces a threshold, and that is the point. The first
# version of this route excluded "saturated" terms with a hand-picked cutoff.
# A cutoff is a knob, and a knob is where a guess hides. Independent agreement
# is evidence; a threshold is a preference.
MENTION_ROUTES = (
    {"into": "glossary",
     "corpora": ("monster", "spell", "item", "class"),
     "min_corroboration": 2},
)


def _mention_profiles(names, blobs, side):
    profiles = {}
    for key, name in names.items():
        # `e?s?` tolerates the French plural and feminine agreement the SRD
        # writes on conditions. It never crosses from one term to another: the
        # word boundaries hold it in place.
        pattern = _re.compile(r"\b" + _re.escape(_fold(name)) + r"e?s?\b")
        profiles[key] = frozenset(i for i, blob in enumerate(blobs)
                                  if pattern.search(blob[side]))
    return profiles


def _bijective_mentions(target, corpus_blobs):
    en_names = {r["id"]: r["name"] for r in target["en"]}
    fr_names = {r["id"]: r["name"] for r in target["fr"]}
    prof_en = _mention_profiles(en_names, corpus_blobs, 0)
    prof_fr = _mention_profiles(fr_names, corpus_blobs, 1)
    found = {}
    for en_id, wanted in prof_en.items():
        if not wanted:
            continue
        forward = [fr_id for fr_id, prof in prof_fr.items() if prof == wanted]
        if len(forward) != 1:
            continue
        backward = [x for x, prof in prof_en.items() if prof == prof_fr[forward[0]]]
        if len(backward) != 1:
            continue
        found[en_id] = forward[0]
    return found


def mention_pairs(route, proven, records_by_kind):
    into = route["into"]
    target = records_by_kind.get(into)
    if not target:
        return [], [{"route": "mention/%s" % into, "reason": "genre-absent",
                     "detail": "%s is not in this build" % into}]

    verdicts, sizes = {}, {}
    for kind in route["corpora"]:
        source = records_by_kind.get(kind)
        if not source:
            continue
        en_by_id = {r["id"]: r for r in source["en"]}
        fr_by_id = {r["id"]: r for r in source["fr"]}
        couples = [(e, f) for e, f in sorted(proven.items())
                   if e in en_by_id and f in fr_by_id]
        if not couples:
            continue
        # sort_keys so a record's blob does not depend on dict ordering, and
        # ensure_ascii=False so a French term is searched as itself.
        def _blob(record):
            return _fold(_json.dumps(record["data"], sort_keys=True,
                                     ensure_ascii=False))
        blobs = [(_blob(en_by_id[e]), _blob(fr_by_id[f])) for e, f in couples]
        verdicts[kind] = _bijective_mentions(target, blobs)
        sizes[kind] = len(couples)

    pairs, refusals = [], []
    claimed_en, claimed_fr = set(proven), set(proven.values())
    names_en = {r["id"]: r["name"] for r in target["en"]}
    names_fr = {r["id"]: r["name"] for r in target["fr"]}

    everyone = sorted({en_id for found in verdicts.values() for en_id in found})
    for en_id in everyone:
        answers = {kind: found[en_id] for kind, found in verdicts.items()
                   if en_id in found}
        distinct = set(answers.values())
        if len(distinct) > 1:
            refusals.append({
                "route": "mention/%s" % into, "reason": "corpora-disagree",
                "en": names_en[en_id],
                "fr": sorted(names_fr[v] for v in distinct),
                "detail": "independent corpora reached different answers: %s"
                          % ", ".join("%s says %s" % (k, names_fr[v])
                                      for k, v in sorted(answers.items()))})
            continue
        if len(answers) < route["min_corroboration"]:
            refusals.append({
                "route": "mention/%s" % into, "reason": "uncorroborated",
                "en": names_en[en_id], "fr": [names_fr[next(iter(distinct))]],
                "detail": "only %s reached this; %d independent corpora are "
                          "required" % (", ".join(answers),
                                        route["min_corroboration"])})
            continue
        fr_id = next(iter(distinct))
        if en_id in claimed_en or fr_id in claimed_fr:
            continue
        pairs.append({"en": en_id, "fr": fr_id,
                      "by": "mention/%s" % into,
                      "corroborated_by": sorted(answers)})
        claimed_en.add(en_id)
        claimed_fr.add(fr_id)

    reached = len(everyone)
    refusals.append({
        "route": "mention/%s" % into, "reason": "never-mentioned",
        "en": None, "fr": [],
        "detail": "%d of %d %s records were never singled out by any corpus "
                  "(corpora read: %s)"
                  % (len(names_en) - reached, len(names_en), into,
                     ", ".join("%s=%d pairs" % (k, n) for k, n in sorted(sizes.items())))})
    pairs.sort(key=lambda pair: pair["en"])
    return pairs, refusals


# ---------------------------------------------------------------------------
# Route 3 — a second, independent axis, applied inside an ambiguous group.
# ---------------------------------------------------------------------------
#
# These records are not unreachable, they are under-discriminated: the
# fingerprint matches several candidates. ⛔ The fix is NOT a finer fingerprint
# mined from the prose — `item` already carries the weakest prose-mined
# fingerprint here and is the most ambiguous genre of all, so digging there
# makes it worse.
#
# Instead, a SECOND axis built from fields the first one never touched, applied
# only WITHIN a group the first axis already isolated. A pair is emitted when
# both axes point at the same record: the first put these few together, the
# second tells them apart. A group the second axis cannot split stays ambiguous.
#
# 📌 `gear` and `item` get no entry here on purpose. `gear` carries three fields
# and the fingerprint already uses two of them; `item` carries no untouched
# field that is not prose. Saying so is the result.

def _casting_time(value):
    if not isinstance(value, str):
        return None
    text = _fold(value)
    number = _re.findall(r"\d+", text)
    kind = ("bonus" if "bonus" in text
            else "reaction" if "reaction" in text
            else "minute" if "minute" in text
            else "hour" if ("hour" in text or "heure" in text)
            else "action")
    return (kind, number[0] if number else None)


def _duration(value):
    if not isinstance(value, str):
        return None
    text = _fold(value)
    number = _re.findall(r"\d+", text)
    kind = ("instant" if ("instantaneous" in text or "instantan" in text)
            else "until" if ("dispelled" in text or "dissip" in text)
            else "round" if ("round" in text or "rond" in text)
            else "minute" if "minute" in text
            else "hour" if ("hour" in text or "heure" in text)
            else "day" if ("day" in text or "jour" in text)
            else "other")
    return (kind, number[0] if number else None)


SECOND_AXIS = {
    "spell": (lambda d: (_casting_time(d.get("casting_time")),
                         _duration(d.get("duration"))),
              "casting time + duration, neither of which the fingerprint reads"),
    "tool": (lambda d: (len([x for x in (d.get("craft") or "").split(",")
                             if x.strip()]),
                        d.get("variants") is None),
             "how many things it crafts + whether it has variants"),
    "species": (lambda d: (len(d.get("lineages") or []),
                           d.get("creature_type") is not None),
                "lineage count + whether a creature type is stated"),
}


def second_axis_pairs(pending, records_by_kind, proven):
    by_id = {r["id"]: r for kind in records_by_kind for lang in ("en", "fr")
             for r in records_by_kind[kind][lang]}
    pairs, refusals = [], []
    claimed_en, claimed_fr = set(proven), set(proven.values())
    no_axis = {}

    for group in pending:
        if group["reason"] != "ambiguous":
            continue
        kind = group["kind"]
        entry = SECOND_AXIS.get(kind)
        if entry is None:
            no_axis[kind] = no_axis.get(kind, 0) + max(len(group["en"]),
                                                       len(group["fr"]))
            continue
        axis, _label = entry
        buckets_en, buckets_fr = {}, {}
        for brief in group["en"]:
            buckets_en.setdefault(repr(axis(by_id[brief["id"]]["data"])), []).append(brief)
        for brief in group["fr"]:
            buckets_fr.setdefault(repr(axis(by_id[brief["id"]]["data"])), []).append(brief)
        for key in sorted(buckets_en):
            here, there = buckets_en[key], buckets_fr.get(key, [])
            if len(here) == 1 and len(there) == 1:
                if here[0]["id"] in claimed_en or there[0]["id"] in claimed_fr:
                    continue
                pairs.append({"en": here[0]["id"], "fr": there[0]["id"],
                              "by": "second-axis/%s" % kind})
                claimed_en.add(here[0]["id"])
                claimed_fr.add(there[0]["id"])

    for kind, count in sorted(no_axis.items()):
        refusals.append({
            "route": "second-axis", "reason": "no-second-axis",
            "en": None, "fr": [],
            "detail": "%s has %d ambiguous record(s) and no field the "
                      "fingerprint has not already read; the only thing left is "
                      "prose, which is what made this genre ambiguous in the "
                      "first place" % (kind, count)})

    pairs.sort(key=lambda pair: pair["en"])
    return pairs, refusals
