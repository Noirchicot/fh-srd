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

---

# Addendum — 2026-08-08, lot 11: `species.traits` and `species.lineages`

The shape the architect ratified, delivered from the exports in both languages:

```json
"traits":   [{ "id": "keen-senses", "name": "Keen Senses",
               "text": "You have proficiency in the Insight, Perception, or Survival skill." }],
"lineages": [{ "id": "wood-elf", "name": "Wood Elf",
               "levels": { "1": "Your Speed increases to 35 feet. You also know the Druidcraft cantrip.",
                           "3": "Longstrider",
                           "5": "Pass without Trace" } }]
```

**33 traits per language across nine species; 12 lineages** (Elf ×3, Tiefling
×3, per language). `traits` is present on all nine species in both languages;
`lineages` only where the SRD prints a table.

## Field by field

| field | what it is |
|---|---|
| `traits[].id` | `canon.slugify` of the printed name. **Language-native** — `darkvision` / `vision-dans-le-noir`. See QUESTIONS-ARCHITECTE Q13: this is the record-slug convention and invents no word, but it is NOT the cross-language convention `senses[].id` uses. |
| `traits[].name` | the printed name, minus its trailing full stop and nothing else |
| `traits[].text` | everything from the end of the name to the next trait, with the lineage table's own prose removed (it is carried in `lineages`) |
| `lineages[].levels` | keyed by the **level number the column header prints**, as a string. The number is read from the header (`"Level 3"` → `"3"`), never assumed from position: a header with no number is a defect, not a silently positional key. |

## The three decisions worth arguing

**1. A trait is found by its FONT, not by its sentence shape.** This is the one
that decides everything else. In English each trait opens its own paragraph, so
a paragraph break would do. In French it does not: the whole Elf entry arrives
as ONE paragraph — `"…traits spéciaux suivants. Ascendance féerique. Vous avez
l'Avantage… un terme. Lignage elfique. Vous appartenez…"` — with no break
anywhere between five traits. Splitting that on "a short phrase before a full
stop" is the Rules Glossary's trap with none of its defences: no line start to
anchor on, no alphabetical safety net.

What the source states unambiguously, in both languages, is typographic: a trait
name is set in Cambria-BoldItalic and nothing else in the chapter is. Measured:
**33 bold-italic runs in the EN species chapter and 33 in FR, every one a trait
name.** Spell names ARE italicised there (`le sort mineur *druidisme*`) and are
correctly not matched — italic without bold.

**2. The phrase stream is consumed ONCE, in document order.** Matching each
species against the phrases on its own pages looks equivalent and is not.
`"Vision dans le noir."` is printed for six of the nine French species; searching
the Elf's description for its page's phrases in page order found the *Dwarf's*
occurrence at the END of the Elf's text, moved the cursor there, and lost the
four traits before it. Measured: **25 French traits that way, 33 this way.**

**3. `species_structure.py` is SHARED between the EN and FR parsers, and it is
the only shared grammar in this repository.** That looks like a violation of the
rule that earned eleven independently calibrated FR parsers, and it is the
opposite. It is not a grammar: it reads a font flag and four column x-positions.
Neither has a French form and an English form. Duplicating it would be two
copies of one measurement — which is the failure the separate grammars exist to
prevent, not an instance of it.

## What it refuses

- A table that does not resolve into cells comes back with a `"defect"` key and
  the species gets **no** `lineages` plus an anomaly. Swept over both PDFs,
  `tables_of` marks 31 of 34 EN and 27 of 32 FR full-width tables as defective —
  that is intended, not a failure rate: the Weapons and Armor tables right-ALIGN
  their numeric columns, so a left-edge anchor cannot address them, and they
  have working parsers already. The four it is calibrated for come back clean.
- If the emphasis stream reaches a species at a phrase its description does not
  contain, the species gets **no** `traits` and an anomaly. It never falls back
  to a sentence heuristic.
- The Dragonborn's, Gnome's and Goliath's own sub-choice lists are **not** read:
  they are printed inside a single column, and `tables_of` reads full-width
  tables only.

---

# Addendum — 2026-08-20, lot 19: `weapon-property` and `weapon-mastery`

Two new genres, **11 and 8 records per language**, from the Equipment
chapter's two definition sections. They close the gap the FHPC named: all 38
weapons already carried the NAME of their mastery (`data.mastery: "Topple"`,
`"Renversement"`) and nothing anywhere carried its definition.

```json
{ "id": "srd:weapon-mastery:en:topple", "kind": "weapon-mastery",
  "name": "Topple", "slug": "topple", "source_locator": "p.90",
  "data": { "name": "Topple",
            "description": "If you hit a creature with this weapon, you can force the creature to make a Constitution saving throw (DC 8 plus the ability modifier used to make the attack roll and your Proficiency Bonus). On a failed save, the creature has the Prone condition." } }
```

`name` + `description`, verbatim, and the record's own `license` /
`attribution` / `srd_version` like every other SRD record. No derived field:
these two genres are text, and the join a consumer needs is by name.

## Where they are, as `extract.py` renders the pages

| | English | French |
|---|---|---|
| weapon properties (11) | `Properties` · p. 89–90 | `Propriétés` · p. 95–**96** |
| mastery properties (8) | `Mastery Properties` · p. 90 | **`Propriétés botte`** · p. **96** |

## The four decisions worth arguing

**1. Two genres, not one, and not the glossary.** A weapon property applies to
anyone holding the weapon; a mastery is LOCKED — "usable only by a character
who has a feature… that unlocks the property", says the section's own first
line. Different unlock, different consumer. And the glossary carries exactly
**one** `reach` — the combat rule, "a creature has a reach of 5 feet" — and
NOT the weapon property `Reach`. Pouring the eleven properties into the
glossary would have **created** a duplicate that does not exist in the source.
`tests/test_acceptance_weapon_definitions.py` asserts the two texts stay
different and stay in different genres.

**2. The two sections are read as ONE region, because a sidebar crosses
them.** `Improvised Weapons` / `Armes improvisées` is a boxed sidebar, and
`extract.py` hands it back *inside* the mastery block — between the "Mastery
Properties" intro and `Cleave`, and between the "Propriétés botte" intro and
`Coup double`. Cut the region at the mastery heading and the properties come
back **10 of 11**; take the mastery block whole and the masteries come back
**9, with a sidebar among them**. Both silently. So the region is read whole
and every head is assigned to a genre by a CLOSED SET OF NAMES, never by the
heading it sits under.

**3. A head is a short unpunctuated line at the start of a group — blank line
before it OR first line of a page.** The page half is not decoration:
`Loading` opens EN p. 90 and `Lourde` opens FR p. 96, with the previous page's
last body line immediately before them in the stream. The blank-line rule
alone loses exactly one property per language. The mirror case is the two
section headings, which have NO blank line before them (`Versatile` runs
straight into `Mastery Properties`, `Portée` into `Propriétés botte`); they
are matched exactly, by line, and excluded by name.

**4. 🔴 French says `botte`, not `maîtrise` — and says `maîtrise` next door
for something else.** The section is `Propriétés botte`, the table's sixth
column is `Botte d'arme`, the class feature is `Bottes d'arme`. `Maîtrise des
armes` exists on FR p. 95 and is the *proficiency* rule ("add your proficiency
bonus to the attack roll"). Two notions, two neighbouring sections, one French
word; an anchor on "maîtrise" returns the wrong section and says nothing.
The eight French names are unguessable from English and are read off the page:
Coup double (= Nick) · Écorchure (= Graze) · Enchaînement (= Cleave) ·
Ouverture (= Vex) · Poussée (= Push) · Ralentissement (= Slow) ·
Renversement (= Topple) · Sape (= Sap). Each language is its own closed set;
nothing here pairs them — the mapping above is for a human reader only.

## What it refuses

- **A closed set that comes back short.** `weapon_sections.SectionCountError`
  names the missing terms and stops the build (`src/build.py` exit code **6**).
  A partial section is an answer, and a wrong one.
- **A head in neither closed set** is excluded and NAMED, landing in
  `exclusions.json` with the term quoted.
- **The section and the table disagreeing.** The eight mastery heads are
  cross-checked against the eight words the Weapons table's own column uses
  (`parse_weapons_{en,fr}.MASTERY_PROPERTIES`) — two independent readings on
  two different pages. If they diverge, the build stops instead of averaging.

## Two of the eleven are never printed as a column value

Named, so a third one showing up is a defect and not a shrug:
`Improvised Weapons` / `Armes improvisées` is a sidebar about weapons you do
not own, and `Range` / `Portée` only ever appears *inside* another property's
parentheses — "Ammunition (Range 80/320; Arrow)", "Munitions (portée 30/120 ;
carreaux)". Its definition is what tells a reader how to read those numbers.

---

## And a derived field: `class.weapon_mastery_count`

**Five classes, both languages** — barbarian 2, fighter 3, paladin 2, ranger
2, rogue 2 (barbare, guerrier, paladin, rôdeur, roublard).

🔴 **THE COUNT IS PRINTED IN TWO DIFFERENT GRAMMARS, and that is the whole
trap.** Barbarian and Fighter state it in their **progression table**, in a
column the table parser already read (`resources.weapon_mastery` /
`resources.bottes_d_arme`). Paladin, Ranger and Rogue have **no such column**:
their count exists only in the **prose of the level-1 feature** — "the mastery
properties of *two* kinds of weapons of your choice with which you have
proficiency". Before this lot, the exports carried the count for **2 of the
5**, and a builder reading them would have offered weapon masteries to the
Barbarian and the Fighter and to nobody else, silently.

So the count is derived from the **prose**, the grammar all five share, and
the table is used as an **independent witness**:
`derive_mechanics.check_weapon_mastery_counts` requires the two readings to
agree wherever both exist and refuses rather than choose (exit code **7**). It
also recounts and NAMES: exactly five classes must carry the feature, exactly
those five must carry a count, and a feature whose prose states no number
stops the build instead of meaning zero.

⛔ **The VIVIER is not here, deliberately.** *Which* weapons a class may pick
from is a different question, and for three of the five classes the SRD's
answer — "weapons with which you have proficiency" — is a **relation** over
class × background × species, not a list. Flattening it into the SRD layer
would be interpretation in a layer that declares itself verbatim. It was
arbitrated to the FH side on 2026-08-20 and belongs in a house layer, on the
pattern of `granted_skill_budget`.
