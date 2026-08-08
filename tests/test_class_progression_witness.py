"""The class progression tables, checked against three independent witnesses.

A synthetic-fixture test proves a parser does what its author thought. It
cannot prove the numbers are the SRD's numbers -- and a wrong progression
table is the worst kind of defect this repository can ship, because it
produces characters that are silently, plausibly wrong. So the exported
records are checked against three things that were not used to produce them:

  1. **Poppler, reading the same pages a different way.** `pdftotext -layout`
     renders a table in its printed geometry, columns aligned under their own
     headers. The pipeline's own extractor (PyMuPDF) hands parsers a linear
     stream in which the header order is destroyed. Two extractors, two
     renderings, one set of numbers -- the same rule extract.py already
     applies page by page, applied here to column ORDER, which is the one
     thing the linear stream cannot vouch for.
  2. **The other language.** The French and English SRDs are separately
     typeset documents parsed by separately calibrated grammars. Every
     number in all twelve tables must agree across them.
  3. **The SRD contradicting itself, if it can.** "Multiclass Spellcaster:
     Spell Slots per Spell Level" (p.26 EN / p.27 FR) prints the full-caster
     slot grid a second time, in a different chapter, for a different
     purpose. All five full casters must match it exactly, and both
     half-casters must match it at ceil(level / 2) -- the SRD's own
     multiclassing rule, arriving as an arithmetic check on data read from
     somewhere else entirely.

This test reads the pinned PDFs. It is skipped, loudly and with an exit code
of 0, when they are absent -- the same posture `test_attribution_verbatim.py`
takes, since the PDFs are deliberately outside git.
"""

import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import canon  # noqa: E402
import extract  # noqa: E402
import sources  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS = os.path.join(ROOT, "exports", "srd")

# The two languages' names for the same class. This mapping exists ONLY here,
# in a test: the base itself draws no FR<->EN edge (see the README's note on
# the absent `translation_of` relation), and this is a witness pairing, not a
# record. Nothing in exports/ depends on it.
PAIRS = [
    ("Barbarian", "Barbare"), ("Bard", "Barde"), ("Cleric", "Clerc"),
    ("Druid", "Druide"), ("Fighter", "Guerrier"), ("Monk", "Moine"),
    ("Paladin", "Paladin"), ("Ranger", "Rôdeur"), ("Rogue", "Roublard"),
    ("Sorcerer", "Ensorceleur"), ("Warlock", "Occultiste"),
    ("Wizard", "Magicien"),
]

# The one column the two languages legitimately disagree on: the Monk's
# Unarmored Movement is printed in feet in English and converted to metres in
# French (+10 ft. / +3 m, +15 ft. / +4,50 m). Both are the source's own text.
# Named here rather than papered over by a loose comparison.
UNIT_COLUMNS = {("Monk", "unarmored_movement"),
                ("Moine", "deplacement_sans_armure")}

# Three names the French progression tables print that the French class
# chapters' own headings do not match. All three were found by this check and
# are documented in the README; none is fixable from this lot's side:
#   * "Bond agressif" (Barbare 7) -- the FR table and the FR heading give the
#     feature TWO DIFFERENT NAMES ("Bond instinctif" in the chapter). A
#     genuine inconsistency in the source, not a parse error.
#   * "Communication avec le protecteur" (Occultiste 9) and "Double attaque
#     supplémentaire" (Guerrier 11) -- both headings wrap onto a second
#     physical line in the FR PDF, and `parse_classes_fr` keeps only the
#     first, so the CLASS records hold truncated names ("Communication avec",
#     "Double attaque"). A defect in that parser, reported rather than fixed
#     here: changing it reshapes existing class records, which is the
#     architect's call, not this lot's.
KNOWN_NAME_GAPS = {
    "en": frozenset(),
    "fr": frozenset({
        "Bond agressif",
        "Communication avec le protecteur",
        "Double attaque supplémentaire",
    }),
}

# The table annotates a few features with a count the heading does not carry:
# "Action Surge (one use)" against "Level 2: Action Surge", "Mystic Arcanum
# (level 6 spell)" against "Level 11: Mystic Arcanum".
_TRAILING_PAREN = re.compile(r"\s*\([^()]*\)$")

MULTICLASS_HEADING = {
    "en": "Multiclass Spellcaster:",
    "fr": "Incantateurs multiclassés :",
}

# The other legitimate cross-language difference, and the only other one:
# English prints the Bard's die column capitalised ("D6"), French does not
# ("d6"). Same die, different house style, and both are kept as printed. Dice
# are therefore compared case-insensitively -- and ONLY dice, so that a real
# divergence anywhere else still fails.
_DIE = re.compile(r"^(?:[Dd]\d+|\d+d\d+)$")

DASH = "—"
_LEVEL_LINE = re.compile(r"^\s*(\d{1,2})\s+\+(\d)\s+(.*)$")
_VALUE = re.compile(r"^(?:—|\d+|\+\d+(?:,\d+)?|[Dd]\d+|\d+d\d+)$")
# A laid-out row separates a distance from its unit with ordinary spaces, so
# "+10 ft." arrives as TWO tokens where the record holds one cell. Read as a
# unit word that belongs to the number before it, rather than stitched with a
# placeholder character -- every obvious placeholder (U+00A0, U+001F) is
# whitespace as far as str.split() is concerned, which takes the stitch back
# apart in the next line of code.
_UNIT = ("ft.", "m")


def load(lang, kind):
    with open(os.path.join(EXPORTS, lang, kind + ".json"), encoding="utf-8") as fh:
        return {r["name"]: r["data"] for r in json.load(fh)["records"]}


def pdf_path(lang):
    try:
        return sources.verify("srd-5.2.1-%s" % lang)
    except sources.SourceError:
        return None


def layout_page(path, page):
    out = subprocess.run(
        ["pdftotext", "-layout", "-enc", "UTF-8", "-f", str(page), "-l",
         str(page), path, "-"],
        capture_output=True, text=True, check=True,
    )
    return out.stdout


# ---------------------------------------------------------------------------
# Witness 1 — poppler, reading the printed geometry.
# ---------------------------------------------------------------------------

def witness_rows(text, trailing_count):
    """Read a laid-out progression table as {level: [trailing cells]}.

    The last `trailing_count` whitespace-separated tokens of a row are its
    value columns; everything before them is the feature cell. A row whose
    values sit on a continuation line (the French Occultiste does this twice,
    where a superscript ordinal breaks the line) is picked up by carrying the
    scan forward until the tokens are found.
    """
    rows, pending = {}, None
    for line in text.split("\n"):
        match = _LEVEL_LINE.match(line)
        tokens = (match.group(3) if match else line).split()
        values = take_values(tokens, trailing_count)
        if match:
            pending = None if len(values) == trailing_count else int(match.group(1))
            if pending is None:
                rows[int(match.group(1))] = values
            continue
        if pending is not None and len(values) == trailing_count:
            rows[pending] = values
            pending = None
    return rows


def take_values(tokens, count):
    """Pop up to `count` value cells off the end of a laid-out row."""
    values = []
    while tokens and len(values) < count:
        token = tokens[-1]
        if token in _UNIT and len(tokens) > 1 and _VALUE.match(tokens[-2]):
            tokens.pop()
            values.insert(0, "%s %s" % (tokens.pop(), token))
            continue
        if not _VALUE.match(token):
            break
        values.insert(0, tokens.pop())
    return values


def printed(value):
    """A record value back in the source's own printed spelling."""
    return DASH if value is None else str(value)


def check_witness(lang, records):
    path = pdf_path(lang)
    if path is None:
        return None
    checked = 0
    for name, data in sorted(records.items()):
        page = int(data["_page"])
        keys = [c["key"] for c in data["resource_columns"]]
        trailing_count = len(keys) + data["spell_slot_levels"]
        rows = witness_rows(layout_page(path, page), trailing_count)
        assert len(rows) == 20, (
            "%s/%s p.%d: poppler yielded %d rows, not 20"
            % (lang, name, page, len(rows)))
        for entry in data["levels"]:
            expected = [printed(entry["resources"][k]) for k in keys]
            expected += [DASH if s == 0 else str(s)
                         for s in entry.get("spell_slots", [])]
            assert rows[entry["level"]] == expected, (
                "%s/%s level %d: poppler reads %r, the record says %r"
                % (lang, name, entry["level"], rows[entry["level"]], expected))
            checked += len(expected)
    return checked


# ---------------------------------------------------------------------------
# Witness 3 — the SRD's own multiclassing table.
# ---------------------------------------------------------------------------

def multiclass_from_pages(pages, heading):
    document = "\n\n".join(pages)
    start = document.index(heading)
    chunks = [[l.strip() for l in c.split("\n") if l.strip()]
              for c in document[start:].split("\n\n")]
    grid, level = [], 1
    for chunk in chunks:
        if chunk and chunk[0] == str(level) and len(chunk) == 10:
            grid.append([0 if v == DASH else int(v) for v in chunk[1:]])
            level += 1
            if level > 20:
                break
    return grid


def main():
    en = load("en", "class-progression")
    fr = load("fr", "class-progression")
    assert len(en) == 12 and len(fr) == 12, (len(en), len(fr))

    # `source_locator` carries the page; re-attach it so the witness knows
    # where to look without the record having to duplicate it in `data`.
    for lang, records in (("en", en), ("fr", fr)):
        with open(os.path.join(EXPORTS, lang, "class-progression.json")) as fh:
            for rec in json.load(fh)["records"]:
                records[rec["name"]]["_page"] = rec["source_locator"].lstrip("p.")

    # -- WITNESS 2: the other language --------------------------------------
    compared = 0
    for en_name, fr_name in PAIRS:
        a, b = en[en_name], fr[fr_name]
        assert a["spell_slot_levels"] == b["spell_slot_levels"], (en_name, fr_name)
        a_keys = [c["key"] for c in a["resource_columns"]]
        b_keys = [c["key"] for c in b["resource_columns"]]
        assert len(a_keys) == len(b_keys), (en_name, a_keys, b_keys)
        for la, lb in zip(a["levels"], b["levels"]):
            assert la["level"] == lb["level"]
            assert la["proficiency_bonus"] == lb["proficiency_bonus"], (en_name, la)
            assert la.get("spell_slots") == lb.get("spell_slots"), (en_name, la["level"])
            compared += 1 + len(la.get("spell_slots", []))
            for ak, bk in zip(a_keys, b_keys):
                if (en_name, ak) in UNIT_COLUMNS:
                    continue
                left, right = la["resources"][ak], lb["resources"][bk]
                if (isinstance(left, str) and isinstance(right, str)
                        and _DIE.match(left) and _DIE.match(right)):
                    left, right = left.lower(), right.lower()
                assert left == right, (
                    "%s/%s level %d, column %s/%s: %r vs %r"
                    % (en_name, fr_name, la["level"], ak, bk,
                       la["resources"][ak], lb["resources"][bk]))
                compared += 1
    print("  ok  %d values agree between the English and French tables "
          "(one named unit exception: the Monk's movement, feet vs metres)" % compared)

    # -- WITNESS 3: the multiclass spellcaster table ------------------------
    slots_checked = 0
    for lang in ("en", "fr"):
        path = pdf_path(lang)
        if path is None:
            continue
        pages = extract.pages_pymupdf(path)
        grid = multiclass_from_pages(pages, MULTICLASS_HEADING[lang])
        assert len(grid) == 20, (lang, len(grid))
        records = en if lang == "en" else fr
        full = [d for d in records.values() if d["spell_slot_levels"] == 9]
        half = [d for d in records.values() if d["spell_slot_levels"] == 5]
        assert len(full) == 5 and len(half) == 2, (lang, len(full), len(half))
        for data in full:
            for entry in data["levels"]:
                assert entry["spell_slots"] == grid[entry["level"] - 1], (
                    "%s/%s level %d: %r against the multiclass table's %r"
                    % (lang, data["name"], entry["level"], entry["spell_slots"],
                       grid[entry["level"] - 1]))
                slots_checked += 9
        for data in half:
            for entry in data["levels"]:
                caster = grid[(entry["level"] + 1) // 2 - 1][:5]
                assert entry["spell_slots"] == caster, (
                    "%s/%s level %d: %r against ceil(N/2) of the multiclass "
                    "table, %r" % (lang, data["name"], entry["level"],
                                   entry["spell_slots"], caster))
                slots_checked += 5
    if slots_checked:
        print("  ok  %d spell-slot values match the SRD's own Multiclass "
              "Spellcaster table, in both languages" % slots_checked)

    # -- WITNESS 1: poppler, reading the printed geometry -------------------
    total = 0
    skipped = []
    for lang, records in (("en", en), ("fr", fr)):
        checked = check_witness(lang, records)
        if checked is None:
            skipped.append(lang)
        else:
            total += checked
    if skipped:
        print("  SKIP poppler witness: the pinned PDF is absent for %s"
              % ", ".join(skipped))
    else:
        print("  ok  %d cells match poppler's own laid-out rendering of the "
              "same tables, column order included" % total)

    # -- the class cross-reference must resolve -----------------------------
    for lang, records in (("en", en), ("fr", fr)):
        classes = load(lang, "class")
        for name, data in records.items():
            assert data["class"] == canon.record_id(
                "srd", "class", lang, canon.slugify(name)), (lang, name)
            assert name in classes, (lang, name)
    print("  ok  every progression record points at a class record that exists")

    # -- WITNESS 4: the feature names, against the class records ------------
    # This is what makes splitting the Class Features cell on ", " a
    # measurement rather than a guess. Every name produced by that split must
    # be a feature heading the class grammar already read from the chapter
    # prose -- a different pass over different pages. A future printing that
    # puts a comma inside a feature name breaks this, loudly, instead of
    # halving the name in silence.
    resolved = 0
    for lang, records in (("en", en), ("fr", fr)):
        classes = load(lang, "class")
        placeholder = ("Subclass feature" if lang == "en"
                       else "Aptitude de sous-classe")
        for name, data in records.items():
            headings = {f["name"] for f in classes[name]["features"]}
            headings |= {f["name"] for f in classes[name]["subclass"]["features"]}
            for entry in data["levels"]:
                for feature in entry["features"]:
                    if feature == placeholder or feature in KNOWN_NAME_GAPS[lang]:
                        continue
                    assert (feature in headings
                            or _TRAILING_PAREN.sub("", feature) in headings), (
                        "%s/%s level %d: %r matches no feature heading"
                        % (lang, name, entry["level"], feature))
                    resolved += 1
    print("  ok  %d feature names resolve against the class records' own headings"
          % resolved)

    # -- NEGATIVE CONTROL: the poppler witness can actually fail ------------
    path = pdf_path("en")
    if path is not None:
        broken = json.loads(json.dumps(en["Wizard"]))
        broken["_page"] = en["Wizard"]["_page"]
        broken["levels"][2]["spell_slots"][1] = 9
        failed = False
        try:
            check_witness("en", {"Wizard": broken})
        except AssertionError:
            failed = True
        assert failed, "a witness that cannot fail cannot pass"
        print("  ok  negative control: one altered slot count fails the poppler witness")

    print("PASS test_class_progression_witness")


if __name__ == "__main__":
    main()
