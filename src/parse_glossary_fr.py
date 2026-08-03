"""Rules Glossary parser for the French SRD 5.2.1.

CALIBRATED against the pinned FR PDF on 2026-08-03, "Glossaire de règles"
(p.187-202, entered at the "Définitions des règles" sub-heading -- the FR
equivalent of EN's "Rules Definitions" -- that follows the abbreviations
table, and bounded by the "Boîte à outils ludique" chapter that follows).
Ported from `parse_glossary_en.py`: same central problem (no mechanical
head shape to anchor on, blank lines that do not reliably mark entry
boundaries, an embedded bulleted list of cross-referenced terms that reads
exactly like a run of real entries), same three-part solution -- name
shape, "what follows is real prose" word-count floor, and global
alphabetical order as the actual safety net.

THREE THINGS THAT ARE NOT A STRAIGHT PORT OF EN'S HEURISTICS, all found by
testing against the real document rather than assumed:

1. **The bracketed sub-type tag can contain letters EN's charset does not
   cover.** EN's five tags are all plain ASCII (Action, Condition, Hazard,
   Attitude, Area of Effect); French's five are Action, Attitude, Danger,
   État, Zone d'effet -- "État" carries an accented capital É, and "Zone
   d'effet" carries a space AND an apostrophe. `TAG_RE`'s bracket content
   is `[^\\]]+` here (anything but the closing bracket) rather than EN's
   `[A-Za-z /]+`, because enumerating "which accented letters and which
   punctuation" would have been guessing at a closed set from five
   examples -- the closing bracket itself is already the real boundary.
2. **EN's "every content word is capitalised" title-case check does not
   hold in French AT ALL, and this is not a minor wording gap -- it is a
   different capitalisation CONVENTION.** French headings use sentence
   case: only the first word is capitalised ("Jet de sauvegarde", "Classe
   d'armure", "Point de vie"), never every content word the way English
   headline-style titles do. Porting EN's `_looks_titlecase` check
   verbatim (even with a French minor-word list swapped in) accepted only
   34 of the chapter's 152 entries -- every one of them a coincidental
   single word ("Action", "Alignement", "Avantage") -- and rejected every
   multi-word name outright, because their second-and-later words are
   lowercase common nouns, not capitals a minor-word exemption list could
   ever cover. Dropped entirely: a name candidate here only needs to
   START with a capital letter, not have every word capitalised. The
   real discriminating work moves onto signals (3) below, unchanged from
   EN's own design.
3. **Word-counting needs the French accented-letter range**, the same
   `[a-zà-öø-ÿ]` class already used by this codebase's dehyphenation
   regexes (`parse_spells.py`), not EN's bare `[A-Za-z]`, so an ordinary
   French sentence's own accented words count toward the prose floor.

THE PAGE SEAM is handled the same way as EN's: a page transition counts as
a boundary for deciding what MAY be a head (an entry's name can be a
page's very first line with no blank line preceding it, since each page
is normalised independently), but an accepted entry's own body text is
sliced from the plain stream between two accepted heads, so a same-
sentence page crossing joins with a space rather than gaining a synthetic
paragraph break.

TAGS are kept as the source's own word, slugified, the same call already
made for EN -- no reason to invent a closed enum when French's own five
words are already unambiguous.
"""

import re

import canon
from parse_spells import _dehyphenate_numbered

CHAPTER_ENTRY_HEADING = "Définitions des règles"

# The chapter that follows Rules Glossary is titled "Boîte à outils
# ludique", but that title NEVER appears as a single bare line anywhere in
# the document -- confirmed by an exhaustive exact-line search coming back
# empty. It wraps across two physical lines, "Boîte à outils" / "ludique",
# at its one real occurrence (p.203); every OTHER occurrence of the phrase
# in the document is a quoted cross-reference embedded in running prose
# ("la « Boîte à outils ludique » détaille..."), never its own line. A
# single-string CHAPTER_END search (the pattern used successfully for
# every OTHER chapter boundary in this codebase) silently found nothing,
# fell through to `chapter_end = len(lines)` -- the end of the ENTIRE
# 380-page document -- and let the glossary's own head-scan run straight
# through Boîte à outils ludique, Objets magiques and into Monstres before
# finally re-triggering (as a coincidental, correctly-shaped candidate) on
# "Points d'expérience"'s SECOND, unrelated occurrence deep in the
# Monsters chapter (p.269, "points d'expérience qu'un monstre rapporte"),
# producing a silent duplicate record with the same name and a different
# body. Caught by that duplicate, not by any anomaly count -- the search
# never fails loudly, it just keeps going.
CHAPTER_END_LINES = ("Boîte à outils", "ludique")

TAG_RE = re.compile(r"^(.*?)\s\[([^\]]+)\]$")
_ALPHA_WORD_RE = re.compile(r"[A-Za-zà-öø-ÿÀ-ÖØ-Þ]+")

# The 18 official skill names ("Comment jouer", p.9) are not Rules Glossary
# entries in either language -- EN's own 152 has no "History" or "Nature"
# entry either, only the generic "Skill" one. They matter here because the
# "Étude" ["Study"] entry embeds a two-column "Compétence / Domaines" table
# (skill name -> what it covers) whose rows read exactly like real entries:
# capitalised, blank-line-preceded, followed by substantial prose (a real
# domain description, not a short list item the prose floor would catch).
# Three of them -- Histoire, Nature, Religion -- were accepted as false
# heads before this exclusion, each poisoning the alphabetical safety net
# and silently dropping every real entry between it and the next skill
# name accepted afterward. Named and excluded outright rather than solved
# generally: this is ONE known embedded table, not a pattern to guess a
# rule for.
_SKILL_NAMES = {
    "Acrobaties", "Arcanes", "Athlétisme", "Discrétion", "Dressage",
    "Escamotage", "Histoire", "Investigation", "Médecine", "Nature",
    "Perception", "Religion", "Survie", "Tromperie", "Intimidation",
    "Intuition", "Persuasion", "Représentation",
}

# Measured across the whole chapter -- see parser test/calibration; kept the
# same headroom EN uses (its own longest real name is 27 characters).
_NAME_MAX_LEN = 60

_PROSE_WORD_FLOOR = 10


def _is_name_candidate(line):
    if not line or not line[0].isupper():
        return False
    if len(line) > _NAME_MAX_LEN:
        return False
    if ". " in line:
        return False
    if line.endswith((".", ",", ":", ";")):
        return False
    # A real entry name is a short noun phrase, never a clause -- neither
    # "En termes de jeu, on parle alors d'attaque à mains" nor "Un état
    # n'est pas cumulable avec lui-même ; le sujet" (both real sentence
    # fragments, wrapped at a page/blank-line boundary purely by
    # coincidence) is one, and both slipped past every other check here:
    # short enough, capitalised, no mid-line period, no trailing
    # punctuation. A comma or semicolon mid-line is the tell -- no real
    # entry name in this chapter has either.
    if "," in line or ";" in line:
        return False
    if line in _SKILL_NAMES:
        return False
    # A real entry name is a noun phrase, never a clause: "Si vous vous
    # êtes reposé au moins 1 heure avant" (a genuine mid-paragraph
    # sentence inside the "Repos long" entry's own "Repos interrompu"
    # sub-section, blank-line-preceded purely because it opens a new
    # paragraph) has no comma to catch it, so the opening word itself is
    # the tell -- no real entry in this chapter opens with a conditional
    # or a second-person pronoun. Kept to the two words actually observed
    # doing this, not a broad stop-word list: "En péril" is a real entry
    # and starts with a preposition, so guessing at prepositions/pronouns
    # generally would have cost a true positive to fix a false one.
    if line.split(" ", 1)[0] in ("Si", "Vous"):
        return False
    return True


def _looks_like_prose(text):
    return len(_ALPHA_WORD_RE.findall(text)) >= _PROSE_WORD_FLOOR


def _preview_end(stripped, page_of, i, limit):
    j = i + 1
    while j < limit and stripped[j] and not (page_of[j] != page_of[j - 1]):
        j += 1
    return j


def _sort_key(name):
    """Accent-insensitive comparison key, so 'É' does not sort after 'Z'.

    Plain `.lower()` (EN's own approach) is not enough in French: raw
    Python string comparison orders by code point, and an accented capital
    like 'É' (U+00C9) or 'À' (U+00C0) sits ABOVE every unaccented letter,
    including lowercase ones -- 'É' > 'z'. The very first real entry in
    the chapter, "À terre", would set `last_key` to something no later
    unaccented entry could ever be `>=` to, poisoning the alphabetical
    safety net for the rest of the chapter (measured: with plain `.lower()`
    this pass accepted 6 entries total, all of them accented). Reusing
    `canon.slugify` -- already NFD-decompose-and-strip-combining-marks,
    the same normalisation every record's own identifier goes through --
    gives a key where accents are gone and ordering behaves the way a
    French dictionary's does.
    """
    try:
        return canon.slugify(name)
    except ValueError:
        return ""


# ONE NAMED, NARROW EXCEPTION to "global alphabetical order is the real
# safety net" (the discipline this parser otherwise shares with EN's): the
# entry "JS" (a cross-reference stub -- "JS est l'acronyme de « jet de
# sauvegarde ». Lire aussi « Jet de sauvegarde ».") sits in the source
# BEFORE "Jet d'attaque", "Jet de dégâts" and "Jet de sauvegarde" -- but
# "js" does not sort before "jet-..." in plain string order ('e' < 's' at
# the second character), so treating it like every other entry advances
# `last_key` past it and rejects all three real entries that genuinely
# follow. Named as the LITERAL string, not a general acronym shape: a
# first attempt matched ANY bare 2-4 letter all-caps token, which also
# matched the document's own short table-header/table-row tokens (CA, TP,
# DD, G, M...) wherever THEIR OWN following text happened to run past the
# 10-word prose floor by coincidence, elsewhere in the chapter -- 473
# "entries" came back, not 152. "JS" is the one bare short-acronym token
# in this whole chapter that is actually followed by a real definition;
# it earns the exception by name, not by shape.
#
# THREE MORE NAMES, A DIFFERENT ROOT CAUSE: "Possession" is printed BEFORE
# "Pointe [Action]" in the extracted stream, even though "pointe" sorts
# before "possession" letter for letter -- a genuine two-column reading-
# order artefact of this page's PDF layout (the same class of issue
# already documented for the Elf/Tiefling lineage tables in
# `parse_species_fr.py`, not something guessable from the text alone).
# That one dip poisons `last_key` at "possession", which then also blocks
# "Points d'expérience" and "Points de vie" -- both genuinely sort before
# "possession" too, and both are otherwise ordinary, complete entries.
_ORDER_EXEMPT = {"JS", "Pointe", "Points d’expérience", "Points de vie"}


def _find_heads(stripped, page_of, start, end):
    """Indices of accepted entry name-lines within [start, end)."""
    heads = []
    last_key = ""
    at_boundary = True
    i = start
    while i < end:
        line = stripped[i]
        if not line:
            at_boundary = True
            i += 1
            continue
        page_changed = i > start and page_of[i] != page_of[i - 1]
        if at_boundary or page_changed:
            preview_end = _preview_end(stripped, page_of, i, end)
            preview = " ".join(stripped[i + 1 : preview_end])
            m = TAG_RE.match(line)
            base_name = m.group(1) if m else line
            key = _sort_key(base_name.strip())
            exempt = base_name.strip() in _ORDER_EXEMPT
            if _is_name_candidate(line) and _looks_like_prose(preview) and (
                key >= last_key or exempt
            ):
                heads.append(i)
                if not exempt:
                    last_key = key
                at_boundary = False
                i += 1
                continue
        at_boundary = False
        i += 1
    return heads


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


def parse_stream(text, page_of):
    lines = [l.strip("\n") for l in text.split("\n")]
    stripped = [l.strip() for l in lines]
    entries, anomalies = [], []

    def page_at(i):
        return page_of[i] if i < len(page_of) else (page_of[-1] if page_of else 0)

    entry_start = None
    for i, l in enumerate(stripped):
        if l == CHAPTER_ENTRY_HEADING:
            entry_start = i
            break
    if entry_start is None:
        anomalies.append({"page": 0, "line": 0, "detail": "'Définitions des règles' heading not found"})
        return entries, anomalies

    # Skip the one-line intro ("Ci-après, les définitions des diverses
    # règles.") and the blank line that closes it -- the abbreviations
    # table above this point is deliberately out of scope.
    i = entry_start + 1
    while i < len(stripped) and stripped[i]:
        i += 1
    i += 1
    chapter_start = i

    chapter_end = len(lines)
    for j in range(chapter_start + 1, len(stripped) - 1):
        if (stripped[j], stripped[j + 1]) == CHAPTER_END_LINES:
            chapter_end = j
            break

    heads = _find_heads(stripped, page_of, chapter_start, chapter_end)

    for pos, idx in enumerate(heads):
        head_line = stripped[idx]
        body_end = heads[pos + 1] if pos + 1 < len(heads) else chapter_end

        m = TAG_RE.match(head_line)
        name = (m.group(1) if m else head_line).strip()
        tag = canon.slugify(m.group(2)) if m else None

        description = _paragraphs(stripped[idx + 1 : body_end])
        if not description:
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "glossary entry %r has a name line but no body text" % name}
            )
            continue

        entries.append(
            {
                "name": name,
                "tag": tag,
                "description": description,
                "page": page_at(idx),
            }
        )

    return entries, anomalies


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

    entries, conflicts = [], []
    for entry in found:
        if entry["page"] in suspect:
            conflicts.append(
                {"page": entry["page"], "name": entry["name"],
                 "detail": "page text disputed between PyMuPDF and pdftotext"}
            )
        else:
            entries.append(entry)

    entries.sort(key=lambda e: canon.slugify(e["name"]))
    return entries, anomalies, conflicts
