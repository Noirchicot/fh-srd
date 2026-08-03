"""Monster (stat block) parser for the English SRD 5.2.1.

CALIBRATED against the pinned EN PDF on 2026-08-03, "Monsters A-Z"
(p.258-364, the rest of the book -- Monsters is the SRD's last chapter).
330 monsters, cross-checked against the document's OWN "Index of Stat
Blocks" (the alphabetical name/page list on p.3-4 of the PDF, part of its
front matter): every one of the 330 names this parser found matches the
index exactly, and the index's own two non-monster rows ("Monsters A-Z"
and "Animals" are chapter/section dividers formatted the same way as a
real entry) are excluded, not counted as missing. The community-Markdown
source in sources.lock.json claims only 235 -- this parser's count comes
from reading the PDF itself, which is the authority the lock file already
names it as.

THE HEAD IS NOT THE MONSTER'S NAME -- IT IS THE SIZE/TYPE/ALIGNMENT LINE
right after it ("Large Aberration, Lawful Evil"), the same discipline
already used for a spell's level line or a feat's category line: a
mechanical, unique shape ("<Size>[ or <Size>] <CreatureType>[ (Swarm of
Tiny/Small <Type>)][ (<tags>)], <Alignment>") that cannot appear in
ordinary prose. Fourteen creature types, six sizes, and the "Swarm of Tiny/
Small <Type>" wording (itself pluralising the type word -- "Swarm of Tiny
Beasts", not "Beast") are all read directly off the "Creature Type" and
"Parts of a Stat Block" sections of this same chapter's own introduction,
not guessed.

THE MONSTER'S NAME IS DUPLICATED ABOVE ITS OWN HEAD, AND THAT DUPLICATION
IS NOT ALWAYS THERE -- measured, not assumed. Every entry that STARTS a
named family of related monsters carries a family-name line before the
member's own name (e.g. "Animated Objects" above "Animated Armor"); a
solo entry's "family" is trivially its own name repeated ("Aboleth" above
"Aboleth"); a LATER member of an already-open family has only its own
single name line (no repeat). All three shapes are handled by the same
rule -- the name is whatever non-blank line sits immediately above the
size/type line, however many other lines (or none) come before that.

THE ABILITY SCORE TABLE HAS NO RELIABLE LINE SHAPE AT ALL, and this is the
one place in the whole pipeline where the field-boundary rule is a token
count, not a line count. "Str 21 +5" carries the modifier inline; "Dex 9"
does not, because "-1" (a negative modifier) renders on its own physical
line where a positive one does not; "Wis 10 +0 +0" carries BOTH the
modifier and the save inline because zero is not negative; "Int 1" splits
to three separate lines when both its modifier and its save are negative.
No per-monster rule explains this except "PyMuPDF's column reader treats a
U+2212 MINUS SIGN glyph differently from a plain digit or a plus sign," an
inconsistency that varies row to row within the SAME stat block. The fix:
flatten the six-ability region into a flat token stream (splitting every
line on whitespace) and walk it positionally -- ability label, integer
score, signed modifier, signed save, six times over -- rather than trying
to say how many physical lines a row occupies.

TRAITS, ACTIONS, BONUS ACTIONS AND REACTIONS SHARE ONE GRAMMAR: a run of
"Name[ (parenthetical)]. Description" entries, blank-line separated --
structurally the same shape already solved for the Rules Glossary, and
the SAME trap applies. A multi-paragraph entry's own internal blank line
(Aboleth's "Mucus Cloud" trait runs two paragraphs) must not be mistaken
for a new entry, and this chapter has no alphabetical-order safety net the
glossary had (entries are grouped by narrative importance -- Multiattack
first -- not A to Z), so the ONLY signal is shape: a real entry's name
sits before the FIRST period within a short prefix (a length cap, checked
against every trait/action name in this chapter); a continuation
paragraph's first period sits much later, if there is one on the first
line at all. "Trigger:"/"Response:" (Reactions) and "Failure:"/"Success:"
(saving-throw effects) use a COLON, never a period, so they are never
mistaken for a new entry's head by this same rule.

LEGENDARY ACTIONS IS THE ONE SECTION THAT IS NOT JUST A LIST OF ENTRIES: it
opens with a fixed-prefix explanatory paragraph ("Legendary Action Uses:
<N>. Immediately after another creature's turn...") that would otherwise
be misread as an entry named "Legendary Action Uses: <N>" -- its own
prefix is short enough, and starts with a capital letter, to pass the
same name-shape check every other section's entries pass. Carved out by
its own fixed, literal opening words rather than folded in by the
name-shape heuristic, and kept as its own `intro` field; the true options
that follow it (Cloud of Insects, Frightful Presence, Pounce, ...) are
read exactly like a Traits or Actions entry.

A WORDING INCONSISTENCY IN WIZARDS' OWN PDF, not a scanning artefact,
verified against the rendered page rather than assumed: Young White
Dragon's Intelligence save prints as a bare "2" instead of "+2" (mod -2,
save +2, opposite signs) while every other ability row in the same stat
block, and the Wyrmling right above it on the same page, prints its sign
normally. The same class of one-off omission already documented for 12
spells' "Component:"/"Components:" split. `_SIGNED_RE` accepts an
unsigned integer as an implicitly positive value for exactly this reason,
rather than treating the missing sign as a parse failure.

TRAITS IS OPTIONAL (Animated Armor has none, going straight from CR to
Actions); BONUS ACTIONS, REACTIONS AND LEGENDARY ACTIONS are all optional
too, and their presence and order are not fixed -- each is looked for by
its own heading rather than assumed to fall in a particular slot.

WHAT STAYS AS THE SOURCE'S OWN RAW TEXT, the same call already made for a
magic item's rarity clause and a spell's components: size/type/tags/
alignment (a monster's own "or" alternation and "Swarm of Tiny X" phrasing
do not collapse into one clean enum without inventing structure the
source does not offer), AC/Initiative/HP/Speed, and every optional field
between the ability table and CR (Skills, Resistances, Vulnerabilities,
Immunities, Gear, Senses, Languages, CR) -- all kept as the label's own
text, read via a label scanner order-agnostic the way parse_tools_en.py's
Ability/Weight/Utilize/Craft/Variants sequence already is, because this
chapter's own "Parts of a Stat Block" section states outright that
several of them simply don't appear when a monster has nothing to put
there.
"""

import re

import canon
from parse_spells_en import _dehyphenate_numbered

SIZES = ["Tiny", "Small", "Medium", "Large", "Huge", "Gargantuan"]
CREATURE_TYPES = [
    "Aberration", "Beast", "Celestial", "Construct", "Dragon", "Elemental",
    "Fey", "Fiend", "Giant", "Humanoid", "Monstrosity", "Ooze", "Plant", "Undead",
]
_SIZE_ALT = "|".join(SIZES)
_TYPE_ALT = "|".join(CREATURE_TYPES)
_SWARM_ALT = r"Swarm of (?:Tiny|Small) (?:%s)s?" % _TYPE_ALT

# "Large Aberration, Lawful Evil" / "Large Dragon (Chromatic), Chaotic Evil" /
# "Medium or Small Humanoid, Neutral" / "Medium Swarm of Tiny Undead, Neutral Evil".
# Anchors on SIZE + TYPE only; tags and alignment are captured whole and kept
# as raw text (see module docstring).
TYPE_HEAD = re.compile(
    r"^(?:%s)(?:\s+or\s+(?:%s))?\s+(?:%s|%s)\b" % (_SIZE_ALT, _SIZE_ALT, _SWARM_ALT, _TYPE_ALT)
)
_TAGS_RE = re.compile(r"^(?P<base>.+?)\s\((?P<tags>[^)]+)\)$")

CHAPTER_START = "Monsters A–Z"

COMBAT_LABELS = ["AC", "Initiative", "HP", "Speed"]
_COMBAT_LABEL_RE = re.compile(r"^(%s)\s+(.*)$" % "|".join(COMBAT_LABELS))

ABILITIES = ["Str", "Dex", "Con", "Int", "Wis", "Cha"]
_ABILITY_HEADER = ["MOD SAVE", "MOD SAVE", "MOD SAVE"]
_SIGNED_RE = re.compile(r"^[+−-]?\d+$")
_TOKEN_RE = re.compile(r"\S+")

OTHER_LABELS = [
    "Skills", "Resistances", "Vulnerabilities", "Immunities", "Gear",
    "Senses", "Languages", "CR",
]
_OTHER_LABEL_RE = re.compile(r"^(%s)\s+(.*)$" % "|".join(OTHER_LABELS))

SECTION_HEADS = ["Traits", "Actions", "Bonus Actions", "Reactions", "Legendary Actions"]

# A real entry's name sits before the FIRST period, in a short prefix --
# measured against every trait/action/reaction/legendary-action name in
# this chapter. "Trigger:"/"Response:"/"Failure:"/"Success:"/"Hit:"/"Miss:"
# use a colon, never a period, to introduce their own clause -- but a
# clause like "Success: Half damage." still ends in a period within the
# same short prefix, so the colon itself must be excluded from a real
# name, not just relied on to make the prefix too long.
_ENTRY_HEAD = re.compile(r"^([A-Z][^.:]{0,58})\.\s+(.*)$")
_LEGENDARY_INTRO_PREFIX = "Legendary Action Uses:"


def _paragraphs(lines):
    end = len(lines)
    while end > 0 and not lines[end - 1]:
        end -= 1
    lines = lines[:end]
    paragraphs = []
    for chunk in "\n".join(lines).split("\n\n"):
        joined = " ".join(l for l in chunk.split("\n") if l)
        if joined:
            paragraphs.append(joined)
    return "\n\n".join(paragraphs)


def _read_ability_block(stripped, start, end):
    """Flatten the six-ability region into tokens and walk it positionally.

    See the module docstring: a per-line rule cannot describe this region,
    because a negative modifier or save renders on its own physical line
    inconsistently, row to row, within the same stat block.
    """
    tokens = []
    for l in stripped[start:end]:
        tokens.extend(_TOKEN_RE.findall(l))

    abilities = {}
    i = 0
    for ability in ABILITIES:
        if i >= len(tokens) or tokens[i] != ability:
            return None, i, "expected ability label %r, found %r" % (
                ability, tokens[i] if i < len(tokens) else None,
            )
        i += 1
        if i >= len(tokens) or not tokens[i].isdigit():
            return None, i, "ability %r: expected a numeric score" % ability
        score = int(tokens[i])
        i += 1
        if i >= len(tokens) or not _SIGNED_RE.match(tokens[i]):
            return None, i, "ability %r: expected a signed modifier" % ability
        mod = int(tokens[i].replace("−", "-"))
        i += 1
        if i >= len(tokens) or not _SIGNED_RE.match(tokens[i]):
            return None, i, "ability %r: expected a signed save" % ability
        save = int(tokens[i].replace("−", "-"))
        i += 1
        abilities[ability.lower()] = {"score": score, "mod": mod, "save": save}

    return abilities, i, None


def _collect_labeled_fields(stripped, label_re, start, end):
    """Generic order-agnostic label scanner, shared shape with parse_tools_en.

    Returns (fields, error). A label's value may wrap to following lines
    until the next recognised label (or the region's end).
    """
    fields = {}
    i = start
    current = None
    while i < end:
        line = stripped[i]
        if not line:
            i += 1
            continue
        m = label_re.match(line)
        if m:
            current = m.group(1)
            fields[current] = [m.group(2)] if m.group(2) else []
        elif current:
            fields[current].append(line)
        else:
            return None, "text %r before any recognised label" % line[:60]
        i += 1
    for key in fields:
        fields[key] = " ".join(p for p in fields[key] if p).strip()
    return fields, None


def _collect_entries(stripped, page_of, start, end):
    """"Name. Description" entries within [start, end).

    Mirrors the Rules Glossary's own entry-detection problem (a blank line
    inside one entry's own multi-paragraph body looks exactly like the gap
    between two entries) but without its alphabetical-order safety net --
    entries in a stat block are not A-to-Z. The one signal available is
    shape: see _ENTRY_HEAD and the module docstring.

    A PAGE TRANSITION IS TREATED AS EXACTLY AS STRONG A SEPARATOR AS A
    BLANK LINE for deciding where a NEW entry may start -- the same rule
    already ported into the FR spell parser -- because several actions
    (Air Elemental's Whirlwind) sit right at a page's first line with no
    blank line before them (each page is normalised independently; a
    "Reactions" section ending its previous entry on a page's last line
    has nothing there to separate it from the entry starting the next
    page). But unlike a blank line, a page transition is NOT used to
    reconstruct the entry's own body text -- a genuine same-entry
    continuation that happens to cross a page with no paragraph break
    must still join with a space, not gain a synthetic one. So the two
    jobs are kept separate: this function decides only WHERE an entry
    starts (scanning with page transitions counted as boundaries); each
    entry's description is then sliced from the plain, unmodified stream
    between one confirmed head and the next.
    """
    heads = []
    at_boundary = True
    for i in range(start, end):
        line = stripped[i]
        if not line:
            at_boundary = True
            continue
        page_changed = i > start and page_of[i] != page_of[i - 1]
        if (at_boundary or page_changed) and _ENTRY_HEAD.match(line):
            heads.append(i)
            at_boundary = False
            continue
        at_boundary = False

    if not heads or (heads[0] != start and any(stripped[start:heads[0]])):
        return None, "no recognisable entry found at the start of this section"

    out = []
    for pos, h in enumerate(heads):
        body_end = heads[pos + 1] if pos + 1 < len(heads) else end
        head_match = _ENTRY_HEAD.match(stripped[h])
        name = head_match.group(1)
        body_lines = [head_match.group(2)] + stripped[h + 1 : body_end]
        description = _paragraphs(body_lines)
        if not description:
            return None, "entry %r has no description text" % name
        out.append({"name": name, "description": description})
    return out, None


def parse_stream(lines, page_of):
    stripped = [l.strip() for l in lines]

    def page_at(i):
        return page_of[i] if i < len(page_of) else (page_of[-1] if page_of else 0)

    chapter_start = None
    for i, l in enumerate(stripped):
        if l == CHAPTER_START:
            chapter_start = i
            break

    monsters, anomalies = [], []
    if chapter_start is None:
        anomalies.append({"page": 0, "line": 0, "detail": "'Monsters A–Z' heading not found"})
        return monsters, anomalies

    chapter_end = len(stripped)

    heads = [i for i in range(chapter_start, chapter_end) if TYPE_HEAD.match(stripped[i])]

    def _looks_like_name_line(line):
        return bool(line) and line[0].isupper() and len(line) <= 40 and not line.endswith(
            (".", ",", ":", ";")
        )

    def name_block_start(type_line_idx):
        """Index where the NAME BLOCK above a type line begins.

        The name block is one line (a solo entry, or a later member of an
        already-open family) or two (a family-opening entry: the shared
        family name directly above the member's own name, no blank
        between them -- "Animated Objects" / "Animated Armor"). Both
        lines, whichever there are, belong to the FOLLOWING monster, not
        the one whose content ends here.

        NOT simply "every contiguous non-blank line above the type line":
        several monsters run straight into the next one's name block with
        NO blank line of their own (Aboleth's last Legendary Action,
        Bandit's last Reaction, Basilisk's last Bonus Action all do this)
        -- a plain non-blank walk would keep consuming the PREVIOUS
        monster's own trailing description text as if it were part of the
        name block. Only the single immediate line is trusted blindly
        (found by skipping actual blank lines); one further line is
        pulled in ONLY if it also looks like a name -- short, capitalised,
        no sentence-ending punctuation -- which a description's last line
        never is.
        """
        j = type_line_idx - 1
        while j >= 0 and not stripped[j]:
            j -= 1
        if j < 0:
            return 0
        start = j
        if j - 1 >= 0 and _looks_like_name_line(stripped[j - 1]) and _looks_like_name_line(stripped[j]):
            start = j - 1
        return start

    for pos, idx in enumerate(heads):
        block_end = name_block_start(heads[pos + 1]) if pos + 1 < len(heads) else chapter_end

        name_at = idx - 1
        while name_at >= 0 and not stripped[name_at]:
            name_at -= 1
        name = stripped[name_at] if name_at >= 0 else ""
        if not name or len(name) > 60:
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "implausible monster name above %r" % stripped[idx][:60]}
            )
            continue

        type_line = stripped[idx]
        m = _TAGS_RE.match(type_line.rsplit(",", 1)[0]) if "," in type_line else None
        if "," not in type_line:
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "monster %r: size/type line has no alignment comma: %r" % (name, type_line)}
            )
            continue
        size_type_and_tags, alignment = type_line.rsplit(",", 1)
        alignment = alignment.strip()
        tag_match = _TAGS_RE.match(size_type_and_tags)
        if tag_match:
            size_type = tag_match.group("base").strip()
            tags = tag_match.group("tags").strip()
        else:
            size_type = size_type_and_tags.strip()
            tags = None

        i = idx + 1
        while i < block_end and not stripped[i]:
            i += 1

        # The blank line that usually separates Speed from the ability
        # table's "MOD SAVE" header is not always there (Bandit Captain,
        # Frost Giant and others run the two regions together with no
        # blank at all) -- found by measuring, not assumed. Anchor on the
        # literal three-times-repeated header instead of a blank line.
        ability_header_at = None
        for k in range(i, block_end - 2):
            if stripped[k:k + 3] == _ABILITY_HEADER:
                ability_header_at = k
                break
        combat_end = ability_header_at if ability_header_at is not None else block_end
        combat_fields, err = _collect_labeled_fields(stripped, _COMBAT_LABEL_RE, i, combat_end)
        if err or any(k not in (combat_fields or {}) for k in COMBAT_LABELS):
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "monster %r: combat stats block: %s"
                           % (name, err or "missing one of AC/Initiative/HP/Speed")}
            )
            continue

        j = combat_end
        while j < block_end and not stripped[j]:
            j += 1
        if stripped[j:j + 3] != _ABILITY_HEADER:
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "monster %r: ability score table header not found" % name}
            )
            continue
        j += 3

        other_start = None
        k = j
        while k < block_end:
            if stripped[k] and _OTHER_LABEL_RE.match(stripped[k]):
                other_start = k
                break
            k += 1
        if other_start is None:
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "monster %r: no Senses/Languages/CR fields found after ability table" % name}
            )
            continue

        abilities, _, err = _read_ability_block(stripped, j, other_start)
        if err:
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "monster %r: ability score table: %s" % (name, err)}
            )
            continue

        other_end = other_start
        while other_end < block_end and stripped[other_end] not in SECTION_HEADS:
            other_end += 1
        other_fields, err = _collect_labeled_fields(stripped, _OTHER_LABEL_RE, other_start, other_end)
        if err or "CR" not in (other_fields or {}) or "Senses" not in other_fields or "Languages" not in other_fields:
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "monster %r: Senses/Languages/CR block: %s"
                           % (name, err or "missing Senses, Languages or CR")}
            )
            continue

        sections = {}
        section_positions = [
            (p, stripped[p]) for p in range(other_end, block_end) if stripped[p] in SECTION_HEADS
        ]
        bad_section = False
        for spos, (start_i, head_name) in enumerate(section_positions):
            body_start = start_i + 1
            body_end = section_positions[spos + 1][0] if spos + 1 < len(section_positions) else block_end

            if head_name == "Legendary Actions":
                b = body_start
                while b < body_end and not stripped[b]:
                    b += 1
                intro_end = b
                while intro_end < body_end and stripped[intro_end]:
                    intro_end += 1
                intro = " ".join(stripped[b:intro_end])
                if not intro.startswith(_LEGENDARY_INTRO_PREFIX):
                    anomalies.append(
                        {"page": page_at(idx), "line": idx,
                         "detail": "monster %r: Legendary Actions missing its 'Legendary Action "
                                   "Uses:' intro" % name}
                    )
                    bad_section = True
                    break
                options, err = _collect_entries(stripped, page_of, intro_end, body_end)
                if err:
                    anomalies.append(
                        {"page": page_at(idx), "line": idx,
                         "detail": "monster %r: Legendary Actions options: %s" % (name, err)}
                    )
                    bad_section = True
                    break
                sections["legendary_actions"] = {"intro": intro, "options": options}
            else:
                entries, err = _collect_entries(stripped, page_of, body_start, body_end)
                if err:
                    anomalies.append(
                        {"page": page_at(idx), "line": idx,
                         "detail": "monster %r: %s section: %s" % (name, head_name, err)}
                    )
                    bad_section = True
                    break
                key = head_name.lower().replace(" ", "_")
                sections[key] = entries
        if bad_section:
            continue

        monsters.append(
            {
                "name": name,
                "size_type": size_type,
                "tags": tags,
                "alignment": alignment,
                "ac": combat_fields["AC"],
                "initiative": combat_fields["Initiative"],
                "hp": combat_fields["HP"],
                "speed": combat_fields["Speed"],
                "abilities": abilities,
                "skills": other_fields.get("Skills"),
                "resistances": other_fields.get("Resistances"),
                "vulnerabilities": other_fields.get("Vulnerabilities"),
                "immunities": other_fields.get("Immunities"),
                "gear": other_fields.get("Gear"),
                "senses": other_fields["Senses"],
                "languages": other_fields["Languages"],
                "cr": other_fields["CR"],
                "traits": sections.get("traits", []),
                "actions": sections.get("actions", []),
                "bonus_actions": sections.get("bonus_actions", []),
                "reactions": sections.get("reactions", []),
                "legendary_actions": sections.get("legendary_actions"),
                "page": page_at(name_at),
            }
        )

    return monsters, anomalies


def parse(pages, suspect_pages=()):
    suspect = set(suspect_pages)

    numbered = []
    for number, raw in enumerate(pages, start=1):
        for line in raw.split("\n"):
            numbered.append((number, line))

    numbered = _dehyphenate_numbered(numbered)
    lines = [l for _, l in numbered]
    page_of = [n for n, _ in numbered]

    found, anomalies = parse_stream(lines, page_of)

    monsters, conflicts = [], []
    for monster in found:
        if monster["page"] in suspect:
            conflicts.append(
                {"page": monster["page"], "name": monster["name"],
                 "detail": "page text disputed between PyMuPDF and pdftotext"}
            )
        else:
            monsters.append(monster)

    monsters.sort(key=lambda m: canon.slugify(m["name"]))
    return monsters, anomalies, conflicts
