"""The Equipment chapter's two definition sections, read as ONE region.

CALIBRATED against both pinned PDFs on 2026-08-20, THROUGH `extract.py` and
not through a bare `fitz` read. The anchors below are what the parsers
actually receive:

    | section                | English (`SRD_CC_v5.2.1.pdf`) | French (`FR_SRD_CC_v5.2.1.pdf`) |
    |------------------------|-------------------------------|---------------------------------|
    | weapon properties (11) | `Properties`       p. 89-90   | `Propriétés`       p. 95-96     |
    | mastery properties (8) | `Mastery Properties`  p. 90   | `Propriétés botte`    p. 96     |

WHY ONE REGION AND NOT TWO, and this is the calibration's real finding:
**`Improvised Weapons` is a boxed sidebar, and `extract.py` hands it back
INSIDE the mastery block** — on EN p.90 it lands between the "Mastery
Properties" intro paragraph and `Cleave`, and on FR p.96 `Armes improvisées`
lands between the "Propriétés botte" intro and `Coup double`. It is a weapon
property all the same (the SRD prints it in the Weapons part of the chapter,
and the FHPC mandate of 2026-08-20 counts it as the eleventh). A parser that
read the properties section as "from the `Properties` heading to the
`Mastery Properties` heading" would therefore return TEN properties and
report nothing, and a parser that read the mastery section as "from its
heading to the end of the page" would return NINE masteries with a sidebar
among them. Both are the silent-partial failure this repository has already
paid for once.

So the region is read whole, once, and each head is assigned to a genre by a
CLOSED SET OF NAMES — never by which heading it happens to sit under.

WHAT MAKES A HEAD, measured rather than guessed. An entry head is a short
line carrying no terminal punctuation, standing at the start of a group:
either preceded by a blank line, or the first line of a page. **The page rule
is not decoration**: `Loading` is the first line of EN p.90 and `Lourde` the
first line of FR p.96, with the previous page's last body line immediately
before them in the stream. Requiring a blank line alone loses exactly one
property per language, which is how a count of 11 becomes a count of 10
without anything looking wrong.

The two SECTION headings are the mirror image: neither is preceded by a blank
line (`Versatile`'s last body line runs straight into `Mastery Properties`,
`Portée`'s into `Propriétés botte`), so they are found by exact match on the
line and excluded from the entry heads by name.

⚠️ THE FRENCH TRAP, and it is why the anchors above are spelled out. French
does not say "maîtrise" for this. It says **botte**, in the fencing sense:
the section is `Propriétés botte`, the weapons table's column is `Botte
d'arme`, the class feature is `Bottes d'arme`. And `Maîtrise des armes`
EXISTS in French, on the very same page (FR p. 95) — it is the *proficiency*
rule, "add your proficiency bonus to the attack roll". Two notions, two
neighbouring sections, one French word. An anchor on "maîtrise" returns the
wrong section and returns it quietly.

📌 The eight French mastery names are not derivable from the English ones by
any root or any rank: Cleave is *Enchaînement*, Nick is *Coup double*, Sap is
*Sape*, Topple is *Renversement*. Each language's list is alphabetical **in
its own language**, so `Reach` is 8th in English while `Allonge` is 1st in
French. Nothing here is paired across languages; each side is its own closed
set, read off its own pages — `layers/TRADUCTION.md`.

THE COUNT GUARD REFUSES, it does not warn. A head inside the region that is
in neither closed set is an anomaly, named and excluded. A closed set that
does not come back complete raises `SectionCountError` naming the missing and
the surplus terms — because a partial export is an answer, and a wrong one.
The mastery set is additionally cross-checked against the eight words the
Weapons table itself uses (`parse_weapons_{en,fr}.MASTERY_PROPERTIES`), so
the section headings and the table column have to agree or the build stops.
"""

import re

import canon
from parse_spells_en import _dehyphenate_numbered

PROPERTY_KIND = "weapon-property"
MASTERY_KIND = "weapon-mastery"

# A head carries no terminal punctuation. Every body line in the region ends
# in one, including the ones that wrap (the wrap lands mid-sentence only after
# `_dehyphenate_numbered` has rejoined split words, and a wrapped line still
# ends in a letter) -- which is why the rule is combined with the
# blank-line/page-start rule rather than used alone.
_END_PUNCT = re.compile(r"[.,;:!?»)’”]$")

# The longest real head is `Mastery Properties` (18) / `Armes improvisées`
# (17). The cap is deliberately loose: it exists to reject a body line that
# happens to end without punctuation, not to fit the known names.
_MAX_HEAD_LEN = 40


class SectionCountError(RuntimeError):
    """A closed set of section entries did not come back complete."""


class Spec(object):
    """One language's calibrated anchors and its two closed sets."""

    def __init__(self, properties_heading, mastery_heading, region_end,
                 properties, masteries):
        self.properties_heading = properties_heading
        self.mastery_heading = mastery_heading
        self.region_end = region_end
        self.properties = frozenset(properties)
        self.masteries = frozenset(masteries)

    def expected(self, kind):
        return self.properties if kind == PROPERTY_KIND else self.masteries

    @property
    def headings(self):
        return (self.properties_heading, self.mastery_heading)


# The eleven English properties, read off EN p.89-90. Ten of them are defined
# under the `Properties` heading; `Improvised Weapons` is the sidebar named in
# the module docstring.
PROPERTIES_EN = (
    "Ammunition", "Finesse", "Heavy", "Improvised Weapons", "Light",
    "Loading", "Range", "Reach", "Thrown", "Two-Handed", "Versatile",
)

# The eleven French properties, read off FR p.95-96 -- NOT translated from the
# line above. The order is French's own alphabet, and `Armes improvisées` is
# the sidebar.
PROPERTIES_FR = (
    "Allonge", "Armes improvisées", "Chargement", "Deux mains", "Finesse",
    "Lancer", "Légère", "Lourde", "Munitions", "Polyvalente", "Portée",
)

SPECS = {
    "en": Spec(
        properties_heading="Properties",
        mastery_heading="Mastery Properties",
        # The Weapons table's own title, first line of EN p.91. `Improvised
        # Weapons` is not an exact match for it, so the region cannot close
        # early on the sidebar.
        region_end="Weapons",
        properties=PROPERTIES_EN,
        masteries=(
            "Cleave", "Graze", "Nick", "Push", "Sap", "Slow", "Topple", "Vex",
        ),
    ),
    "fr": Spec(
        properties_heading="Propriétés",
        mastery_heading="Propriétés botte",
        region_end="Armes",
        properties=PROPERTIES_FR,
        masteries=(
            "Coup double", "Écorchure", "Enchaînement", "Ouverture",
            "Poussée", "Ralentissement", "Renversement", "Sape",
        ),
    ),
}


def _table_masteries(lang):
    """The eight mastery words the Weapons TABLE uses, in this language.

    Imported late so this module stays importable on its own, and compared
    rather than reused: the section headings and the table's sixth column are
    two independent readings of the same eight words, calibrated on different
    pages by different parsers. If they ever disagree, one of them is wrong
    and the build should say so instead of averaging them.
    """
    if lang == "en":
        import parse_weapons_en
        return parse_weapons_en.MASTERY_PROPERTIES
    import parse_weapons_fr
    return parse_weapons_fr.MASTERY_PROPERTIES


def _region(lines, spec):
    """(start, mastery_heading_index, end) of the two-section region.

    Returns None if the mastery heading is absent -- the one anchor that has
    no plausible double anywhere else in the document.
    """
    mastery = None
    for i, line in enumerate(lines):
        if line == spec.mastery_heading:
            mastery = i
            break
    if mastery is None:
        return None

    # `Properties` / `Propriétés` on its own line is NOT unique in the
    # document -- the Weapons table's column header is the same word. The one
    # that opens this region is the LAST such line before the mastery
    # heading, which is the section heading itself; the table's header comes
    # after. (Measured: EN p.89 vs p.91, FR p.95 vs p.97.)
    start = None
    for i in range(mastery):
        if lines[i] == spec.properties_heading:
            start = i
    if start is None:
        return None

    end = len(lines)
    for i in range(mastery + 1, len(lines)):
        if lines[i] == spec.region_end:
            end = i
            break
    return start, mastery, end


def _heads(lines, page_of, start, mastery, end, spec):
    """Every head in [start, end), section headings included, in order."""
    out = []
    for i in range(start, end):
        line = lines[i]
        if not line or len(line) > _MAX_HEAD_LEN or _END_PUNCT.search(line):
            continue
        if i not in (start, mastery):
            # A head starts a group: blank line before it, or a new page.
            if lines[i - 1] and page_of[i] == page_of[i - 1]:
                continue
        # A head is followed by a body. The blank between them is optional:
        # the two sidebars have one, the section entries do not.
        nxt = i + 1
        while nxt < end and not lines[nxt]:
            nxt += 1
        if nxt >= end:
            continue
        out.append((i, page_of[i], line))
    return out


def _body(lines, lo, hi):
    """Lines [lo, hi) as text: blank lines separate paragraphs, nothing else.

    Measured: every one of the 19 entries in both languages is a single
    paragraph. Joining paragraphs with a blank line rather than a space keeps
    that a fact the text can still state if the source ever stops being true,
    instead of a shape baked in here.
    """
    paragraphs, current = [], []
    for i in range(lo, hi):
        if lines[i]:
            current.append(lines[i])
        elif current:
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(paragraphs).strip()


def parse_stream(lines, page_of, lang, kind):
    spec = SPECS[lang]
    span = _region(lines, spec)
    if span is None:
        return [], [{
            "page": 0, "line": 0,
            "detail": "the %r / %r region was not found in this source"
                      % (spec.properties_heading, spec.mastery_heading),
        }]
    start, mastery, end = span

    heads = _heads(lines, page_of, start, mastery, end, spec)
    wanted = spec.expected(kind)
    other = spec.expected(
        MASTERY_KIND if kind == PROPERTY_KIND else PROPERTY_KIND)

    entries, anomalies, seen = [], [], []
    for pos, (idx, page, name) in enumerate(heads):
        stop = heads[pos + 1][0] if pos + 1 < len(heads) else end
        if name in spec.headings:
            continue
        if name in other:
            continue
        if name not in wanted:
            # NAMED, not skipped. A head inside this region that belongs to
            # neither closed set is the thing the guard exists to catch.
            anomalies.append({
                "page": page, "line": idx,
                "detail": "head %r stands in the %s / %s region but is in "
                          "neither closed set (%d properties, %d masteries); "
                          "it is not exported"
                          % (name, spec.properties_heading,
                             spec.mastery_heading,
                             len(spec.properties), len(spec.masteries)),
            })
            continue
        seen.append(name)
        entries.append({
            "name": name,
            "description": _body(lines, idx + 1, stop),
            "page": page,
        })

    missing = sorted(wanted - set(seen))
    surplus = sorted(name for name in seen if seen.count(name) > 1)
    if missing or surplus:
        raise SectionCountError(
            "%s/%s: the section yielded %d of the %d entries the SRD prints.\n"
            "  missing : %s\n"
            "  repeated: %s\n\n"
            "The set is closed and calibrated against the pinned PDF, so this "
            "is an extraction failure, not a source that changed. Nothing has "
            "been exported. A partial set here would ship a builder that "
            "silently cannot offer what is absent."
            % (lang, kind, len(seen), len(wanted),
               ", ".join(missing) or "(none)",
               ", ".join(sorted(set(surplus))) or "(none)")
        )

    if kind == MASTERY_KIND:
        table = set(_table_masteries(lang))
        if table != set(wanted):
            raise SectionCountError(
                "%s/%s: the mastery words defined in the %r section (%s) are "
                "not the ones the Weapons table's own column uses (%s). Two "
                "independent readings of the same eight words disagree; the "
                "build stops rather than choose one."
                % (lang, kind, spec.mastery_heading,
                   ", ".join(sorted(wanted)), ", ".join(sorted(table)))
            )

    return entries, anomalies


def parse(pages, suspect_pages, lang, kind):
    suspect = set(suspect_pages)

    numbered = []
    for number, raw in enumerate(pages, start=1):
        for line in raw.split("\n"):
            numbered.append((number, line))

    numbered = _dehyphenate_numbered(numbered)
    lines = [l.strip() for _, l in numbered]
    page_of = [n for n, _ in numbered]

    found, anomalies = parse_stream(lines, page_of, lang, kind)

    entries, conflicts = [], []
    for entry in found:
        if entry["page"] in suspect:
            conflicts.append(
                {"page": entry["page"], "name": entry["name"],
                 "detail": "page text disputed between PyMuPDF and pdftotext"}
            )
        else:
            entries.append(entry)

    entries.sort(key=lambda e: canon.slugify(e["name"]))
    return entries, anomalies, conflicts
