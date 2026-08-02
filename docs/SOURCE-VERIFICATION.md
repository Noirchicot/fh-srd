# Source verification — 2026-08-03

Measured, not quoted. Every number below came from running the comparison, and
the method is stated so it can be re-run and disagreed with.

## The pinned sources

| id | file | sha256 (12) | bytes | upstream date |
|---|---|---|---|---|
| `srd-5.2.1-fr` | `FR_SRD_CC_v5.2.1.pdf` | `480604d949a3` | 5 130 470 | 2025-12-08 |
| `srd-5.2.1-en` | `SRD_CC_v5.2.1.pdf` | `8974902d109d` | 6 031 375 | 2025-05-01 |
| `srd-5.2.1-en-markdown` | git `1b4b99dcb786` | per-file | ~2.3 MB | 2026-01-09 |

The French PDF is **380 pages**, the English **364**. Different documents in
length, same version number.

## Attribution — transcribed from the PDFs, and tested

Both statements were read off page 1 of their own PDF and written into
`sources/sources.lock.json`. `tests/test_attribution_verbatim.py` re-reads the
PDF on every run and fails if the recorded statement is not present character
for character (whitespace excluded — the PDF wraps the licence URL mid-token).

**The French PDF carries its own French statement.** French records must carry
it; attributing French content with a statement transcribed from the English
file would be a defective attribution.

### A finding for the publish plan

Both legal pages carry a restriction the vault audit did not record:

> « Veuillez n’inclure **aucune autre attribution** à Wizards, sa société mère
> ou ses sociétés affiliées que celle fournie ci-dessus. »
>
> "Please do not include any **other attribution** to Wizards or its parent or
> affiliates other than that provided above."

The audit's proposed B5 block does three things the document does not ask for:

1. it says **"SRD 5.2"**, while the required wording names **"SRD 5.2.1"** —
   the version number is inside the statement;
2. it appends **"Changes were made"**, which is not in the required wording;
3. it appends **"neither approved nor endorsed by Wizards of the Coast"** —
   and that is *another attribution to Wizards*, which is what the restriction
   asks you to omit.

Point 3 is the awkward one, because that disclaimer is standard fan-content
practice and reads as the cautious choice. Here it is the opposite.

The same page states what you **may** say, verbatim: *« compatible avec la
cinquième édition »* / *« compatible 5E »*, or "compatible with fifth edition"
/ "5E compatible". That matches the audit's "5E-compatible" recommendation.

**Not legal advice.** This is what the document says; whether to follow it to
the letter is Eric's decision, and worth a lawyer's five minutes given that the
plan is to sell.

## The Markdown conversion — verified for spells, not for the rest

`github.com/downfallx/dnd-5e-srd-markdown`, one commit, no maintenance, CC-BY.

**Spells: VERIFIED.** Method — recover every spell name from the PDF by
anchoring on the level line (`Level N <School>` / `<School> Cantrip`) and
taking the line above it; recover every `####` heading in `spells.md` whose
block contains a casting-time line; slugify both and diff the sets.

- **339 spell names in the PDF. 339 matched in the Markdown. 0 missing.**
- The single Markdown "extra" was a false positive of the heading heuristic
  ("Casting without Slots" is a rules section, not a spell).
- Bodies compared for all 339: **302 at ≥0.97 word similarity**; the remaining
  37 differ only by the HTML table markup the Markdown uses for tables
  (`<table>`, `<td>`, `colspan`). One outlier at 0.002 was a defect in the
  comparison script — *Zone of Truth* is the last spell, so "up to the next
  spell" gave it the rest of the document.

**Monsters: NOT VERIFIED, and the gap is material.** 235 `###` entries in
`monsters-A-Z.md` against ~336 AC-anchored stat blocks in the PDF. Some of
those AC lines belong to non-monster content, so the true gap is smaller than
101 — but it is not zero, and nothing here establishes what is missing. Do not
rely on this file without a name-level diff of the same kind run for spells.

**Classes, magic items, rules glossary: not verified.**

### Two cautions about this repository

**Its README is promotional, not measured.** It advertises "500+ spells, 400+
monsters". Measured: 339 spells, 235 monster entries. The spell figure is not a
shortfall — 339 is what the PDF contains — but the README is not a source of
counts.

**Its `LICENSE` paraphrases the required attribution.** It writes "material
*taken* from the System Reference Document 5.2.1" and omits
`https://www.dndbeyond.com/srd`. The required wording is "material from", with
the URL. So this source's attribution is **not** inherited from the converter:
the lock gives it Wizards' own English statement, and records the converter
credit separately. Using this source means crediting **both**.

## A defect this found in our own extraction

`page.get_text("text", sort=True)` is **wrong for this document**, and wrong in
a way that survives a word count.

The SRD is set in two columns (left x≈63, right x≈313.5, page width 594).
`sort=True` orders every block by y then x across the *full page width*, so it
reads one line of the left column, then one of the right, and back —
interleaving two unrelated spells into one stream. It produced entries such as
`Acid Arrow designate creatures that won't set off the alarm`.

A per-page word-count cross-check between PyMuPDF and poppler would have
**passed** this: the same words are present, in the wrong order.

Fixed in `src/extract.py:columns_of()` — blocks are grouped into columns by
their horizontal centre and ordered within each, with wide blocks treated as
spanning. After the fix the spell recovery went from garbage to 339/339.

**The lesson, for the record:** the cross-check compares two extractors, and
both were making the same reading-order mistake, so agreement between them
proved nothing here. What caught it was diffing against an *independent
conversion* of the same document. Two tools sharing a wrong assumption agree
perfectly.
