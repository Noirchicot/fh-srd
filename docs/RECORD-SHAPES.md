# The shape of the two new record kinds — `skill` and `class-progression`

> **Written for the architect.** Lot `6-srd-tables` was asked to add the two
> SRD tables the catalogue was missing, and to hand back **the form of the new
> records** so that `fh-char/1` and `fh-layer/1` can be revised on the `fhpc`
> side. Nothing in `fhpc` has been touched from here. This document is the
> handover.
>
> Both schemas enumerate the twelve `fh-srd` genres explicitly, with
> `additionalProperties: false` — so an unknown genre is a loud rejection, by
> design. Two genres are added below. The change is two lines in
> `schemas/fh-layer.schema.json` and two in `schemas/fh-char.schema.json`,
> plus whatever the record bodies need.

---

## What changed in `fh-srd`

| | before | after |
|---|---|---|
| records | 2553 | **2613** |
| genres | 12 | **14** |
| exports per language | 12 files | **14 files** |

The sixty new records are `18 skills × 2 languages` and
`12 class progressions × 2 languages`. **No existing record changed** — the
twelve pre-existing export files are byte-identical to what they were; only
`MANIFEST.json` and the two new files per language moved.

---

## 1. `skill` — 18 records per language

The 18 SRD skills were in none of the twelve genres. Verified before writing
any code: nothing for athletics, stealth, persuasion or arcana in either
language, and the single hit for "perception" was the *concept* of Passive
Perception in the Rules Glossary. Every class record already said
`"Choose 2: Animal Handling, Athletics, …"` as raw source text, and no record
anywhere said what Athletics **is** or which ability it uses. A character could
not pick a skill from data.

```json
{
  "id": "srd:skill:en:acrobatics",
  "kind": "skill",
  "lang": "en",
  "layer": "srd",
  "name": "Acrobatics",
  "slug": "acrobatics",
  "data": {
    "name": "Acrobatics",
    "ability": "Dexterity",
    "ability_key": "dex",
    "example_uses": "Stay on your feet in a tricky situation, or perform an acrobatic stunt."
  },
  "source_locator": "p.9",
  "license": "CC-BY-4.0",
  "attribution": "…"
}
```

**Three fields, and one of them needs a decision from you.**

- `ability` — the ability's **printed name** in that record's language
  (`"Dexterity"` / `"Dextérité"`).
- `ability_key` — ~~the three-letter abbreviation the SRD's own stat blocks
  use, `for/dex/con/int/sag/cha` in French~~ — **REVERSED 2026-08-08 by the
  architect, on lot `8-srd-mecanique`'s Q1. It is now `str/dex/con/int/wis/cha`
  in both languages**, and `data.ability` still carries the displayable word
  ("Sagesse"). The argument recorded here rested on a false premise: this was
  never a question about joining *across* languages. `resolved.abilities` in
  `fh-char/1` is `additionalProperties: false` and requires those six keys of a
  **French** character sheet too — so a French skill keyed `sag` could not
  address the abilities of its own French document. The key was unjoinable
  *inside* one language. The reasoning and the reversal live in
  `src/parse_skills_fr.py`'s docstring; `srd:monster:fr:*` is untouched and
  still keys stat blocks `for`/`sag`, because a stat block's abbreviations are
  the PDF's own printed table rather than a key a character sheet must address.
- `example_uses` — the table's own third column, verbatim.

No SRD skill uses Constitution. Five of the six abilities appear.

---

## 2. `class-progression` — 12 records per language

```json
{
  "id": "srd:class-progression:en:wizard",
  "kind": "class-progression",
  "lang": "en",
  "layer": "srd",
  "name": "Wizard",
  "slug": "wizard",
  "data": {
    "name": "Wizard",
    "class": "srd:class:en:wizard",
    "resource_columns": [
      { "key": "cantrips",        "label": "Cantrips" },
      { "key": "prepared_spells", "label": "Prepared Spells" }
    ],
    "spell_slot_levels": 9,
    "subclass_placeholder": "Subclass feature",
    "levels": [
      {
        "level": 1,
        "proficiency_bonus": 2,
        "features": ["Spellcasting", "Ritual Adept", "Arcane Recovery"],
        "resources": { "cantrips": 3, "prepared_spells": 4 },
        "spell_slots": [2, 0, 0, 0, 0, 0, 0, 0, 0]
      }
      // … nineteen more, always exactly levels 1..20 …
    ]
  },
  "source_locator": "p.77"
}
```

### Field by field

| field | type | notes |
|---|---|---|
| `class` | string | the id of the `class` record in the same language. Always present, always resolves (asserted). |
| `resource_columns` | array | the table's non-slot value columns, **in printed left-to-right order**, each `{key, label}`. Empty is possible in principle; no SRD class has none. |
| `spell_slot_levels` | int | `9` (full casters), `5` (Paladin, Ranger), `0` (no slot band). |
| `subclass_placeholder` | string | the exact string the table prints where a subclass grants a feature — `"Subclass feature"` / `"Aptitude de sous-classe"`. Carried on the record so a consumer can recognise it without a literal of its own. |
| `levels[].level` | int | 1..20, in order, always all twenty. |
| `levels[].proficiency_bonus` | int | `2..6`. Printed `"+2"`; stored as arithmetic. |
| `levels[].features` | array of strings | the Class Features cell split on `", "`. `[]` when the source prints an em dash. |
| `levels[].resources` | object | keyed by `resource_columns[].key`. **`null` where the source prints "—".** |
| `levels[].spell_slots` | array of ints | length `spell_slot_levels`, indexed by spell level − 1, **`0` where the source prints "—"**. **Absent entirely** when `spell_slot_levels` is 0 — not an empty array. |

### The three decisions worth arguing

**(a) A separate genre rather than a `progression` field inside `class`.**
The class grammar nested its one subclass inside the class record and gave
three reasons: `record_link` does not model same-layer 1:1 composition; a
one-to-one always-present child is a field; and a consumer wants both in the
same read. All three apply here too — so nesting was the default and had to be
argued *out* of, not into.

What decided it against nesting is size against use. `class.json` is 173 KB per
language, almost all of it feature prose. The progression grid is the one thing
a builder reads on **every** level-up, for one class at a time, and it is
~2 KB. Nesting makes the cheapest, hottest lookup in the builder pull the most
expensive file in the catalogue. A separate genre also keeps the grid's
identifier stable and quotable (`srd:class-progression:fr:magicien`) without
having to say "field `progression` of record X".

The cost is one join, and it is a trivial one: `class` on the progression
record is the class's full id, and it is asserted to resolve.

**(b) Resource keys are language-native, and this is deliberate.**
`srd:class-progression:en:wizard` has `cantrips` / `prepared_spells`;
`srd:class-progression:fr:magicien` has `sorts_mineurs` / `sorts_prepares`.
The key is `canon.slugify(label)` with hyphens turned into underscores, so it
is derived from the source's own printed label and nothing else.

This follows the precedent already visible in the exports — the FR monster
records key abilities `for`/`sag`, not `str`/`wis` — and the repository's
standing position that there is **no FR↔EN record linking** (the README names
the absent `translation_of` edge as future work). A cross-language key would
be an assertion about translation that the SRD does not make and that this
importer has no licence to invent.

**Consequence for `fhpc`, stated plainly:** a builder that wants "the cantrip
count" for an arbitrary language cannot key on `cantrips`. It has two honest
routes — read `resource_columns` and match on `label`, or carry its own
per-language key map in the FH layer. Neither is free. If you would rather
have a canonical key, the right place to add it is a *third* field on the
column (`{key, label, canonical}`) populated by an explicitly FH-owned
mapping — and that is a contract decision, not an importer one.

**(c) `0` for a missing spell slot, `null` for a missing resource.**
An em dash in the slot band means "no slots of that level", which is zero, and
an array of integers indexed by spell level is the shape the rule is actually
used in. An em dash in a resource column means the feature does not exist yet
at that level (a level 1 Cleric has no Channel Divinity), which is absence, not
zero. Two different meanings, printed identically; read as what they mean.

Resource values are otherwise the source's own text unless they are entirely
digits: `digits → int`, `"—" → null`, everything else → the printed string.
That keeps `"1d6"`, `"D8"`, `"+10 ft."` and `"+4,50 m"` intact without the
importer inventing a type for them.

---

## What was verified, and how

A wrong progression table is the worst defect this repository could ship: it
produces characters that are silently, plausibly wrong. So the numbers are
checked against three witnesses that were not used to produce them
(`tests/test_class_progression_witness.py`):

1. **Poppler.** `pdftotext -layout` renders each table in its printed geometry,
   with headers aligned over their columns — which is exactly what the
   pipeline's own PyMuPDF stream destroys. **3480 cells agree, column order
   included.**
2. **The other language.** Two separately typeset PDFs, two separately
   calibrated grammars. **1960 values agree**, with one named exception: the
   Monk's Unarmored Movement is printed in feet in English and metres in
   French (`+10 ft.` / `+3 m`). Both are kept as printed.
3. **The SRD contradicting itself.** "Multiclass Spellcaster: Spell Slots per
   Spell Level" prints the full-caster grid a second time, in another chapter.
   All five full casters match it exactly and both half-casters match it at
   `ceil(level / 2)` — the SRD's own multiclassing rule arriving as arithmetic
   on data read from elsewhere. **2200 slot values.**
4. **The feature names**, against the class records' own `"Level N: <Name>"`
   headings — a different pass over different pages. **443 of them resolve**,
   which is what makes splitting on `", "` a measurement rather than a guess.

The acceptance test (`tests/test_acceptance_srd_tables.py`) reads `exports/`
and nothing else: a level 3 Wizard draws 4 level-1 and 2 level-2 slots, and all
ten skills a Rogue may choose resolve to skill records with an ability — in
both languages, plus all 78 skill choices across the eleven classes whose menu
is an explicit list.

---

## Deliberately NOT included — one table, and it is available

**"Multiclass Spellcaster: Spell Slots per Spell Level"** (EN p.26 / FR p.27)
parses cleanly under the same grammar and is used as witness 3 above. It is
not exported, for one reason: it is not a class's progression. It belongs to
the multiclassing rules and has no class, and a `"class": null` record inside a
genre called `class-progression` would be a shape the source does not ask for.

Section §L6 asked for the twelve classes; this is the thirteenth thing next to
them, so it is flagged rather than smuggled in. **If the builder is to support
multiclassing it will need this table**, and adding it is small — say where it
should live (its own genre, or a `class: null` case) and it can be exported in
one commit.

---

## Findings the architect should see (not this lot's to fix)

The feature-name cross-check found **three French names in the progression
tables that the French class chapters' own headings do not match.** Two are
defects in an existing parser and one is the source's own inconsistency. All
three are held in a named exception list in the witness test, with the reason,
rather than being papered over — but none of them is fixed here, because
changing `parse_classes_fr.py` reshapes existing class records and their
content hashes, which is a contract decision.

| where | the progression table prints | the class record holds | what it is |
|---|---|---|---|
| `srd:class:fr:occultiste`, level 9 | `Communication avec le protecteur` | `Communication avec` | **parser defect** — the heading wraps to a second line (`Niveau 9 : Communication avec` / `le protecteur`) and only the first is kept |
| `srd:class:fr:guerrier`, level 11 | `Double attaque supplémentaire` | `Double attaque` | **parser defect** — same wrap, same truncation |
| `srd:class:fr:barbare`, level 7 | `Bond agressif` | `Bond instinctif` | **source inconsistency** — the French PDF gives the same feature two different names, table vs. chapter. Nothing to fix in code; worth knowing before a builder tries to join on the name |

The two truncations mean two FR class records currently carry an incomplete
feature name. The English side is clean.

---

## Checklist for the `fhpc` revision

1. `schemas/fh-layer.schema.json` → `records`: add `"class-progression"` and
   `"skill"` to the enumerated genres.
2. `schemas/fh-char.schema.json` (the genre list around line 624): same two.
3. Decide (b) above — whether a canonical cross-language resource key is
   wanted, and if so that it is FH-owned, not importer-owned.
4. Decide whether the Multiclass Spellcaster table ships, and under what genre.
5. Only then release lot `4-couche-srd`: its prompt cites
   `exports/srd/{fr,en}/*.json` and `MANIFEST.json`, both of which this lot
   has rewritten.
