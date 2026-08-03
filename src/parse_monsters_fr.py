"""Monster (stat block) parser for the French SRD 5.2.1.

CALIBRATED against the pinned FR PDF on 2026-08-03, "Monstres de A à Z"
(p.272-359). Ported from `parse_monsters_en.py` -- same overall strategy
(anchor on the size/type/alignment head line rather than the name; flatten
the six-ability region into a token stream and walk it positionally,
because a negative modifier or save renders on its own physical line
inconsistently, row to row, in French exactly as in English; Traits/
Actions/Bonus Actions/Reactions share the Rules Glossary's own "Name.
Description" entry shape and its own trap, solved the same way -- a real
entry's name sits before the FIRST period in a short, colon-free prefix).

THE HEAD LINE PUTS SIZE AND TYPE IN THE OPPOSITE ORDER FROM ENGLISH, not
merely translated word-for-word: "Aberration de taille G, Loyale Mauvaise"
-- TYPE first, then "de taille" + SIZE, then alignment, where EN puts
SIZE first ("Large Aberration, Lawful Evil"). The size itself is also
ABBREVIATED here (TP/P/M/G/TG/Gig), not the full word EN's head line uses
(Tiny/Small/.../Gargantuan) -- both facts read directly off real head
lines across many monsters, not assumed from EN's shape.

THE SWARM SHAPE IS ALSO REORDERED, not the same clause with translated
words: "Nuée de taille M de Morts-vivants de taille TP, Neutre Mauvais" --
the SWARM's own size, then the MEMBER type, then the MEMBER's own size
again, where EN's "Medium Swarm of Tiny Undead" folds all three into one
noun phrase read left to right. `TYPE_HEAD` anchors on the line simply
STARTING with "Nuée" or one of the fourteen type words (`\b`-bounded, so
"Nuée de taille M de..." matches on "Nuée" and an unrelated capitalised
plural like "Dragons." in glossary-style prose does NOT match "Dragon\b",
since there is no word-boundary between "n" and the following "s") --
after that, the entry-processing step separately requires a comma (for
the alignment split) and the literal substring "de taille" before it,
so a monster's own TRAIT text that happens to start a line with a type
word (rare, not observed, but not ruled out either) would still fail
these secondary checks rather than being accepted as a false head.

TAGS ARE NOT AT THE END OF THE BASE STRING THE WAY EN'S ARE: "Fiélon
(Démon) de taille P, Chaotique Mauvais" -- the "(Démon)" sits between the
type word and "de taille", not trailing the whole clause the way EN's
"Dragon (Chromatic)" does. `_TAGS_RE` here strips a parenthetical found
ANYWHERE in the pre-alignment text, not just at its end.

FIELD LABELS, read off real stat blocks rather than translated from EN's:
combat block "CA" / "Initiative" / "Pv" / "Vitesse" (AC/Initiative/HP/
Speed); ability abbreviations "For" / "Dex" / "Con" / "Int" / "Sag" /
"Cha" (Str/Dex/Con/Int/Wis/Cha -- Dex, Con and Cha happen to already be
identical to EN's own abbreviations); the ability table's own column
header renders as SIX separate one-word lines here -- "MOD", "JS", "MOD",
"JS", "MOD", "JS" -- not EN's three two-word "MOD SAVE" lines, checked
directly rather than assumed the same shape; other-fields block
"Compétences" / "Résistances" / "Vulnérabilités" / "Immunités" /
"Équipement" / "Sens" / "Langues" / "FP" (Skills/Resistances/
Vulnerabilities/Immunities/Gear/Senses/Languages/CR -- "FP", Facteur de
Puissance, is French's own name for Challenge Rating); section headings
"Traits" / "Actions" / "Actions Bonus" / "Réactions" / "Actions
Légendaires" (capital L on "Légendaires", checked directly -- EN's own
"Legendary Actions" capitalises both words too, but nothing here should
be assumed to carry over unchecked). "Trigger:"/"Response:" become
"Déclencheur :"/"Réaction :" and "Hit:"/"Miss:" become "Touché :"/
"Raté :" in the source's own trait prose -- like EN, none of these needs
special handling: they use a COLON, never a period, so `_ENTRY_HEAD`
(which requires a period) never mistakes them for a new entry.

`_ENTRY_HEAD`'S CHARACTER CLASS IS WIDENED TO ACCEPT AN ACCENTED CAPITAL
opening a trait/action name (Écorchure-shaped names are common in this
document, the same accented-capital concern already handled in the Rules
Glossary parser) -- EN's own `[A-Z]` would silently reject every such
entry's name as "text before any recognised label" wherever a scanner
depends on it, so this is not cosmetic.

THE LEGENDARY ACTIONS INTRO PREFIX reads "Utilisations d'action
Légendaire :" (colon at the end, matching the labelled-field convention
used everywhere else in this stat-block grammar), not a literal
translation of EN's "Legendary Action Uses: N." sentence shape.
"""

import re

import canon
from parse_spells import _dehyphenate_numbered

SIZES = ["TP", "P", "M", "G", "TG", "Gig"]
CREATURE_TYPES = [
    "Aberration", "Artificiel", "Bête", "Céleste", "Dragon", "Élémentaire",
    "Fée", "Fiélon", "Géant", "Humanoïde", "Monstruosité", "Mort-vivant",
    "Plante", "Vase",
]
_SIZE_ALT = "|".join(SIZES)
_TYPE_ALT = "|".join(re.escape(t) for t in sorted(CREATURE_TYPES, key=len, reverse=True))

# Anchors on the line simply STARTING with "Nuée" or a recognised type
# word -- see module docstring for why a fuller structural regex (size +
# type + alignment all inline) is not attempted here the way EN's is: the
# swarm shape reorders its three parts in a way a single regex would have
# to special-case anyway, and the secondary "has a comma and 'de taille'
# before it" checks in `parse_stream` already do the real discriminating
# work EN's own SIZE-first anchor does structurally.
TYPE_HEAD = re.compile(r"^(?:Nuée|%s)\b" % _TYPE_ALT)
_TAGS_RE = re.compile(r"^(?P<pre>.*?)\s?\((?P<tags>[^)]+)\)\s*(?P<post>.*)$")
_DE_TAILLE = "de taille"

# The alignment clause can wrap across the line break that closes the
# type/size head, when the tags/type text before it is already long
# enough to push it there: "Monstruosité (Lycanthrope) de taille M ou P,
# Chaotique" / "Mauvaise" (Loup-garou) -- found by "text 'Mauvaise' before
# any recognised label" anomalies (the wrapped word landing in the combat-
# stats scan with no field label of its own), not assumed from a shorter
# EN alignment that never needed to wrap. Recognising a COMPLETE alignment
# clause (rather than guessing a fixed line count to always join) is what
# lets the join happen only when it is genuinely needed.
_ALIGNMENT_RE = re.compile(
    r"^(?:(?:Loyale?|Neutre|Chaotique)\s+)?(?:Bon(?:ne)?|Mauvais(?:e)?|Neutre)$"
    r"|^[Nn]on align[ée]e?s?$"
)


def _resolve_alignment(stripped, idx, limit):
    """Split `stripped[idx]` on its last comma and, if the tail is not yet
    a complete-looking alignment, join up to two more lines and re-split.

    Returns (alignment, extra_lines_consumed) once `_ALIGNMENT_RE`
    matches, or None if it never does within the join budget -- the
    latter is what tells a genuine head (Loup-garou's wrapped "Chaotique
    Mauvaise") apart from a false one (a shapeshifter TRAIT's own prose,
    "...se transforme en Humanoïde de taille P ou M, ou bien retrouve sa
    forme véritable...", whose "alignment" position holds a subordinate
    clause with a verb, never a real alignment word). Without this
    validation gate, the false candidate was silently accepted as a
    monster with a garbage alignment string, corrupting the SUBSEQUENT
    combat-stats scan with its own trailing prose.
    """
    text = stripped[idx]
    extra = 0
    while True:
        if "," not in text:
            if extra >= 2 or idx + extra + 1 >= limit or not stripped[idx + extra + 1]:
                return None
            extra += 1
            text = text + " " + stripped[idx + extra]
            continue
        _, alignment = text.rsplit(",", 1)
        alignment = alignment.strip()
        if _ALIGNMENT_RE.match(alignment):
            # "Neutre" ALONE is a genuinely complete alignment (true
            # neutral) -- but it is also the first word of a wrapped
            # "Neutre Bon(ne)"/"Neutre Mauvais(e)", found on Ours-garou
            # and Sanglier-garou ("...de taille M ou P, Neutre\nBonne" /
            # "\nMauvaise"). The two cannot be told apart from the word
            # itself, only from what follows: a genuinely standalone
            # "Neutre" is followed by the blank line that closes the head
            # block, where a wrapped one is immediately followed (no
            # blank) by its own second word.
            if (
                alignment == "Neutre"
                and extra < 2
                and idx + extra + 1 < limit
                and re.match(r"^(?:Bon(?:ne)?|Mauvais(?:e)?)$", stripped[idx + extra + 1] or "")
            ):
                extra += 1
                text = text + " " + stripped[idx + extra]
                continue
            return alignment, extra
        if extra >= 2 or idx + extra + 1 >= limit or not stripped[idx + extra + 1]:
            return None
        extra += 1
        text = text + " " + stripped[idx + extra]

CHAPTER_START = "Monstres de A à Z"

COMBAT_LABELS = ["CA", "Initiative", "Pv", "Vitesse"]
_COMBAT_LABEL_RE = re.compile(r"^(%s)\s+(.*)$" % "|".join(COMBAT_LABELS))

ABILITIES = ["For", "Dex", "Con", "Int", "Sag", "Cha"]
_ABILITY_HEADER = ["MOD", "JS", "MOD", "JS", "MOD", "JS"]
_SIGNED_RE = re.compile(r"^[+−-]?\d+$")
_TOKEN_RE = re.compile(r"\S+")

OTHER_LABELS = [
    "Compétences", "Résistances", "Vulnérabilités", "Immunités",
    "Équipement", "Sens", "Langues", "FP",
]
_OTHER_LABEL_RE = re.compile(r"^(%s)\s+(.*)$" % "|".join(OTHER_LABELS))

SECTION_HEADS = ["Traits", "Actions", "Actions Bonus", "Réactions", "Actions Légendaires"]

# TWO WRAP SHAPES, NEITHER GUESSABLE FROM EN'S OWN SINGLE-LINE ENTRIES,
# both found by "no recognisable entry at the start of this section"
# anomalies rather than a wrong record (the discipline holding even when
# the fix is still pending): French's longer words push this document's
# names past a column width EN's shorter ones fit inside.
#
# 1. The trailing content is OPTIONAL on the name's own line: "Attaques
#    multiples (forme de vampire uniquement)." ends the physical line
#    right at its own period, with the description starting entirely on
#    the NEXT line -- EN's `\.\s+(.*)$` requires something after the
#    period on the SAME line and would reject this outright.
# 2. The name itself can wrap BEFORE reaching its own closing period:
#    "Résistance légendaire (3/jour, ou 4/jour dans son" / "antre). Si le
#    dragon rate..." -- `_try_entry_head` retries a 2-line join when the
#    single line has no period at all, the same discipline already used
#    for a magic item's subtype parenthetical wrap.
_ENTRY_HEAD = re.compile(r"^([A-ZÀ-Þ][^.:]{0,58})\.(?:\s+(.*))?$")
_LEGENDARY_INTRO_PREFIX = "Utilisations d’action Légendaire :"


def _try_entry_head(stripped, i, end):
    """Return (name, description_start_text, lines_consumed) or None."""
    line = stripped[i]
    m = _ENTRY_HEAD.match(line)
    if m:
        return m.group(1), (m.group(2) or ""), 1
    if i + 1 < end and stripped[i + 1] and line and line[0].isupper() and "." not in line:
        joined = line + " " + stripped[i + 1]
        m2 = _ENTRY_HEAD.match(joined)
        if m2:
            return m2.group(1), (m2.group(2) or ""), 2
    return None


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
    heads = []
    at_boundary = True
    for i in range(start, end):
        line = stripped[i]
        if not line:
            at_boundary = True
            continue
        page_changed = i > start and page_of[i] != page_of[i - 1]
        if at_boundary or page_changed:
            found = _try_entry_head(stripped, i, end)
            if found:
                name, desc_start, extra = found
                heads.append((i, name, desc_start, extra))
                at_boundary = False
                continue
        at_boundary = False

    if not heads or (heads[0][0] != start and any(stripped[start:heads[0][0]])):
        return None, "no recognisable entry found at the start of this section"

    out = []
    for pos, (h, name, desc_start, extra) in enumerate(heads):
        body_end = heads[pos + 1][0] if pos + 1 < len(heads) else end
        body_lines = ([desc_start] if desc_start else []) + stripped[h + extra : body_end]
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
        anomalies.append({"page": 0, "line": 0, "detail": "'Monstres de A à Z' heading not found"})
        return monsters, anomalies

    chapter_end = len(stripped)

    # Candidates are anchored loosely (see module docstring); a real head
    # additionally needs a comma (to split off the alignment) with the
    # literal substring "de taille" somewhere before it. Both checked here
    # rather than folded into TYPE_HEAD itself, so a candidate that fails
    # them is simply not a head -- not an anomaly, the same way EN's own
    # anchor does not flag ordinary prose that happens not to match.
    heads = []
    for i in range(chapter_start, chapter_end):
        line = stripped[i]
        if not TYPE_HEAD.match(line):
            continue
        if "," not in line:
            continue
        pre_comma = line.rsplit(",", 1)[0]
        if _DE_TAILLE not in pre_comma:
            continue
        if _resolve_alignment(stripped, i, chapter_end) is None:
            continue
        heads.append(i)

    def _looks_like_name_line(line):
        return bool(line) and line[0].isupper() and len(line) <= 40 and not line.endswith(
            (".", ",", ":", ";")
        )

    def name_block_start(type_line_idx):
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
        resolved = _resolve_alignment(stripped, idx, block_end)
        if resolved is None:
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "monster %r: alignment clause did not resolve within the family block" % name}
            )
            continue
        alignment, type_extra = resolved
        # The comma is always on `idx`'s own line -- only the alignment
        # TAIL after it ever needs extra lines joined (see
        # `_resolve_alignment`), so the pre-comma part is already complete.
        size_type_and_tags = type_line.rsplit(",", 1)[0]
        tag_match = _TAGS_RE.match(size_type_and_tags)
        if tag_match and tag_match.group("tags"):
            size_type = (tag_match.group("pre") + " " + tag_match.group("post")).strip()
            size_type = re.sub(r"\s+", " ", size_type)
            tags = tag_match.group("tags").strip()
        else:
            size_type = size_type_and_tags.strip()
            tags = None

        i = idx + 1 + type_extra
        while i < block_end and not stripped[i]:
            i += 1

        ability_header_at = None
        for k in range(i, block_end - len(_ABILITY_HEADER) + 1):
            if stripped[k : k + len(_ABILITY_HEADER)] == _ABILITY_HEADER:
                ability_header_at = k
                break
        combat_end = ability_header_at if ability_header_at is not None else block_end
        combat_fields, err = _collect_labeled_fields(stripped, _COMBAT_LABEL_RE, i, combat_end)
        if err or any(k not in (combat_fields or {}) for k in COMBAT_LABELS):
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "monster %r: combat stats block: %s"
                           % (name, err or "missing one of CA/Initiative/Pv/Vitesse")}
            )
            continue

        j = combat_end
        while j < block_end and not stripped[j]:
            j += 1
        if stripped[j : j + len(_ABILITY_HEADER)] != _ABILITY_HEADER:
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "monster %r: ability score table header not found" % name}
            )
            continue
        j += len(_ABILITY_HEADER)

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
                 "detail": "monster %r: no Sens/Langues/FP fields found after ability table" % name}
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
        if (
            err or "FP" not in (other_fields or {})
            or "Sens" not in other_fields or "Langues" not in other_fields
        ):
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "monster %r: Sens/Langues/FP block: %s"
                           % (name, err or "missing Sens, Langues or FP")}
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

            if head_name == "Actions Légendaires":
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
                         "detail": "monster %r: Actions Légendaires missing its 'Utilisations "
                                   "d'action Légendaire :' intro" % name}
                    )
                    bad_section = True
                    break
                options, err = _collect_entries(stripped, page_of, intro_end, body_end)
                if err:
                    anomalies.append(
                        {"page": page_at(idx), "line": idx,
                         "detail": "monster %r: Actions Légendaires options: %s" % (name, err)}
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
                key = {
                    "Traits": "traits", "Actions": "actions",
                    "Actions Bonus": "bonus_actions", "Réactions": "reactions",
                }[head_name]
                sections[key] = entries
        if bad_section:
            continue

        monsters.append(
            {
                "name": name,
                "size_type": size_type,
                "tags": tags,
                "alignment": alignment,
                "ac": combat_fields["CA"],
                "initiative": combat_fields["Initiative"],
                "hp": combat_fields["Pv"],
                "speed": combat_fields["Vitesse"],
                "abilities": abilities,
                "skills": other_fields.get("Compétences"),
                "resistances": other_fields.get("Résistances"),
                "vulnerabilities": other_fields.get("Vulnérabilités"),
                "immunities": other_fields.get("Immunités"),
                "gear": other_fields.get("Équipement"),
                "senses": other_fields["Sens"],
                "languages": other_fields["Langues"],
                "cr": other_fields["FP"],
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
