"""Static reference site — exports/srd/{en,fr}/*.json -> web/{lang}/{kind}/index.html.

This is a downstream consumer, not a producer: it reads the already-exported,
already-verified JSON under `exports/srd/` and never touches the database, the
parsers, or `exports/MANIFEST.json` itself. If a record looks wrong here, the
fix belongs in the importer, not in this file.

URL contract (frozen, do not rename slugs or restructure paths):

    web/{lang}/{kind}/index.html#{slug}

The Fate's Hand Player Companion links directly to that shape. Nothing about
site *styling* is contractual — only the path and the anchor.

Determinism follows from the inputs: `exports/srd/*.json` is itself byte-stable
(see `export_json.py`), record order inside each file is fixed, and this
module does no non-deterministic iteration (no bare `set`/`dict` ordering that
isn't itself derived from the fixed field-order tables below). Two runs over
the same exports tree produce byte-identical HTML.

Run:
    python3 src/build_web.py                # exports/srd -> web/
    python3 src/build_web.py --out DIR       # write elsewhere (tests use this)
"""

import argparse
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EXPORTS = os.path.join(ROOT, "exports", "srd")
WEB = os.path.join(ROOT, "web")

LANGS = ("en", "fr")

# Display order matters (it is the nav order on every page) and is therefore
# part of the fixed, deterministic output — not derived from a directory
# listing.
KINDS = (
    "spell", "monster", "class", "class-progression", "skill", "feat",
    "species", "background", "armor", "weapon", "gear", "tool", "item",
    "glossary",
)

CC_BY_URL = "https://creativecommons.org/licenses/by/4.0/legalcode"


# ---------------------------------------------------------------------------
# UI strings. The SRD *data* is already localised per export file; only the
# chrome around it (labels, nav, search placeholder) needs translating here.
# ---------------------------------------------------------------------------

KIND_LABEL = {
    "en": {
        "spell": "Spells", "monster": "Monsters", "class": "Classes",
        "class-progression": "Class Progression", "skill": "Skills",
        "feat": "Feats", "species": "Species", "background": "Backgrounds",
        "armor": "Armor", "weapon": "Weapons", "gear": "Gear",
        "tool": "Tools", "item": "Magic Items", "glossary": "Glossary",
    },
    "fr": {
        "spell": "Sorts", "monster": "Monstres", "class": "Classes",
        "class-progression": "Progression de classe", "skill": "Compétences",
        "feat": "Dons", "species": "Espèces", "background": "Historiques",
        "armor": "Armures", "weapon": "Armes", "gear": "Équipement",
        "tool": "Outils", "item": "Objets magiques", "glossary": "Glossaire",
    },
}

FIELD_LABEL = {
    "en": {
        "casting_time": "Casting Time", "range": "Range", "components": "Components",
        "duration": "Duration", "classes": "Classes", "ritual": "Ritual",
        "size_type": "Size & Type", "ac": "Armor Class", "hp": "Hit Points",
        "initiative": "Initiative", "speed": "Speed", "skills": "Skills",
        "senses": "Senses", "languages": "Languages", "cr": "Challenge Rating",
        "immunities": "Immunities", "resistances": "Resistances",
        "vulnerabilities": "Vulnerabilities", "gear": "Gear", "tags": "Tags",
        "traits": "Traits", "actions": "Actions", "bonus_actions": "Bonus Actions",
        "reactions": "Reactions", "legendary_actions": "Legendary Actions",
        "hit_point_die": "Hit Point Die", "primary_ability": "Primary Ability",
        "saving_throw_proficiencies": "Saving Throw Proficiencies",
        "armor_training": "Armor Training", "weapon_proficiencies": "Weapon Proficiencies",
        "tool_proficiencies": "Tool Proficiencies", "skill_proficiencies": "Skill Proficiencies",
        "starting_equipment": "Starting Equipment", "features": "Class Features",
        "subclass": "Subclass", "category": "Category", "prerequisite": "Prerequisite",
        "creature_type": "Creature Type", "size": "Size",
        "ability_scores": "Ability Scores", "tool_proficiency": "Tool Proficiency",
        "feat": "Bonus Feat", "equipment": "Equipment", "armor_class": "Armor Class",
        "cost": "Cost", "weight": "Weight", "strength": "Strength Requirement",
        "stealth_disadvantage": "Stealth Disadvantage", "damage": "Damage",
        "properties": "Properties", "mastery": "Mastery", "ability": "Key Ability",
        "craft": "Craft", "utilize": "Utilize", "variants": "Variants",
        "subtype": "Subtype", "rarity": "Rarity", "attunement": "Requires Attunement",
        "tag": "Tag", "example_uses": "Example Uses", "level": "Level",
        "proficiency_bonus": "Proficiency Bonus",
        "spell_slots": "Spell Slots per Spell Level",
    },
    "fr": {
        "casting_time": "Temps d'incantation", "range": "Portée", "components": "Composantes",
        "duration": "Durée", "classes": "Classes", "ritual": "Rituel",
        "size_type": "Taille et type", "ac": "Classe d'armure", "hp": "Points de vie",
        "initiative": "Initiative", "speed": "Vitesse", "skills": "Compétences",
        "senses": "Sens", "languages": "Langues", "cr": "Facteur de puissance",
        "immunities": "Immunités", "resistances": "Résistances",
        "vulnerabilities": "Vulnérabilités", "gear": "Équipement", "tags": "Étiquettes",
        "traits": "Traits", "actions": "Actions", "bonus_actions": "Actions bonus",
        "reactions": "Réactions", "legendary_actions": "Actions légendaires",
        "hit_point_die": "Dé de vie", "primary_ability": "Caractéristique principale",
        "saving_throw_proficiencies": "Jets de sauvegarde maîtrisés",
        "armor_training": "Entraînement aux armures", "weapon_proficiencies": "Maîtrise des armes",
        "tool_proficiencies": "Maîtrise des outils", "skill_proficiencies": "Compétences maîtrisées",
        "starting_equipment": "Équipement de départ", "features": "Aptitudes de classe",
        "subclass": "Sous-classe", "category": "Catégorie", "prerequisite": "Prérequis",
        "creature_type": "Type de créature", "size": "Taille",
        "ability_scores": "Caractéristiques", "tool_proficiency": "Maîtrise d'outil",
        "feat": "Don bonus", "equipment": "Équipement", "armor_class": "Classe d'armure",
        "cost": "Coût", "weight": "Poids", "strength": "Force requise",
        "stealth_disadvantage": "Désavantage en discrétion", "damage": "Dégâts",
        "properties": "Propriétés", "mastery": "Maîtrise (bonus)", "ability": "Caractéristique clé",
        "craft": "Fabrication", "utilize": "Utilisation", "variants": "Variantes",
        "subtype": "Sous-type", "rarity": "Rareté", "attunement": "Harmonisation requise",
        "tag": "Étiquette", "example_uses": "Exemples d’application", "level": "Niveau",
        "proficiency_bonus": "Bonus de maîtrise",
        "spell_slots": "Emplacements par niveau de sort",
    },
}

# The FR export keys abilities in French (for/sag), not a transliteration of
# the EN keys (str/wis) — the data files disagree on this, so the display
# order is keyed per language rather than assumed shared.
ABILITY_KEYS = {
    "en": ("str", "dex", "con", "int", "wis", "cha"),
    "fr": ("for", "dex", "con", "int", "sag", "cha"),
}
ABILITY_LABEL = {
    "en": {"str": "STR", "dex": "DEX", "con": "CON", "int": "INT", "wis": "WIS", "cha": "CHA"},
    "fr": {"for": "FOR", "dex": "DEX", "con": "CON", "int": "INT", "sag": "SAG", "cha": "CHA"},
}

UI = {
    "en": {
        "site_title": "Fate's Hand SRD Reference",
        "home": "Home",
        "all_categories": "All categories",
        "search_placeholder": "Filter by name…",
        "shown_of": "{shown} / {total}",
        "other_lang_name": "Français",
        "other_lang_code": "fr",
        "attribution_heading": "Source & Licence",
        "no_results": "No matches.",
        "records_count": "{n} records",
    },
    "fr": {
        "site_title": "Référence SRD — Fate's Hand",
        "home": "Accueil",
        "all_categories": "Toutes les catégories",
        "search_placeholder": "Filtrer par nom…",
        "shown_of": "{shown} / {total}",
        "other_lang_name": "English",
        "other_lang_code": "en",
        "attribution_heading": "Source et licence",
        "no_results": "Aucun résultat.",
        "records_count": "{n} entrées",
    },
}

ORDINAL_SUFFIX_EN = {1: "st", 2: "nd", 3: "rd"}


def ordinal(n, lang):
    if lang == "fr":
        return "1er" if n == 1 else "%de" % n
    return "%d%s" % (n, ORDINAL_SUFFIX_EN.get(n if n < 20 else n % 10, "th"))


def esc(value):
    return html.escape(str(value), quote=False)


def esc_attr(value):
    return html.escape(str(value), quote=True)


_PARA_SPLIT = re.compile(r"\n{2,}")


def paragraphs(text):
    parts = [p.strip() for p in _PARA_SPLIT.split(text) if p.strip()]
    out = []
    for p in parts:
        out.append("<p>%s</p>" % esc(p).replace("\n", "<br>"))
    return "".join(out)


def yesno(value, lang):
    if lang == "fr":
        return "Oui" if value else "Non"
    return "Yes" if value else "No"


def fmt_value(value, lang):
    if isinstance(value, bool):
        return yesno(value, lang)
    if isinstance(value, list):
        return esc(", ".join(str(v) for v in value))
    return esc(value)


# ---------------------------------------------------------------------------
# Per-kind body renderers. Every record within a given kind carries the exact
# same set of `data` keys (asserted at build time), so a fixed field-order
# table per kind is safe rather than a guess.
# ---------------------------------------------------------------------------

GENERIC_ORDER = {
    "feat": ("category", "prerequisite", "description"),
    "species": ("creature_type", "size", "speed", "description"),
    "background": ("ability_scores", "skill_proficiencies", "tool_proficiency", "feat", "equipment"),
    "armor": ("armor_class", "cost", "weight", "strength", "stealth_disadvantage"),
    "weapon": ("cost", "damage", "properties", "mastery", "weight"),
    "gear": ("cost", "weight"),
    "tool": ("ability", "cost", "craft", "utilize", "variants", "weight"),
    "item": ("category", "subtype", "rarity", "attunement", "description"),
    "glossary": ("tag", "description"),
    "skill": ("ability", "example_uses"),
}

# Boolean fields that are only worth showing when true (a "No" row on every
# single weapon/item is noise, not information).
BOOL_SHOW_ONLY_IF_TRUE = {"stealth_disadvantage", "attunement"}


def render_generic(kind, data, lang):
    rows = []
    prose = ""
    for key in GENERIC_ORDER[kind]:
        value = data.get(key)
        if key == "description":
            if value:
                prose = paragraphs(value)
            continue
        if value is None or value == "" or value == []:
            continue
        if isinstance(value, bool):
            if not value and key in BOOL_SHOW_ONLY_IF_TRUE:
                continue
            if value and key in BOOL_SHOW_ONLY_IF_TRUE:
                rows.append('<div class="stat"><dt>%s</dt></div>' % FIELD_LABEL[lang][key])
                continue
        rows.append(
            '<div class="stat"><dt>%s</dt><dd>%s</dd></div>'
            % (FIELD_LABEL[lang][key], fmt_value(value, lang))
        )
    out = ""
    if rows:
        out += '<dl class="stats">%s</dl>' % "".join(rows)
    out += prose
    return out


def render_spell(data, lang):
    school = str(data["school"]).capitalize()
    if data["cantrip"]:
        head = "%s %s" % (school, "cantrip" if lang == "en" else "(sort mineur)")
    else:
        head = "%s-level %s" % (ordinal(data["level"], lang), school) if lang == "en" \
            else "%s niveau — %s" % (ordinal(data["level"], lang), school)
    if data["ritual"]:
        head += " (%s)" % ("ritual" if lang == "en" else "rituel")
    rows = [
        '<div class="stat"><dt>%s</dt><dd>%s</dd></div>' % (FIELD_LABEL[lang]["casting_time"], esc(data["casting_time"])),
        '<div class="stat"><dt>%s</dt><dd>%s</dd></div>' % (FIELD_LABEL[lang]["range"], esc(data["range"])),
        '<div class="stat"><dt>%s</dt><dd>%s</dd></div>' % (FIELD_LABEL[lang]["components"], esc(data["components"])),
        '<div class="stat"><dt>%s</dt><dd>%s</dd></div>' % (FIELD_LABEL[lang]["duration"], esc(data["duration"])),
    ]
    if data.get("classes"):
        rows.append(
            '<div class="stat"><dt>%s</dt><dd>%s</dd></div>'
            % (FIELD_LABEL[lang]["classes"], fmt_value(data["classes"], lang))
        )
    return (
        '<p class="subtitle">%s</p><dl class="stats">%s</dl>%s'
        % (esc(head), "".join(rows), paragraphs(data["description"]))
    )


def _named_block_list(items, lang):
    out = []
    for item in items:
        out.append(
            '<div class="named-block"><h4>%s</h4>%s</div>'
            % (esc(item["name"]), paragraphs(item["description"]))
        )
    return "".join(out)


def render_monster(data, lang):
    L = FIELD_LABEL[lang]
    out = ['<p class="subtitle">%s</p>' % esc(data["size_type"])]

    top_rows = [
        '<div class="stat"><dt>%s</dt><dd>%s</dd></div>' % (L["ac"], esc(data["ac"])),
        '<div class="stat"><dt>%s</dt><dd>%s</dd></div>' % (L["hp"], esc(data["hp"])),
        '<div class="stat"><dt>%s</dt><dd>%s</dd></div>' % (L["initiative"], esc(data["initiative"])),
        '<div class="stat"><dt>%s</dt><dd>%s</dd></div>' % (L["speed"], esc(data["speed"])),
    ]
    out.append('<dl class="stats">%s</dl>' % "".join(top_rows))

    ab_labels = ABILITY_LABEL[lang]
    ab_cells = []
    for key in ABILITY_KEYS[lang]:
        a = data["abilities"][key]
        ab_cells.append(
            '<div class="ability"><span class="ab-name">%s</span>'
            '<span class="ab-score">%s</span>'
            '<span class="ab-mod">%+d / %+d</span></div>'
            % (ab_labels[key], a["score"], a["mod"], a["save"])
        )
    out.append('<div class="abilities">%s</div>' % "".join(ab_cells))

    mid_rows = []
    for key in ("skills", "senses", "languages", "cr", "immunities", "resistances", "vulnerabilities", "gear", "tags"):
        value = data.get(key)
        if not value:
            continue
        mid_rows.append('<div class="stat"><dt>%s</dt><dd>%s</dd></div>' % (L[key], esc(value)))
    if mid_rows:
        out.append('<dl class="stats">%s</dl>' % "".join(mid_rows))

    for key in ("traits", "actions", "bonus_actions", "reactions"):
        items = data.get(key)
        if items:
            out.append('<h3>%s</h3>%s' % (L[key], _named_block_list(items, lang)))

    legendary = data.get("legendary_actions")
    if legendary and (legendary.get("intro") or legendary.get("options")):
        out.append("<h3>%s</h3>" % L["legendary_actions"])
        if legendary.get("intro"):
            out.append(paragraphs(legendary["intro"]))
        if legendary.get("options"):
            out.append(_named_block_list(legendary["options"], lang))

    return "".join(out)


def render_class(data, lang):
    L = FIELD_LABEL[lang]
    rows = []
    for key in (
        "hit_point_die", "primary_ability", "saving_throw_proficiencies",
        "armor_training", "weapon_proficiencies", "tool_proficiencies",
        "skill_proficiencies", "starting_equipment",
    ):
        value = data.get(key)
        if not value:
            continue
        rows.append('<div class="stat"><dt>%s</dt><dd>%s</dd></div>' % (L[key], fmt_value(value, lang)))
    out = ['<dl class="stats">%s</dl>' % "".join(rows)]
    if data.get("description"):
        out.append(paragraphs(data["description"]))

    if data.get("features"):
        out.append("<h3>%s</h3>" % L["features"])
        for feat in data["features"]:
            out.append(
                '<div class="named-block"><h4>%s <span class="level-tag">%s %s</span></h4>%s</div>'
                % (
                    esc(feat["name"]),
                    "Lvl" if lang == "en" else "Niv.",
                    feat["level"],
                    paragraphs(feat["description"]),
                )
            )

    sub = data.get("subclass")
    if sub:
        out.append('<h3>%s — %s</h3>' % (L["subclass"], esc(sub["name"])))
        if sub.get("description"):
            out.append(paragraphs(sub["description"]))
        for feat in sub.get("features", []):
            out.append(
                '<div class="named-block"><h4>%s <span class="level-tag">%s %s</span></h4>%s</div>'
                % (
                    esc(feat["name"]),
                    "Lvl" if lang == "en" else "Niv.",
                    feat["level"],
                    paragraphs(feat["description"]),
                )
            )
    return "".join(out)


def render_class_progression(data, lang):
    """The level table, rendered as the table it is.

    Every other kind on this site is a stat block or a prose entry; this one
    is a grid, and flattening it into a definition list would make the one
    lookup it exists for -- "what does level 3 give me" -- unreadable. The
    header is rebuilt from the record's own `resource_columns` and
    `spell_slot_levels` rather than from a per-class layout table here: the
    columns are data, and the site must not carry a second copy of them.
    """
    L = FIELD_LABEL[lang]
    resources = data["resource_columns"]
    slot_levels = data["spell_slot_levels"]

    head = ["<th>%s</th>" % esc(L["level"]),
            "<th>%s</th>" % esc(L["proficiency_bonus"]),
            "<th>%s</th>" % esc(L["features"])]
    head += ["<th>%s</th>" % esc(col["label"]) for col in resources]
    if slot_levels:
        head += ["<th>%s</th>" % ordinal(n, lang) for n in range(1, slot_levels + 1)]

    body = []
    for row in data["levels"]:
        cells = ["<td>%d</td>" % row["level"],
                 "<td>+%d</td>" % row["proficiency_bonus"],
                 "<td>%s</td>" % esc(", ".join(row["features"]) or "—")]
        for col in resources:
            value = row["resources"].get(col["key"])
            cells.append("<td>%s</td>" % ("—" if value is None else esc(value)))
        for slots in row.get("spell_slots", []):
            cells.append("<td>%s</td>" % (slots if slots else "—"))
        body.append("<tr>%s</tr>" % "".join(cells))

    caption = ""
    if slot_levels:
        caption = '<caption>%s</caption>' % esc(L["spell_slots"])
    return (
        '<div class="table-wrap"><table class="progression">%s<thead><tr>%s</tr>'
        '</thead><tbody>%s</tbody></table></div>'
        % (caption, "".join(head), "".join(body))
    )


SPECIAL_RENDERERS = {
    "spell": render_spell,
    "monster": render_monster,
    "class": render_class,
    "class-progression": render_class_progression,
}


def render_record_body(kind, data, lang):
    renderer = SPECIAL_RENDERERS.get(kind)
    if renderer:
        return renderer(data, lang)
    return render_generic(kind, data, lang)


# ---------------------------------------------------------------------------
# Page shell (shared CSS/JS, inline, no CDN, no remote fonts).
# ---------------------------------------------------------------------------

CSS = """
:root {
  --bg: #fbf9f5; --fg: #201c16; --muted: #6b6255; --border: #ddd4c4;
  --card: #ffffff; --accent: #8a3324; --link: #8a3324; --code-bg: #f1ece0;
  color-scheme: light dark;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #16140f; --fg: #ece6d9; --muted: #a89e8b; --border: #3a3427;
    --card: #1e1b14; --accent: #e0a37a; --link: #e0a37a; --code-bg: #221f17;
  }
}
* { box-sizing: border-box; }
[hidden] { display: none !important; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0; background: var(--bg); color: var(--fg);
  font: 16px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
a { color: var(--link); }
.wrap { max-width: 900px; margin: 0 auto; padding: 1rem 1.25rem 4rem; }
header.site {
  border-bottom: 1px solid var(--border); padding: 0.75rem 0; margin-bottom: 1rem;
  display: flex; flex-wrap: wrap; gap: 0.5rem 1rem; align-items: baseline; justify-content: space-between;
}
header.site h1 { font-size: 1.1rem; margin: 0; }
header.site nav a { margin-right: 0.75rem; text-decoration: none; }
header.site nav a:hover { text-decoration: underline; }
.langlink { font-size: 0.9rem; border: 1px solid var(--border); border-radius: 999px; padding: 0.15rem 0.7rem; text-decoration: none; }
h1, h2, h3, h4 { font-family: Georgia, "Times New Roman", serif; line-height: 1.25; }
h1 { font-size: 1.6rem; }
.search-bar { position: sticky; top: 0; background: var(--bg); padding: 0.6rem 0; z-index: 5; border-bottom: 1px solid var(--border); margin-bottom: 1rem; }
.search-bar input[type=search] {
  width: 100%; padding: 0.6rem 0.8rem; font-size: 1rem; border: 1px solid var(--border);
  border-radius: 0.5rem; background: var(--card); color: var(--fg);
}
.search-bar .count { color: var(--muted); font-size: 0.85rem; margin: 0.35rem 0 0; }
article.record {
  background: var(--card); border: 1px solid var(--border); border-radius: 0.6rem;
  padding: 1rem 1.25rem; margin-bottom: 1rem;
}
article.record h2 { margin: 0 0 0.15rem; font-size: 1.25rem; }
article.record h2 a { text-decoration: none; color: inherit; }
article.record .subtitle { margin: 0 0 0.6rem; color: var(--muted); font-style: italic; }
dl.stats { display: flex; flex-wrap: wrap; gap: 0.35rem 1.5rem; margin: 0.4rem 0; padding: 0; }
dl.stats .stat { display: flex; gap: 0.35rem; margin: 0; }
dl.stats dt { font-weight: 600; color: var(--muted); }
dl.stats dd { margin: 0; }
.abilities { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.6rem 0; }
.ability { background: var(--code-bg); border-radius: 0.4rem; padding: 0.3rem 0.55rem; text-align: center; min-width: 4.2rem; font-size: 0.85rem; }
.ability .ab-name { display: block; font-weight: 700; }
.ability .ab-score { display: block; }
.ability .ab-mod { display: block; color: var(--muted); }
.named-block { margin: 0.6rem 0; }
.named-block h4 { margin: 0 0 0.15rem; font-size: 1rem; }
.level-tag { color: var(--muted); font-weight: 400; font-size: 0.85rem; }
.table-wrap { overflow-x: auto; margin: 0.6rem 0; }
table.progression { border-collapse: collapse; font-size: 0.85rem; white-space: nowrap; }
table.progression caption { text-align: left; color: var(--muted); font-size: 0.8rem; padding-bottom: 0.3rem; }
table.progression th, table.progression td { border: 1px solid var(--border); padding: 0.2rem 0.45rem; text-align: left; }
table.progression th { background: var(--code-bg); font-weight: 600; }
table.progression td:first-child { font-weight: 700; }
article.record p { margin: 0.5rem 0; }
footer.attribution {
  border-top: 1px solid var(--border); margin-top: 2rem; padding-top: 1rem;
  color: var(--muted); font-size: 0.85rem;
}
footer.attribution h2 { font-size: 0.95rem; color: var(--fg); }
.index-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 0.75rem; margin: 1rem 0; }
.index-grid a {
  display: block; background: var(--card); border: 1px solid var(--border); border-radius: 0.5rem;
  padding: 0.8rem 1rem; text-decoration: none; color: var(--fg);
}
.index-grid a:hover { border-color: var(--accent); }
.index-grid .n { color: var(--muted); font-size: 0.85rem; display: block; }
.langswitch { display: flex; gap: 0.5rem; margin: 1rem 0; }
.langswitch button {
  border: 1px solid var(--border); background: var(--card); color: var(--fg);
  border-radius: 999px; padding: 0.35rem 1rem; font-size: 0.95rem; cursor: pointer;
}
.langswitch button[aria-pressed=true] { background: var(--accent); color: var(--bg); border-color: var(--accent); }
@media (max-width: 600px) {
  .wrap { padding: 0.75rem 0.9rem 3rem; }
  dl.stats { gap: 0.25rem 1rem; }
}
"""

SEARCH_JS = """
(function () {
  var q = document.getElementById("q");
  var items = Array.prototype.slice.call(document.querySelectorAll("#list > .record"));
  var shownEl = document.getElementById("shown");
  function apply() {
    var v = q.value.trim().toLowerCase();
    var n = 0;
    items.forEach(function (el) {
      var match = !v || el.getAttribute("data-name").indexOf(v) !== -1;
      el.hidden = !match;
      if (match) n += 1;
    });
    shownEl.textContent = n;
  }
  q.addEventListener("input", apply);
  apply();
})();
"""

LANGSWITCH_JS = """
(function () {
  var buttons = Array.prototype.slice.call(document.querySelectorAll(".langswitch button"));
  buttons.forEach(function (b) {
    b.addEventListener("click", function () {
      buttons.forEach(function (x) { x.setAttribute("aria-pressed", String(x === b)); });
      document.getElementById("panel-" + b.getAttribute("data-lang")).hidden = false;
      buttons.forEach(function (x) {
        if (x !== b) document.getElementById("panel-" + x.getAttribute("data-lang")).hidden = true;
      });
    });
  });
})();
"""


def page_shell(lang, title, body, extra_head=""):
    ui = UI[lang]
    return (
        "<!doctype html>\n"
        '<html lang="%s">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>%s</title>\n"
        "<style>%s</style>\n"
        "%s"
        "</head>\n<body>\n<div class=\"wrap\">\n%s\n</div>\n</body>\n</html>\n"
    ) % (lang, esc(title), CSS, extra_head, body)


def kind_page(lang, kind, records):
    ui = UI[lang]
    label = KIND_LABEL[lang][kind]
    items_html = []
    for rec in records:
        slug = rec["slug"]
        name = rec["name"]
        body = render_record_body(kind, rec["data"], lang)
        items_html.append(
            '<article class="record" id="%s" data-name="%s">'
            '<h2><a href="#%s">%s</a></h2>%s</article>'
            % (esc_attr(slug), esc_attr(name.lower()), esc_attr(slug), esc(name), body)
        )

    attribution = records[0]["attribution"] if records else ""
    srd_version = records[0]["srd_version"] if records else ""

    header = (
        '<header class="site"><h1><a href="../../index.html">%s</a></h1>'
        '<nav><a href="../../index.html">%s</a> '
        '<span> · </span> <a href="../../%s/%s/index.html" class="langlink">%s</a></nav></header>'
    ) % (esc(ui["site_title"]), esc(ui["all_categories"]), ui["other_lang_code"], kind, esc(ui["other_lang_name"]))

    search = (
        '<div class="search-bar">'
        '<input type="search" id="q" placeholder="%s" aria-label="%s">'
        '<p class="count"><span id="shown">%d</span> / %d</p>'
        "</div>"
    ) % (esc_attr(ui["search_placeholder"]), esc_attr(ui["search_placeholder"]), len(records), len(records))

    footer = (
        '<footer class="attribution"><h2>%s</h2><p>%s</p>'
        '<p>SRD %s · <a href="%s">CC BY 4.0</a></p></footer>'
    ) % (esc(ui["attribution_heading"]), esc(attribution), esc(srd_version), CC_BY_URL)

    body = (
        "<h1>%s</h1>%s"
        '<div id="list">%s</div>'
        "%s"
        "<script>%s</script>"
    ) % (esc(label), search, "".join(items_html), footer, SEARCH_JS)

    title = "%s — %s" % (label, ui["site_title"])
    return page_shell(lang, title, header + body)


def root_index(counts):
    """counts: {lang: {kind: n}}"""
    panels = []
    buttons = []
    for i, lang in enumerate(LANGS):
        ui = UI[lang]
        pressed = "true" if i == 0 else "false"
        buttons.append(
            '<button type="button" data-lang="%s" aria-pressed="%s">%s</button>'
            % (lang, pressed, esc(_LANG_NAME[lang]))
        )
        links = []
        for kind in KINDS:
            n = counts[lang][kind]
            links.append(
                '<a href="%s/%s/index.html">%s<span class="n">%s</span></a>'
                % (lang, kind, esc(KIND_LABEL[lang][kind]), esc(ui["records_count"].format(n=n)))
            )
        hidden = "" if i == 0 else " hidden"
        panels.append(
            '<section id="panel-%s" class="index-grid"%s>%s</section>' % (lang, hidden, "".join(links))
        )

    body = (
        "<h1>Fate's Hand — SRD 5.2.1 Reference</h1>"
        '<p>System Reference Document 5.2.1, browsable by category, in English and French. '
        "Generated from the fh-srd import; every entry links back to its own attribution and licence.</p>"
        '<div class="langswitch">%s</div>'
        "%s"
        "<script>%s</script>"
    ) % ("".join(buttons), "".join(panels), LANGSWITCH_JS)

    return page_shell("en", "Fate's Hand — SRD 5.2.1 Reference", body)


_LANG_NAME = {"en": "English", "fr": "Français"}


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def load_kind(exports_dir, lang, kind):
    path = os.path.join(exports_dir, lang, kind + ".json")
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    records = payload["records"]
    attrs = set(r["attribution"] for r in records)
    assert len(attrs) <= 1, "mixed attribution within one export file: %s/%s" % (lang, kind)
    return records


def _refuse_unrendered_kinds(exports_dir):
    """A kind in the exports that this site does not render is a silent drop.

    KINDS is a fixed tuple on purpose -- it is the nav order and part of the
    deterministic output -- but "fixed" and "stale" look identical from the
    outside. When `class-progression` and `skill` were added to the importer,
    the site kept building, kept passing its contract test, and simply did
    not publish them: the contract test iterates KINDS, so what is missing
    from KINDS is invisible to it. This is the loud version.
    """
    present = set()
    for lang in LANGS:
        directory = os.path.join(exports_dir, lang)
        if not os.path.isdir(directory):
            continue
        for entry in os.listdir(directory):
            if entry.endswith(".json"):
                present.add(entry[: -len(".json")])
    missing = sorted(present - set(KINDS))
    if missing:
        raise SystemExit(
            "exports carry kind(s) the site does not render: %s\n"
            "  Add them to KINDS, KIND_LABEL (both languages) and either\n"
            "  GENERIC_ORDER or SPECIAL_RENDERERS -- or state why they are\n"
            "  deliberately unpublished. Building without them ships a\n"
            "  reference site that quietly lacks part of the catalogue."
            % ", ".join(missing)
        )


def build(out_dir=WEB, exports_dir=EXPORTS):
    _refuse_unrendered_kinds(exports_dir)
    counts = {lang: {} for lang in LANGS}
    for lang in LANGS:
        for kind in KINDS:
            records = load_kind(exports_dir, lang, kind)
            counts[lang][kind] = len(records)
            html_text = kind_page(lang, kind, records)
            write(os.path.join(out_dir, lang, kind, "index.html"), html_text)
    write(os.path.join(out_dir, "index.html"), root_index(counts))
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=WEB, help="output directory (default: web/)")
    parser.add_argument("--exports", default=EXPORTS, help="exports/srd directory to read from")
    args = parser.parse_args(argv)
    counts = build(args.out, args.exports)
    total = sum(sum(k.values()) for k in counts.values())
    print("built %d pages, %d records" % (len(LANGS) * len(KINDS) + 1, total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
