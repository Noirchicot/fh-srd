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
src/parse_spells.py        FR spell grammar — calibrated, 339 spells, stat lines only
src/parse_spells_en.py     EN spell grammar — calibrated, 339 spells, with description
src/parse_items_en.py      EN magic item grammar — calibrated, 253 items
src/parse_feats_en.py      EN feat grammar — calibrated, 17 feats (the whole SRD subset)
src/parse_backgrounds_en.py EN background grammar — calibrated, 4 backgrounds (the whole SRD subset)
src/parse_species_en.py    EN species grammar — calibrated, 9 species
src/parse_classes_en.py    EN class grammar — calibrated, 12 classes, subclass nested
src/parse_glossary_en.py   EN Rules Glossary grammar — calibrated, 152 entries
src/parse_weapons_en.py    EN Weapons table — calibrated, 38 weapons
src/parse_armor_en.py      EN Armor table — calibrated, 13 armors (incl. Shield)
src/parse_tools_en.py      EN Tools grammar — calibrated, 25 tools
src/parse_gear_en.py       EN Adventuring Gear table — calibrated, 82 items
src/parse_monsters_en.py   EN Monsters (stat block) grammar — calibrated, 330 monsters
src/build.py               verify -> extract -> parse -> insert -> export,
                            over a (lang, kind) parser registry, every source in one run
src/export_json.py         exports + MANIFEST.json
sources/sources.lock.json  the pin
exports/                   committed, text, diffable
build/                     gitignored — the .sqlite is a build artefact
```

## State

**1613 SRD 5.2.1 records, zero anomalies, zero exclusions, `srd` layer only.**
339 French spells (stat lines only — v1, see below), 339 English spells (full
description text), 253 English magic items, 17 English feats, 4 English
backgrounds (the entire SRD subset — Acolyte, Criminal, Sage, Soldier), 9
English species (Dragonborn, Dwarf, Elf, Gnome, Goliath, Halfling, Human, Orc,
Tiefling), 12 English classes with their one SRD subclass each nested inside,
152 English Rules Glossary entries, 38 English weapons, 13 English armors
(including the Shield), 25 English tools, 82 English adventuring gear items,
and 330 English monster stat blocks — see `ATTRIBUTION.md` for what the 2024
books have that this doesn't. Replayed in a separate process with a fixed
`PYTHONHASHSEED`: identical `.dump`. The publish gate passes.

339 is the same spell count recovered independently from each of the French
PDF, the English PDF and the community Markdown conversion — three routes,
one number — and the French and English imports agree exactly on the
school/cantrip/ritual distribution (27 cantrips, 29 rituals, same per-school
counts) despite being parsed by two independently calibrated grammars. 330 is
the same monster count recovered independently from the pinned PDF's own
"Index of Stat Blocks" (front matter, p.3-4) — the community Markdown
conversion in `sources.lock.json` claims only 235.

**21 suites green.** Schema, identifiers, layer separation, write guards,
source refusal, exports, manifest, determinism, attribution-vs-PDF, tripwire,
paragraph-break normalisation, and the eleven EN grammars (spells, items,
feats, backgrounds, species, classes, Rules Glossary, weapons, armor, tools,
adventuring gear, monsters) — each with its own negative control proving its
checks can fail, not just pass.

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
docstring has the full reasoning, including the two things this round
deliberately did NOT decompose: the numeric level-progression table (spell
slots, class resource dice — a genuine multi-column table, still deferred;
see the Equipment note above for what "genuine multi-column table" turned
out to mean in practice) and each caster's own "Spell List" section
(redundant with the `classes` field every spell record already carries).

**"Drow" is licensed SRD text, not an accidental leak.** It appears inside
the Elf species entry's "Elven Lineages" table — one of three lineage
flavours a player picks when choosing Elf, not a standalone playable species.
No standalone Drow record was created (that stays a `not-in-srd` species, per
`ATTRIBUTION.md`); the tripwire does not flag the word for exactly this
reason. Aasimar, Half-Elf, Half-Orc and Eladrin do not appear anywhere in the
species chapter at all.

**The French spell catalogue (v1) carries stat lines only** — the parser
stops at the blank line that closes the stat block, deliberately, and that
decision has not been revisited this round; description text for French
spells is future work. Every English catalogue (spells, items, feats,
backgrounds, species, classes, the Rules Glossary, weapons, armor, tools,
adventuring gear, monsters) carries full description/rules text, including
"Using a Higher-Level Spell Slot" / "Cantrip Upgrade" paragraphs for spells.

Not done: the class level-progression tables (spell slots, class resource
dice) and Adventuring Gear's own richer per-item prose catalogue — both
genuine multi-column-or-interleaved-grammar problems, deliberately deferred
rather than rushed. Everything in this lot is English only; the French
catalogue still carries spells alone (stat lines, v1). `ATTRIBUTION.md`
carries a finding about the vault audit's proposed attribution block that
needs Eric's decision before anything is published.
