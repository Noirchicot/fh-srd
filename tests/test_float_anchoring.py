"""The witness for float anchoring: a table belongs to the entry that prints it.

`columns_of` reads a page in its PRINTED order. That is right for a table
printed under the entry it belongs to, and wrong for one that has floated to
the foot of the page past unrelated entries. EN p.210 prints the "Apparatus of
the Crab Levers" table full-width at the page foot; the Apparatus's own entry
fills the LEFT column, and the RIGHT column holds three other magic items. So
printed order appended a ten-row lever table to the last of them, and
`srd:item:en:armor-of-resistance` shipped 1581 characters of which 1294
belonged to a different item — on a public site, under CC-BY.

`extract.float_anchors` repairs the ANCHOR rather than the record: it re-anchors
a page-foot float to the entry the source says owns it, and it demands the
source say so TWICE — the caption begins with an entry head printed on the same
page (typography), and that entry's own prose names the caption ("functions as
shown in the Apparatus of the Crab Levers table").

FOUR CONFRONTATIONS, all re-derived from the pinned PDFs rather than from the
exports, so a hand-edited export cannot make this suite pass:

  1. **THE RULE, SWEPT.** Every full-width run on all 744 pages of both
     documents is put to the rule, and exactly one is re-anchored. The one is
     named. A sweep that re-anchored a second table without this suite naming
     it is a failure, not a detail.

  2. **BOTH SIGNALS ARE LOAD-BEARING.** The same sweep measures what each
     signal would do alone. Signal 1 alone fires 3 times and 2 are wrong (the
     Armor table's "Shield …" sub-category labels, which begin with the name of
     the Shield entry printed higher up). Signal 2 alone fires 24 times, and it
     is not merely noisy — FR p.91 "Héritages fiélons" is ALREADY correctly
     placed, and its cross-reference sits in the OTHER column, so acting on the
     reference would have moved that table into the middle of the record it
     already ends. A cross-reference says which table an entry uses; it does
     not say where the table is printed. Neither number may drift without
     someone reading this.

  3. **THE TWO RECORDS.** Rebuilt from the PDF: Armor of Resistance keeps its
     own 1d10 damage table and carries not one line of the Apparatus's; the
     Apparatus carries the whole lever table, all ten rows, in printed order,
     directly after the sentence that references it.

  4. **AN INDEPENDENT RENDERER.** Poppler's `pdftotext -layout` shares no code
     with MuPDF. It is asked to confirm what the repair assumes about EN p.210:
     the Apparatus entry, its cross-reference and the table's caption are all
     printed on that one page, the caption below the reference, and the three
     other item heads are printed there too — which is why printed order put
     the table on the wrong one.

⚠️ THIS SUITE FAILS WHEN IT CANNOT RUN. It does not skip. A test that exits 0
because its fixture is missing is a test that lies, and this repository has
already paid for that once.
"""

import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import extract  # noqa: E402
from parse_spells_en import _dehyphenate_numbered  # noqa: E402

PDFS = [
    ("en", os.path.join(ROOT, "sources", "pdf", "SRD_CC_v5.2.1.pdf")),
    ("fr", os.path.join(ROOT, "sources", "pdf", "FR_SRD_CC_v5.2.1.pdf")),
]

EXPORTS = os.path.join(ROOT, "exports", "srd")

# The one float the rule re-anchors, over both documents. Named, not counted.
EXPECTED_ANCHORED = [("en", 210, "Apparatus of the Crab Levers",
                      "Apparatus of the Crab")]

# What each signal would do on its own. Measured, and asserted so that a change
# to either one cannot pass unnoticed.
SIGNAL_1_ALONE = 3     # caption begins with an entry head on the same page
SIGNAL_2_ALONE = 24    # something above it names the caption in its prose

# Below this the sweep has not swept and says so.
MIN_RUNS = 60

CLEAN_ARMOR_OF_RESISTANCE = 285
LEVER_ROWS = 10


def require_sources():
    missing = [path for _lang, path in PDFS if not os.path.exists(path)]
    if missing:
        raise AssertionError(
            "the pinned PDFs are not present:\n  %s\n"
            "This suite re-derives the anchoring rule from the source bytes. "
            "Without them it can confront nothing, and a witness that cannot "
            "run must FAIL rather than pass quietly."
            % "\n  ".join(missing)
        )


def require_exports():
    missing = [p for p in (os.path.join(EXPORTS, "en", "item.json"),)
               if not os.path.exists(p)]
    if missing:
        raise AssertionError(
            "the exports are not present:\n  %s\nRun `python3 src/build.py`."
            % "\n  ".join(missing))


def flat(text):
    return re.sub(r"\s+", " ", extract.normalise(text)).strip()


# ---------------------------------------------------------------------------
# 1 and 2: the rule and its two signals, swept over every run in both PDFs.
# ---------------------------------------------------------------------------

def sweep(fitz):
    """(re-anchored, signal-1-only hits, signal-2-only hits, runs examined)."""
    anchored, only_1, only_2, runs_seen = [], [], [], 0
    for lang, path in PDFS:
        doc = fitz.open(path)
        try:
            for number, page in enumerate(doc, start=1):
                blocks = page.get_text("blocks")
                runs, left, right = extract._runs(
                    blocks, page.rect.width, page.rect.height, 0.93,
                    extract.RUN_GAP, extract.GROW_GAP)
                if not runs:
                    continue
                heads = extract.entry_heads(page)
                for run in runs:
                    runs_seen += 1
                    caption = flat(
                        extract.normalise(run[0][4]).split("\n")[0])
                    if len(caption) < extract.MIN_CAPTION:
                        continue
                    top = min(b[0] for b in run)
                    bottom = max(b[2] for b in run)
                    foot = not any(b[0] >= bottom for b in left + right)
                    above = [b for b in left + right if b[2] <= top]

                    # Signal 1, on its own: the caption begins with the text of
                    # an entry head printed above it on the same page.
                    if foot and any(
                            (caption == h or caption.startswith(h + " "))
                            for b in above
                            for h in [extract._head_at(b, heads)]
                            if h and len(h) >= extract.MIN_CAPTION):
                        only_1.append((lang, number, caption))

                    # Signal 2, on its own: some entry above names the caption.
                    if foot and any(caption in flat(b[4]) for b in above):
                        only_2.append((lang, number, caption))

                # The rule itself, both signals together.
                for at, _side, _y in extract.float_anchors(page):
                    run = next(r for r in runs
                               if abs(min(b[0] for b in r) - at) < 0.01)
                    caption = flat(
                        extract.normalise(run[0][4]).split("\n")[0])
                    owner = next(
                        h for b in left + right
                        for h in [extract._head_at(b, heads)]
                        if h and (caption == h or caption.startswith(h + " ")))
                    anchored.append((lang, number, caption, owner))
        finally:
            doc.close()
    return anchored, only_1, only_2, runs_seen


# ---------------------------------------------------------------------------
# 3: the two records, as they come out of the build.
# ---------------------------------------------------------------------------

def item(lang, slug):
    with open(os.path.join(EXPORTS, lang, "item.json"), encoding="utf-8") as fh:
        records = json.load(fh)["records"]
    for record in records:
        if record["slug"] == slug:
            return record
    raise AssertionError("no srd:item:%s:%s in the exports" % (lang, slug))


def lever_rows(fitz):
    """The table's ten rows, read straight off EN p.210.

    Dehyphenated with the pipeline's OWN `_dehyphenate_numbered` rather than a
    second copy of the rule: the layout splits "bonuses" across a line as
    "bo-"/"nuses", and a witness that spelled its own un-splitting would be
    asserting against its own idea of the text instead of the parser's.
    """
    doc = fitz.open(PDFS[0][1])
    try:
        page = doc[209]
        blocks = page.get_text("blocks")
        runs, _l, _r = extract._runs(
            blocks, page.rect.width, page.rect.height, 0.93,
            extract.RUN_GAP, extract.GROW_GAP)
        run = next(r for r in runs
                   if flat(extract.normalise(r[0][4]).split("\n")[0])
                   == "Apparatus of the Crab Levers")
        rows = []
        for block in run[1:]:
            lines = [l for l in extract.normalise(block[4]).split("\n") if l]
            merged = _dehyphenate_numbered([(210, l) for l in lines])
            text = flat(" ".join(l for _p, l in merged))
            if re.match(r"^\d+ ", text):
                rows.append(text)
        return rows
    finally:
        doc.close()


# ---------------------------------------------------------------------------
# 4: poppler, which shares no code with MuPDF.
# ---------------------------------------------------------------------------

def poppler_page(path, number):
    out = subprocess.run(
        ["pdftotext", "-layout", "-enc", "UTF-8",
         "-f", str(number), "-l", str(number), path, "-"],
        capture_output=True, text=True, check=True,
    )
    return [extract.normalise(line) for line in out.stdout.split("\n")]


def sole_index(lines, needle):
    hits = [i for i, line in enumerate(lines) if needle in line]
    assert len(hits) == 1, (
        "poppler prints %r %d times on this page; the witness needs it once"
        % (needle, len(hits)))
    return hits[0]


def main():
    require_sources()
    require_exports()
    extract.extractor_id()      # refuses on an unpinned MuPDF
    extract.cross_checker_id()  # refuses on an unpinned poppler
    fitz = extract._pymupdf()

    # -- 1. the rule, swept --------------------------------------------------
    anchored, only_1, only_2, runs_seen = sweep(fitz)
    assert runs_seen >= MIN_RUNS, (
        "only %d full-width runs were examined (floor is %d). The sweep ran "
        "and found almost nothing to put to the rule, which is a failure."
        % (runs_seen, MIN_RUNS))
    assert anchored == EXPECTED_ANCHORED, (
        "the set of re-anchored floats is %r, expected %r.\n"
        "Every table this rule moves changes a published record, so each one "
        "has to be named here by somebody who looked at it."
        % (anchored, EXPECTED_ANCHORED))
    print("  ok  rule: %d full-width runs over 2 documents, exactly 1 "
          "re-anchored: %s p.%d %r -> %r"
          % (runs_seen, anchored[0][0], anchored[0][1],
             anchored[0][2], anchored[0][3]))

    # -- 2. both signals are load-bearing ------------------------------------
    assert len(only_1) == SIGNAL_1_ALONE, (
        "signal 1 alone now fires %d times, expected %d: %r"
        % (len(only_1), SIGNAL_1_ALONE, only_1))
    assert len(only_2) == SIGNAL_2_ALONE, (
        "signal 2 alone now fires %d times, expected %d: %r"
        % (len(only_2), SIGNAL_2_ALONE, only_2))
    # The specific counter-examples, named: dropping either signal is wrong.
    shields = [c for _l, _p, c in only_1
               if c not in [a[2] for a in EXPECTED_ANCHORED]]
    assert len(shields) == 2, shields
    assert all("Shield" in c or "Bouclier" in c for c in shields), shields
    assert ("fr", 91, "Héritages fiélons") in only_2, (
        "FR p.91 no longer trips signal 2. That case is the reason signal 2 "
        "cannot stand alone — it is a correctly placed table whose entry "
        "cross-references it from the other column — and the witness has lost "
        "its counter-example.")
    print("  ok  signals: 1 alone fires %d (2 of them wrong: %s), 2 alone "
          "fires %d (including FR p.91 'Héritages fiélons', already correctly "
          "placed); together, 1"
          % (len(only_1), " / ".join(c[:34] for c in shields), len(only_2)))

    # -- 3. the two records --------------------------------------------------
    rows = lever_rows(fitz)
    assert len(rows) == LEVER_ROWS, (
        "read %d lever rows off EN p.210, expected %d" % (len(rows), LEVER_ROWS))

    armor = item("en", "armor-of-resistance")["data"]["description"]
    for row in rows:
        assert row not in flat(armor), (
            "srd:item:en:armor-of-resistance still carries a lever row: %r" % row)
    assert "Apparatus" not in armor, (
        "srd:item:en:armor-of-resistance still names the Apparatus")
    assert len(armor) == CLEAN_ARMOR_OF_RESISTANCE, (
        "srd:item:en:armor-of-resistance is %d characters, expected %d. Its "
        "own 1d10 damage table IS its own — it is printed in its own column, "
        "under its own sentence — so the clean record is not the bare prose."
        % (len(armor), CLEAN_ARMOR_OF_RESISTANCE))

    apparatus = item("en", "apparatus-of-the-crab")["data"]["description"]
    at = -1
    for row in rows:
        found = flat(apparatus).find(row)
        assert found > at, (
            "srd:item:en:apparatus-of-the-crab is missing lever row %r, or "
            "prints it out of order" % row)
        at = found
    reference = flat(apparatus).find(
        "functions as shown in the Apparatus of the Crab Levers table")
    caption = flat(apparatus).find("Apparatus of the Crab Levers table.") + 1
    assert reference > 0 and caption > reference, (
        "the table no longer follows the sentence that references it")
    print("  ok  records: armor-of-resistance %d chars and not one lever row; "
          "apparatus-of-the-crab carries all %d rows, in order, after its own "
          "cross-reference" % (len(armor), LEVER_ROWS))

    # -- 4. an independent renderer ------------------------------------------
    rendered = poppler_page(PDFS[0][1], 210)
    # Poppler lays the two columns side by side, so one rendered line can carry
    # a head from each. The Apparatus's head shares its line with "Armor, +1,
    # +2, or +3"; what matters is the ORDER of the lines, not their contents.
    subtitle = sole_index(rendered, "Wondrous Item, Legendary")
    head = next(i for i, line in enumerate(rendered)
                if "Apparatus of the Crab" in line)
    assert subtitle == head + 1, (
        "poppler does not print 'Wondrous Item, Legendary' under the Apparatus "
        "head (%d, %d)" % (head, subtitle))
    ref = sole_index(rendered, "functions as shown in the Apparatus of the Crab")
    caption_lines = [i for i, line in enumerate(rendered)
                     if line.strip() == "Apparatus of the Crab Levers"]
    assert len(caption_lines) == 1, (
        "poppler prints the caption on its own line %d times, expected once"
        % len(caption_lines))
    cap = caption_lines[0]
    assert head < ref < cap, (
        "poppler does not print the Apparatus entry, then its cross-reference, "
        "then the table caption, in that order on p.210 (%d, %d, %d)"
        % (head, ref, cap))
    # And the reason printed order picked the wrong owner: three other item
    # heads are printed on this page between the Apparatus and its table.
    others = [sole_index(rendered, name) for name in
              ("Armor, +1, +2, or +3", "Armor of Invulnerability",
               "Armor of Resistance")]
    assert all(head <= other < cap for other in others), (
        "poppler does not put the three other item heads between the Apparatus "
        "and its table on p.210 (%r), which is the whole reason this repair is "
        "needed and the witness has lost it" % (others,))
    print("  ok  poppler: p.210 prints the Apparatus entry, its reference and "
          "the caption in that order, with three unrelated item heads in "
          "between — which is why printed order picked the wrong owner")

    # -- NEGATIVE CONTROL ----------------------------------------------------
    # Prove the rule can say no: strip the cross-reference from the page's own
    # blocks and the same float must stop being re-anchored.
    doc = fitz.open(PDFS[0][1])
    try:
        page = doc[209]
        blocks = page.get_text("blocks")
        runs, left, right = extract._runs(
            blocks, page.rect.width, page.rect.height, 0.93,
            extract.RUN_GAP, extract.GROW_GAP)
        heads = extract.entry_heads(page)
        run = next(r for r in runs
                   if flat(extract.normalise(r[0][4]).split("\n")[0])
                   == "Apparatus of the Crab Levers")
        assert extract._anchor_of(run, left, right, heads) is not None
        muted = [b[:4] + (b[4].replace("Levers table", "levers"),)
                 if isinstance(b[4], str) else b for b in left]
        assert extract._anchor_of(run, muted, right, heads) is None, (
            "the float is still re-anchored with the printed cross-reference "
            "removed, so the rule is not resting on signal 2 and this witness "
            "is not measuring what it claims to")
    finally:
        doc.close()
    print("  ok  negative control: with the cross-reference muted, the same "
          "float is left where the page prints it")

    print("PASS test_float_anchoring")


if __name__ == "__main__":
    main()
