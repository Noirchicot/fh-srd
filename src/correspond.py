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

METHOD = "structured-fingerprint/1"

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


def _fp_item(data):
    """Magic items carry no numeric field at all — everything is in the prose.

    So the prose is mined for the two things a translator does not touch: dice
    expressions and signed bonuses. It is the weakest fingerprint here and it
    is reported as such; it decides roughly a third of the catalogue and hands
    the rest over NAMED rather than pretending.
    """
    text = data.get("description") or ""
    return (data.get("category"), data.get("attunement"),
            dice(text), bonuses(text))


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
    "item": (_fp_item, "category + attunement + dice + bonuses (prose-mined)"),
    "class": (_fp_class,
              "saving throw keys + hit die + mastery count "
              "+ spellcasting ability + feature count"),
    "class-progression": (_fp_class_progression,
                          "the twenty rows: level + proficiency bonus "
                          "+ feature count + resource VALUES + slot levels"),
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
                            "by": METHOD})
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


def correspond_all(records_by_kind):
    """`records_by_kind` maps kind -> {"en": [...], "fr": [...]}.

    Refuses a kind that is present in one language and absent from the other:
    that is not a correspondence problem, it is a broken build, and it must not
    be reported as "nothing matched".
    """
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

    by_kind, pairs, pending = {}, [], []
    for kind in kinds:
        result = correspond_kind(kind, records_by_kind[kind]["en"],
                                 records_by_kind[kind]["fr"])
        n_pending = sum(max(len(g["en"]), len(g["fr"])) for g in result["pending"])
        by_kind[kind] = {
            "fingerprint": result["fingerprint"],
            "en_records": len(records_by_kind[kind]["en"]),
            "fr_records": len(records_by_kind[kind]["fr"]),
            "matched": len(result["matched"]),
            "pending_groups": len(result["pending"]),
            "pending_records": n_pending,
        }
        pairs.extend(result["matched"])
        pending.extend(result["pending"])

    pairs.sort(key=lambda pair: pair["en"])
    # Smallest groups first: a two-against-two is decided at a glance, a
    # hundred-against-a-hundred is a different job. Whoever signs this list
    # should meet the cheap questions first and stop when it stops being cheap.
    pending.sort(key=lambda g: (max(len(g["en"]), len(g["fr"])), g["kind"],
                                g["en"][0]["id"] if g["en"] else g["fr"][0]["id"]))
    return {
        "method": METHOD,
        "langs": ["en", "fr"],
        "by_kind": by_kind,
        "totals": {
            "matched": len(pairs),
            "pending_groups": len(pending),
            "pending_records": sum(max(len(g["en"]), len(g["fr"]))
                                   for g in pending),
        },
        "pairs": pairs,
        "pending": pending,
    }
