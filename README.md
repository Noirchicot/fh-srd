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
src/build.py               verify -> extract -> parse -> insert -> export,
                            over a (lang, kind) parser registry, every source in one run
src/export_json.py         exports + MANIFEST.json
sources/sources.lock.json  the pin
exports/                   committed, text, diffable
build/                     gitignored — the .sqlite is a build artefact
```

## State

**948 SRD 5.2.1 records, zero anomalies, zero exclusions, `srd` layer only.**
339 French spells (stat lines only — v1, see below), 339 English spells (full
description text), 253 English magic items, 17 English feats (the entire SRD
feat subset — see `ATTRIBUTION.md` for what the 2024 books have that this
doesn't). Replayed in a separate process with a fixed `PYTHONHASHSEED`:
identical `.dump`. The publish gate passes.

339 is the same spell count recovered independently from each of the French
PDF, the English PDF and the community Markdown conversion — three routes,
one number — and the French and English imports agree exactly on the
school/cantrip/ritual distribution (27 cantrips, 29 rituals, same per-school
counts) despite being parsed by two independently calibrated grammars.

**12 suites green.** Schema, identifiers, layer separation, write guards,
source refusal, exports, manifest, determinism, attribution-vs-PDF, tripwire,
paragraph-break normalisation, and the three EN grammars (spells, items,
feats) — each with its own negative control proving its checks can fail, not
just pass.

**The French spell catalogue (v1) carries stat lines only** — the parser
stops at the blank line that closes the stat block, deliberately, and that
decision has not been revisited this round; description text for French
spells is future work. The English spell/item/feat catalogues (this round)
carry full description text, including "Using a Higher-Level Spell Slot" /
"Cantrip Upgrade" paragraphs for spells.

Not done: Equipment (weapons, armor, tools, adventuring gear) — genuine
multi-column tables and nested sub-tables, a different extraction problem
from a stat-block-shaped entry, deliberately deferred rather than rushed.
Classes, species, backgrounds, monsters and the rules glossary are
unimported, in either language. `ATTRIBUTION.md` carries a finding about the
vault audit's proposed attribution block that needs Eric's decision before
anything is published.
