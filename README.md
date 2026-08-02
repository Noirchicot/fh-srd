# fh-srd — canonical SRD 5.2.1 base

A deterministic import of the official SRD 5.2.1 into a canonical SQLite base,
with static JSON exports for the Fate's Hand Player Companion, and four layers
kept strictly apart.

**This is a catalogue, not a character.** It can tell you that *Boule de Feu* is
a 3rd-level evocation with its full stat line — school, level, casting time,
range, components, duration, ritual, classes, page. **It does not yet carry the
description text**: the parser deliberately stops at the blank line that closes
the stat block (`parse_spells.py`), so v1 is a picker index, not a reader.
Importing the descriptions is the named next step for this base (architect
review, 2026-08-03). It cannot tell you whether
Yedrivel prepared it, how many slots she has left, or what her save DC is —
`ctx.character` does not carry that (finding of 2026-08-01), and no amount of
rules data fixes it. The base makes it possible to *offer* a spell in a list.
Knowing which one a player chose is a different problem.

```bash
python3 src/build.py --fixture      # full pipeline, no PDF needed
python3 src/build.py                # from the pinned PDF (once fetched)
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
src/parse_spells.py        PROVISIONAL — grammar not yet calibrated on the PDF
src/build.py               verify -> extract -> parse -> insert -> export
src/export_json.py         exports + MANIFEST.json
sources/sources.lock.json  the pin
exports/                   committed, text, diffable
build/                     gitignored — the .sqlite is a build artefact
```

## State

**The French SRD 5.2.1 spell catalogue is imported and verified.** 339 spells,
zero anomalies, zero exclusions, `srd` layer only. Replayed in a separate
process: identical `.dump`. The publish gate passes.

339 is the same count recovered independently from the English PDF, and the
same set the community Markdown conversion carries — three routes, one number.

**8 suites green.** Schema, identifiers, layer separation, write guards, source
refusal, exports, manifest, determinism, attribution-vs-PDF, tripwire, and a
negative control proving the extractor cross-check can still fail.

Not done: only spells, and only their stat lines — **description text is not
imported** (see the head of this file; found in architect review, 2026-08-03).
Classes, species, feats, magic items, monsters and the
rules glossary are unimported. The English side is unimported. `ATTRIBUTION.md`
carries a finding about the vault audit's proposed attribution block that needs
Eric's decision before anything is published.
