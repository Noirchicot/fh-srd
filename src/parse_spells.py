"""Spell parser for the French SRD 5.2.1.

CALIBRATED against the pinned FR PDF on 2026-08-03. Every shape below was
observed by clustering the 345 `Temps d’incantation` anchors in the document,
not assumed from the English edition — which has a different grammar entirely
(EN puts the level first, "Level 2 Transmutation"; FR puts the school first,
"Transmutation du 2e niveau").

Four things the real document does that a plausible-looking parser gets wrong:

1. **Cantrips agree in gender.** Seven schools are feminine and take
   "mineure" — but *Enchantement* is masculine and takes "mineur". Hard-coding
   "mineure" silently loses every enchantment cantrip; there is exactly one in
   the SRD (Moquerie cruelle, p.161), which is precisely the kind of single
   missing record nobody notices.
2. **The level line wraps.** When the class list is long it runs onto the next
   line — "Transmutation du 2e niveau (Barde, Clerc, Druide," / "Ensorceleur,
   Magicien, Rôdeur)". The name sits above the FIRST line, not above the last.
3. **Ordinals differ.** "du 1er niveau" for level 1, "du 2e niveau" after.
4. **Words break across lines.** The PDF hyphenates: "incanta-\ntion".

The discipline is unchanged: a block that does not parse cleanly becomes an
`unparsed` exclusion. It never becomes a half-filled record.
"""

import re

import canon

# Observed in the document. French uses "Invocation" where English uses
# "Conjuration"; both appear here only in their French form because the source
# being parsed is the French PDF.
SCHOOLS = {
    "Abjuration": "abjuration",
    "Divination": "divination",
    "Enchantement": "enchantement",
    "Évocation": "evocation",
    "Illusion": "illusion",
    "Invocation": "invocation",
    "Nécromancie": "necromancie",
    "Transmutation": "transmutation",
}

_SCHOOL_ALT = "|".join(SCHOOLS)

# `mineure?` covers both genders: "Évocation mineure" and "Enchantement mineur".
LEVEL_HEAD = re.compile(
    r"^(?P<school>%s)\s+(?:du\s+(?P<level>\d+)\s*(?:er|e|ème)\s+niveau|(?P<cantrip>mineure?))\s*\("
    % _SCHOOL_ALT
)

FIELDS = [
    ("casting_time", re.compile(r"^Temps d[’']incantation\s*:\s*(.+)$")),
    ("range", re.compile(r"^Port[ée]e\s*:\s*(.+)$")),
    ("components", re.compile(r"^Composantes?\s*:\s*(.+)$")),
    ("duration", re.compile(r"^Dur[ée]e\s*:\s*(.+)$")),
]

RITUAL = re.compile(r"rituel", re.IGNORECASE)

_HYPH_END = re.compile(r"[a-zà-öø-ÿ]-$")
_HYPH_START = re.compile(r"^[a-zà-öø-ÿ]")


def _dehyphenate_numbered(numbered):
    """Merge a hyphenated line break WITHOUT losing the page number.

    The previous approach joined the whole document into one string,
    substituted, and re-split it -- then kept the result only if the line
    count didn't change, on the theory that a changed count meant the 1:1
    page mapping broke. Measured against the real document: with 2471
    hyphenated line breaks across ~57000 lines, that count changes on nearly
    every real run, so the fallback fired every time and dehyphenation never
    actually applied -- a wrapped field came back as "incanta- tion" (hyphen,
    space, and all) instead of "incantation", silently, because the record
    still looked complete.

    Fixed by merging line-by-line instead of on the whole joined string: a
    line ending in a lowercase letter then a hyphen, followed by a line
    starting with a lowercase letter, is one word split by the layout. The
    merged line takes the FIRST fragment's page number, which only matters
    when a word is split across a page boundary -- rare, and no worse than
    the alternative of not merging at all.

    Checked against the last line ALREADY WRITTEN, not against a fixed
    two-line window, so a chain of consecutive breaks ("in-" / "canta-" /
    "tion") is caught, not just the first.
    """
    out = []
    for page, line in numbered:
        if out and _HYPH_END.search(out[-1][1]) and _HYPH_START.match(line):
            prev_page, prev_line = out.pop()
            out.append((prev_page, prev_line[:-1] + line))
        else:
            out.append((page, line))
    return out


def _classes(text):
    """'(Barde, Druide, Ensorceleur)' -> ['Barde','Druide','Ensorceleur']."""
    inner = text[text.find("(") + 1 : text.rfind(")")] if "(" in text else ""
    return [c.strip() for c in inner.split(",") if c.strip()]


def parse_stream(text, page_of):
    """Return (spells, anomalies) for the whole de-hyphenated document.

    `page_of[i]` is the source page of line `i`, so a spell reports the page it
    starts on even though the parser reads across page breaks.
    """
    lines = [l.strip() for l in text.split("\n")]
    spells, anomalies = [], []

    def page_at(i):
        return page_of[i] if i < len(page_of) else (page_of[-1] if page_of else 0)

    # Every entry's level line, so one entry can never read into the next.
    #
    # Reading the document as a continuous stream fixed spells split across a
    # page break, and introduced a worse bug in exchange: an entry MISSING a
    # stat line would scan forward past its own description and pick up the
    # NEXT spell's field. The fixture caught it — a spell deliberately stripped
    # of its components line came back with the following spell's "V", looking
    # complete and being wrong.
    #
    # A missing field is an exclusion. A borrowed field is a lie, and it is the
    # kind that survives every count-based check.
    heads = [i for i, l in enumerate(lines) if LEVEL_HEAD.match(l)]
    next_head = {}
    for position, index in enumerate(heads):
        next_head[index] = heads[position + 1] if position + 1 < len(heads) else len(lines)

    for idx, line in enumerate(lines):
        head = LEVEL_HEAD.match(line)
        if not head:
            continue

        # The level line may wrap; collect until the parenthesis closes.
        level_lines = [line]
        cursor = idx
        while "(" in " ".join(level_lines) and ")" not in " ".join(level_lines):
            cursor += 1
            if cursor >= len(lines) or cursor > idx + 3:
                break
            level_lines.append(lines[cursor])
        level_text = " ".join(level_lines)

        if ")" not in level_text:
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "unterminated class list: %r" % level_text[:110]}
            )
            continue

        # The name is above the FIRST line of the level block.
        name_at = idx - 1
        while name_at >= 0 and not lines[name_at]:
            name_at -= 1
        name = lines[name_at] if name_at >= 0 else ""
        if not name or len(name) > 60 or name.endswith(":") or name.endswith(","):
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "implausible spell name above %r: %r"
                           % (level_text[:50], name[:80])}
            )
            continue

        # Stat block follows the level block.
        #
        # Values WRAP. "Composantes : V, S, M (une boulette de guano de
        # chauve-souris et de soufre)" runs onto the next line, and taking only
        # the matched line truncates it mid-parenthesis — which is how the base
        # ended up claiming Boule de feu needs "une boulette de guano de".
        # Truncated silently: the record looked complete, the parenthesis just
        # never closed.
        #
        # So a value continues onto following lines until the next field label
        # or a blank line ends it.
        stats, missing = {}, []
        # Hard-bounded by the next entry's level line, minus its name line.
        # min() keeps the old 16-line cap for the ordinary case.
        limit = min(cursor + 16, max(next_head.get(idx, len(lines)) - 1, cursor + 1))
        window = lines[cursor + 1 : limit]
        current = None
        for wline in window:
            matched = None
            for key, pattern in FIELDS:
                match = pattern.match(wline)
                if match:
                    matched = key
                    stats[key] = match.group(1).strip()
                    current = key
                    break
            if matched:
                continue
            if not wline.strip():
                # A blank line closes the stat block; the description follows.
                if len(stats) == len(FIELDS):
                    break
                current = None
                continue
            if current:
                stats[current] = (stats[current] + " " + wline.strip()).strip()

        missing = [key for key, _ in FIELDS if key not in stats]

        if missing:
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "spell %r missing stat line(s): %s"
                           % (name, ", ".join(missing))}
            )
            continue

        level = 0 if head.group("cantrip") else int(head.group("level"))
        spells.append(
            {
                "name": name,
                "level": level,
                "school": SCHOOLS[head.group("school")],
                "cantrip": bool(head.group("cantrip")),
                "classes": _classes(level_text),
                # The French edition marks a ritual in the CASTING TIME line
                # ("Temps d’incantation : 1 minute ou rituel"), where the
                # English edition marks it on the level line. Reading the level
                # line here — the English habit — reported zero rituals in a
                # document that has plenty.
                "ritual": bool(RITUAL.search(stats["casting_time"])),
                "casting_time": stats["casting_time"],
                "range": stats["range"],
                "components": stats["components"],
                "duration": stats["duration"],
                "page": page_at(name_at),
            }
        )

    return spells, anomalies


def parse(pages, suspect_pages=()):
    """Parse the document as ONE CONTINUOUS STREAM, not page by page.

    Spell entries cross page boundaries. *Arrêt du temps* (p.118) has its name,
    level line, casting time and range at the foot of one page and its
    components and duration on the next. Parsing page by page loses the stat
    block and sends a perfectly good spell to the exclusion register — eight of
    them, in this document. That is the failure mode this project has to avoid:
    not a wrong record, but a silently missing one.

    Page numbers are carried alongside each line so `source_locator` still
    points at the page a spell *starts* on.

    `suspect_pages` are page numbers where the two extractors disagreed. A
    spell starting on one is not parsed — a page two extractors read
    differently is not a page to guess from.
    """
    suspect = set(suspect_pages)

    numbered = []
    for number, raw in enumerate(pages, start=1):
        for line in raw.split("\n"):
            numbered.append((number, line))

    numbered = _dehyphenate_numbered(numbered)

    stream = "\n".join(l for _, l in numbered)
    page_of = [n for n, _ in numbered]

    found, anomalies = parse_stream(stream, page_of)

    spells, conflicts = [], []
    for spell in found:
        if spell["page"] in suspect:
            conflicts.append(
                {"page": spell["page"], "name": spell["name"],
                 "detail": "page text disputed between PyMuPDF and pdftotext"}
            )
        else:
            spells.append(spell)

    # Sorted by content, so the record set never depends on which page a spell
    # happened to land on in this printing.
    spells.sort(key=lambda s: (canon.slugify(s["name"]), s["level"]))
    return spells, anomalies, conflicts
