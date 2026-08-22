# Which French record is which English record

> **Lot `2-correspondance`.** Produces `exports/srd/correspondence.json`.
> Nothing in `fhpc` has been touched, and **no existing export changed by a
> single byte** — the two catalogues came out of the build identical to their
> committed versions. What is new is one file beside them, plus its manifest
> entry.

---

## The thing that was believed impossible

`fhpc/layers/TRADUCTION.md`, written on 2026-08-08 and never abrogated:

> *Les deux langues du SRD n'ont aucune clé de jointure.* […] *L'appariement
> par rang dans le document échoue dès le deuxième élément : les deux
> catalogues sont triés alphabétiquement, chacun dans sa langue (*Elfe* tombe
> en face de *Dwarf*).*

Every clause of that is still true. Every identifier carries its language
(`srd:species:fr:drakeide` against `srd:species:en:dragonborn`), the slugs are
transliterations of translated names, no export carries a `translation_of`
field, and the alphabetical sort really does put *Elfe* opposite *Dwarf*.

What had never been tested is whether the **data** can do what the names
cannot. It can, for most of the catalogue.

## Three things a translator never touched

| signal | why it crosses | example |
|---|---|---|
| **price** | the NUMBER is identical in both layers; only the coin is spelled differently | `25 GP` / `25 po` |
| **weight** | the French layer is the English one divided by **exactly 2** | `1 lb.` / `0,5 kg` |
| **spell components** | V / S / M are the same three letters in French | `V, S, M (…)` |

…plus everything that was already a number and never went through a
translator at all: an armour class, a hit point total, a damage die, six
ability scores, twenty rows of a progression table.

⚠️ **The `/2` is measured, not assumed.** It holds on **133 of the 134**
numeric weights in the catalogue, checked as multisets so the check does not
lean on the pairing it is meant to justify (`tests/test_correspond.py`,
`acceptance_weight_rule`). The single exception is *Entertainer's Pack*: 58½ lb
halves to 29.25 kg and the French layer wrote 29 kg. **The pairing found that
record on its own** — it is one of the two `gear` orphans — instead of pairing
it with something close.

⛔ The `/2` is **not** the physical 2.2046, and **not** Foundry's 2.5. Using
either would break every match. Whatever conversion is written toward Foundry
later, it is a different number from this one, and this file is not the place
to reconcile them.

## The rule the whole artefact rests on

**A fingerprint counts only when it is unique on BOTH sides.** One English
record, one French record, nothing else wearing it. Everything else leaves here
**named**, never resolved:

- `ambiguous` — several records share a fingerprint. Two-against-two is still a
  question: the data says these four belong together, not which goes with which.
- `unmatched-en` / `unmatched-fr` — a fingerprint with no counterpart. **Both
  directions are walked**, because the French catalogue is the longer one (258
  magic items against 253) and the records missing from an English-only sweep
  are exactly the interesting ones.
- `no-fingerprint` — a genre this pass has no fingerprint for. Its records are
  listed in full.

⛔ **There is no hardcoded list of genres.** The pass iterates over the kinds it
is given; a genre the catalogue gains shows up as an unanswered question. The
failure being refused is downstream and cost real time: `gen-srd-layer.mjs`
iterates over its own constant, so a genre absent from that constant is not
rejected — it is never read, and the build succeeds having produced nothing.

## Why it is a third file and not a fix to the two

`TRADUCTION.md`, point 3:

> *Le résultat est une COUCHE, pas une modification des couches SRD […] jamais
> fusionnée dedans, pour ne pas transformer un export CC-BY vérifié en un
> artefact partiellement inventé.*

The 527 records still pending **are** the invented part, or would be. Folding
them into a verified extraction would make what was measured and what was
supposed impossible to tell apart afterwards. So `correspondence.json` sits
beside the catalogues, points at them by id, and changes nothing in them.

📌 This also settles a question that looked like an arbitration and was not:
rewriting the French export to carry English identifiers **requires this table
first**. It is a prerequisite of that plan, not an alternative to it, so
building it is wasted under neither.

## What came out

```
genre                EN   paired   groups   pending      fingerprint
armor                13       13        0         0
background            4        4        0         0
class                12       12        0         0
class-progression    12       10        4         4
monster             330      330        0         0      six ability scores + AC + HP + CR
species               9        7        1         2
weapon               38       35        3         4
tool                 25       21        2         4
spell               339      259       47        86
gear                 82       46       16        37
item                253       82       42       184      prose-mined; the weakest here
feat                 17        0        1        17      — no fingerprint
glossary            152        0        1       152      — no fingerprint
skill                18        0        1        18      — no fingerprint
weapon-mastery        8        0        1         8      — no fingerprint
weapon-property      11        0        1        11      — no fingerprint
─────────────────────────────────────────────────────
TOTAL              1323      819      120       527      61.9 % paired, nothing guessed
```

The pairs are a **strict bijection** and every pair joins two records of the
same genre — both checked on a fresh recomputation rather than read out of the
published file.

## What is left, sorted by what it costs

| tier | groups | records | what it is |
|---|---|---|---|
| **cheap** | 69 | ~150 | two or three records against the same on the other side. `Glaive`/`Halberd` ↔ `Coutille`/`Hallebarde` is decided at a glance. |
| **orphans** | 35 | 35 | one record, no counterpart. ⚠️ **Several of these are the parser defect, not a translation problem** — `Folding Boat` and `Lantern of Revealing` are two of the five English records that swallowed a neighbour's text. The correspondence surfaced them without being asked to. |
| **large** | 11 | 136 | four or more a side. Needs a better fingerprint before it needs a human. |
| **no fingerprint** | 5 | 206 | five genres. See below. |

## The obvious next lot, not done here

**Transitive pairing.** 35 of the 38 weapons are paired, and each weapon
carries the NAME of its mastery (`Topple` / `Renversement`). Walking already-
proven pairs would close `weapon-mastery` without a single new guess. It is a
second layer of inference and it needs its own proof, so it is not in this lot:
one method, one proof.

`feat`, `skill`, `glossary` and `weapon-property` carry nothing numeric at all.
They need either a transitive route or a curated table.

## Files

```
src/correspond.py            the fingerprints and the pairing rule; pure, no I/O
src/export_json.py           +1 helper, +1 expected path, +1 write pass
exports/srd/correspondence.json   the artefact (235 KB)
tests/test_correspond.py     7 unit checks, 3 acceptance checks
```

Run: `python3 src/build.py`, then `python3 tests/test_correspond.py`.
Two consecutive builds are byte-identical, manifest included.
