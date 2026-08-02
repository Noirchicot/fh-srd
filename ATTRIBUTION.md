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

## The required attribution statement — NOT YET VERIFIED

`sources/sources.lock.json` currently carries the placeholder
`"attribution_verified": false` for both sources, and the test suite asserts
that it is still false. That assertion is deliberate: it fails the day someone
flips the flag without doing the work.

**What has to happen before anything ships:** read the legal page of the actual
PDF — the French one for the French records, the English one for the English —
and transcribe the statement *verbatim* into the lock file. Not paraphrased,
not reconstructed from a search result, not copied from this file.

Two reasons this is not pedantry:

1. **The wording differs between SRD versions.** The 5.1 statement names the
   OGL-era document; the 5.2.1 statement names 5.2.1 and points at
   `https://www.dndbeyond.com/srd`. The existing vault audit quotes a **5.2**
   form, which predates the document actually being imported here.
2. **The French PDF may carry a French statement.** If it does, the French
   records must carry that one. Attributing French content with an English
   statement transcribed from a different file is exactly the kind of detail
   that makes an attribution defective.

Once transcribed, every record inherits it automatically: the schema refuses an
`srd` row whose `attribution` is empty, and the exporter writes it onto each
record rather than once per file.

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
