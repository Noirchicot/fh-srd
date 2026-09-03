"""Which French species trait is which English one — computed, never guessed.

WHAT THIS CLOSES. A species record is paired (both catalogues address it
`srd:species:en:elf` since the cold transition), but its TRAITS are not: they
live inside `data.traits[]` as elements keyed by a slugified NAME, so
`keen-senses` and `sens-aiguises` are the same rule under two identities that
share nothing. Measured 2026-09-04: 1 trait key out of 33 matches across the
two languages, and that one is `brave` on the Halfling -- a homograph, not a
pair. No neutral field, no `translation_of` edge, no `trait` record kind to
link. That is the last thing standing between the project and a French Fate's
Hand character, and it is what this module gives an identity to.

WHAT IT MAY NOT DO, AND WHY THE FIRST TRY WOULD HAVE DONE IT.

  * ⛔ Not by NAME. Slugs are transliterations of translated names; joining on
    them is the thing the whole chantier forbids.
  * ⛔ Not by POSITION. Each catalogue sorts its traits in its own alphabet, so
    rank means different things on the two sides. This repo has already paid
    for that once, on lineages: pairing by position produced `elfe-sylvestre`
    as `high-elf` and `haut-elfe` as `wood-elf`, exactly swapped, and reported
    ZERO CONFLICTS -- a clean conflict count proves nothing, because an
    inversion never contradicts itself. Only reading the values caught it.

HOW IT IS DONE INSTEAD -- four signals, weakest claim first, run to a fixpoint
inside each species. Every one of them reads a VALUE, never a label, and every
one is computed within a single language before the two sides are compared.

  1. NUMBERS. A trait's text carries distances, dice and counts. Distances are
     converted between editions (`60 feet` / `18 m`) and are normalised on a
     common scale; dice and plain integers travel unchanged. Two traits of one
     species almost never carry the same numbers. Settles 17 of 33.
  2. MENTIONS OF PAIRED RECORDS. `Keen Senses` names Insight, Perception and
     Survival; `Sens aiguisés` names Intuition, Perception et Survie -- and
     those skills are already paired records. The trait inherits their proof
     without ever comparing its own words. Settles 6 more.
  3. SIBLING DEGREE, then TRANSITIVE MENTION. Some traits name their own
     siblings: the Dragonborn's ancestry names two of them, its damage
     resistance names one, its breath weapon names none. ⭐ That count is a
     property of the text's SHAPE, identical in both editions (verified on all
     nine species), and it is read inside one language -- it is not a
     cross-language join. Once a sibling is paired, the traits that name it
     pair in turn.
  4. ELIMINATION inside the species. When one trait is left unpaired on each
     side, it is the pair. Same move that settled `chtonien` on the lineages,
     and it is sound because a species is a closed set.

⛔ AND IT REFUSES RATHER THAN GUESS. A species whose sides do not close
completely yields NO keys at all for that species, and says so. A partial
species is not a partial success: it is an unpaired trait wearing a key.
"""

import re
import unicodedata


# The SRD prints distances in feet and the French edition in metres, on the
# fixed scale both editions use. ⛔ Not a conversion of our own: these are the
# pairs the two books actually print against each other.
FEET_TO_METRES = {
    5: "1.5", 10: "3", 15: "4.5", 20: "6", 30: "9",
    60: "18", 90: "27", 120: "36", 150: "45", 300: "90",
}


def _flat(text):
    """Accents stripped, lowercased -- for matching a name inside ONE language."""
    plain = unicodedata.normalize("NFD", text or "")
    plain = "".join(c for c in plain if not unicodedata.combining(c))
    return plain.replace("’", "'").lower()


def numbers_of(text, lang):
    """The numeric fingerprint of a trait's text, on a scale shared by both
    editions. Distances are folded to metres; dice and counts travel as they
    are written.

    ⚠️ Plain integers matter as much as distances. A version of this that kept
    only distances and dice scored 10 pairs where the full fingerprint scores
    17 -- measured, not supposed.
    """
    body = (text or "").replace(" ", " ")
    found = set()

    if lang == "en":
        for match in re.finditer(r"(\d+)\s*(?:feet|foot|ft)\b", body, re.I):
            feet = int(match.group(1))
            found.add("D" + FEET_TO_METRES.get(feet, str(feet)))
    else:
        for match in re.finditer(r"(\d+(?:[.,]\d+)?)\s*m\b", body, re.I):
            found.add("D" + match.group(1).replace(",", "."))

    for match in re.finditer(r"\b(\d*d\d+)\b", body, re.I):
        found.add("d" + match.group(1).lower())

    for match in re.finditer(r"\b(\d+)\b", body):
        tail = body[match.start():match.start() + len(match.group(1)) + 8]
        if re.match(r"^\d+\s*(feet|foot|ft|m\b|m[eè]tre)", tail, re.I):
            continue                                  # already taken as a distance
        around = body[max(0, match.start() - 2):match.end() + 3]
        if re.search(r"d\d", around):
            continue                                  # part of a die expression
        found.add("N" + match.group(1))

    return "|".join(sorted(found))


def mentions_of(text, names_by_address, lang):
    """The addresses of already-paired records this text names, in its own
    language. `names_by_address` maps a shared address to `{"en": …, "fr": …}`.
    """
    body = _flat(text)
    return "|".join(sorted(
        address for address, names in names_by_address.items()
        if names.get(lang) and len(names[lang]) > 3 and _flat(names[lang]) in body
    ))


def siblings_named(trait, traits):
    """The ids of the OTHER traits of this species that this one names.

    ⭐ Read inside a single language: the trait's text against its siblings'
    names, both French or both English. It is a shape, not a translation.
    """
    body = _flat(trait.get("text"))
    return {
        other["id"] for other in traits
        if other.get("id") != trait.get("id")
        and other.get("name") and _flat(other["name"]) in body
    }


class TraitsNotPaired(RuntimeError):
    """A species whose traits did not close on both sides."""


def pair_species_traits(traits_en, traits_fr, names_by_address=None):
    """`{french_id: english_id}` for one species, or raise.

    ⛔ All or nothing. A species that does not close yields nothing: a trait
    that got a key it was not proven to deserve is worse than a trait with no
    key, because nothing downstream can tell the two apart.
    """
    names_by_address = names_by_address or {}
    free_en = {t["id"]: t for t in traits_en if t.get("id")}
    free_fr = {t["id"]: t for t in traits_fr if t.get("id")}
    pairs = {}

    def close(id_en, id_fr, how):
        pairs[id_fr] = (id_en, how)
        free_en.pop(id_en, None)
        free_fr.pop(id_fr, None)

    def sweep(key_en, key_fr, how):
        """Close every trait whose key names exactly one candidate on the other
        side AND is named by exactly one on its own -- a one-way majority is
        not a pair."""
        moved = True
        while moved:
            moved = False
            for id_en in list(free_en):
                key = key_en(free_en[id_en])
                if not key:
                    continue
                cands = [i for i in free_fr if key_fr(free_fr[i]) == key]
                rivals = [i for i in free_en if key_en(free_en[i]) == key]
                if len(cands) == 1 and len(rivals) == 1:
                    close(id_en, cands[0], how)
                    moved = True

    # 1 — les nombres
    sweep(lambda t: numbers_of(t.get("text"), "en"),
          lambda t: numbers_of(t.get("text"), "fr"), "numbers")

    # 2 — les mentions de records déjà appariés
    sweep(lambda t: mentions_of(t.get("text"), names_by_address, "en"),
          lambda t: mentions_of(t.get("text"), names_by_address, "fr"), "mention")

    # 2 bis — LE RECOUVREMENT RÉCIPROQUE des mentions. Les deux éditions ne
    # citent pas toujours le même nombre de termes : le Halfelin anglais nomme
    # `creature` ET `size`, le français seulement `creature`. Une égalité
    # STRICTE d'ensembles rate donc des paires que les preuves partagées
    # désignent sans ambiguïté.
    # ⛔ Mais un recouvrement est plus faible qu'une égalité, alors il est tenu
    # court : le meilleur candidat doit être STRICTEMENT meilleur que le
    # deuxième, et il doit l'être DANS LES DEUX SENS. Un « meilleur » à
    # égalité, ou qui ne se choisit pas réciproquement, ne ferme rien.
    def overlap(id_en, id_fr):
        a = set(mentions_of(free_en[id_en].get("text"), names_by_address, "en").split("|")) - {""}
        b = set(mentions_of(free_fr[id_fr].get("text"), names_by_address, "fr").split("|")) - {""}
        return len(a & b)

    def best(source, others, score):
        marks = sorted(((score(o), o) for o in others), reverse=True)
        if not marks or marks[0][0] == 0:
            return None
        if len(marks) > 1 and marks[1][0] == marks[0][0]:
            return None                                # ⛔ une égalité ne tranche pas
        return marks[0][1]

    moved = True
    while moved:
        moved = False
        for id_en in list(free_en):
            pick = best(id_en, list(free_fr), lambda f: overlap(id_en, f))
            if pick is None:
                continue
            back = best(pick, list(free_en), lambda e: overlap(e, pick))
            if back == id_en:                          # ⭐ réciproque, sinon rien
                close(id_en, pick, "mention-overlap")
                moved = True

    # 3 — le degré de mention entre frères, puis la mention transitive
    sweep(lambda t: "deg:%d" % len(siblings_named(t, traits_en)),
          lambda t: "deg:%d" % len(siblings_named(t, traits_fr)), "sibling-degree")

    def through_siblings(trait, traits, side):
        named = siblings_named(trait, traits)
        keys = []
        for other in named:
            if side == "en":
                keys += [pairs[fr][0] for fr in pairs if pairs[fr][0] == other]
            elif other in pairs:
                keys.append(pairs[other][0])
        return "via:" + "|".join(sorted(set(keys))) if keys else ""

    sweep(lambda t: through_siblings(t, traits_en, "en"),
          lambda t: through_siblings(t, traits_fr, "fr"), "sibling-transitive")

    # 4 — l'élimination : un seul de chaque côté
    while len(free_en) == 1 and len(free_fr) == 1:
        close(next(iter(free_en)), next(iter(free_fr)), "elimination")

    if free_en or free_fr:
        raise TraitsNotPaired(
            "traits did not close: %d English (%s) and %d French (%s) left unpaired; "
            "a species yields keys for all of its traits or for none of them"
            % (len(free_en), ", ".join(sorted(free_en)) or "-",
               len(free_fr), ", ".join(sorted(free_fr)) or "-")
        )
    return {fr: how[0] for fr, how in pairs.items()}, {fr: how[1] for fr, how in pairs.items()}
