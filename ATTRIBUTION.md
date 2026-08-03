# Attribution and licensing

> **This is not legal advice.** It records what the pipeline enforces and what
> remains unverified, so that a decision about publishing can be made on facts
> rather than on an impression. Confirm the specifics with a lawyer before
> selling anything.

## What this repository contains

Two kinds of thing, deliberately kept apart:

| | Licence | Where |
|---|---|---|
| **The pipeline** — importer, schema, tests | MIT (see `LICENSE-CODE`) | `src/`, `schema/`, `tests/` |
| **The imported SRD content** | CC-BY-4.0, Wizards of the Coast LLC | `exports/srd/`, and only there |

The upstream PDFs are **not committed**. They are pinned by SHA-256 in
`sources/sources.lock.json` and fetched on demand.

## The required attribution statement — TRANSCRIBED AND TESTED

Both statements were read off page 1 of their own PDF on 2026-08-03 and written
into `sources/sources.lock.json`. `tests/test_attribution_verbatim.py` re-opens
the pinned PDF on every run and fails if the recorded statement is not present
character for character. The schema then refuses any `srd` row whose
`attribution` is empty, and the exporter writes it onto **each record** rather
than once per file.

**French (for French records) — the French PDF carries its own statement:**

> Cette œuvre inclut du matériel issu du System Reference Document 5.2.1
> (« SRD 5.2.1 ») de Wizards of the Coast LLC, disponible à l’adresse
> https://www.dndbeyond.com/srd. Le SRD 5.2.1 est régi par la Licence Creative
> Commons Attribution 4.0 International, disponible à l’adresse
> https://creativecommons.org/licenses/by/4.0/legalcode.

**English (for English records):**

> This work includes material from the System Reference Document 5.2.1
> (“SRD 5.2.1”) by Wizards of the Coast LLC, available at
> https://www.dndbeyond.com/srd. The SRD 5.2.1 is licensed under the Creative
> Commons Attribution 4.0 International License, available at
> https://creativecommons.org/licenses/by/4.0/legalcode.

### The restriction the vault audit does not record

Both legal pages continue:

> Veuillez n’inclure **aucune autre attribution** à Wizards, sa société mère ou
> ses sociétés affiliées que celle fournie ci-dessus.

The audit's proposed B5 block says "SRD 5.2" where the required wording says
**5.2.1**; adds "Changes were made", which is not in it; and appends "neither
approved nor endorsed by Wizards of the Coast" — which is *another attribution
to Wizards*, exactly what this sentence asks you to omit. That disclaimer is
standard fan-content practice, which is what makes it easy to add without
noticing.

What the same page permits, verbatim: « compatible avec la cinquième édition »
/ « compatible 5E », or "compatible with fifth edition" / "5E compatible".

**Not legal advice** — this is what the document says. Whether to follow it to
the letter is Eric's call, and worth a lawyer's five minutes before selling.
Full detail: `docs/SOURCE-VERIFICATION.md`.

## Protection against wild importing

Eric asked for it; `src/tripwire.py` and `src/check_publishable.py` are it.

The schema's guards are *structural* — they check what a record claims about
itself. A row inserted with `layer='srd'` and a valid source id satisfies every
constraint while containing a page of Forgotten Realms lore. The tripwire is
*lexical*: it reads what records actually say and fires on trademarks, product
identity, known non-SRD mechanics, and any mention of a forbidden source.

`python3 src/check_publishable.py` refuses on: a record outside the `srd` layer;
a source whose attribution was never transcribed; a record missing provenance;
an **empty exclusion register** (a real import always excludes something, so an
empty one means nothing was reported, not that nothing needed reporting); or
any tripwire hit.

This repository imports SRD and nothing else. Content from books Eric owns goes
to a separate FHPC mirror by his decision — so there is nothing here to filter,
and nothing that can leak by being forgotten.

## What CC-BY does *not* grant

Trademarks. "Dungeons & Dragons", "D&D", the logo, and *Player's Handbook* as a
title are outside the grant regardless of the SRD. Nothing in this repository
may reintroduce them into a published surface. See the vault audit, blocker B1.

## What is deliberately excluded

The exclusion register (`exports/exclusions.json`, table `exclusion`) is the
audit artefact. The rule the pipeline follows, from the project's standing
instruction: **when membership in the SRD is uncertain, exclude and report —
never include to see what happens.**

Reasons the register uses:

| Reason | Meaning |
|---|---|
| `not-in-srd` | In the 2024 books, absent from the SRD subset (most feats, 44 of 48 subclasses, ~80 spells, Artificer) |
| `trademark` | A WotC mark, which CC-BY never grants |
| `product-identity` | Named IP: Forgotten Realms, Dragonlance, Underdark, Spelljammer |
| `unparsed` | Extraction could not produce a trustworthy record |
| `extractor-conflict` | PyMuPDF and poppler read the page differently |
| `slug-collision` | Two entries claim the same identifier; both were disambiguated |
| `ambiguous` | SRD membership not certain — excluded by the standing rule |

The vault audit already names the content that will land in `not-in-srd`,
`trademark` and `product-identity` when the Fate's Hand layers are imported:
Aasimar, Half-Elf, Half-Orc, Eladrin, Drow; Lunar Sorcery (Dragonlance); Circle
Magic (*Heroes of Faerûn*); the *Ceremony* spell; Great Weapon Master,
Sharpshooter, Spell Sniper, Observant, Keen Mind, Dual Wielder.

**Drow is a subtler case than the rest of that list, confirmed importing
species (2026-08-03).** The word is not absent from the SRD PDF the way
Aasimar/Eladrin/Half-Elf/Half-Orc are — it appears, licensed and verbatim,
inside the *Elf* species entry's "Elven Lineages" table as one of three
lineage flavours a player picks when they choose Elf (High Elf, Drow, Wood
Elf), not as a standalone species with its own Creature Type/Size/Speed. That
is why the tripwire's pattern list (below) does not include "Drow": flagging
it would fire on legitimate SRD prose every single build. The `not-in-srd`
exclusion that still applies is a *standalone Drow species record* — the
Forgotten Realms-flavoured, fully-statted playable species other sourcebooks
present — which `src/parse_species_en.py` does not manufacture, because the
SRD itself does not present Drow as one.
