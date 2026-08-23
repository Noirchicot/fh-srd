"""The lists a class CHOOSES FROM, read as one shape in both languages.

⏳ THE GENRE'S NAME IS REVOCABLE, and this paragraph is the record of why.
The architect's arbitration — *genre à part, or a `feat` carrying a category?*
— has **not** been rendered. What HAS been ratified is the principle that
constrains it:

    « Ce n'est pas "invocation" ni "métamagie" qu'il faut décrire, c'est **une
    liste dans laquelle une classe choisit**. Le SRD en remplit deux ; qui
    possède Eberron en ajoute une troisième ; un homebrew en ajoute une
    quatrième. La catégorie reste ouverte, jamais énumérée dans le schéma. »

So `class-option` is a PROPOSAL, chosen because it names the shape and not the
contents, and because it reads beside the `class-progression` genre that is
already here. Rename it if the architect picks another word; the DATA does not
move when the name does, which is the whole reason it could be extracted
before the arbitration. Two measurements bound the question and neither
settles it: the 2024 fighting styles ARE already feats here, carrying
`category: "fighting-style"` — but the `feat` genre is bounded to the Feats
CHAPTER by its own parser's anchors, and these twenty-eight and ten are
printed in the CLASSES chapter.

⛔ `CATEGORIES` BELOW IS NOT A CLOSED SET AND MUST NOT BECOME ONE. It is the
list of sections THIS pinned source prints. Nothing validates a record's
category against it; a third list arriving from Eberron or a homebrew adds a
section here and changes nothing else. The same refusal the glossary extractor
already makes.

--------------------------------------------------------------------------
CALIBRATED against both pinned PDFs on 2026-08-24, through `extract.py`:

    | list                         | English                  | French                              |
    |------------------------------|--------------------------|-------------------------------------|
    | Eldritch Invocations (28)    | `Eldritch Invocation Options`  p. 72-74 | `Options de Manifestation occulte`  p. 70-73 |
    | Metamagic (10)               | `Metamagic Options`      p. 66-67 | `Options de Métamagie`       p. 52-53 |

⚠️ **THE FRENCH DOES NOT SAY "INVOCATION".** It says **Manifestation occulte**
(and **Arcanum mystique** for the Warlock's other feature). A search for
"invocation" over the French corpus returns nothing and would conclude the
data is absent — the exact failure this repository keeps paying for: looking
for a NAME instead of measuring the THING.

⚠️ **AND THE PAGE NUMBERS DO NOT TRANSFER.** French orders its classes by
their French names, so *Ensorceleur* is the fifth class where *Sorcerer* is
the tenth: Metamagic is p. 66 in English and p. 52 in French — sixteen pages
apart, in the same book. Every anchor below is a LINE, never a page.

--------------------------------------------------------------------------
WHAT MAKES A HEAD, and why the text stream alone could not say.

An entry head here is a bare name on its own line. It is followed by a cost
line in the Metamagic list, by a prerequisite line in twenty-three of the
twenty-eight invocations, and by **nothing but prose in the other five**
(`Armor of Shadows`, `Eldritch Mind` and the three Pacts — `Armure d'ombres`,
`Esprit occulte`, `Pacte de la chaîne`, `Pacte de la lame`, `Pacte du
grimoire`).
So there is no punctuation, no label and no keyword that separates a head from
the first line of a paragraph. And the paragraphs in this section are full of
lines that would pass any "short line, title case" rule: *"Repeatable."*,
*"Cantrips and Rituals."*, *"Quick Attack."*, *"Your Save DC."*.

The source does state it, typographically: a head is set wholly in
`extract.HEAD_FONT` at `extract.HEAD_SIZE`, the same face and size as a spell
name or a class feature, and nothing inside an entry's body is. That reading
arrives as `layout[page]["heads"]` (see `extract.heads_of`), which is why this
parser declares `WANTS_LAYOUT`.

TWO SIGNALS, AND THEY HAVE TO AGREE. A line is taken as a head only when the
FONT says so *and* it opens a group — preceded by a blank line, or the first
line of a page. Neither alone is enough:

  * font alone would also match a wrapped prerequisite whose continuation
    happens to be exactly a name printed elsewhere on the same page — and this
    is MEASURED, not hypothetical: FR p.71 wraps `Lame dévorante`'s
    prerequisite as "Prérequis : Niveau d'Occultiste 12+, manifestation" /
    "Lame assoiffée", and that second line is character-for-character the head
    of the entry seven lines above it;
  * group-start alone matches every paragraph in the section.

And a head-face line printed inside an entry's BODY is reported as an
anomaly — that is the shape that could swallow a real entry whole. The same
collision inside a clause block is not reported: it is the wrap above, an
explained shape, and a register full of explained shapes is a register nobody
reads.

THREE GUARDS THAT REFUSE RATHER THAN WARN (`ListCountError`):

  1. **the count**, per list per language. The architect's own verification:
     28 invocations and 10 metamagic options. A region read from the wrong
     anchor swallows the class features printed above it and overshoots;
     a region cut short undershoots.
  2. **the order**. Both sources state it in their own prose — "options appear
     in alphabetical order" / "sont listées par ordre alphabétique" — so the
     names must strictly increase. A body line mistaken for a head almost
     never lands in alphabetical position.
  3. **nothing may be claimed twice**: one head, one record.

⛔ NOTHING HERE PAIRS THE TWO LANGUAGES. Each side is read off its own pages
and sorted in its own alphabet — *Décharge déchirante* is 3rd in French while
*Agonizing Blast* is 1st in English, and *Mille visages* (= Mask of Many
Faces) is 14th against 16th. Appariement by position would be wrong in both
directions at once and would never contradict itself. That work belongs to
`correspond.py` and to a person who signs it.

--------------------------------------------------------------------------
🔴 THE ASYMMETRY THAT IS DELIBERATE: **a manifestation is free once taken; a
metamagic is paid for at EVERY use.** Only the second needs a cost, and only
the second carries one. An invocation record has **no `cost` key at all** —
not `null`, which would read as "a cost nobody has extracted yet". The absence
is the statement. `prerequisite`, by contrast, is a field of the GENRE (some
entries in a list have one, some do not) and is emitted as `null` when the
source prints none, exactly as `feat` does.
"""

import re

import canon
from parse_spells_en import _dehyphenate_numbered

KIND = "class-option"

# The sections THIS pinned source prints, per language, as
# (category, start anchor line, end anchor line). ⛔ Open, never closed:
# adding a list means adding a row, and nothing validates against it.
CATEGORIES = {
    "en": (
        ("eldritch-invocation", "Eldritch Invocation Options", "Warlock Spell List"),
        ("metamagic", "Metamagic Options", "Sorcerer Spell List"),
    ),
    "fr": (
        ("eldritch-invocation", "Options de Manifestation occulte",
         "Liste des sorts d’Occultiste"),
        ("metamagic", "Options de Métamagie", "Liste des sorts d’Ensorceleur"),
    ),
}

# The architect's verification, and the only numbers hardcoded here. They are
# per CATEGORY, not per language: the two books print the same two lists.
EXPECTED = {"eldritch-invocation": 28, "metamagic": 10}

# The label that opens a clause line, per language. Both are matched on the
# NORMALISED stream, so the French narrow no-break space before the colon is
# already an ordinary space by the time it gets here (`extract.normalise`).
LABELS = {
    "en": {"prerequisite": "Prerequisite:", "cost": "Cost:"},
    "fr": {"prerequisite": "Prérequis :", "cost": "Coût :"},
}

# A clause may wrap ("Prerequisite: Level 5+ Warlock, Pact of the Blade" /
# "Invocation"). Four lines is twice the longest measured; hitting the cap is
# reported, not silently accepted.
MAX_CLAUSE_LINES = 4


class ListCountError(RuntimeError):
    """A list came back with the wrong number of entries, or out of order."""


def _region(stripped, start, end):
    """(first line after `start`, line of `end`), or None if either is absent.

    The FIRST occurrence of each anchor as a WHOLE line. "Metamagic Options"
    is also printed inside a sentence twenty lines above its own heading
    ("…of your choice from “Metamagic Options” later in this class's
    description"), which is why the match is on the stripped line and not on a
    substring — and why the count guard exists behind it anyway.
    """
    try:
        first = stripped.index(start)
    except ValueError:
        return None
    last = next((j for j in range(first + 1, len(stripped))
                 if stripped[j] == end), None)
    if last is None:
        return None
    return first + 1, last


def _clause(stripped, page_of, at, label):
    """The text of a labelled clause starting at line `at`, and where it ends.

    Collected to the next blank line or page change, whichever comes first.
    Returns (text, next line index, hit_cap).
    """
    parts = [stripped[at][len(label):].strip()]
    cursor = at
    while len(parts) < MAX_CLAUSE_LINES:
        nxt = cursor + 1
        if nxt >= len(stripped) or not stripped[nxt]:
            break
        if page_of[nxt] != page_of[cursor]:
            break
        parts.append(stripped[nxt])
        cursor = nxt
    text = re.sub(r"\s+", " ", " ".join(p for p in parts if p)).strip()
    return text, cursor + 1, len(parts) >= MAX_CLAUSE_LINES


def _paragraphs(lines):
    out = []
    for chunk in "\n".join(lines).split("\n\n"):
        joined = " ".join(l for l in chunk.split("\n") if l)
        if joined:
            out.append(joined)
    return "\n\n".join(out)


def parse_stream(stripped, page_of, heads_by_page, lang):
    records, anomalies = [], []
    label = LABELS[lang]

    for category, start, end in CATEGORIES[lang]:
        bounds = _region(stripped, start, end)
        if bounds is None:
            raise ListCountError(
                "%s/%s: the section anchors %r … %r were not both found as "
                "whole lines. Nothing was read for this list; a missing anchor "
                "is a source that changed shape, not an empty list."
                % (lang, category, start, end)
            )
        region_start, region_end = bounds

        def heads_on(index):
            page = page_of[index]
            return heads_by_page[page - 1] if 0 < page <= len(heads_by_page) else ()

        head_at = []
        for j in range(region_start, region_end):
            line = stripped[j]
            if not line or line not in heads_on(j):
                continue
            opens_group = (j == 0 or not stripped[j - 1]
                           or page_of[j] != page_of[j - 1])
            if opens_group:
                head_at.append(j)

        for position, j in enumerate(head_at):
            stop = head_at[position + 1] if position + 1 < len(head_at) else region_end
            name = stripped[j]
            record = {"name": name, "category": category, "prerequisite": None}

            cursor = j + 1
            for field in ("prerequisite", "cost"):
                if cursor < stop and stripped[cursor].startswith(label[field]):
                    text, cursor, capped = _clause(
                        stripped, page_of, cursor, label[field]
                    )
                    record[field] = text or None
                    if capped:
                        anomalies.append(
                            {"page": page_of[j], "line": j,
                             "detail": "%s/%s: the %s clause of %r ran to the "
                                       "%d-line cap and may be truncated"
                                       % (lang, category, field, name,
                                          MAX_CLAUSE_LINES)}
                        )

            while cursor < stop and not stripped[cursor]:
                cursor += 1

            # THE WITNESS, and it is deliberately narrow. A line whose text is
            # also one of this page's head texts, sitting INSIDE this entry's
            # body, is the shape that would let a real entry be swallowed
            # whole — so it is named. The same collision inside the clause
            # block above is NOT reported: it is the wrap this section
            # actually contains ("Prérequis : Niveau d'Occultiste 12+,
            # manifestation" / "Lame assoiffée", FR p.71), an explained shape,
            # and a register full of explained shapes is a register nobody
            # reads.
            for k in range(cursor, stop):
                line = stripped[k]
                if line and line in heads_on(k):
                    anomalies.append(
                        {"page": page_of[k], "line": k,
                         "detail": "%s/%s: %r is printed inside the body of "
                                   "%r and is set in the source's entry-head "
                                   "face; it was read as prose, not as an "
                                   "entry" % (lang, category, line[:60], name)}
                    )

            body = stripped[cursor:stop]
            while body and not body[-1]:
                body.pop()
            record["description"] = _paragraphs(body)

            if not record["description"]:
                anomalies.append(
                    {"page": page_of[j], "line": j,
                     "detail": "%s/%s: %r has a head line but no description"
                               % (lang, category, name)}
                )
                continue

            record["page"] = page_of[j]
            records.append(record)

    return records, anomalies


def check(records, lang):
    """Count and order, per list. Refuses; does not warn."""
    by_category = {}
    for record in records:
        by_category.setdefault(record["category"], []).append(record)

    problems = []
    for category, expected in sorted(EXPECTED.items()):
        found = by_category.get(category, [])
        if len(found) != expected:
            problems.append(
                "  %s/%s: %d entr%s, expected %d"
                % (lang, category, len(found),
                   "y" if len(found) == 1 else "ies", expected)
            )
        slugs = [canon.slugify(r["name"]) for r in found]
        for a, b in zip(slugs, slugs[1:]):
            if a >= b:
                problems.append(
                    "  %s/%s: %r is printed after %r, but the source states "
                    "this list is alphabetical" % (lang, category, b, a)
                )
    surplus = sorted(set(by_category) - set(EXPECTED))
    for category in surplus:
        problems.append(
            "  %s/%s: read from the source but carries no expected count"
            % (lang, category)
        )

    if problems:
        raise ListCountError(
            "%d problem(s) reading the lists a class chooses from:\n%s\n\n"
            "These counts are the architect's own verification (28 "
            "manifestations, 10 metamagic options) and the alphabetical order "
            "is stated by the source's own prose. A list that comes back the "
            "wrong length or out of order has been cut at the wrong anchor; "
            "exporting it anyway would ship a catalogue that is quietly "
            "incomplete. Nothing was written."
            % (len(problems), "\n".join(problems))
        )


def parse(pages, suspect_pages=(), layout=(), lang="en"):
    suspect = set(suspect_pages)
    heads_by_page = [page.get("heads", ()) for page in layout]

    numbered = []
    for number, raw in enumerate(pages, start=1):
        for line in raw.split("\n"):
            numbered.append((number, line))
    numbered = _dehyphenate_numbered(numbered)

    stripped = [line.strip() for _, line in numbered]
    page_of = [number for number, _ in numbered]

    # A document that prints NONE of these sections is not a failure — it is
    # `--fixture`, a six-page synthetic stub of French spells. A document that
    # prints SOME of them and not the others is a failure, and `parse_stream`
    # raises on it below.
    if not any(_region(stripped, start, end)
               for _, start, end in CATEGORIES[lang]):
        return [], [], []

    if not any(heads_by_page):
        raise ListCountError(
            "%s: the per-page layout carries no entry heads, but the section "
            "anchors ARE in this document. This parser reads an entry's name "
            "from the face the source sets it in (extract.heads_of); without "
            "that channel it cannot tell a name from the first line of a "
            "paragraph, and guessing is the failure this genre exists to "
            "avoid. Nothing was read." % lang
        )

    found, anomalies = parse_stream(stripped, page_of, heads_by_page, lang)
    check(found, lang)

    records, conflicts = [], []
    for record in found:
        if record["page"] in suspect:
            conflicts.append(
                {"page": record["page"], "name": record["name"],
                 "detail": "page text disputed between PyMuPDF and pdftotext"}
            )
        else:
            records.append(record)

    records.sort(key=lambda r: (r["category"], canon.slugify(r["name"])))
    return records, anomalies, conflicts
