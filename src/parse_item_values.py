"""The magic item value scale, and the three rules that make it usable.

WHAT THIS CLOSES. The book prints `Magic Item Rarities and Values` -- six
tiers and a price for each -- and it had never been extracted. Zero occurrences
in the layer. Same family as the armor category of lot 85: the data is in the
book, nobody had taken it.

🔴 THE NOTES TRAVEL WITH THE TABLE, IN THE SAME RECORD, and that is not a
filing preference. The scale alone is wrong for half the corpus: a consumable
is worth HALF, and a Spell Scroll is worth twice its scribing cost instead.
Potions and scrolls are the bulk of the SRD's magic items. Publishing the six
numbers without the two footnotes would publish a scale that lies, and somebody
would apply it -- in fact somebody already does: 32 records carry a
`halved, consumable (p.206)` provenance from another lot, applying a rule whose
source was not extracted. That is the hole this fills.

⛔ NO PRICE IS WRITTEN ONTO AN ITEM HERE. A value carried in two places ends up
contradicting itself. This is the SRD's own table, as the SRD prints it; the
calculation lives elsewhere.

⚠️ `Priceless` / `Inestimable` IS A VALUE, NOT A BLANK. An artifact the book
declares priceless and an artifact whose price we failed to read are two
different facts, so the record carries `priced: false` beside a null number
rather than leaving a hole for a reader to interpret.
"""

import re

import canon

# The six tiers, in each language's printed spelling, mapped to one set of
# English keys. A closed set -- the book prints exactly six -- so an
# unrecognised name is an extraction defect, not a seventh rarity.
RARITY_LABELS = {
    "en": {
        "Common": "common", "Uncommon": "uncommon", "Rare": "rare",
        "Very Rare": "very-rare", "Legendary": "legendary",
        "Artifact": "artifact",
    },
    "fr": {
        "Courante": "common", "Peu courante": "uncommon", "Rare": "rare",
        "Très rare": "very-rare", "Légendaire": "legendary",
        "Artefact": "artifact",
    },
}

TABLE_TITLE = {
    "en": "Magic Item Rarities and Values",
    "fr": "Rareté et valeur des objets magiques",
}

# The word the book uses where a number would go.
PRICELESS = {"en": "Priceless", "fr": "Inestimable"}

# `100 GP`, `40,000 GP`, `200 000 po` -- the thousands separator is a comma in
# English and a (normalised) space in French.
_VALUE = {
    "en": re.compile(r"^([\d,]+)\s*GP$"),
    "fr": re.compile(r"^([\d\s]+)\s*po$"),
}

# The sentence that says to add the base item's cost. It is printed ABOVE the
# table, and in English it starts on the previous page -- so it is found by its
# opening words rather than by position.
_ADD_RULE_START = {
    "en": "If a magic item incorporates an item",
    "fr": "Quand un objet magique comprend un objet",
}
_FOOTNOTE_START = {"en": "*Halve the value", "fr": "*Réduire de moitié"}


class ValueTableError(RuntimeError):
    """The table is not where it is expected, or not the shape it should be."""


def _value_of(text, lang):
    """A price in gold pieces, or None when the book prints a word instead."""
    if text == PRICELESS[lang]:
        return None
    match = _VALUE[lang].match(text)
    if not match:
        raise ValueTableError(
            "value %r is neither a gold-piece amount nor %r"
            % (text, PRICELESS[lang])
        )
    return int(re.sub(r"[,\s]", "", match.group(1)))


def _gather(lines, start, first_words):
    """The paragraph beginning at the line that starts with `first_words`.

    Joined until a line that ends a sentence and is followed by something that
    is not a continuation -- bounded, because a runaway here would swallow the
    chapter that follows.
    """
    for i in range(start, len(lines)):
        if lines[i].startswith(first_words):
            out = [lines[i]]
            j = i + 1
            while j < len(lines) and lines[j] and len(out) < 8:
                out.append(lines[j])
                if lines[j].rstrip().endswith((".", "»")) and (
                        j + 1 >= len(lines) or not lines[j + 1]
                        or lines[j + 1][:1].isupper()):
                    break
                j += 1
            return canon.dehyphenate(" ".join(out)) if hasattr(canon, "dehyphenate") \
                else " ".join(out)
    return None


def parse_stream(lines, page_of, lang):
    stripped = [l.strip() for l in lines]

    def page_at(i):
        return page_of[i] if i < len(page_of) else (page_of[-1] if page_of else 0)

    title = TABLE_TITLE[lang]
    where = next((i for i, l in enumerate(stripped) if l == title), None)
    if where is None:
        return [], [{"page": 0, "line": 0,
                     "detail": "%r not found in this source" % title}]

    labels = RARITY_LABELS[lang]
    # The table is printed in TWO column pairs, so the extracted stream reads
    # Common / 100 GP / Very Rare / 40,000 GP / Uncommon / ... -- the tiers do
    # not arrive in the book's own top-to-bottom order. Read (name, value)
    # couples and place each by its NAME; the interleave then costs nothing.
    tiers, anomalies, seen = [], [], set()
    i = where + 1
    while i + 1 < len(stripped) and len(seen) < len(labels):
        name, value = stripped[i], stripped[i + 1]
        if name in labels and name not in seen:
            try:
                amount = _value_of(value, lang)
            except ValueTableError as exc:
                anomalies.append({"page": page_at(i), "line": i,
                                  "detail": "%s: %s" % (name, exc)})
                return [], anomalies
            seen.add(name)
            tiers.append({
                "rarity_key": labels[name],
                "rarity_label": name,
                "value_label": value,
                "value_gp": amount,
                "priced": amount is not None,
            })
            i += 2
            continue
        i += 1

    missing = sorted(set(labels) - seen)
    if missing:
        anomalies.append({
            "page": page_at(where), "line": where,
            "detail": "the value table came back short: %d of %d tiers read, "
                      "missing %s. A partial scale is worse than none -- half "
                      "the corpus would be priced from it."
                      % (len(seen), len(labels), ", ".join(missing))})
        return [], anomalies

    add_rule = _gather(stripped, 0, _ADD_RULE_START[lang])
    footnote = _gather(stripped, where, _FOOTNOTE_START[lang])
    for label, text in (("add-base-cost", add_rule), ("footnote", footnote)):
        if not text:
            anomalies.append({
                "page": page_at(where), "line": where,
                "detail": "the %r rule was not found. ⛔ The scale must not "
                          "ship without it: a consumable is worth half and a "
                          "Spell Scroll twice its scribing cost, which is most "
                          "of the magic items in the book." % label})
            return [], anomalies

    return [{
        "name": title,
        "tiers": tiers,
        "add_base_cost_rule": add_rule,
        "value_footnote": footnote,
        "page": page_at(where),
    }], anomalies


def parse(pages, suspect_pages, lang):
    numbered = []
    for number, raw in enumerate(pages, start=1):
        for line in raw.split("\n"):
            numbered.append((number, line))
    lines = [l for _, l in numbered]
    page_of = [n for n, _ in numbered]
    records, anomalies = parse_stream(lines, page_of, lang)
    conflicts = [r for r in records if r["page"] in set(suspect_pages)]
    kept = [r for r in records if r["page"] not in set(suspect_pages)]
    return kept, anomalies, [
        {"page": c["page"], "name": c["name"],
         "detail": "page text disputed between PyMuPDF and pdftotext"}
        for c in conflicts]
