# The mechanical fields — what was derived, what was measured, what was refused

> **Written for the architect and for lot `9-bloc-build`.** Lot `8-srd-mecanique`
> was asked to put numbers and identifiers beside the prose the SRD prints, so
> that a character builder stops having to read French sentences. This document
> is the handover: the inventory of what came out, the measurement behind each
> field, and the list of things that were deliberately not emitted.
>
> The field names are the ones in `fhpc/contracts/DERIVATION-FIELDS.md`. None
> was renamed, none was added beyond it. Where the contract left a shape open,
> the reading taken is stated here and repeated as a question in
> `QUESTIONS-ARCHITECTE.md`.

---

## The rule that governs everything below

**Added beside, never instead of.** `hit_point_die` is still
`"d6 par niveau de Magicien"`; `hit_die` is `6`, next to it. The printed string
is what a player reads and what the attribution suite compares to the PDF
character for character; the mechanical field is what the engine applies.

**Proven, not asserted:**

| check | result |
|---|---|
| record ids, before vs. after | identical set, 2613 records, both languages |
| every pre-existing `data` field, before vs. after | **equal, value for value, on all 2613** |
| the 9 genres that gained no field | **byte-identical export files** |
| the public site under `web/` | **byte-identical**, all 29 pages |
| two consecutive full builds | byte-identical exports; rebuild leaves the tree clean |
| publish gate (`src/check_publishable.py`) | passes; tripwire clean over 26 patterns |

Only ten export files moved — `class`, `background`, `species`, `weapon` and
`armor` in each language — plus `MANIFEST.json`, which is what `fhpc` verifies.

---

## Where the derivation happens, and why there

`src/derive_mechanics.py`, called once per record from `src/build.py`, between
the parse and the insert. It **reads no PDF and no page**: every value is a
second reading of a field a calibrated parser already produced. That keeps the
twenty-eight parser grammars untouched — and their tests green — and keeps the
derivation reviewable on its own.

One structural change was needed in `build.py`. The kinds used to be parsed and
inserted one at a time in alphabetical order, which puts `feat`, `skill` and
`tool` **after** the `background` and `class` records that must resolve names
against them. Now every kind of one source is parsed first, the three index
kinds are resolved to identifiers, and only then is anything written. The index
kinds receive no derived field, so the identifiers computed for them are final
before any other record uses them.

**A name that does not resolve stops the build.** There is no fallback and no
plausible-looking id pointing at nothing.

---

## Group A — the fields that were due, and are here

All counts are **per language**, and every one is symmetric between French and
English.

### `class` — 12/12, complete

| field | measure | notes |
|---|---|---|
| `hit_die` | **12/12** | `6, 8, 10, 12`. A die outside that set is a refusal. |
| `saving_throw_keys` | **12/12** | two canonical keys, e.g. `["int","wis"]` for the Wizard **in both languages** |
| `skill_choice` | **12/12** | `{count, from}`; `from` is a list of real `skill` ids, or `"any"` |

All 78 skill options across the eleven classes with a listed menu resolve to
`skill` records — the same join `tests/test_acceptance_srd_tables.py` already
proved, reused rather than reinvented.

**B1, arbitrated and carried through:** the Bard prints `"3 compétences au
choix (cf. « Comment jouer »)"` with no list, so it gets
`{count: 3, from: "any"}`. No list was fabricated.

### `background` — 4/4, complete

| field | measure | notes |
|---|---|---|
| `skill_ids` | **4/4** (8 ids) | every one resolves to a `skill` record carrying an `ability_key` |
| `ability_keys` | **4/4** (12 keys) | canonical, both languages |
| `feat_id` | **4/4** | resolves to a real `feat` record |
| `tool_id` / `tool_choice` | **3 + 1** | three granted tools, one choice |

**B2, arbitrated and carried through:** the Soldier prints `"Choisissez un type
de boîte de jeux"`, so it gets `tool_choice`, not `tool_id`. A choice is not a
granted proficiency.

### `species` — 9/9 for speed, 7/9 for size

| field | measure | notes |
|---|---|---|
| `speed_m` (FR) / `speed_ft` (EN) | **9/9** | the Goliath's `"10,50 m"` becomes `10.5`; `"9 m"` becomes `9`, an integer, not `9.0` |
| `size_key` | **7/9** | the two omissions are explained below, and they are not failures |

### `weapon` — 38/38

| field | measure | notes |
|---|---|---|
| `damage_dice` | **37/38** + 1 `null` | |
| `damage_flat` | **1** | the Blowgun |
| `damage_type_key` | **38/38** | 19 piercing, 9 bludgeoning, 10 slashing — *the same three counts in both languages*, which is a cross-language witness, not a coincidence |

**B3, arbitrated and carried through:** the Blowgun deals `"1 perforant"` —
`damage_dice: null`, `damage_flat: 1`. Never `"1d1"`, which is a die a table
would actually roll.

### `armor` — 12/13 + the Shield

| field | measure | notes |
|---|---|---|
| `ac_base` | **12** integers + `null` for the Shield | |
| `ac_dex_cap` | **12** | `2` where the source caps, `null` where it does not, `0` where Dexterity does not apply at all |
| `ac_bonus` | **1** | the Shield |

**B4, arbitrated and carried through:** the Shield prints `"+2"` —
`ac_bonus: 2`, `ac_base: null`, and **no** `ac_dex_cap`, because a modifier has
no base to cap Dexterity against.

---

## Group B — attempted, and split

The contract allowed this group to be refused outright. It is **partly
delivered and partly refused**, and the line between the two is drawn here
rather than left for someone to discover.

### Delivered: `senses` — 6/9, both languages

```json
"senses": [{ "id": "darkvision", "range_m": 18 }]
```

Six species print a Darkvision trait; three (Goliath, Halfling, Human) print
none at all — verified as **zero occurrences of the word** in their
descriptions, so the absence is the source's, not the parser's.

The reading is anchored on the trait's own sentence
(`"Vision dans le noir. Vous disposez de la Vision dans le noir sur 18 m."`),
which matters: the Elf's description also contains
`"Drow La portée de votre Vision dans le noir passe à 36 m"`, a **lineage
benefit** that must not be read as the species' base sense. The anchored
pattern excludes it.

Cross-checked between languages, which were parsed by two independent
grammars: 18 m ↔ 60 ft and 36 m ↔ 120 ft, on all six, with no exception.

### Delivered: `granted_skill_choice` — 2/9, both languages

The Elf (`"Sens aiguisés"` / `"Keen Senses"`) offers three named skills, all
three resolving to real `skill` records. The Human (`"Compétent"` /
`"Skillful"`) grants a free choice, so `{count: 1, from: "any"}` — the same
convention the Bard's class menu uses. No other species grants a skill.

One trap, worth recording because it was caught by a refusal rather than by
reading: the species trait separates its options with **"ou"** where a class
skill menu uses **"et"** (`"Intuition, Perception ou Survie"` against
`"Persuasion et Tromperie"`). Reusing the class splitter produced
`"Perception ou Survie"` as a single name, and the join refused it by name.
Two lists, two conjunctions, two grammars.

### REFUSED: `traits`, and the elven / draconic / fiendish lineages

**Not attempted, and this is a measurement, not fatigue.** The species
descriptions are a two-column PDF layout flattened into one string, and the
flattening does not preserve reading order or record boundaries:

- In `srd:species:fr:elfe`, the `"Vision dans le noir."` trait appears **after**
  the lineage table, below three lineage rows and the table's own title.
- In `srd:species:fr:elfe`, the Wood Elf row's level-3 and level-5 spells arrive
  as `"grande foulée passage sans trace"` — two spell names, no separator.
- The lineage table's header row (`"Lignage Niveau 1 Niveau 3 Niveau 5"`) and
  its title (`"Lignages elfiques"`) sit **inside** the paragraph flow.
- Worst, and load-bearing: **`srd:species:en:human` ends with the Tiefling's
  `"Fiendish Legacies"` table** — `Legacy Level 1 Level 3 Level 5`, `Abyssal…`,
  `Infernal…`. A `"Name. text"` segmenter would hand the Human three traits it
  does not have.

Any `traits` array built from this would be right for the four short species
and quietly wrong for the five long ones. That is exactly the outcome the
contract forbids — "neuf espèces dont trois sont approximatives sans le dire".

**This is a pre-existing artefact of `parse_species_en.py` / `_fr.py`, not
something introduced here, and it was left alone**: reshaping those records
would change content hashes that are already published. It is written up as a
question rather than fixed.

---

## What is deliberately absent, and what the absence means

An absent field is never "we could not read it" without this list saying so.

| what | where | why |
|---|---|---|
| `size_key` on Human and Tiefling | both languages | The SRD prints **a choice**: `"M (moyenne…) ou P (petite…), à choisir lors de la sélection de l'espèce"`. Emitting one of the two would be choosing for the player; the contract has no field for a size choice. A size string matching **neither** shape is a hard refusal, so "no `size_key`" keeps one meaning. |
| `senses` on Goliath, Halfling, Human | both languages | The SRD gives them no Darkvision. Verified as zero occurrences. |
| `granted_skill_choice` on the other seven species | both languages | The SRD grants them no skill. |
| the feat's parenthetical option | `background.feat_id` | See below — a real loss, and a question. |
| `traits`, lineages | all nine species | Refused, see above. |
| `starting_equipment` | everywhere | Out of scope by architect's decision, contract §6. Untouched. |

### The one place information is lost

`srd:background:fr:acolyte` prints `"Initié à la magie (Clerc) (cf. « Dons »)"`
and `srd:background:fr:sage` prints `"Initié à la magie (Magicien)"`. Both
resolve to the **same** `feat_id`, `srd:feat:fr:initie-a-la-magie`, because the
contract defines `feat_id` and nothing else. **The Cleric/Wizard distinction —
which spell list the feat grants — is not carried by any derived field.**

The printed string still carries it, so nothing is destroyed; but a builder
reading `feat_id` alone cannot tell an Acolyte's Magic Initiate from a Sage's.
Naming a field for it would have meant inventing a name. It is question Q3.

The chapter pointer (`(cf. « Dons »)` / `(see "Feats")`) is dropped outright.
The option parenthesis is dropped **only when the full name fails to resolve**,
so a feat legitimately named with a parenthesis would keep it.

---

## The two key conventions, stated once

**Canonical, cross-language:** `ability_keys`, `saving_throw_keys`, `size_key`,
and the `senses` id. The French Wizard returns `["int","wis"]`, not
`["int","sag"]`; the French Elf returns `size_key: "medium"`. This is what the
contract specifies — its `background.ability_keys` example, `["con","int","wis"]`,
is the **French** Sage's Constitution / Intelligence / Sagesse — and what
`fh-char/1` stores.

**Language-native:** `damage_type_key` (`perforant` / `piercing`), and every
record id in `skill_ids`, `feat_id`, `tool_id`, `skill_choice.from`.

⚠️ **These two do not join.** `skill.ability_key` is language-native in the
French layer (`sag`, `for` — the abbreviations the French PDF's own stat blocks
print, a lot-6 decision), while `saving_throw_keys` here is canonical (`wis`,
`str`). A consumer that wants "is this save the same ability as this skill?" in
French needs a map. That divergence is the contract's, not this module's, and it
is question Q1.

The singular in `perforant` is not a style choice: the SRD prints
`"1d4 perforants"` for the dagger and `"1 perforant"` for the blowgun, so
slugifying what is printed would give one damage type two keys.

---

## How to break it on purpose

`tests/test_acceptance_derived_fields.py` reads `exports/` and nothing else,
and **names every value it expects** — all twelve hit dice, all twelve save
pairs, all four backgrounds' skills, all thirteen armour classes. A guard that
asserted `len(skill_ids) >= 2` would stay green while the stack returned two
wrong identifiers; this one says which number moved.

It was made to fail on purpose four times, and each time it named the thing:

| the value that was corrupted | what the suite said |
|---|---|
| French `Sagesse` keyed `sag` | `fr/clerc: saving_throw_keys is ['sag', 'cha'], expected ['wis', 'cha'] (printed: ['Sagesse', 'Charisme'])` |
| Blowgun written as a die | `fr/sarbacane: damage_dice is '1d1', expected None (printed: '1 perforant')` |
| Human given the first of its two sizes | `fr/humain: the SRD offers two sizes here; emitting one would be picking for the player: 'medium'` |
| `hit_point_die` replaced instead of kept | `fr: srd:class:fr:barbare lost its printed field 'hit_point_die' — the derivation must add beside, never replace` |

`tests/test_derive_mechanics.py` covers the other half: every refusal path,
checked for the string a reader would need — an unknown die, an ability outside
the six, an uncalibrated skill menu, a feat/tool/skill that resolves to nothing,
a size category outside the six, a damage type no SRD weapon deals, an AC
formula in an unknown shape, an uncalibrated language, and an attempt to
overwrite a field that already exists.
