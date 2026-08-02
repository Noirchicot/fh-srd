"""Fetch a pinned source, or pin it for the first time.

Two modes, deliberately separate:

    python3 src/fetch_source.py srd-5.2.1-fr
        Download and verify against the existing pin. Refuses on mismatch.

    python3 src/fetch_source.py --pin srd-5.2.1-fr
        Download and WRITE the pin. This is the only path that changes what the
        pipeline considers canonical, so it is explicit and it prints what it
        recorded.

Re-pinning is not a routine refresh. Wizards of the Coast reissued the French
PDF in December 2025 under the same version number, 5.2.1 — so "same version"
does not mean "same bytes", and a new file can move content in or out of the
CC-BY subset. That is a licensing change. Read the diff, then decide.
"""

import argparse
import json
import os
import sys
import urllib.request

import canon
import sources


def _download(url, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "fh-srd/1.0"})
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as out:
        headers = dict(resp.headers)
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
    return headers


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_id")
    parser.add_argument(
        "--pin",
        action="store_true",
        help="write the observed sha256 into sources.lock.json",
    )
    args = parser.parse_args(argv)

    src = sources.get(args.source_id)
    dest = os.path.join(sources.ROOT, src["file"])

    print("source : %s" % src["id"])
    print("url    : %s" % src["url"])
    print("dest   : %s" % src["file"])

    headers = _download(src["url"], dest)
    digest = canon.sha256_file(dest)
    size = os.path.getsize(dest)

    print("sha256 : %s" % digest)
    print("bytes  : %d" % size)
    print("etag   : %s" % headers.get("ETag", "—"))

    if src.get("sha256"):
        if digest != src["sha256"]:
            print(
                "\nREFUSED: this file does not match the pin.\n"
                "  pinned %s\n  actual %s\n"
                "  Upstream changed, or the local copy was touched. Do not re-pin\n"
                "  without reading what moved: content can cross the SRD boundary\n"
                "  between two reissues of the same version number." % (src["sha256"], digest),
                file=sys.stderr,
            )
            return 1
        print("\nmatches the existing pin.")
        return 0

    if not args.pin:
        print(
            "\nThis source has no pin yet. Nothing was recorded.\n"
            "  Re-run with --pin to make these bytes canonical.",
            file=sys.stderr,
        )
        return 2

    with open(sources.LOCK, "r", encoding="utf-8") as fh:
        lock = json.load(fh)
    for entry in lock["sources"]:
        if entry["id"] == args.source_id:
            entry["sha256"] = digest
            entry["bytes"] = size
            if headers.get("ETag"):
                entry["etag"] = headers["ETag"].strip('"')
            if headers.get("Last-Modified"):
                entry["last_modified"] = headers["Last-Modified"]
    with open(sources.LOCK, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(lock, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("\npinned in sources/sources.lock.json — commit this change.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
