"""Canonical forms: slugs, identifiers, hashes, JSON.

Every value the pipeline writes passes through here. That is what makes a
replay produce the same bytes: there is exactly one way to render a slug, one
way to render JSON, one way to derive an id.

Nothing in this module reads the clock, the environment, the filesystem, or a
random source.
"""

import hashlib
import json
import re
import unicodedata

# Bumped whenever a change here would alter the bytes of an existing export.
# It is part of the import run's identity, so a pipeline change is visible in
# the ledger rather than silently reshaping records.
PIPELINE_VERSION = "1.0.0"

_NON_SLUG = re.compile(r"[^a-z0-9]+")


def slugify(text):
    """'Boule de Feu' -> 'boule-de-feu'; 'Épée à deux mains' -> 'epee-a-deux-mains'.

    NFD-decompose, drop combining marks, lowercase, collapse the rest. French
    accents are stripped rather than transliterated: 'é' and 'e' must not
    produce two different identifiers for the same word.
    """
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    # Keep the ligatures French actually uses; NFD does not decompose them.
    stripped = stripped.replace("œ", "oe").replace("Œ", "OE")
    stripped = stripped.replace("æ", "ae").replace("Æ", "AE")
    slug = _NON_SLUG.sub("-", stripped.lower()).strip("-")
    if not slug:
        raise ValueError("slugify produced an empty slug for %r" % (text,))
    return slug


def canonical_json(value, indent=None):
    """The only JSON writer in the pipeline.

    sort_keys makes dict ordering irrelevant. ensure_ascii=False keeps French
    text readable in a diff instead of turning it into \\u escapes. The
    separators are pinned so a Python upgrade cannot change the spacing.
    """
    if indent is None:
        return json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        )
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, indent=indent, separators=(",", ": ")
    )


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def content_hash(kind, lang, name, data):
    """Identity of a record's *content*, independent of where it was found.

    Two extraction runs that read the same rule from the same page produce the
    same hash; a run that reads it from a different page still does.
    """
    payload = canonical_json(
        {"kind": kind, "lang": lang, "name": name, "data": data}
    )
    return sha256_text(payload)


def record_id(layer, kind, lang, slug):
    """The id spells out its own layer.

    Once a record is in a JSON export, on a web page, or in someone's notes,
    `srd:spell:fr:boule-de-feu` still says which layer it came from. An
    integer key would not, and that is the whole legal question.
    """
    return "%s:%s:%s:%s" % (layer, kind, lang, slug)


def resolve_slug_collisions(candidates):
    """Disambiguate records whose names slugify to the same string.

    `candidates` is a list of dicts carrying at least `slug` and
    `content_hash`. When N > 1 records collide, *all* of them take a
    `-<hash6>` suffix — not just the later ones.

    The reason is stability under re-import: if the winner kept the bare slug,
    then a record appearing upstream later would silently reassign identifiers
    that the FHPC already references. Suffixing everyone means a collision
    never moves an id that already existed, and the collision is reported as an
    exclusion-register anomaly rather than resolved in silence.

    Returns (resolved, collisions).
    """
    by_slug = {}
    for cand in candidates:
        by_slug.setdefault(cand["slug"], []).append(cand)

    resolved = []
    collisions = []
    for slug in sorted(by_slug):
        group = by_slug[slug]
        if len(group) == 1:
            resolved.append(group[0])
            continue
        for cand in sorted(group, key=lambda c: c["content_hash"]):
            out = dict(cand)
            out["slug"] = "%s-%s" % (slug, cand["content_hash"][:6])
            resolved.append(out)
            collisions.append(out)
    return resolved, collisions
