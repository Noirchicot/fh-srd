"""A weapon's properties, as a list you can tick instead of a sentence.

WHAT THIS CLOSES. `data.properties` is one printed sentence --
`"Finesse, Light, Thrown (Range 20/60)"` -- and a sentence does not tick. Nine
distinct properties live inside it, each already a record of its own in the
`weapon-property` genre with its definition. A screen that wants to filter on
"light weapons" has to cut that string; so does anyone who wants to know
whether a weapon a player just invented behaves like a shortsword.

⛔ THE STRING IS NOT REPLACED. It is what the book prints, and the layer stays
a faithful copy; the list is derived BESIDE it. That also makes the conversion
free to check: recompose the sentence from the list and it must come back
word for word, on all 38 weapons, in both languages.

🔴 AND YOU CANNOT SPLIT IT ON COMMAS. The French prints
`"Munitions (portée 7,50/30 ; dards)"` -- a DECIMAL COMMA inside the
parenthesis -- so a naive split cuts a range in half and invents a tenth
property called "50/30 ; dards)". Depth-aware splitting is not defensive
programming here, it is the difference between right and wrong on a real row.

⚠️ A parenthesis carries three different kinds of thing, and they are not
interchangeable: a die (`Versatile (1d10)`), a range plus an ammunition type
(`Ammunition (Range 25/100; Needle)`), and a plain condition
(`Two-Handed (unless mounted)` / `Deux mains (sauf à cheval)`). Kept VERBATIM
in `detail`, not taken apart: turning a range into numbers means choosing feet
or metres and parsing a French decimal comma, which is the typed-field work
(route versatilité, étape 3) and not an extraction repair.
"""


def split_properties(text):
    """Split on the commas that are OUTSIDE any parenthesis.

    Returns [] for None or an empty string -- three weapons carry no property
    at all, and that is an answer, not a gap.
    """
    if not text:
        return []
    parts, buffer, depth = [], "", 0
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if char == "," and depth == 0:
            parts.append(buffer.strip())
            buffer = ""
        else:
            buffer += char
    if buffer.strip():
        parts.append(buffer.strip())
    return [p for p in parts if p]


def split_one(part):
    """`Thrown (Range 20/60)` -> ("Thrown", "Range 20/60"). No paren -> detail None."""
    if part.endswith(")") and "(" in part:
        head, _, tail = part.partition("(")
        return head.strip(), tail[:-1].strip()
    return part.strip(), None


# The property names each language prints, mapped to ONE set of English keys.
#
# ⛔ The keys are English on both sides, and that is the rule the versatility
# route settled: one set of keys, the French living in the labels above them.
# `Légère` and `Light` are the same key `light`; only what a screen prints
# differs.
#
# A closed set per language, because the book prints a closed set: an
# unrecognised name is an extraction defect, not a tenth property to invent.
# Every one of these names is also a `weapon-property` record, which is what
# keeps one vocabulary instead of two.
PROPERTY_KEYS = {
    "en": {
        "Ammunition": "ammunition", "Finesse": "finesse", "Heavy": "heavy",
        "Light": "light", "Loading": "loading", "Reach": "reach",
        "Thrown": "thrown", "Two-Handed": "two-handed", "Versatile": "versatile",
        "Improvised Weapons": "improvised-weapons", "Range": "range",
    },
    "fr": {
        "Munitions": "ammunition", "Finesse": "finesse", "Lourde": "heavy",
        "Légère": "light", "Chargement": "loading", "Allonge": "reach",
        "Lancer": "thrown", "Deux mains": "two-handed", "Polyvalente": "versatile",
        "Armes improvisées": "improvised-weapons", "Portée": "range",
    },
}


class UnknownProperty(ValueError):
    """A property name the book is not known to print in this language."""


def property_list(text, lang):
    """The printed sentence, as a list of {key, label} plus `detail` when the
    book puts something in a parenthesis.

    Order is the book's own, which is what lets `recompose` be an exact test.
    """
    keys = PROPERTY_KEYS[lang]
    out = []
    for part in split_properties(text):
        label, detail = split_one(part)
        key = keys.get(label)
        if key is None:
            raise UnknownProperty(
                "weapon property %r is not one of the %d the SRD prints in %r "
                "(%s). A tenth name is an extraction defect, not a property to "
                "invent." % (label, len(keys), lang, ", ".join(sorted(keys)))
            )
        entry = {"key": key, "label": label}
        if detail is not None:
            entry["detail"] = detail
        out.append(entry)
    return out


def recompose(items):
    """Rebuild the printed sentence from the list.

    ⭐ THIS IS THE PROOF, and it costs nothing: if what comes back is not the
    string the book printed, character for character, the conversion lost or
    invented something. Run over all 38 weapons in both languages by
    `tests/test_weapon_properties.py`.
    """
    if not items:
        return None
    return ", ".join(
        "%s (%s)" % (i["label"], i["detail"]) if "detail" in i else i["label"]
        for i in items
    )
