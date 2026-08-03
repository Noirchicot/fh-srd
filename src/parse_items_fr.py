"""Magic item parser for the French SRD 5.2.1.

CALIBRATED against the pinned FR PDF on 2026-08-03, "Objets magiques de A à
Z" (p.220-266, inside the wider "Objets magiques" chapter p.215-266). Ported
from `parse_items_en.py` rather than reinvented -- same continuous-stream
approach, same page-transition-closes-a-field guard, same "next line also
looks like a type line" false-head guard, same discipline that an unparsed
block becomes an `unparsed` exclusion, never a half-filled record.

NOT A TRANSLATED HEAD SHAPE -- measured, not assumed. The category word is
SINGULAR in an entry's own head line ("Anneau, rare", "Objet merveilleux,
peu courant") even though the "Catégories d'objets magiques" table (p.215)
lists all nine in the PLURAL ("Anneaux", "Armes", "Armures", "Baguettes",
"Bâtons", "Objets merveilleux", "Parchemins", "Potions", "Sceptres"). The
nine categories map onto EN's nine one-for-one: Anneau=Ring, Arme=Weapon,
Armure=Armor, Baguette=Wand, Bâton=Staff, Objet merveilleux=Wondrous Item,
Parchemin=Scroll, Potion=Potion, Sceptre=Rod.

THE EN "+1, +2, OR +3" FALSE-HEAD TRAP DOES NOT REPRODUCE IN FRENCH, and
that is worth recording rather than silently carrying over EN's exact
guard unexamined. In English, a generic item's own NAME ("Armor, +1, +2,
or +3") happens to contain a comma right after the category word, so it
accidentally matches the type-line shape itself and sits directly above
the REAL type line with nothing to tell them apart except "the next line
is ALSO shaped like a head". In French the equivalent name reads "Arme +1,
+2 ou +3" -- no comma directly after the category word, because the French
phrasing puts the "+1, +2 ou +3" straight after "Arme" with a space, not a
comma -- so it fails `TYPE_HEAD` outright and is read as an ordinary name
line. Checked exhaustively: zero pairs of consecutive lines both matching
`TYPE_HEAD` exist anywhere in this chapter. The guard is kept anyway (cheap
insurance, matches the EN parser's own discipline), but it earns its keep
differently here: defensive, not load-bearing.

ATTUNEMENT reads "Harmonisation requise" (bare, or "Harmonisation requise
avec un/une <classes>" for a restricted grant -- FR's "avec" where EN uses
"by"). The clause wraps across a line break routinely ("Harmonisation
requise\navec un Clerc ou Paladin"), so it is searched across the whole
joined head text exactly like EN's own "Requires Attunement" search, not
line-by-line.

`rarity` is kept as the source's own text, the same call already made for
a spell's `components` and now ported unchanged: a single entry can name
several rarities tied to different bonuses ("peu courante (+1), rare (+2)
ou très rare (+3)"), and forcing that into one enum value would fabricate
structure the source does not commit to.

TWO GENUINE FR-SPECIFIC TRAPS, found by a count mismatch against EN (247 vs
253, all six missing from Armure/Arme -- 3 each) and confirmed by reading
the raw lines, not assumed from EN's own head shape:

1. **The comma before the rarity word is not always there.** "Armure
   (armure de cuir clouté) rare" (Armure de cuir clouté enchantée) has a
   bare space where every other entry in the chapter has a comma. A
   wording inconsistency in Wizards' own PDF, the same class of one-off
   already documented for EN's "Component:"/"Components:" split -- not a
   scanning artefact (reads the same under both extractors). Fixed by
   making the comma OPTIONAL rather than required, but only safely so
   because the rarity text itself is anchored to a closed, known set of
   opening words (`_RARITY_START`) -- an ordinary name line's second word
   is never "rare" or "courante", so this does not open the door to a
   prose line being mistaken for a type line.
2. **The subtype parenthetical itself can wrap onto a second line BEFORE
   its closing paren**, something no EN item does: "Armure (intermédiaire
   ou lourde, sauf armure de" / "peaux), peu courante" (Armure de mithral,
   Armure en adamantium) -- the French phrasing for "Any Medium or Heavy,
   but Not Hide" is long enough to overflow one line where English's is
   not. `_head_match` joins up to two extra lines whenever the open/close
   paren count is unbalanced, mirroring the level-line wrap already used
   for spells, before attempting `TYPE_HEAD` -- so a head is found whether
   its subtype clause needed one line or two.

NOT ATTEMPTED HERE, same limitation as EN and for the same reason: the
random tables embedded inside item descriptions (Miscibilité des potions,
etc.) are swept into `description` as prose in whatever reading order the
page's two-column layout produces them.
"""

import re

import canon
from parse_spells import _dehyphenate_numbered

CATEGORIES = {
    "Anneau": "ring",
    "Arme": "weapon",
    "Armure": "armor",
    "Baguette": "wand",
    "Bâton": "staff",
    "Objet merveilleux": "wondrous-item",
    "Parchemin": "scroll",
    "Potion": "potion",
    "Sceptre": "rod",
}
_CATEGORY_ALT = "|".join(re.escape(c) for c in sorted(CATEGORIES, key=len, reverse=True))

# "Anneau, rare (Harmonisation requise)"
# "Armure (armure d'écailles), très rare (Harmonisation requise)"
# "Arme (courante ou de guerre), peu courante (+1), rare (+2) ou très rare (+3)"
# "Parchemin, rareté variable"
# "Armure (armure de cuir clouté) rare"                 (no comma -- see docstring)
#
# The comma before the rarity clause is OPTIONAL: safe only because
# `_RARITY_START` anchors the rarity group to a closed, known set of
# opening words, so a bare name line's own words never satisfy it.
#
# "courante?" and "peu courante?" cover BOTH genders: "Objet merveilleux,
# peu courant" (masculine, Objet) vs "Baguette, peu courante" (feminine,
# Baguette) -- missing the masculine form silently lost every Common/
# Uncommon wondrous item head, the same class of mistake already guarded
# against in the spell parser's cantrip gender agreement. "Artefact" is
# capitalised in its one real occurrence in the chapter ("Objet
# merveilleux, Artefact (Harmonisation requise)", the Deck of Many
# Things' orbs) where every other rarity word in the document is not --
# another one-off wording inconsistency in Wizards' own PDF, so both
# cases are matched rather than assumed lowercase.
_RARITY_START = (
    r"(?:[Pp]eu courante?|[Tt]rès rare|[Rr]areté variable|[Cc]ourante?|"
    r"[Rr]are|[Ll]égendaire|[Aa]rtefact)"
)
TYPE_HEAD = re.compile(
    r"^(?P<category>%s)\s*(?:\((?P<subtype>[^)]*)\))?\s*,?\s*(?P<rarity>%s.*)$"
    % (_CATEGORY_ALT, _RARITY_START)
)

ATTUNEMENT = re.compile(r"Harmonisation requise", re.IGNORECASE)


def _head_match(stripped, i, end):
    """Try TYPE_HEAD at line i, joining up to two more lines if a single
    line does not resolve to a full match. Returns (match, joined_text,
    extra) where `extra` is how many lines beyond i were consumed for the
    head itself; (None, stripped[i], 0) if no head is found here.

    Two DISTINCT wrap shapes are covered by the SAME retry loop, not two
    separate rules -- both found by a count mismatch against EN (see
    module docstring, traps 1 and 2), neither guessable from the other:

    1. The subtype parenthetical itself can wrap onto a second line
       BEFORE its closing paren -- "Armure (intermédiaire ou lourde,
       sauf armure de" / "peaux), peu courante" (Armure de mithral). This
       one alone would be caught by only joining while parens are
       unbalanced.
    2. The rarity word can wrap onto a THIRD line even after the subtype
       paren closes cleanly and a comma is already present -- "Armure
       (légère, intermédiaire ou lourde)," / "rare (Harmonisation
       requise)" (Armure de vulnérabilité). Here the parens are already
       balanced after line one, so a paren-count guard alone never
       triggers a retry, and this item was silently dropped -- no
       anomaly, because a line ending right after a bare comma is not a
       malformed head, it is simply not a head YET. Retrying unconditionally
       (bounded to two extra lines, still gated by `TYPE_HEAD`'s own
       `_RARITY_START` anchor so ordinary prose never matches) catches
       both shapes with one mechanism instead of two special cases.
    """
    text = stripped[i]
    m = TYPE_HEAD.match(text)
    if m:
        return m, text, 0
    extra = 0
    while extra < 2 and i + extra + 1 < end and stripped[i + extra + 1]:
        extra += 1
        text = text + " " + stripped[i + extra]
        m = TYPE_HEAD.match(text)
        if m:
            return m, text, extra
    return None, stripped[i], 0

CHAPTER_START = "Objets magiques de A à Z"
CHAPTER_END = "Monstres"


def parse_stream(text, page_of):
    lines = [l.strip("\n") for l in text.split("\n")]
    items, anomalies = [], []

    def page_at(i):
        return page_of[i] if i < len(page_of) else (page_of[-1] if page_of else 0)

    stripped = [l.strip() for l in lines]

    chapter_start = 0
    for i, l in enumerate(stripped):
        if l == CHAPTER_START:
            chapter_start = i
            break

    chapter_end = len(lines)
    for i, l in enumerate(stripped):
        if i > chapter_start and l == CHAPTER_END:
            chapter_end = i
            break

    head_info = {}
    for i in range(chapter_start + 1, chapter_end):
        m, joined_text, extra = _head_match(stripped, i, chapter_end)
        if m:
            head_info[i] = (m, joined_text, extra)

    candidates = sorted(head_info)
    heads = [
        i for i in candidates
        if not (
            i + 1 + head_info[i][2] < len(stripped)
            and stripped[i + 1 + head_info[i][2]]
            and TYPE_HEAD.match(stripped[i + 1 + head_info[i][2]])
        )
    ]
    next_head = {}
    has_next_entry = {}
    for position, index in enumerate(heads):
        has_next = position + 1 < len(heads)
        following = heads[position + 1] if has_next else chapter_end
        next_head[index] = min(following, chapter_end)
        has_next_entry[index] = has_next and next_head[index] == following

    heads_set = set(heads)
    for idx, line in enumerate(stripped):
        if idx not in heads_set:
            continue
        head, head_first_line, head_extra = head_info[idx]

        # The rarity clause may wrap further still ("très rare
        # (Harmonisation\nrequise avec un Clerc...")) -- beyond whatever
        # lines `_head_match` already consumed to close the subtype paren.
        head_lines = [head_first_line]
        cursor = idx + head_extra
        while cursor < idx + head_extra + 3:
            nxt = cursor + 1
            if nxt >= len(stripped) or not stripped[nxt]:
                break
            head_lines.append(stripped[nxt])
            cursor = nxt
        head_text = " ".join(head_lines)

        # The name can wrap onto two lines when it is long. The wrapped
        # TAIL of a title starts lowercase; a real item name is always
        # Title Case at its first word.
        name_end = idx - 1
        while name_end >= 0 and not stripped[name_end]:
            name_end -= 1
        name_start = name_end
        if name_start >= 0 and name_start - 1 >= 0 and stripped[name_start][:1].islower():
            above = stripped[name_start - 1]
            if above:
                name_start -= 1
        name = " ".join(stripped[name_start:name_end + 1]) if name_end >= 0 else ""
        if not name or len(name) > 80 or name.endswith(":") or name.endswith(","):
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "implausible item name above %r: %r"
                           % (head_text[:60], name[:80])}
            )
            continue

        i = cursor + 1
        while i < len(stripped) and not stripped[i]:
            i += 1
        desc_end = next_head.get(idx, chapter_end)
        desc_lines = stripped[i:desc_end]
        end = len(desc_lines)
        while end > 0 and not desc_lines[end - 1]:
            end -= 1
        if has_next_entry.get(idx):
            if end > 0:
                end -= 1
                while end > 0 and not desc_lines[end - 1]:
                    end -= 1
        desc_lines = desc_lines[:end]
        paragraphs = []
        for chunk in "\n".join(desc_lines).split("\n\n"):
            joined = " ".join(l for l in chunk.split("\n") if l)
            if joined:
                paragraphs.append(joined)
        description = "\n\n".join(paragraphs)

        if not description:
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "item %r has a type line but no description text" % name}
            )
            continue

        items.append(
            {
                "name": name,
                "category": CATEGORIES[head.group("category")],
                "subtype": (head.group("subtype") or "").strip() or None,
                "rarity": re.sub(r"\s+", " ", head.group("rarity") + " "
                                  + " ".join(head_lines[1:])).strip(),
                "attunement": bool(ATTUNEMENT.search(head_text)),
                "description": description,
                "page": page_at(name_start),
            }
        )

    return items, anomalies


def parse(pages, suspect_pages=()):
    suspect = set(suspect_pages)

    numbered = []
    for number, raw in enumerate(pages, start=1):
        for line in raw.split("\n"):
            numbered.append((number, line))

    numbered = _dehyphenate_numbered(numbered)

    stream = "\n".join(l for _, l in numbered)
    page_of = [n for n, _ in numbered]

    found, anomalies = parse_stream(stream, page_of)

    items, conflicts = [], []
    for item in found:
        if item["page"] in suspect:
            conflicts.append(
                {"page": item["page"], "name": item["name"],
                 "detail": "page text disputed between PyMuPDF and pdftotext"}
            )
        else:
            items.append(item)

    items.sort(key=lambda it: canon.slugify(it["name"]))
    return items, anomalies, conflicts
