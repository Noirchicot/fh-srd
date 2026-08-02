# Proposal — how the FHPC would consume these exports

> **This is a proposal and it stops here.** Nothing in `fh-phb` has been
> touched. Two other packages are live in that repository (the dock and its
> roll engine); sequencing this belongs to the architect, not to this seat.

## What it can and cannot buy

It buys a **catalogue**: enough to populate a spell list, show a rule's text,
or check that a name exists, with its layer and its licence attached.

It does not buy a **character**. `ctx.character` carries no structured traits,
actions or weapons, and its spell list is `{name, level}` with no slots, no
preparation, no attack bonus and no save DC (established 2026-08-01). The
Traits, Actions and Spells panels are manual for that reason and they invent
nothing. This base does not change that. It lets a panel offer *Boule de Feu*
in a picker; it cannot tell that panel whether Yedrivel prepared it.

Anyone reading a spell catalogue and concluding the source-data problem is
solved will be wrong, and the panels will start inventing again.

## Shape

One-way, build-time, verified.

```
fh-srd                                fh-phb
──────                                ──────
exports/srd/fr/spell.json   ──sync──▶ docs/data/srd/srd/fr/spell.json
exports/MANIFEST.json       ──sync──▶ docs/data/srd/MANIFEST.json
```

A `sync_srd.py` in `fh-phb`, alongside `sync_from_vault.py`, that:

1. reads `MANIFEST.json` from the source repository;
2. **verifies the destination copy before overwriting it.** If a destination
   file exists and its hash matches neither the incoming manifest nor the
   previously synced one, it was hand-edited — **stop and say so**, do not
   overwrite. This is the whole reason the manifest exists;
3. copies, then re-verifies the destination against the manifest;
4. refuses to run at all if `sources.lock.json` has no pin, or if any record
   carries an unverified attribution.

Step 2 is the one that matters. `sync_from_vault.py` silently overwrites, which
is correct for the vault (the vault is the source) and wrong here (a
hand-edited export is a *symptom* — somebody tried to fix a bug in the wrong
repository, and they need to be told, not reverted).

## Why files and not a database

The dock is a static page on `github.io`. It cannot reach a database, and every
self-hosting variant of that idea died on the HTTPS/mixed-content constraint
already established for the table server. Static JSON fetched from the same
origin has none of those problems, needs no Worker route, and adds no
KV `list()` on a polled path — the failure that took production down on
2026-07-30.

Size is the thing to watch: ~320 SRD spells with full text is on the order of
1 MB of JSON. Loading that on dock open would be wasteful for a player who
never opens the Spells panel. Suggested split, to be decided when the real
numbers exist rather than now:

- `spell-index.json` — id, name, level, school, classes. Small, loaded once.
- `spell/<id>.json` or a sharded bundle — full text, fetched on demand.

The index is what a picker needs. The text is what one spell needs.

## What core would need

Nothing, if a panel fetches its own data. That is the cheapest first step and
it keeps `fh-player-sheet.js` untouched, which the panel contract requires.

If several panels end up wanting the catalogue, a single shared loader in core
(one fetch, one cache, layer-aware) is the right consolidation — but that is a
core change and therefore an architect decision, not a package one.

## Layer visibility in the interface

The base tracks four layers; a player should be able to see which one a rule
came from. Concretely: a small marker on any entry that is not `srd`, and a
filter that shows the SRD layer alone.

That is a genuine UI decision touching `UI-TERMINOLOGY.md` and the belt, and it
is out of scope here. Flagged, not designed.

## Suggested order

1. Fetch and pin the source; calibrate the spell grammar; import for real.
2. Verify: replay the import, compare dumps, read a dozen spells against the
   PDF by hand. An importer that "worked" is not an importer that is right.
3. Write `sync_srd.py` with the verify-before-overwrite rule. Do not sync yet.
4. Only then propose a panel change, through the architect.
