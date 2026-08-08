# fh-srd — canonical SRD 5.2.1 base

A deterministic import of the official SRD 5.2.1 into a canonical SQLite base,
with static JSON exports for the Fate's Hand Player Companion, and four layers
kept strictly apart.

**This is a catalogue, not a character.** It can tell you that *Fireball* is a
3rd-level evocation with its full stat line — school, level, casting time,
range, components, duration, ritual, classes, page — and now its full
description text, including the "Using a Higher-Level Spell Slot" paragraph.
It cannot tell you whether Yedrivel prepared it, how many slots she has left,
or what her save DC is — `ctx.character` does not carry that (finding of
2026-08-01), and no amount of rules data fixes it. The base makes it possible
to *offer* a spell in a list. Knowing which one a player chose is a different
problem.

```bash
python3 src/build.py --fixture      # full pipeline, no PDF needed
python3 src/build.py                # every pinned, calibrated source
python3 src/build.py --source srd-5.2.1-en   # just one, for narrow debugging
for t in tests/test_*.py; do python3 "$t"; done
```

## Why a separate repository

The licence posture here is not the one in `fh-phb`. This repository holds a
derivative of a CC-BY document that must carry attribution on every record;
`fh-phb` holds Eric's own work. Keeping them apart makes "publish the SRD
layer" mean *publish this repository* rather than *extract a subset from a
mixed one* — and that boundary is the condition of the project, not a filing
preference.

The cost is real and named: the JSON exports land in `fh-phb` as files whose
source lives elsewhere, which is the shape of the trap that lost a deployed
bugfix on 2026-08-02. Two mechanisms answer it — a `$generated` header that
warns a human, and `exports/MANIFEST.json` that lets the consuming side
*check*. See `src/export_json.py`.

## Determinism

Replaying the import on the same source produces the same records under the
same identifiers. Three things make that true, and one test proves it.

**The source is pinned by hash, not by URL.** `sources/sources.lock.json`
records SHA-256, size and ETag; `src/sources.py` refuses to import a file that
does not match. This is not paranoia: Wizards of the Coast reissued the French
PDF on 2025-12-08, seven months after the English one, **under the same version
number 5.2.1**. "Same version" does not mean "same bytes", and a reissue can
move content across the SRD boundary — a licensing change wearing the clothes
of a refresh.

**The extractor is pinned and asserted.** WotC publishes PDF and nothing else,
in any of the four localised languages, so the weakest link is the moment a
glyph becomes a character. PyMuPDF 1.26.5 / MuPDF 1.26.10 is the primary
extractor and the pipeline refuses to run on any other build. Poppler
`pdftotext` 26.03.0 reads the same pages as an independent witness: where the
two agree the text is sound; where they disagree the affected records go to the
exclusion register as `extractor-conflict` rather than being guessed at.

**Nothing reads a clock.** No timestamps in any table. `import_run.id` is
derived from the pipeline version, the lock hash and the extractor identity —
so two replays of the same inputs are *the same run*, and the ledger says so.

**The proof** (`tests/test_determinism.py`) compares two builds four ways: the
`sqlite3 .dump` (not the `.db` file — SQLite is not byte-stable and comparing
raw bytes would fail for reasons that have nothing to do with content), the
exported JSON byte for byte, the identifier list, and a third build in a
**separate process** with a fixed `PYTHONHASHSEED`. Plus a negative control, so
a comparison that cannot fail cannot pass.

## Identifiers

`srd:spell:fr:boule-de-feu` — layer, kind, language, slug. Never an
autoincrement: an integer key would not survive an upstream reordering, and it
would not say which layer a record came from once it had left the database,
which is the whole legal question.

Colliding slugs take a `-<hash6>` suffix — **all of them, not just the later
ones**. If the first kept the bare slug, a record appearing upstream later
would silently reassign an identifier the FHPC already references. Every
collision is also reported in the exclusion register.

## The four layers

`srd` → `phb_opt` → `fates_hand` → `manual`. One record belongs to exactly one
layer; there is no merged record. A Fate's Hand rule that changes an SRD spell
does not edit the SRD row — it inserts an edge in `record_link`. So:

```sql
SELECT * FROM publishable_srd;   -- everything shippable under the CC-BY grant
```

Four guarantees are enforced by the **database**, not by the importer's good
intentions, and each is tested by making SQLite refuse the thing that would
break it (`tests/test_layers.py`):

- the `srd` layer is importer-owned — a write with the guard shut aborts;
- an `srd` row without a source, a licence and a locator cannot be inserted;
- an `id` that contradicts its `layer` column cannot exist;
- the `srd` layer can never override a layer above it; the edge is refused.

## Layout

```
schema/001_canonical.sql   the invariants, in SQL
src/canon.py               slugs, ids, hashes, canonical JSON
src/sources.py             pin verification — three refusals, three remedies
src/extract.py             PDF -> text, two extractors, versions asserted
src/parse_spells.py         FR spell grammar — calibrated, 339 spells, WITH description (v2)
src/parse_spells_en.py      EN spell grammar — calibrated, 339 spells, with description
src/parse_items_fr.py       FR magic item grammar — calibrated, 258 items
src/parse_items_en.py       EN magic item grammar — calibrated, 253 items
src/parse_feats_fr.py       FR feat grammar — calibrated, 17 feats
src/parse_feats_en.py       EN feat grammar — calibrated, 17 feats (the whole SRD subset)
src/parse_backgrounds_fr.py FR background grammar — calibrated, 4 backgrounds
src/parse_backgrounds_en.py EN background grammar — calibrated, 4 backgrounds (the whole SRD subset)
src/parse_species_fr.py     FR species grammar — calibrated, 9 species
src/parse_species_en.py     EN species grammar — calibrated, 9 species
src/parse_classes_fr.py     FR class grammar — calibrated, 12 classes, subclass nested
src/parse_classes_en.py     EN class grammar — calibrated, 12 classes, subclass nested
src/parse_class_progression_en.py  EN level tables — calibrated, 12 classes, 240 rows
src/parse_class_progression_fr.py  FR level tables — calibrated, 12 classes, 240 rows
src/parse_skills_en.py      EN Skills table — calibrated, the 18 SRD skills
src/parse_skills_fr.py      FR Compétences table — calibrated, the 18 SRD skills
src/parse_glossary_fr.py    FR Glossaire de règles grammar — calibrated, 152 entries
src/parse_glossary_en.py    EN Rules Glossary grammar — calibrated, 152 entries
src/parse_weapons_fr.py     FR Armes table — calibrated, 38 weapons
src/parse_weapons_en.py     EN Weapons table — calibrated, 38 weapons
src/parse_armor_fr.py       FR Armures table — calibrated, 13 armors (incl. Bouclier)
src/parse_armor_en.py       EN Armor table — calibrated, 13 armors (incl. Shield)
src/parse_tools_fr.py       FR Outils grammar — calibrated, 25 tools
src/parse_tools_en.py       EN Tools grammar — calibrated, 25 tools
src/parse_gear_fr.py        FR Matériel d'aventurier table — calibrated, 82 items
src/parse_gear_en.py        EN Adventuring Gear table — calibrated, 82 items
src/parse_monsters_fr.py    FR Monstres grammar — calibrated, 330 monsters
src/parse_monsters_en.py    EN Monsters (stat block) grammar — calibrated, 330 monsters
src/derive_mechanics.py    mechanical fields (numbers, keys, record ids) added
                            BESIDE the printed strings — see docs/DERIVED-FIELDS.md
src/build.py               verify -> extract -> parse -> derive -> insert -> export,
                            over a (lang, kind) parser registry, every source in one run
src/export_json.py         exports + MANIFEST.json
sources/sources.lock.json  the pin
exports/                   committed, text, diffable
build/                     gitignored — the .sqlite is a build artefact
```

## State

**2613 SRD 5.2.1 records, zero anomalies, zero exclusions, `srd` layer only.**
The catalogue is now bilingual and, with one named exception, count-for-count
identical between languages: 339 spells, 253/258 magic items (EN/FR — see
below), 17 feats, 4 backgrounds, 9 species, 12 classes, 152 Rules Glossary
entries, 38 weapons, 13 armors, 25 tools, 82 adventuring gear items, 330
monster stat blocks, 12 class level-progression tables and the 18 skills, each
parsed once by an EN grammar and once by an
independently calibrated FR grammar — every French record carries full
description/rules text, the same as English, including the "Emplacement de
niveau supérieur" upcast paragraph for spells. Replayed in a separate process
with a fixed `PYTHONHASHSEED`: identical `.dump`. The publish gate passes.

**The magic item count differs by exactly 5, and it is a genuine content
difference between the two PDF printings, not a parsing gap.** FR has 258
items against EN's 253 — every category matches exactly (potions, rings,
rods, scrolls, staves, wands, wondrous items) except weapons, where FR has
33 against EN's 28. The five extra are real, complete, licensed entries with
their own full rules text: Épée dansante (Dancing Sword), Épée mordante
(Sword of Wounding), Fer gelé (Frost Brand), Lame porte-bonheur (Luck Blade),
and a second life-draining sword alongside the one EN also has (Voleuse de
vie, distinct from Épée voleuse de vie / Nine Lives Stealer). Consistent with
the warning already on record in this README: Wizards reissued the French
PDF on 2025-12-08, seven months after the English one, under the same
version number — "same version" evidently did not mean "same magic item
list" for this one category. No FR-only equivalents were found missing from
EN in any other kind.

**Five genres now carry mechanical fields beside their printed ones.** A class
record still says `hit_point_die: "d6 par niveau de Magicien"` and now also says
`hit_die: 6`; a species still says `speed: "10,50 m"` and now also says
`speed_m: 10.5`; a background's `skill_proficiencies` are still the two printed
names and now also `skill_ids`, two identifiers that resolve to real `skill`
records. Nothing printed was removed, reworded or reordered — the public pages
under `web/` regenerate byte-identical, and the nine genres that gained no field
export byte-identical too. What each field is, how it was measured, and the four
things it deliberately refuses to do are in **`docs/DERIVED-FIELDS.md`**.

**41 suites green** — the original 22 (schema, identifiers, layer separation,
write guards, source refusal, exports, manifest, determinism, attribution-
vs-PDF, tripwire, paragraph-break normalisation, and the eleven EN grammars)
plus twelve FR ones (spell v2, and the eleven other kinds) and six added with
the class-progression and skill tables (two grammars per new kind, the
three-witness check on the progression numbers, and the acceptance test that
reads only `exports/`), plus two for the derived mechanical fields (the
derivation's refusals, and a second acceptance test that reads only `exports/`
and names every value it expects rather than counting them), each with its own
negative control proving its checks can fail, not just pass.

**The French grammar is not the English grammar with words swapped, and
every one of the eleven new FR parsers found at least one shape EN's own
calibration gave no reason to expect:**

- **Spells (v2):** the "Emplacement de niveau supérieur" upcast paragraph
  carries the tab-driven paragraph-break marker in only 6 of 110 cases
  (EN's "Using a Higher-Level Spell Slot" has it in 121 of 124) — a real
  typesetting difference in the source, read as-is rather than smoothed
  into a synthetic break.
- **Magic items:** the comma before a rarity word is sometimes just a
  space ("Armure (armure de cuir clouté) rare"); a subtype parenthetical
  can wrap onto a second line before its own closing paren; a rarity word
  can wrap onto a THIRD line after a bare, unclosed comma with no anomaly
  to catch it; "Artefact" is capitalised in its one real occurrence where
  every other rarity word is not; and EN's own "+1, +2, or +3" false-head
  trap does not reproduce in French at all (no comma sits directly after
  the category word).
- **Classes:** the core-traits table's own label wrap point is not fixed
  ("Formation aux\narmures" vs. "Formation aux\narmures" at a different
  split per class) — matched by joining candidate lines and comparing
  against the full label string, not a hard-coded line count. Ensorceleur
  and Occultiste elide "de" three different ways across three different
  anchor phrases in the SAME chapter ("Traits de base de l'Ensorceleur"
  but "Sous-classe d'Ensorceleur" — no article at all in the second case).
- **Rules Glossary:** French capitalises only the first word of a heading,
  never every content word the way English title-case does — porting EN's
  title-case name check verbatim recovered 34 of 152 entries. Raw
  Python string comparison is not French alphabetical order: an accented
  capital ("À terre") sorts after every unaccented letter in code-point
  order, which poisoned the alphabetical safety net for the whole rest of
  the chapter until the sort key went through the same accent-stripping
  normalisation every record's own slug does.
- **Weapons:** one row ("Hache à deux mains") has its name and damage
  merged onto a single physical line with no break at all; Sarbacane
  (Blowgun) deals flat "1 perforant" rather than a dice expression, the
  same fixed-damage exception EN's own regex already carries for the same
  weapon.
- **Monsters:** the head line reorders size and type relative to English
  ("Aberration de taille G" vs. EN's "Large Aberration") and abbreviates
  size (TP/P/M/G/TG/Gig, not a full word); the alignment clause can wrap
  across the line that closes the head, and a bare "Neutre" is genuinely
  ambiguous — a complete true-neutral alignment on its own, or the first
  word of a wrapped "Neutre Bon/Mauvais", distinguishable only by whether
  a blank line follows; trait/action names can wrap before their own
  closing period ("Résistance légendaire (3/jour, ou 4/jour dans son" /
  "antre)."), or end their own line at the period with nothing following
  it at all; a shapeshifter's own "Changement d'aspect" trait describes
  what it turns INTO using the same size/type/alignment shape as a real
  monster head and was, before a dedicated validation gate, briefly
  creating a phantom second "monster" out of the hag's own prose. "Loyal"
  agrees in gender ("Loyale Mauvaise" for a feminine noun like Aberration)
  the same way spell cantrips already do for their school.

**Equipment's "genuine multi-column table" question, settled rather than
deferred a third time: the tables ARE row-coherent.** Measured by reading raw
PyMuPDF block coordinates directly, not just the normalised text every parser
receives: the Weapons, Armor and Adventuring Gear tables are wide enough on
the page to be read as single unbroken blocks in the correct top-to-bottom
order, the same shape already found for the class level-progression table —
what does NOT survive is each table's own narrow, one-line sub-category
headers ("Simple Melee Weapons," "Light Armor (1 Minute to Don or Doff)"),
which fall under the column-width threshold that correctly separates the
document's ordinary two-column body text and get displaced as a group to the
end of their page. Re-deriving those categories from row content was tried
and rejected as a guess (a weapon's own properties do not reliably imply
Melee vs. Ranged — Javelin and Dart both carry "Thrown"). Tools turned out
not to be a table at all: a stat-block-shaped catalogue, parsed with full
rules text the same way a feat or magic item is. Adventuring Gear's own
richer per-item prose catalogue (interleaved with its reference table in the
source) is a distinct grammar, named and deliberately deferred rather than
rushed into the same pass.

**Monsters is the SRD's longest and most structurally varied grammar,** and
the one place in this pipeline where a field boundary is a token count
rather than a line count: the six-ability score table renders a negative
modifier on its own physical line inconsistently, row to row, within the
same stat block, so it is read as a flat token stream instead. Traits,
Actions, Bonus Actions, Reactions and Legendary Actions share the Rules
Glossary's own "Name. Description" shape and its own trap (a multi-paragraph
entry's internal blank line looks exactly like a new entry) with no
alphabetical safety net this time — solved by requiring a real entry's name
to sit in a short, colon-free prefix before its first period, which excludes
saving-throw clauses ("Success: Half damage.") that would otherwise pass.

**A class record nests its one SRD subclass rather than using a separate
`kind`.** The schema's `record_link` table models cross-layer relations, not
a 1:1, always-present, same-layer composition — and every SRD 5.2.1 class
carries exactly one subclass, so a foreign-key relationship would be
machinery for a shape that never varies here. `src/parse_classes_en.py`'s
docstring has the full reasoning, including the two things that round
deliberately did NOT decompose: the numeric level-progression table and each
caster's own "Spell List" section (redundant with the `classes` field every
spell record already carries). The first of those is now done — see below.

**The class level-progression tables are in, as their own `class-progression`
genre, and the numbers are checked against three independent witnesses.**
Twelve tables per language, 240 level rows each way: proficiency bonus, class
features, every class's own resource column (Rages, Sorcery Points, Bardic
Die, Pact Magic's two columns) and, where the class has one, the spell-slot
band as an array indexed by spell level.

The measurement the previous round left for its successor was right: the rows
ARE row-coherent, one blank-line-separated group per level. **What it did not
go on to check is the header, and that is what decides the design** — the
header is made of narrow one- and two-line cells, so `columns_of()` scatters
it. Barbarian's survives in printed order; Bard's comes back as neither
printed nor column order; Sorcerer's, Cleric's, Druid's, Wizard's and
Ranger's are split across the page with half of each landing *after* the last
row; and the French Cleric table has no header text before its rows at all.
So column names cannot be read in order from the extracted text. They are
declared per class, and then checked — every row must yield exactly the
declared cell count, every declared label must appear on that table's own
page, and `tests/test_class_progression_witness.py` re-reads all 24 tables
with poppler's `pdftotext -layout` (which renders the header *aligned over its
column*) and asserts agreement: **3480 cells, column order included**. Two
further witnesses: the two languages agree on 1960 values, with one named
exception — the Monk's Unarmored Movement is feet in English and metres in
French, decimal comma and all ("+15 ft." / "+4,50 m") — and the SRD's own
"Multiclass Spellcaster" table, printed in a different chapter for a
different purpose, matches all five full casters exactly and both half-casters
at ceil(level / 2).

Splitting the Class Features cell on ", " is a measurement too: all 443
resulting names resolve against a "Level N: <Name>" heading the class grammar
read from the chapter prose. **Three French names do not, and two of them are
a defect in `parse_classes_fr.py`, found here and reported rather than fixed**
(fixing it reshapes existing class records, which is the architect's call):
the FR Occultiste's level 9 feature is stored as "Communication avec" and the
Guerrier's level 11 as "Double attaque", both truncated because the heading
wraps to a second physical line. The third is the source's own inconsistency:
the FR Barbare table prints "Bond agressif" where its chapter heading prints
"Bond instinctif". `docs/RECORD-SHAPES.md` has the detail.

**The 18 skills are in, as a `skill` genre.** They were in none of the twelve
existing genres — nothing for athletics, stealth, persuasion or arcana in
either language, and the one hit for "perception" was the *concept* of Passive
Perception in the Rules Glossary. Every class record said "Choose 2: Animal
Handling, Athletics, …" as raw text and nothing said what Athletics is or
which ability it uses. Each record carries the printed ability name, the
abbreviation the stat blocks already use (`dex`, and `for`/`sag` in French,
not `str`/`wis`), and the table's own example-uses text.

**Not exported, and flagged rather than smuggled in:** the "Multiclass
Spellcaster: Spell Slots per Spell Level" table. It parses cleanly under the
same grammar and is used as a witness above, but it is not a class's
progression — it belongs to the multiclassing rules and has no class, and a
`"class": null` record inside a genre named `class-progression` would be a
shape the source does not ask for. A builder that supports multiclassing will
need it; where it should live is a contract decision.

**"Drow" is licensed SRD text, not an accidental leak.** It appears inside
the Elf species entry's "Elven Lineages" table — one of three lineage
flavours a player picks when choosing Elf, not a standalone playable species.
No standalone Drow record was created (that stays a `not-in-srd` species, per
`ATTRIBUTION.md`); the tripwire does not flag the word for exactly this
reason. Aasimar, Half-Elf, Half-Orc and Eladrin do not appear anywhere in the
species chapter at all.

Not done, in either language: Adventuring Gear's own richer per-item prose
catalogue — an interleaved-grammar problem, deliberately deferred rather than
rushed. Still not done: no
FR↔EN record linking (`boule-de-feu` and `fireball` are not connected by any
edge) — proposed as future work, a `record_link` `translation_of` edge, not
improvised here. `ATTRIBUTION.md` carries a finding about the vault audit's
proposed attribution block that needs Eric's decision before anything is
published.
