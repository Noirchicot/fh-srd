"""The web build's actual promises, checked against the built HTML.

Four things the FHPC (and Eric) are entitled to rely on:

  1. URL contract: `web/{lang}/{kind}/index.html`, one file per (lang, kind) —
     frozen, because the Player Companion links directly to this shape.
  2. Every record in `exports/srd/{lang}/{kind}.json` appears on its page
     exactly once, anchored at `id="{slug}"` — no record silently dropped or
     duplicated by the render step.
  3. Attribution is present on every page, in the page's own language — the
     condition the SRD layer's licence is published under.
  4. Zero external resources: no `<script src=`, `<link>`, `<img>`, or
     `<iframe>` pointing anywhere — the site must render offline, with no
     CDN, no remote font, nothing for a strict CSP to block.
"""

import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import build_web  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH = os.path.join(ROOT, "build", "web-contract")
EXPORTS = os.path.join(ROOT, "exports", "srd")

RECORD_ID_RE = re.compile(r'<article class="record" id="([^"]+)"')
EXTERNAL_TAG_RE = re.compile(
    r"<(script[^>]*\bsrc=|link\b|img\b|iframe\b|embed\b|object\b)", re.IGNORECASE
)
CSS_IMPORT_RE = re.compile(r"@import", re.IGNORECASE)


def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def main():
    shutil.rmtree(SCRATCH, ignore_errors=True)
    counts = build_web.build(SCRATCH, EXPORTS)

    total_records = 0
    total_pages = 0

    for lang in build_web.LANGS:
        for kind in build_web.KINDS:
            # -- 1. URL contract -------------------------------------------
            page_path = os.path.join(SCRATCH, lang, kind, "index.html")
            assert os.path.isfile(page_path), "missing contract path %s/%s/index.html" % (lang, kind)
            text = read(page_path)
            total_pages += 1

            with open(os.path.join(EXPORTS, lang, kind + ".json"), encoding="utf-8") as fh:
                payload = json.load(fh)
            records = payload["records"]
            expected_slugs = [r["slug"] for r in records]

            # -- 2. every record present exactly once, anchored at its slug -
            found_ids = RECORD_ID_RE.findall(text)
            assert len(found_ids) == len(records), (
                "%s/%s: found %d record anchors, expected %d"
                % (lang, kind, len(found_ids), len(records))
            )
            assert len(found_ids) == len(set(found_ids)), (
                "%s/%s: duplicate anchors: %s" % (lang, kind, sorted(
                    x for x in set(found_ids) if found_ids.count(x) > 1
                ))
            )
            assert sorted(found_ids) == sorted(expected_slugs), (
                "%s/%s: anchor set does not match record slugs" % (lang, kind)
            )
            for slug in expected_slugs:
                assert ('id="%s"' % slug) in text, "%s/%s: slug %s not anchored" % (lang, kind, slug)
                assert ('href="#%s"' % slug) in text, "%s/%s: slug %s has no self-link" % (lang, kind, slug)

            # -- 3. attribution present, in the page's own language ---------
            assert records, "%s/%s: no records to source an attribution from" % (lang, kind)
            attribution = records[0]["attribution"]
            assert text.count(attribution) == 1, (
                "%s/%s: attribution paragraph should appear exactly once, found %d"
                % (lang, kind, text.count(attribution))
            )
            assert "CC BY 4.0" in text and build_web.CC_BY_URL in text, (
                "%s/%s: missing CC BY 4.0 licence link" % (lang, kind)
            )
            # The strict-SRD wording decision: no non-affiliation disclaimer.
            lowered = text.lower()
            assert "endorsed" not in lowered and "approuv" not in lowered, (
                "%s/%s: a non-affiliation/endorsement line was added; SRD wording must stay verbatim"
                % (lang, kind)
            )

            # -- 4. zero external resources ----------------------------------
            bad = EXTERNAL_TAG_RE.findall(text)
            assert not bad, "%s/%s: external-resource tag(s) found: %s" % (lang, kind, bad)
            assert not CSS_IMPORT_RE.search(text), "%s/%s: @import in inline CSS" % (lang, kind)

            total_records += len(records)

    print("  ok  %d pages match the URL contract" % total_pages)
    print("  ok  %d records total, each anchored exactly once at its slug" % total_records)
    print("  ok  attribution (verbatim SRD wording, no endorsement line) present on every page")
    print("  ok  zero external resource tags across every page")

    # -- root index links to every kind page, in both languages -------------
    root_text = read(os.path.join(SCRATCH, "index.html"))
    for lang in build_web.LANGS:
        for kind in build_web.KINDS:
            href = "%s/%s/index.html" % (lang, kind)
            assert href in root_text, "root index missing link to %s" % href
    print("  ok  root index links to all %d category pages" % (len(build_web.LANGS) * len(build_web.KINDS)))

    assert counts, "build() returned no counts"
    shutil.rmtree(SCRATCH, ignore_errors=True)
    print("PASS test_web_contract")


if __name__ == "__main__":
    main()
