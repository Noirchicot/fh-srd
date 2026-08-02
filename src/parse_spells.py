"""Spell parser for the French SRD 5.2.1.

PROVISIONAL. The grammar below is written from the published layout of SRD
spell entries; it has NOT yet been calibrated against the real PDF, because the
PDF has not been fetched. Expect the anchors to need adjustment. What will not
need adjustment is the discipline:

    a block that does not parse cleanly becomes an `unparsed` exclusion.
    It never becomes a half-filled record.

Excluding and reporting is cheap. A spell record that quietly lost its
components line is a rule someone plays wrong at the table, and — for a project
that intends to publish — a claim about SRD content that nobody can audit.
"""

import re

import canon

# The anchor. Every SRD spell entry carries a casting-time line, and no other
# kind of block does. Finding the anchor first and reading outwards is far more
# robust than trying to recognise a spell by its title, which is just a line of
# prose in a slightly larger font that text extraction discards.
ANCHOR = re.compile(r"^\s*Temps d[’']incantation\s*:\s*(.+)$", re.IGNORECASE)

FIELDS = [
    ("casting_time", re.compile(r"^\s*Temps d[’']incantation\s*:\s*(.+)$", re.I)),
    ("range", re.compile(r"^\s*Port[ée]e\s*:\s*(.+)$", re.I)),
    ("components", re.compile(r"^\s*Composantes?\s*:\s*(.+)$", re.I)),
    ("duration", re.compile(r"^\s*Dur[ée]e\s*:\s*(.+)$", re.I)),
]

# "Sort de 3e niveau d'évocation" / "Tour de magie d'évocation"
LEVEL_LINE = re.compile(
    r"^\s*(?:Sort de (?P<level>\d+)(?:er|e|ème)? niveau|Tour de magie)"
    r"\s+d[e’']?\s*(?P<school>[A-Za-zÀ-ÖØ-öø-ÿ']+)",
    re.IGNORECASE,
)

RITUAL = re.compile(r"\(rituel\)", re.IGNORECASE)


def _clean(line):
    return line.replace(" ", " ").strip()


def parse_page(text, page_number):
    """Return (spells, anomalies) for one page of extracted text.

    Deliberately conservative: an entry is emitted only when the name, the
    level line and all four stat lines were found. Anything else is an anomaly
    carrying enough context to look it up in the PDF by hand.
    """
    lines = [_clean(l) for l in text.split("\n")]
    spells, anomalies = [], []

    anchors = [i for i, l in enumerate(lines) if ANCHOR.match(l)]
    for idx in anchors:
        # Walk back: the level line sits directly above the stat block, and the
        # spell name directly above that.
        level_at = None
        for back in range(idx - 1, max(idx - 5, -1), -1):
            if LEVEL_LINE.match(lines[back]):
                level_at = back
                break
        if level_at is None or level_at == 0:
            anomalies.append(
                {
                    "page": page_number,
                    "line": idx,
                    "detail": "casting-time anchor with no level line above it: %r"
                    % lines[idx][:120],
                }
            )
            continue

        name = lines[level_at - 1]
        if not name or len(name) > 80 or name.endswith(":"):
            anomalies.append(
                {
                    "page": page_number,
                    "line": level_at - 1,
                    "detail": "implausible spell name above level line: %r" % name[:120],
                }
            )
            continue

        meta = LEVEL_LINE.match(lines[level_at])
        level = int(meta.group("level")) if meta.group("level") else 0
        school = meta.group("school").lower()

        stats, missing = {}, []
        window = lines[idx : idx + 8]
        for key, pattern in FIELDS:
            value = None
            for line in window:
                match = pattern.match(line)
                if match:
                    value = match.group(1).strip()
                    break
            if value is None:
                missing.append(key)
            else:
                stats[key] = value

        if missing:
            anomalies.append(
                {
                    "page": page_number,
                    "line": idx,
                    "detail": "spell %r missing stat line(s): %s"
                    % (name, ", ".join(missing)),
                }
            )
            continue

        # Body text runs to the next anchor's entry, or to the end of the page.
        body_start = idx + len(FIELDS)
        next_anchor = next((a for a in anchors if a > idx), None)
        body_end = (next_anchor - 2) if next_anchor else len(lines)
        body = [l for l in lines[body_start:body_end] if l]

        spells.append(
            {
                "name": name,
                "level": level,
                "school": school,
                "ritual": bool(RITUAL.search(lines[level_at])),
                "casting_time": stats["casting_time"],
                "range": stats["range"],
                "components": stats["components"],
                "duration": stats["duration"],
                "text": body,
                "page": page_number,
            }
        )

    return spells, anomalies


def parse(pages, suspect_pages=()):
    """Parse every page, routing suspect pages to the exclusion register.

    `suspect_pages` are the page numbers where PyMuPDF and pdftotext disagreed.
    Their spells are not parsed at all — a page whose text two extractors read
    differently is not a page to guess from.
    """
    suspect = set(suspect_pages)
    spells, anomalies, conflicts = [], [], []

    for number, text in enumerate(pages, start=1):
        if number in suspect:
            found, _ = parse_page(text, number)
            for spell in found:
                conflicts.append(
                    {
                        "page": number,
                        "name": spell["name"],
                        "detail": "page text disputed between PyMuPDF and pdftotext",
                    }
                )
            continue
        found, page_anomalies = parse_page(text, number)
        spells.extend(found)
        anomalies.extend(page_anomalies)

    # Sort by content, not by discovery order, so the record set does not
    # depend on which page a spell happened to land on in this printing.
    spells.sort(key=lambda s: (canon.slugify(s["name"]), s["level"]))
    return spells, anomalies, conflicts
