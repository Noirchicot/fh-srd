"""The seven adventuring packs' CONTENTS — the one prose entry the gear table cannot carry.

WHAT THIS IS, AND WHY IT IS NOT THE WHOLE PROSE CATALOGUE. `parse_gear_en.py`
and `parse_gear_fr.py` read the Item/Weight/Cost reference table and say, in so
many words, that the per-item prose catalogue printed around it is a DIFFERENT
grammar, deliberately deferred. That deferral stands. This module opens exactly
ONE window into that prose, and it opens it because the seven packs are the only
rows in the table whose price and weight are *not* the record: a Burglar's Pack
that does not say what is in it is a 16 GP line with nothing behind it, and a
character sheet cannot unpack it.

⭐ NO VOCABULARY. Nothing here names a pack. The packs are found by the SENTENCE
the source prints — "A Burglar's Pack contains the following items: …" / "Le
paquetage de cambrioleur contient les objets suivants : …" — and the subject of
that sentence is then required to BE a row of the table already parsed. A pack
this module cannot tie to a row is reported, never invented; a row this module
never meets simply carries no `contents`. ⛔ There is no list of seven anywhere
in this file, so a pack that left the SRD would show up as a missing field, not
as a constant quietly disagreeing with the book.

THE THREE THINGS THE PROSE DOES THAT A NAIVE READ GETS WRONG, each found by
reading the pinned PDFs rather than by guessing:

1. **The sentence is broken by the layout, in three different ways.** EN's
   Dungeoneer's Pack is cut by a COLUMN BREAK mid-list ("…2 flasks of Oil, 10"
   / blank line / "days of Rations, …"); FR's "objets sui-" / "vants :" is cut
   by a hyphenated line break; FR's Priest's Pack is cut by a plain line wrap
   INSIDE the anchor phrase itself ("contient les objets" / "suivants :").
   Anchoring on a line, or on a paragraph bounded by blank lines, fails on all
   three. So the whole line stream is joined into one text first and the
   sentence is matched across it; the list then ends where the book ends it,
   at the first period.

2. **The cited name is not the table's name.** The table prints
   "Lantern, Hooded", "Case, Map or Scroll", "Clothes, Fine" — alphabetised by
   inversion — while the prose cites them as a reader says them, "Hooded
   Lantern", "2 Map or Scroll Cases", "Fine Clothes". And the prose counts,
   so it pluralises: "10 Candles", "10 Torches", "3 Costumes", "5 Ink Pens".
   ⛔ Neither is repaired by a hand-written alias table. Two MECHANICAL rules
   are applied to the whole catalogue instead, and both are exact-match rules
   after transformation, so a match is a match and not a resemblance:
     · a record name with exactly one comma also answers to its rotation
       ("Lantern, Hooded" → "Hooded Lantern");
     · a record name containing a hyphen also answers to that hyphen removed
       (FR only in practice — see 3).
   The CITED phrase is tried verbatim first, then with a trailing "s" dropped,
   then with a trailing "es" dropped. Verbatim first is not a detail: "Ball
   Bearings", "Rations" and "Caltrops" are records whose own names end in "s",
   and a depluralise-first order mis-files all three.

3. **Dehyphenation is right about line breaks and wrong about real hyphens.**
   `_dehyphenate_numbered` joins "Back-" / "pack" into "Backpack", which is
   what the layout meant. But FR breaks "porte-plume" and "chausse-trappes" at
   their OWN hyphens, and the same rule then yields "porteplume" and
   "chaussetrappes". That is why record names also answer to themselves with
   hyphens removed: the damage is in the citation, so the repair is an extra
   door on the record, not a guess about the citation.

⛔ AN ELEMENT THAT RESOLVES TO NOTHING IS KEPT AND SAID SO. Its `text` is the
book's words, `name` and `ref` are null, and `unresolved()` names it. Measured
on the two pinned PDFs, 64 elements each: EN resolves 64/64; FR resolves 63/64,
the one holdout being "2 étuis à cartes et à parchemins" against the record
"Étui à cartes ou à parchemins" — the book says *et* in one place and *ou* in
the other, and no mechanical rule should paper over a word the source itself
changed.

⚠️ `text` IS THE LINE STREAM'S WORDS, NOT THE PRINTED GLYPHS, and for FR's two
own-hyphen breaks that is one character short: the export reads "porteplume"
and "chaussetrappes" where the page prints "porte-plume" and "chausse-trappes".
That is the dehyphenator's doing, upstream of here, and it is left visible
rather than repaired from the record it resolved to — `name` already carries
the record's own spelling, and a `text` quietly rewritten to match would stop
being a quotation.

A quantity with no number is 1, because the book writes "Backpack" and means
one. A "unit" is the counted word when the book counts something other than
the item — "7 flasks of Oil", "5 days of Rations", "5 sheets of Paper" — and
it is tried ONLY after the whole phrase has failed to resolve, so "sac de
couchage" (a record) is never split into a "sac" of "couchage".
"""

import re

import canon

_QTY = re.compile(r"^(\d+)\s+(\S.*)$")

#: One entry per language. `sentence` carries the two groups the read needs —
#: the pack as the book names it, and the list as the book prints it — and
#: `anchor` is the same phrase with nothing else, used only to COUNT: a
#: sentence the anchor finds and `sentence` does not is a read this module
#: failed to complete, and it says so rather than returning one pack fewer.
LANGS = {
    "en": {
        "anchor": re.compile(r"contains the following items:"),
        "sentence": re.compile(
            r"(?<![\w’'])(?:An?)\s+(\S[^.]{0,60}?)\s+"
            r"contains the following items:\s*([^.]{1,400})\."
        ),
        "lead": re.compile(r"^and\s+"),
        "of": re.compile(r"^(\S+)\s+of\s+(\S.*)$"),
    },
    "fr": {
        "anchor": re.compile(r"contient les objets suivants"),
        "sentence": re.compile(
            r"(?<![\w’'])Le\s+(\S[^.]{0,60}?)\s+"
            r"contient les objets suivants\s*:\s*([^.]{1,400})\."
        ),
        "lead": re.compile(r"^et\s+"),
        "of": re.compile(r"^(\S+)\s+(?:de|des|du|d[’'])\s*(\S.*)$"),
    },
}


def _variants(name):
    """The other spellings a RECORD answers to. See rules 2 and 3 above."""
    head, sep, tail = name.partition(", ")
    if sep and ", " not in tail:
        yield tail + " " + head
    if "-" in name:
        yield name.replace("-", "")


def build_index(gear):
    """(primary, alias, ambiguous) for a catalogue of parsed gear rows.

    `primary` is the slug of each record's printed name. `alias` holds the
    mechanical variants, and an alias is kept ONLY when it is unambiguous: a
    variant that lands on an existing record name is dropped (a real name
    always wins), and a variant two different records both claim is dropped
    from both and named in `ambiguous`. A door that opens onto two rooms is
    not a door.
    """
    primary = {}
    for row in gear:
        primary[canon.slugify(row["name"])] = row["name"]

    claims = {}
    for row in gear:
        for variant in _variants(row["name"]):
            claims.setdefault(canon.slugify(variant), set()).add(row["name"])

    alias, ambiguous = {}, []
    for slug, names in claims.items():
        if slug in primary:
            continue
        if len(names) > 1:
            ambiguous.append(slug)
            continue
        alias[slug] = next(iter(names))
    return primary, alias, sorted(ambiguous)


def _forms(phrase):
    """The cited phrase, then de-pluralised — verbatim first. See rule 2."""
    yield phrase
    if phrase.endswith("s"):
        yield phrase[:-1]
        if phrase.endswith("es"):
            yield phrase[:-2]


def _resolve(phrase, primary, alias):
    for form in _forms(phrase):
        form = form.strip()
        if not form:
            continue
        try:
            slug = canon.slugify(form)
        except ValueError:
            continue
        if slug in primary:
            return primary[slug]
        if slug in alias:
            return alias[slug]
    return None


def _element(raw, cfg, lang, primary, alias):
    text = cfg["lead"].sub("", raw.strip()).strip()
    quantity = 1
    body = text
    m = _QTY.match(body)
    if m:
        quantity = int(m.group(1))
        body = m.group(2)

    unit = None
    name = _resolve(body, primary, alias)
    if name is None:
        m = cfg["of"].match(body)
        if m:
            found = _resolve(m.group(2), primary, alias)
            if found is not None:
                unit, name = m.group(1), found

    return {
        "text": text,
        "quantity": quantity,
        "unit": unit,
        "name": name,
        "ref": (canon.record_id("srd", "gear", lang, canon.slugify(name))
                if name else None),
    }


def attach(gear, lines, lang):
    """Hang a `contents` list on every gear row the prose describes.

    `gear` is mutated in place — the rows are the ones the table parser just
    produced, so a pack's contents land on the pack's own record and nowhere
    else. Returns the anomaly list: an unread sentence, a subject that is on
    no row, and an ambiguous alias are all reported here. ⛔ A source with no
    pack prose at all (the synthetic fixtures) is NOT an anomaly — it is a
    source with no pack prose, and this module has nothing to say about it.
    """
    cfg = LANGS[lang]
    anomalies = []
    if not gear:
        return anomalies

    primary, alias, ambiguous = build_index(gear)
    for slug in ambiguous:
        anomalies.append({
            "page": 0, "line": 0,
            "detail": "gear pack contents: the variant %r is claimed by two "
                      "records — dropped, not guessed" % slug,
        })

    by_slug = {canon.slugify(row["name"]): row for row in gear}
    text = " ".join(l.strip() for l in lines if l.strip())

    read = 0
    for m in cfg["sentence"].finditer(text):
        subject, listing = m.group(1), m.group(2)
        read += 1
        try:
            slug = canon.slugify(subject)
        except ValueError:
            slug = None
        row = by_slug.get(slug)
        if row is None:
            anomalies.append({
                "page": 0, "line": 0,
                "detail": "gear pack contents: %r describes its contents but is "
                          "on no row of the gear table" % subject,
            })
            continue
        contents = [
            _element(part, cfg, lang, primary, alias)
            for part in listing.split(",")
            if part.strip()
        ]
        if contents:
            row["contents"] = contents

    seen = len(cfg["anchor"].findall(text))
    if seen != read:
        anomalies.append({
            "page": 0, "line": 0,
            "detail": "gear pack contents: %d contents sentence(s) begun in the "
                      "source, %d read to their end — the difference is a list "
                      "this parser did not finish, not a pack without contents"
                      % (seen, read),
        })
    return anomalies


def unresolved(gear):
    """Every cited element that landed on no record, as (pack, text) pairs."""
    out = []
    for row in gear:
        for element in row.get("contents") or []:
            if element["name"] is None:
                out.append((row["name"], element["text"]))
    return out
