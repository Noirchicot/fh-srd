# Which French record is which English record

> **Lots `2-correspondance` and `3-transitif`.** Produce `exports/srd/correspondence.json`.
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
genre                  EN   paired   pending      how
monster               330      330         0      six ability scores + AC + HP + CR
spell                 339      265        74      level + ritual + concentration + cantrip + component
item                  253      160        98      category + attunement + which dice appear + small bo
gear                   82       51        31      price + weight
weapon                 38       36         2      damage die + category + range + price + weight + pro
tool                   25       21         4      ability + price + weight
armor                  13       13         0      AC + Dex cap + stealth + price + weight
class                  12       12         0      saving throw keys + hit die + mastery count + spellc
class-progression      12       12         0      the twenty rows: level + proficiency bonus + feature
weapon-mastery          8        8         0      — deduced through weapon.mastery —
species                 9        7         2      size + speed + trait count + sense count
background              4        4         0      ability keys + skill count + feat option
feat                   17        0        17      — no fingerprint —
glossary              152        0       152      — no fingerprint —
skill                  18        0        18      — no fingerprint —
weapon-property        11        0        11      — no fingerprint —
────────────────────────────────────────────────────────────────────────────
TOTAL                 1323      919       409      69.5 % paired, nothing guessed
```

Provenance of the 1040 pairs:

| by | count |
|---|---|
| `structured-fingerprint/2` | 822 |
| `human` | 89 |
| `second-axis/spell` | 50 |
| `mention/glossary` | 40 |
| `occurrence/skill` | 15 |
| `occurrence/weapon-property` | 9 |
| `transitive/weapon.mastery` | 8 |
| `occurrence/feat` | 3 |
| `second-axis/species` | 2 |
| `second-axis/tool` | 2 |

…plus **5 computed pairs a person reached independently**, carried as
`confirmed_by: "human"` on the pair itself.

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

---

# Lot 3 — deduction, provenance, and a third state

## Three passes, in decreasing order of strength

1. **the data** — a fingerprint unique on both sides;
2. **deduction** — a pair reached by following an already-proven pair;
3. **a person** — what somebody looked at and signed.

Order is not a preference. A deduction may not overturn a measurement, because
the measurement is the stronger claim. A signature may not silently overturn
either — a person contradicting the data is something to **look at**, not to
apply, so it comes back refused and named. **Every pair carries the pass that
produced it** in its `by` field; a file that mixed the three without saying
which is which would lose the only thing that made the artefact honest.

## The route that worked

`weapon.mastery` → **8 of 8, zero conflicts.** 35 weapons are paired and each
prints the name of its mastery (`Topple` / `Renversement`), so the eight mastery
records fall out with no new guess. Four guards stand between a route and a
pair: consistency (one disagreement anywhere refuses the whole name — **no
majority vote**, a majority here is a guess wearing a number), existence on both
sides, no contradiction with a measured pair, and no double claim.

## The route that did not, and why that is the result

`weapon.properties` looks like the same shape and is not. Splitting the prose
and pairing by position is wrong: **the French SRD lists properties in its own
alphabetical order.** Positional pairing made `Ammunition` map to `Chargement`,
`Deux mains` *and* `Munitions` depending on the weapon — **8 contradictions out
of 9 names**. The consistency guard caught every one and shipped nothing.

`tests/test_correspond.py` recomputes that contradiction from the real exports,
so the reason stays a measurement instead of decaying into folklore.

## A fingerprint that counted the wrong thing

`_fp_item` used the **multiset** of dice expressions. English prose mentions
`1d100` one more time than French prose does — same table, same roll, one extra
mention — and that was enough to make five items look like orphans when they are
word-for-word translations of each other: *Deck of Illusions* / *Tarot
fantasmagorique*, *Ring of Warmth* / *Anneau de chaleur constante*, *Robe of
Useful Items* / *Robe du camelot*, *Hat of Many Spells* / *Chapeau mille-sorts*,
*Mysterious Deck* / *Tarot mystérieux*.

**How many times a die is mentioned is a fact about the prose; which dice appear
is a fact about the item.** Set, not multiset. A stray `-18` was also dropped —
the French *Anneau de chaleur constante* gives a temperature in °C where the
English wording does not, and a bare signed number swallowed it.

Measured: **82 pairs → 85**, English orphans **7 → 2**, two pairs lost to
ambiguity, and **no pair moved**. Loosening a fingerprint cannot create a wrong
pair — only unique-on-both-sides emits — so the trade is always pairs against
ambiguity, never against correctness.

🔴 **And what is left unpaired there is not a translation problem at all.**

The extraction defect leaves a **ten-record signature**, and the correspondence
reads it without being asked to. Five English magic items swallowed the text of
the item printed after them, which does two separate things:

| what happened | records | consequence |
|---|---|---|
| **eaten** — no English record exists | *Dancing Sword, Frost Brand, Luck Blade, Sword of Life Stealing, Sword of Wounding* | their five French twins — *Épée dansante, Fer gelé, Lame porte-bonheur, Épée voleuse de vie, Épée mordante* — **can never pair** |
| **polluted** — carries somebody else's prose | *Folding Boat, Lantern of Revealing, Sword of Sharpness* | their French twins *Bateau pliable, Lanterne de révélation, Épée acérée* are **stranded with them** |
| **polluted but paired anyway** | *Dagger of Venom, Sun Blade* | the foreign text did not move the fingerprint far enough |

⚠️ **Ten, not four** — and the correction matters. `unmatched` and `unpaired`
are not the same thing: *Sword of Sharpness*, *Bateau pliable*, *Lanterne de
révélation* and *Épée acérée* are all unpaired but sit in **ambiguous** groups,
so a check that looked only at the orphan groups walked straight past them. A
pattern narrower than the thing it claims to count, one more time.

⛔ **None of these ten should be signed by hand.** A human signature closes a
question, and closing this one would hide the defect. They are symptoms, not
decisions.

⭐ **They are the acceptance test for the extraction repair.** When the five
swallowed records are separated, these ten should pair **by themselves** — no
new fingerprint, no signature. If they do, the repair worked. If they do not, it
did not. `tests/test_correspond.py::acceptance_item_orphans_are_the_parser_bug`
asserts the whole signature, so the day it changes is the day the test tells
somebody.

## The third state

`sources/correspondence-signed.json` is the only hand-edited input to the
pipeline besides `sources.lock.json`. It carries two lists:

```
pairs[]          {en, fr, note?}   two records a person paired that the data could not
no_equivalent[]  {id, note?}       a record a person examined and found to have NO twin
```

⭐ **`no_equivalent` is a third state, not a tidier way of saying `pending`.** A
record nobody has looked at and a record somebody established has no counterpart
are different facts, and collapsing them means searching forever for something
already known not to exist. It is also **the only state that closes a question
rather than opening one**, which is why it is the hardest to enter: every
identifier is checked against the catalogue, a signature that contradicts a
computed pair is refused, and a note explaining how it was established is worth
more here than anywhere else in this repository.

A typo in that file does not become a pair — and does not vanish either. It
comes back in `refusals`, named. A file that exists but will not parse **stops
the build**: an unparseable file is a mistake in it, not an absence of decisions.

## Still not done

`feat` (17), `glossary` (152), `skill` (18) and `weapon-property` (11) carry
nothing numeric and have no route. `item` still hands over 175 records, and
`spell` 86 — both need a better fingerprint before they need a person.

---

# The first signature pass — 2026-08-22

95 signatures arrived. **89 became pairs, 5 were confirmations of pairs the data
had already made, and 1 was refused.** Every identifier was re-checked against
the catalogue here rather than trusted: 0 unknown, 0 genre mismatches, 0
contradictions, 0 duplicates.

## What the refusal caught, and why the guard exists

A signature paired `sword-of-sharpness` with **`Épée mordante`**. That is *Sword
of Wounding* — the item that record **swallowed**. Its real twin is **`Épée
acérée`**, and both open with the same sentence about maximising damage dice
against an object.

🔴 **The reader matched on the glued-on tail.** That is not carelessness; it is
what a corrupted record does to anyone who reads it. Two items live in one
record and nothing on the page says so.

So `POLLUTED_BY_EXTRACTION` names the five, and a signature touching one is
refused **unless it carries a `note` saying it knows what it is touching**. Not
a veto — a second look, which is the right amount of friction when the thing at
stake closes a question permanently. `folding-boat` and `lantern-of-revealing`
were signed with exactly such a note and went through.

⛔ **Delete that list when the extraction is repaired**, not before. The day the
five swallowed items come back,
`acceptance_item_orphans_are_the_parser_bug` fails, and that is the day the list
is stale.

## Agreement is not a conflict

Five signatures landed on pairs the fingerprint had already made — the five the
set-of-dice repair rescued that same morning (*Deck of Illusions*, *Ring of
Warmth*, *Robe of Useful Items*, *Hat of Many Spells*, *Mysterious Deck*).
Refusing those as duplicates would have thrown away the best evidence in the
file, so they come back as `confirmed_by: "human"` on the computed pair.

⭐ Worth stating plainly: the person signed them from the **lot 2** list, which
the multiset defect had corrupted — they were still showing as orphans. Machine
and human corrected the same five records independently, on the same day, and
agreed on all five.

## The file is cumulative

`sources/correspondence-signed.json` is added to, never replaced. 408 records
are still open; there will be more passes, and a pass must not erase the one
before it.

---

# Lot 83 — three routes for records that carry no number

198 records carry nothing measurable at all — `glossary` 152, `skill` 18, `feat`
17, `weapon-property` 11 — and 211 more have a fingerprint that matches too many
candidates. **Two problems, and a route that treated them alike would fail on
both.**

⛔ **Not one of these routes compares two names.** Each uses a name only to find
that name's own occurrences in its own language, then compares the resulting
SETS. A French name and an English name are never set side by side and judged to
look alike. `skill` and `glossary` are exactly where a near-miss name is a trap.

## Route 1 — occurrence profile · 27 records

⭐ **This route exists because an earlier refusal was read correctly rather than
reversed.** Lot 3 refused `weapon.properties` because pairing them **by
position** contradicted itself on 8 names out of 9: the French SRD lists a
weapon's properties in its own alphabetical order. That refusal was right — and
it only ever condemned the *position*.

**The order lies; the membership does not.** Take the set of proven weapons
carrying an English property, map it through the weapon pairs, and ask which
French property is carried by exactly those weapons and no others.

```
weapon-property   9 / 11    via 36 proven weapon pairs
skill            15 / 18    via 23 proven class, background and species pairs
feat              3 / 17    via 4 proven background pairs
```

**What it refuses:**

- **Indiscernible** — `Animal Handling` and `Survival` are cited by exactly the
  same carriers. Nothing outside them separates them, so both stay pending with
  that written down. This is the normal case, not a failure.
- **Never carried** — `Improvised Weapons` and `Range` are weapon properties no
  weapon in the table carries; `Performance` is a skill no proven carrier cites.
  An empty profile is not weak evidence, it is none.
- **14 of 17 feats** are cited by no proven carrier at all. Only backgrounds
  name a feat, and there are four of them.

⚠️ Both sides are read over the **same** proven carriers. A carrier that is not
paired contributes to neither profile — otherwise one side would carry evidence
the other cannot have and every extension would miss by one.

## Route 2 — mention profile, corroborated · 40 records

`glossary` is cited by **nobody**: no record anywhere carries a glossary id. But
the terms are *used* — a monster is Frightened, a spell shapes a Cone, an item
grants Advantage — so each term leaves a footprint in the prose of records that
are already paired.

🔴 **And that footprint lies if you trust it alone.** Measured: the monster
corpus on its own proposed `Attack Roll → Allonge` **and** `Damage → Allonge`.
Both English terms appear in nearly every English stat block; *allonge* appears
in nearly every French one. Their profiles coincide by **saturation**, not by
identity — and the same French term was claimed twice.

Two guards, and the second is what makes the route sound:

1. **Bijection** — the English term's profile must single out one French term,
   and that term's profile must single out the same English term. This alone
   kills the saturation pairs above.
2. **Corroboration** — the same pair must be reached in **at least two
   independent corpora** (monsters 330, spells 265, items 160, classes 12), and
   **no corpus may disagree**.

⭐ **Corroboration replaces a threshold, and that is the point.** The first
version of this route excluded "saturated" terms with a hand-picked cutoff. A
cutoff is a knob, and a knob is where a guess hides. Independent agreement is
evidence; a threshold is a preference.

**What it refuses:**

- 🔴 **`Long Rest`** — one corpus reads it as *Repos court*, another as *Repos
  long*. A single-corpus route would have shipped whichever it consulted first.
  **This refusal is the route's justification, found in the real data.**
- **45 terms reached by one corpus only.** One witness is not corroboration.
- **52 terms no corpus ever singled out.** Never mentioned, or mentioned only in
  company that never varies.

## Route 3 — a second axis, inside a group the first one isolated · 54 records

These records are not unreachable, they are **under-discriminated**. ⛔ The fix
is *not* a finer fingerprint mined from the prose: `item` already carries the
weakest prose-mined fingerprint in the file and is the most ambiguous genre of
all, so digging there makes it worse.

Instead, a second axis built from fields the first never touched, applied only
*within* a group the first axis already isolated. Both axes then point at the
same record: the first put these few together, the second tells them apart.

```
spell     50    casting time + duration
species    2    lineage count + whether a creature type is stated
tool       2    how many things it crafts + whether it has variants
```

**What it refuses:** a group the axis cannot split **stays ambiguous** — it
narrows or it abstains, it never picks. And `gear` (31) and `item` (96) get no
axis at all: `gear` carries three fields and the fingerprint reads two of them;
`item` has no untouched field that is not prose. **Saying so is the result.**

## What is still open — 288 records, 38 groups

```
glossary          112   no-fingerprint
item               96   ambiguous
gear               31   ambiguous
spell              24   ambiguous
feat               14   no-fingerprint
skill               3   no-fingerprint
item                2   unmatched-fr
tool                2   ambiguous
weapon              2   ambiguous
weapon-property     2   no-fingerprint
```

## And the refusals went from 1 to 56

```
uncorroborated              45
never-carried                3
no-second-axis               3
indiscernible                2
signed-on-polluted-record    1
corpora-disagree             1
never-mentioned              1
```

⚠️ **That number is written here because it moved by 55 and nothing announced
it.** The three new routes each refuse in their own way, so a jump was expected
— but "expected" is not "stated", and a count that changes silently is what
makes somebody reopen a review to find out whether anything broke. Nothing did:
every one of the 56 carries its reason and its detail, and
45 of them are the single-witness glossary terms the
corroboration guard is there to hold back.

**919 → 1040 pairs, 409 → 288 pending.** The three guards held: the 32 SRD
catalogues came out of the build byte-identical, no `human` provenance was
written by any route, and no pair anywhere was made by two names resembling
each other.

---

## 2026-08-24, lot 100 — `class-option` arrive, et arrive SANS empreinte

Le genre `class-option` (28 Manifestations occultes + 10 Métamagies, par
langue) entre dans la base avec **38 records de chaque côté** et **aucune
empreinte** : `correspond.py` le porte en `no-fingerprint`, un groupe de 38 en
attente. C'est la posture que ce module prévoit lui-même — *« Not an error. An
unanswered question, carried in the open »* — et c'est une décision, pas un
oubli.

**Mesuré avant de renoncer.** Les deux candidats évidents ne discriminent pas :

| candidat | distribution EN | distribution FR |
|---|---|---|
| `cost` (métamagie) | 1 point ×8, 2 points ×2 | identique |
| niveau minimal du prérequis (manifestation) | 2+ ×9, 5+ ×8, 9+ ×3, 7+ ×1, 12+ ×1, 15+ ×1, aucun ×5 | identique |

Les deux côtés portent **exactement les mêmes effectifs**, ce qui est rassurant
sur la lecture et inutile pour apparier : un seau unique des deux côtés
n'existe que pour `7+`, `12+` et `15+`. Une empreinte faible ne fabrique pas de
faux appariements — la règle « exactement un de chaque côté » l'interdit — mais
elle ne rend presque rien non plus, et elle donnerait l'illusion d'un genre
traité.

⭐ **La route qui marcherait est une `OCCURRENCE_ROUTE`, pas une empreinte.**
**Mesuré : 15 des 28 manifestations nomment un sort du catalogue, dans
CHAQUE langue** — *« You can cast Mage Armor »* / *« Vous pouvez lancer armure
du mage »*, *Disguise Self* / *Déguisement*, *Speak with Dead* / *Communication
avec les morts* — et les sorts sont déjà appariés dans cette table. ⚠️ Le
rapprochement se fait **à la casse et aux accents près** : le français imprime
les noms de sorts en minuscules dans la prose (*armure du mage*) là où
l'enregistrement les capitalise (*Armure du mage*), et une comparaison
littérale n'en retrouve que 3 sur 15. Marcher des paires déjà prouvées vers les
manifestations qui les citent fermerait **plus de la moitié** du genre sans un
seul appariement neuf deviné. C'est du travail de `correspond.py` et il lui faut
sa propre preuve ; il n'est pas fait ici, et il n'a pas été improvisé depuis un
extracteur.

⛔ **Et surtout, il n'a pas été fait par position.** Chaque liste est
alphabétique **dans sa propre langue** : *Décharge déchirante* est 3e en
français quand *Agonizing Blast* est 1er en anglais, *Mille visages* 14e contre
16e pour *Mask of Many Faces*. Un appariement par rang serait faux dans les deux
sens à la fois et **ne se contredirait jamais**.
