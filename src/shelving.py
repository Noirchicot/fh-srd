"""Where an object is SHELVED, and where on a body it is WORN.

The SRD prints 416 pieces of equipment and never says where to look for one.
There is no aisle, no shelf, no body location anywhere in the book — those are
Fate's Hand decisions taken on the book's own matter, which is what the `srfh`
layer is for. Eric arrested the classification by hand on the 21st and 22nd of
August 2026; this module makes it machine-readable.

TWO AXES, NEVER ONE. Eric's own words: *ou ca se range, ou ca se porte*. The
shelf answers "where do I look for it", the slot answers "where do I wear it".
Boots and cloaks share a shelf and take two different slots; an amulet and a
ring are both jewellery and go to the neck and to the fingers. Folding the two
into one field costs a second pass over the whole catalogue, so they are two
fields here and they are computed by two functions.

DERIVE FIRST, WRITE ONLY WHAT CANNOT BE DERIVED. 182 of the 416 carry a field
that answers the shelf question — `item.category`, `weapon.weapon_range`,
`armor.armor_category`. The other 234 do not, and they are written down: the
107 mundane rows (82 adventuring gear, 25 tools) have nothing but a name, and
the 127 marvels all carry the SAME category, which is exactly why deriving from
it put them in one drawer of 127. A value written in two places ends up
disagreeing with itself;
the catalyst price list in this house already carries one derived tier from two
different fields, 463 records against 2, divergent before it ever had a reader.

⛔ NO NAME ANALYSER, ANYWHERE. Four "obvious" lexical rules were tested against
the 82 common items and three of them break on their first object: *ends with
"pack"* catches Backpack, which is a container; *contains "scroll"* catches
`Case, Map or Scroll`, which is a case; *contains "pouch"* catches both
`Component Pouch` (magic) and `Pouch` (a container) — one word, two shelves.
The table below is keyed by the EXACT catalogue name, never by a substring.

⚠️ AND THE ABSENCE TRAP, which has a name in this workshop. `item.subtype` has
its key present 258 times out of 258 and its VALUE is null 206 of those times:
52 real values. Anything asking `"subtype" in data` believes it holds an axis
and holds nothing. Every test below reads the VALUE.
"""

import json

import canon
import db

LAYER = "srfh"
KIND = "shelving"

# Same licence question as the rest of the SRFH layer, and it is still Eric's
# to answer. See `srfh.py`: `undecided` is a state, not a placeholder.
LICENSE = "undecided"
ATTRIBUTION = (
    "Fate's Hand (Eric). Shelving and body slots decided on 2026-08-21/22 for "
    "the System Reference Document 5.2.1 by Wizards of the Coast LLC, licensed "
    "under CC-BY-4.0. The classification is not part of the SRD."
)


class ShelvingError(Exception):
    """A guard in this module refused. Never caught: the build stops."""


# ---------------------------------------------------------------------------
# The seven aisles
# ---------------------------------------------------------------------------
# Alphabetical at both levels, and the first one is the one that opens (Eric,
# 2026-08-22). Keys are ENGLISH on both sides — repository law §0.13, *the
# engine makes identifiers, the interface makes words*. The ten French words in
# the source document are labels, not keys. The counter-example is in this same
# repository and it cost a day: `damage_type_key` holds `slashing` in English
# and `perforant` in French, a field whose name promises a key and carries a
# translation.
#
# `Arcana` and `Marvels` are PROPOSED names, never ratified. They are used here
# because the structure under them is firm, and flagged so nobody mistakes use
# for agreement.
PROVISIONAL_AISLE = ("arcana", "marvels")

SHELVES = {
    "adventuring": ("camp", "force-and-trap", "light-and-fire", "packs",
                    "ropes-and-climbing", "watch-and-signal"),
    "arcana": ("consumables-and-potions", "scrolls-foci-components",
               "wands-rods-staves"),
    # ⛔ `projectiles` A DISPARU LE 2026-09-23, ET CE N'EST PAS UN OUBLI.
    # Eric, fhpc, 2026-09-20 : « toutes les armes de jet, les munitions vont
    # dans cette catégorie », puis « idem pour FH et SRD ». L'étagère est donc
    # FUSIONNÉE dans `ranged-weapons`, pas vidée en attendant mieux.
    # ⭐ La différence compte : `companions` et `crafting` gardent des étagères
    # à zéro parce qu'elles seront remplies ; celle-ci ne le sera jamais, et une
    # étagère déclarée qui n'attend rien est une promesse qui ment.
    "armory": ("armor", "magic-armor", "magic-weapons", "melee-weapons",
               "ranged-weapons"),
    # ✅ RATIFIÉ PAR ERIC LE 2026-08-24 (« Je valide »), ET HÉRITÉ, PAS INVENTÉ. Ce rayon
    # n'en déclarait que DEUX, donc il sortait à deux crans — sous le minimum
    # de trois, et l'écran le rendait « court », ce qu'Eric a vu et n'aime pas.
    # ⛔ Les quatre viennent de SON PROPRE DOCUMENT de rangement : « Familiers
    # (max 15) · Hommes de main (max 15) · Sur mesure (import statblock) ·
    # Recherche dans les monstres ». Le brouillon en avait retenu deux.
    "companions": ("bespoke", "familiars", "henchmen", "monster-search"),
    "crafting": ("gems", "ingredients", "tools"),
    # The seven Eric arrested on 2026-08-21. `wondrous` is GONE: it was a
    # holding shelf for 127 records with nowhere to go, and 127 on one shelf
    # is nine pages of a screen aimed at 35. The largest of the seven is 33.
    "marvels": ("clothing", "consumables", "containers-and-vehicles",
                "foci-and-curios", "helms-and-lenses", "jewellery",
                "rings"),
    # 🔤 TRIÉ LE 2026-08-24, RATIFIÉ PAR ERIC LE MÊME JOUR : Eric a ratifié « ordre alphabétique aux
    # deux niveaux » le 22/08, et six rayons sur sept l'étaient déjà.
    # ⛔ Le lot 103 avait REFUSÉ de trier, et il avait raison : trier aurait
    # déplacé un rayon PEUPLÉ, donc cassé la preuve de son propre lot (« publier
    # du vide ne déplace rien »). Ce lot-ci n'a pas cette preuve à tenir.
    "mundane": ("clothing", "containers", "writing-and-reading"),
}

# Shelves this lot ADDED rather than transcribed, and why each one exists. The
# source document assumed the magic weapons and the magic armor would stop
# being records at all — *elles se fabriquent depuis leur base mondaine* — so it
# never said where to put them. The lot's requirement is 416 out of 416 with no
# remainder, which reopens the question. Keeping them on their own two shelves
# leaves every count the document printed exactly as it printed it.
PROVISIONAL_SHELF = {
    ("armory", "magic-weapons"):
        "the document expected these to stop being records; 416/416 says they "
        "are still here, and this shelf leaves its printed counts untouched",
    ("armory", "magic-armor"):
        "same, for armor",
}

# ---------------------------------------------------------------------------
# The ten body slots
# ---------------------------------------------------------------------------
# Read off the 77 worn objects, 77 out of 77 with no remainder. `eyes` is kept
# apart from `head` on purpose: merged, a helm would forbid goggles, which the
# SRD does not forbid.
SLOTS = ("back", "eyes", "feet", "fingers", "forearms", "hands", "head",
         "neck", "torso", "waist")

# ⛔ THIS IS THE SILHOUETTE'S SHAPE, NOT A RULE OF THE GAME. A square on the
# doll holds one object, and `fingers` is the one square Eric left open —
# *les anneaux pas de limites, mais deux bottes, gants, capes l'une sur l'autre
# non*. It is deliberately NOT written onto the objects: a slot PLACES, it does
# not FORBID. No SRD 5.2.1 rule limits how many rings or cloaks are worn; the
# only limit in the game is attunement, and that already exists in the data.
# Emitting a per-object exclusivity here would be a second limit, drifting away
# from the first.
SLOT_CAPACITY = {slot: (None if slot == "fingers" else 1) for slot in SLOTS}

# ---------------------------------------------------------------------------
# The 309 that derive — one field already answers
# ---------------------------------------------------------------------------
# `item.category` carries nine values and every one of them names a shelf. Three
# of the counts this produces land exactly on the document's own figures without
# anything being written down: wands+rods+staves = 32, potions+9 mundane
# consumables = 33, the scroll + 6 mundane magic gear = 7. That agreement is the
# evidence that the derivation is the right one.
# ⛔ `wondrous-item` IS DELIBERATELY ABSENT from this table. All 127 of them
# carried one category and one shelf, which is how they ended up in a drawer of
# 127; they are read object by object from MARVEL_SHELVES below.
SHELF_OF_ITEM_CATEGORY = {
    "armor": ("armory", "magic-armor"),
    "potion": ("arcana", "consumables-and-potions"),
    "ring": ("marvels", "rings"),
    "rod": ("arcana", "wands-rods-staves"),
    "scroll": ("arcana", "scrolls-foci-components"),
    "staff": ("arcana", "wands-rods-staves"),
    "wand": ("arcana", "wands-rods-staves"),
    "weapon": ("armory", "magic-weapons"),
}

SHELF_OF_WEAPON_RANGE = {
    "melee": ("armory", "melee-weapons"),
    "ranged": ("armory", "ranged-weapons"),
}

# ---------------------------------------------------------------------------
# The 107 that do not derive — transcribed from the source, 2026-08-22
# ---------------------------------------------------------------------------
#   ~/obsidian-vault/FH-WEB/FHPC/FHPCv2 rangement equipement.md
#
# Keyed by the exact catalogue name, apostrophes included (the catalogue uses
# U+2019, not U+0027). The build refuses if a key here matches no record or if
# a record matches no key, so a rename upstream cannot pass in silence.
SHELF_OF_GEAR = {}
for _names, _shelf in (
    # Containers, 16
    (("Backpack", "Barrel", "Basket", "Bottle, Glass", "Bucket",
      "Case, Crossbow Bolt", "Case, Map or Scroll", "Chest", "Flask", "Jug",
      "Pot, Iron", "Pouch", "Quiver", "Sack", "Vial", "Waterskin"),
     ("mundane", "containers")),
    # Force and trap, 10
    (("Ball Bearings", "Caltrops", "Crowbar", "Hunting Trap", "Lock",
      "Manacles", "Net", "Ram, Portable", "Shovel", "Spikes, Iron"),
     ("adventuring", "force-and-trap")),
    # Consumables, 9 — they join the potions in Arcana, as the document says
    (("Acid", "Alchemist’s Fire", "Antitoxin", "Healer’s Kit", "Holy Water",
      "Oil", "Poison, Basic", "Potion of Healing", "Rations"),
     ("arcana", "consumables-and-potions")),
    # Ropes and climbing, 8
    (("Block and Tackle", "Chain", "Climber’s Kit", "Grappling Hook", "Ladder",
      "Pole", "Rope", "String"),
     ("adventuring", "ropes-and-climbing")),
    # Packs, 7 — filed INSIDE Adventuring rather than given an aisle of their
    # own: an aisle with no shelves would empty the lower carousel on that one
    # aisle and make the page jump height, and a screen that moves under the
    # finger is a screen nobody dares touch.
    (("Burglar’s Pack", "Diplomat’s Pack", "Dungeoneer’s Pack",
      "Entertainer’s Pack", "Explorer’s Pack", "Priest’s Pack",
      "Scholar’s Pack"),
     ("adventuring", "packs")),
    # Light and fire, 6
    (("Candle", "Lamp", "Lantern, Bullseye", "Lantern, Hooded", "Tinderbox",
      "Torch"),
     ("adventuring", "light-and-fire")),
    # Writing and reading, 6
    (("Book", "Ink", "Ink Pen", "Map", "Paper", "Parchment"),
     ("mundane", "writing-and-reading")),
    # Magic, 6 — the mundane half of the Arcana scroll shelf
    (("Arcane Focus", "Component Pouch", "Druidic Focus", "Holy Symbol",
      "Spell Scroll (Cantrip)", "Spell Scroll (Level 1)"),
     ("arcana", "scrolls-foci-components")),
    # Clothing, 5
    (("Clothes, Fine", "Clothes, Traveler’s", "Costume", "Perfume", "Robe"),
     ("mundane", "clothing")),
    # Watch and signal, 5
    (("Bell", "Magnifying Glass", "Mirror", "Signal Whistle", "Spyglass"),
     ("adventuring", "watch-and-signal")),
    # Camp, 3
    (("Bedroll", "Blanket", "Tent"), ("adventuring", "camp")),
    # Ammunition, 1 — the SRD's single empty `Varies/Varies` row, and the ONLY
    # gear row in the armory. It sat on a shelf of its own until 2026-09-23;
    # Eric merged that shelf into `ranged-weapons` (« idem pour FH et SRD »),
    # where Fate's Hand's five real munitions already stand.
    (("Ammunition",), ("armory", "ranged-weapons")),
):
    for _n in _names:
        SHELF_OF_GEAR[_n] = _shelf

# ---------------------------------------------------------------------------
# The 149 marvels — the split Eric arrested on 2026-08-21, rebuilt from the SRD
# ---------------------------------------------------------------------------
#   ~/obsidian-vault/FH-WEB/FHPC/FHPCv2 rangement equipement.md, "Marvels — les
#   149, rangés". The per-object file the document names,
#   `merveilleux-ranges.json`, is on no disk; this table replaces it, and the
#   seven counts it printed are the proof that the reconstruction is his and
#   not a new one. All seven land exactly (see MARVEL_SHELF_COUNT).
#
# ⭐ THE AXIS IS GARMENT/JEWEL, NOT BODY PART. Arrested after the other axis was
# tried and failed: shelving by body part forced a "legs and feet" shelf down to
# 7, because the SRD prints boots and no marvellous greaves at all. ⛔ Do not
# try it again — and do not confuse this axis with the slot axis below, which is
# read in the same pass and answers a different question.
#
# ⭐ CONSUMABLE ONLY IF THE OBJECT CEASES TO EXIST. Eric's rule, and it is
# strict: the six Manuals and Tomes *regain it in a century*, so they sleep,
# they do not vanish — they are curios. `Manual of Golems` is the seventh
# manual and the one that is *consumed in eldritch flames*, which is why the
# document says six and the catalogue holds seven.
#
# Each row carries the SRD sentence that decides it. That sentence is also the
# provenance written onto the exported record, so a reader never has to take
# this module's word for anything.
#
#   (name, slot or None, the sentence that decides it)
#
# `None` in the slot column means MEASURED NOT WORN — an object whose own text
# says it is held, thrown, poured, ridden or planted. It is not the same value
# as "nobody has answered yet", and the exported record says which one it is in
# a `state` field rather than leaving a reader to interpret a null.
MARVEL_SHELVES = (
    ("clothing", (
        # capes and mantles — back, 10 with the wings
        ("Cape of the Mountebank", "back", "While wearing it, you can use it to cast Dimension Door as a Magic action."),
        ("Cloak of Arachnida", "back", "While wearing it, you gain the following benefits."),
        ("Cloak of Displacement", "back", "While you wear this cloak, it magically projects an illusion that makes you appear to be standing in a place near your actual location."),
        ("Cloak of Elvenkind", "back", "While you wear this cloak, Wisdom (Perception) checks made to perceive you have Disadvantage."),
        ("Cloak of Invisibility", "back", "While wearing the cloak, you can take a Magic action to pull its hood over your head."),
        ("Cloak of Protection", "back", "You gain a +1 bonus to Armor Class and saving throws while you wear this cloak."),
        ("Cloak of the Bat", "back", "While wearing this cloak, you have Advantage on Dexterity (Stealth) checks."),
        ("Cloak of the Manta Ray", "back", "While wearing this cloak, you can breathe underwater, and you have a Swim Speed of 60 feet."),
        ("Mantle of Spell Resistance", "back", "You have Advantage on saving throws against spells while you wear this cloak."),
        ("Wings of Flying", "back", "While wearing this cloak, you can take a Magic action to turn the cloak into a pair of wings on your back."),
        # boots and slippers — feet, 7
        ("Boots of Elvenkind", "feet", "While you wear these boots, your steps make no sound, regardless of the surface you are moving across."),
        ("Boots of Levitation", "feet", "While you wear these boots, you can cast Levitate on yourself."),
        ("Boots of Speed", "feet", "While you wear these boots, you can take a Bonus Action to click the boots’ heels together."),
        ("Boots of Striding and Springing", "feet", "While you wear these boots, your Speed becomes 30 feet unless your Speed is higher."),
        ("Boots of the Winterlands", "feet", "These furred boots are snug and feel warm. While wearing them, you gain the following benefits."),
        ("Slippers of Spider Climbing", "feet", "While you wear these light shoes, you can move up, down, and across vertical surfaces and along ceilings."),
        ("Winged Boots", "feet", "While wearing the boots, you can take a Magic action to expend 1 charge, gaining a Fly Speed of 30 feet for 1 hour."),
        # gloves and gauntlets — hands, 4
        ("Gauntlets of Ogre Power", "hands", "Your Strength is 19 while you wear these gauntlets."),
        ("Gloves of Missile Snaring", "hands", "If you’re hit by an attack roll made with a Ranged or Thrown weapon while wearing these gloves, you can take a Reaction to reduce the damage."),
        ("Gloves of Swimming and Climbing", "hands", "While wearing these gloves, you have a Climb Speed and a Swim Speed equal to your Speed."),
        ("Gloves of Thievery", "hands", "These gloves are imperceptible while worn."),
        # robes — torso, 5
        ("Robe of Eyes", "torso", "While you wear the robe, you gain the following benefits: All-Around Vision."),
        ("Robe of Scintillating Colors", "torso", "While you wear it, you can take a Magic action and expend 1 charge to cause the garment to display a shifting pattern of dazzling hues."),
        ("Robe of Stars", "torso", "You gain a +1 bonus to saving throws while you wear it."),
        ("Robe of the Archmagi", "torso", "You gain these benefits while wearing the robe."),
        ("Robe of Useful Items", "torso", "While wearing the robe, you can take a Magic action to detach one of the patches."),
        # hat and headband — head, 2 of the eight
        ("Hat of Disguise", "head", "While wearing this hat, you can cast the Disguise Self spell."),
        ("Headband of Intellect", "head", "Your Intelligence is 19 while you wear this headband."),
        # bracers — forearms, 2
        ("Bracers of Archery", "forearms", "While wearing these bracers, you have proficiency with the Longbow and Shortbow."),
        ("Bracers of Defense", "forearms", "While wearing these bracers, you gain a +2 bonus to Armor Class if you are wearing no armor and using no Shield."),
        # belts — waist, 2
        ("Belt of Dwarvenkind", "waist", "While wearing this belt, you gain the following benefits: Dwarvish."),
        ("Belt of Giant Strength", "waist", "While wearing this belt, your Strength changes to a score granted by the belt."),
    )),
    ("consumables", (
        ("Bead of Force", None, "The bead explodes in a 10-foot-radius Sphere on impact and is destroyed."),
        ("Bead of Nourishment", None, "This flavorless, gelatinous bead dissolves on your tongue and provides as much nourishment as 1 day of Rations."),
        ("Candle of Invocation", None, "After burning for 4 hours, the candle is destroyed."),
        ("Dust of Disappearance", None, "The duration is the same for all subjects, and the dust is consumed when its magic takes effect."),
        ("Dust of Dryness", None, "This small packet contains 1d6 + 4 pinches of dust. As a Utilize action, you can sprinkle a pinch of the dust over water."),
        ("Dust of Sneezing and Choking", None, "Found in a small container, this powder resembles Dust of Disappearance."),
        ("Elemental Gem", None, "When you take a Utilize action to break the gem, an elemental is summoned (see \u201cMonsters\u201d for its stat block), and the gem ceases to be magical."),
        ("Feather Token", None, "Different types of feather tokens exist, each with a different single-use effect. When the effect ends, the token disappears."),
        ("Manual of Golems", None, "Once you finish creating the golem, the book is consumed in eldritch flames."),
        ("Marvelous Pigments", None, "If your Concentration is broken or you leave the Cube before the work is done, all the painted elements vanish, and the pot of pigment is wasted."),
        ("Necklace of Fireballs", None, "You can hurl multiple beads, or even the whole necklace, at one time."),
        ("Scarab of Protection", None, "The scarab crumbles into powder and is destroyed when its last charge is expended."),
        ("Sovereign Glue", None, "This viscous, milky-white substance can form a permanent adhesive bond between any two objects. When found, a container contains 1d6 + 1 ounces."),
        ("Universal Solvent", None, "This tube holds milky liquid with a strong alcohol smell. When found, a tube contains 1d6 + 1 ounces."),
    )),
    ("containers-and-vehicles", (
        ("Apparatus of the Crab", None, "To be used as a vehicle, the apparatus requires one pilot."),
        ("Bag of Beans", None, "This heavy cloth bag contains 3d4 dry beans when found."),
        ("Bag of Devouring", None, "Inanimate objects can be stored in the bag, which can hold a cubic foot of such material."),
        ("Bag of Holding", None, "The bag can hold up to 500 pounds, not exceeding a volume of 64 cubic feet."),
        ("Bag of Tricks", None, "This bag made from gray, rust, or tan cloth appears empty. Reaching inside the bag, however, reveals the presence of a small, fuzzy object."),
        ("Broom of Flying", None, "This wooden broom functions like a mundane broom until you stand astride it and take a Magic action to make it hover beneath you, at which time it can be ridden in the air."),
        ("Carpet of Flying", None, "You can make this carpet hover and fly by taking a Magic action and using the carpet’s command word."),
        ("Decanter of Endless Water", None, "This stoppered flask sloshes when shaken, as if it contains water."),
        ("Dimensional Shackles", None, "You can take a Utilize action to place these shackles on a creature that has the Incapacitated condition."),
        ("Efficient Quiver", None, "Each of the quiver’s three compartments connects to an extradimensional space that allows the quiver to hold numerous items."),
        ("Efreeti Bottle", None, "When you take a Magic action to remove the stopper of this painted brass bottle, a cloud of thick smoke flows out of it."),
        ("Eversmoking Bottle", None, "As a Magic action, you can open or close this bottle."),
        ("Folding Boat", None, "It can be opened to store items inside. The box unfolds into a Rowboat."),
        ("Handy Haversack", None, "This backpack has a central pouch and two side pouches, each of which is an extradimensional space."),
        ("Horseshoes of a Zephyr", None, "As a Magic action, you can touch one of the horseshoes to the hoof of a horse or similar creature, whereupon the horseshoe affixes itself to the hoof."),
        ("Horseshoes of Speed", None, "While all four horseshoes are attached to the same creature, its Speed is increased by 30 feet."),
        ("Instant Fortress", None, "As a Magic action, you can place this 1-inch adamantine statuette on the ground and, using a command word, cause it to grow rapidly into a square adamantine tower."),
        ("Iron Bands", None, "On a hit, the target has the Restrained condition until you take a Bonus Action to issue a command that releases it."),
        ("Iron Flask", None, "The flask can hold only one creature at a time."),
        ("Mirror of Life Trapping", None, "Any creature other than you that sees its reflection in the activated mirror while within 30 feet of the mirror must succeed on a DC 15 Charisma saving throw or be trapped, along with anything it is wearing or carrying, in one of the mirror’s twelve extradimensional cells."),
        ("Portable Hole", None, "A closed Portable Hole holds enough air for 1 hour of breathing, divided by the number of breathing creatures inside."),
        ("Rope of Climbing", None, "This 60-foot length of rope can hold up to 3,000 pounds."),
        ("Rope of Entanglement", None, "While holding one end of the rope, you can take a Magic action to command the other end to dart forward and entangle one creature."),
        ("Well of Many Worlds", None, "This fine black cloth, soft as silk, is folded up to the dimensions of a handkerchief."),
    )),
    ("foci-and-curios", (
        # summoning foci, 4 — one per element, and none of them is worn
        ("Bowl of Commanding Water Elementals", None, "While this bowl is filled with water and you are within 5 feet of it, you can take a Magic action to summon a Water Elemental."),
        ("Brazier of Commanding Fire Elementals", None, "While you are within 5 feet of this brazier, you can take a Magic action to summon a Fire Elemental."),
        ("Censer of Controlling Air Elementals", None, "While gently swinging this censer, you can take a Magic action to summon an Air Elemental."),
        ("Stone of Controlling Earth Elementals", None, "While touching this 5-pound stone to the ground, you can take a Magic action to summon an Earth Elemental."),
        # crystal balls and orbs, 5
        ("Crystal Ball", None, "While touching this crystal orb, you can cast Scrying (save DC 17) with it."),
        ("Crystal Ball of Mind Reading", None, "While touching this crystal orb, you can cast Scrying (save DC 17) with it."),
        ("Crystal Ball of Telepathy", None, "While touching this crystal orb, you can cast Scrying (save DC 17) with it."),
        ("Crystal Ball of True Seeing", None, "While touching this crystal orb, you can cast Scrying (save DC 17) with it."),
        ("Dragon Orb", None, "An orb is an etched crystal globe about 10 inches in diameter."),
        # horns and pipes, 4
        ("Horn of Blasting", None, "You can take a Magic action to blow the horn, which emits a thunderous blast in a 30-foot Cone."),
        ("Horn of Valhalla", None, "You can take a Magic action to blow this horn."),
        ("Pipes of Haunting", None, "You can take a Magic action to play them and expend 1 charge to create an eerie, spellbinding tune."),
        ("Pipes of the Sewers", None, "While these pipes are on your person, ordinary rats and giant rats are Indifferent toward you."),
        # decks and figurines, 3
        ("Deck of Illusions", None, "This box contains a set of cards. The magic of the deck functions only if its cards are drawn at random."),
        ("Mysterious Deck", None, "Usually found in a box or pouch, this deck contains a number of cards made of ivory or vellum."),
        ("Figurine of Wondrous Power", None, "A Figurine of Wondrous Power is a statuette small enough to fit in a pocket."),
        # 💎 LA PERLE DE PUISSANCE — RATIFIÉE PAR ERIC LE 2026-08-24
        # (« Je valide »), ET ELLE VIENT DES CONSOMMABLES.
        # ⚠️ LA LISTE D'ERIC DIT « perles → Consommables ». SA RÈGLE DIT NON, et
        # la règle gagne — c'est tout l'intérêt d'en avoir écrit une : elle
        # tranche les cas que la liste n'a pas revus.
        #   · sa règle : « consommable SEULEMENT si l'objet CESSE D'EXISTER » ;
        #   · le record : « it can’t be used again until the NEXT DAWN » — elle
        #     se recharge, elle ne disparaît pas ;
        #   · ⭐ SON PROPRE PRÉCÉDENT, six lignes plus bas : les Manuels et
        #     Tomes sont ici pour exactement cette raison — « regains it in a
        #     century ». La Perle est le même cas, une aube au lieu d'un siècle.
        # 📌 CONSÉQUENCE ASSUMÉE : `consumables` passe de 15 à 14. Les sept
        # comptes d'Eric étaient la PREUVE qu'on avait reproduit sa
        # classification, pas une cible à tenir — un objet qu'une règle nommée
        # déplace n'est pas un compte qu'on rate.
        # ⛔ RATIFIÉ N'EST PAS SANS ARGUMENT : le motif reste écrit en entier
        # au-dessus, parce qu'une décision dont on a perdu la raison SE REFAIT.
        # Sans le précédent des Manuels, celle-ci aurait l'air d'un caprice.
        ("Pearl of Power", None, "Once you use the pearl, it can\u2019t be used again until the next dawn."),
        # the 6 manuals and tomes — they sleep, they do not vanish
        ("Manual of Bodily Health", None, "The manual then loses its magic but regains it in a century."),
        ("Manual of Gainful Exercise", None, "The manual then loses its magic but regains it in a century."),
        ("Manual of Quickness of Action", None, "The manual then loses its magic but regains it in a century."),
        ("Tome of Clear Thought", None, "The manual then loses its magic but regains it in a century."),
        ("Tome of Leadership and Influence", None, "The manual then loses its magic but regains it in a century."),
        ("Tome of Understanding", None, "The manual then loses its magic, but regains it in a century."),
        # the curios — held, struck, peered through, pressed
        ("Chime of Opening", None, "As a Magic action, you can strike the chime to cast Knock."),
        ("Cube of Force", None, "You can press one of those faces, expend the number of charges required for it, and thereby cast the spell associated with it."),
        ("Cubic Gate", None, "Pressing one side of the cube, you cast Gate, opening a portal to the plane of existence keyed to that side."),
        ("Gem of Brightness", None, "While you are holding it, you can take a Magic action and use one of three command words."),
        ("Gem of Seeing", None, "For the next 10 minutes, you have Truesight out to 120 feet when you peer through the gem."),
        ("Hat of Many Spells", None, "While holding the hat, you can use it as a Spellcasting Focus for your Wizard spells."),
        ("Lantern of Revealing", None, "While lit, this hooded lantern burns for 6 hours on 1 pint of oil."),
        ("Sending Stones", None, "Sending Stones come in pairs, with each stone carved to match the other so the pairing is easily recognized."),
        ("Sphere of Annihilation", None, "This 2-foot-diameter black sphere is a hole in the multiverse, hovering in space and stabilized by a magical field surrounding it."),
        ("Stone of Good Luck (Luckstone)", None, "While this polished agate is on your person, you gain a +1 bonus to ability checks and saving throws."),
        ("Wind Fan", None, "While holding this fan, you can cast Gust of Wind (save DC 13) from it."),
    )),
    ("helms-and-lenses", (
        ("Helm of Brilliance", "head", "You gain the following benefits while wearing the helm."),
        ("Helm of Comprehending Languages", "head", "While wearing this helm, you can cast Comprehend Languages from it."),
        ("Helm of Telepathy", "head", "While wearing this helm, you have telepathy with a range of 30 feet."),
        ("Helm of Teleportation", "head", "While wearing it, you can expend 1 charge to cast Teleport from it."),
        ("Eyes of Charming", "eyes", "These crystal lenses fit over the eyes. While wearing them, you can expend 1 or more charges to cast Charm Person."),
        ("Eyes of Minute Seeing", "eyes", "These crystal lenses fit over the eyes. While wearing them, your vision improves significantly out to a range of 1 foot."),
        ("Eyes of the Eagle", "eyes", "These crystal lenses fit over the eyes. While wearing them, you have Advantage on Wisdom (Perception) checks that rely on sight."),
        ("Goggles of Night", "eyes", "While wearing these dark lenses, you have Darkvision out to 60 feet."),
    )),
    ("jewellery", (
        ("Amulet of Health", "neck", "Your Constitution is 19 while you wear this amulet."),
        ("Amulet of Proof against Detection and Location", "neck", "While wearing this amulet, you can’t be targeted by Divination spells or perceived through magical scrying sensors unless you allow it."),
        ("Amulet of the Planes", "neck", "While wearing this amulet, you can take a Magic action to name a location that you are familiar with on another plane of existence."),
        ("Brooch of Shielding", "neck", "While wearing this brooch, you have Resistance to Force damage."),
        ("Medallion of Thoughts", "neck", "While wearing it, you can expend 1 charge to cast Detect Thoughts (save DC 13) from it."),
        ("Necklace of Adaptation", "neck", "While wearing this necklace, you can breathe normally in any environment."),
        ("Necklace of Prayer Beads", "neck", "To use one, you must be wearing the necklace."),
        ("Periapt of Health", "neck", "While wearing this pendant, you can take a Magic action to regain 2d4 + 2 Hit Points."),
        ("Periapt of Proof against Poison", "neck", "While you wear it, you have Immunity to the Poisoned condition and Poison damage."),
        ("Periapt of Wound Closure", "neck", "While wearing this pendant, you gain the following benefits."),
        ("Talisman of Pure Good", "neck", "You gain a +2 bonus to spell attack rolls while you wear or hold it."),
        ("Talisman of the Sphere", "neck", "While holding or wearing this talisman, you have Advantage on any Intelligence (Arcana) check you make to control a Sphere of Annihilation."),
        ("Talisman of Ultimate Evil", "neck", "You gain a +2 bonus to spell attack rolls while you wear or hold it."),
        # the two jewels that sit on the head rather than at the neck — which is
        # why the shelf axis and the slot axis cannot be deduced from each other
        ("Circlet of Blasting", "head", "While wearing this circlet, you can cast Scorching Ray with it (+5 to hit)."),
        ("Ioun Stone", "head", "Each Ioun Stone orbiting your head is considered to be an object you are wearing."),
    )),
)

MARVEL = {}
for _shelf, _rows in MARVEL_SHELVES:
    for _name, _slot, _why in _rows:
        if _name in MARVEL:
            raise ShelvingError("%r is on two marvel shelves" % _name)
        MARVEL[_name] = (_shelf, _slot, _why)

# ⭐ ERIC'S SEVEN NUMBERS, AND THEY COST NOTHING TO CHECK. He printed these on
# 2026-08-21 from a classification he made by hand. Landing on all seven is what
# says this table is his and not a second opinion wearing his labels. `rings` is
# not in this table — the 22 derive from `item.category` — but it is one of the
# seven, so it is counted with them below.
# ✅ AMENDÉ LE 2026-08-24, ET RATIFIÉ PAR ERIC LE MÊME JOUR (« Je valide »).
# Deux comptes bougent, et un seul objet en est la cause : la 💎 Perle de
# puissance passe de `consumables` à `foci-and-curios` (voir le motif entier
# à sa ligne, plus bas).
#
# 📌 CE QUE CES SEPT NOMBRES SONT, ET CE QU'ILS NE SONT PAS. Ils ont été
# arrêtés par Eric le 2026-08-21, et leur rôle est d'être la PREUVE qu'on a
# reproduit sa classification — pas une cible à atteindre. Le garde qui les lit
# le dit lui-même : « ne déplace PAS un objet pour que l'arithmétique tombe ».
# ⭐ Ici c'est l'inverse : une RÈGLE nommée déplace un objet, et l'arithmétique
# suit. Un compte qu'une règle déplace n'est pas un compte qu'on rate.
MARVEL_SHELF_COUNT = {
    "foci-and-curios": 34,   # 33 → 34 : la Perle de puissance (ratifié 24/08)
    "clothing": 32,
    "containers-and-vehicles": 24,
    "rings": 22,
    "jewellery": 15,
    "consumables": 14,       # 15 → 14 : idem, et c'est la conséquence assumée
    "helms-and-lenses": 8,
}

# ⭐ WHAT ERIC READS FIRST. A doubt is not a hedge: it names an object whose SRD
# text does not settle the question on its own, says which way this table went,
# and says what would flip it. The document that arrested the split announced 33
# of them without listing them; this reconstruction finds 11, and the difference
# is worth saying out loud rather than padding the list to match a number.
MARVEL_DOUBT = {
    "Hat of Many Spells":
        "Eric's own arbitration, taken as given: the name says hat, the text "
        "never says wear — only 'While holding the hat'. Shelved as a focus "
        "and NOT worn. Reversing it would move it to clothing and to `head`.",
    "Horseshoes of a Zephyr":
        "Eric's arbitration settles that it is NOT worn (the shoes affix to a "
        "mount's hooves, not to the character). The SHELF is mine: filed with "
        "the vehicles because the mount is the vehicle. Foci would also hold "
        "it, and the seven counts cannot tell the two apart — see the note on "
        "Well of Many Worlds for the pair that fixes the arithmetic.",
    "Horseshoes of Speed":
        "Same arbitration and the same open shelf question as its twin.",
    "Well of Many Worlds":
        "Filed with the containers on the SRD's own repeated sentence: it opens "
        "'This fine black cloth, soft as silk, is folded up to the dimensions of "
        "a handkerchief' — word for word the opening of Portable Hole. Cubic "
        "Gate, its rival for the planar-portal reading, opens 'This cube is 3 "
        "inches across' and is filed beside Cube of Force for the same reason.",
    "Mirror of Life Trapping":
        "A container of creatures, not a curio: victims are trapped 'in one of "
        "the mirror's twelve extradimensional cells', and the SRD lists it "
        "beside Bag of Holding and Portable Hole in the clause about nesting "
        "extradimensional spaces. It is 50 pounds and hangs on a wall.",
    "Necklace of Fireballs":
        "Moved OFF the jewellery shelf to consumables, and three independent "
        "numbers agree: jewellery falls from 16 to Eric's 15, consumables rises "
        "from 14 to his 15, and `neck` falls from 14 to his 13. The text: 'You "
        "can hurl multiple beads, or even the whole necklace, at one time.'",
    "Pearl of Power":
        "⚠️ HERE THE TABLE AND ERIC'S OWN RULE DISAGREE, and the count decides. "
        "His consumables shelf is listed as 'poudres · perles · gemmes "
        "élémentaires · pigments · colle · solvant' and this is the SRD's pearl; "
        "but his strict rule is that consumable wins only if the object ceases "
        "to exist, and this one does not — 'Once you use the pearl, it can't be "
        "used again until the next dawn'. Filed where his list puts it. His call.",
    "Scarab of Protection":
        "Eric's arbitration, taken as given: a worn medallion, but it 'crumbles "
        "into powder and is destroyed'. Shelved as a consumable. Its slot is "
        "measured separately and comes back NOT worn — the text says 'while it "
        "is on your person', which is carried, not worn — and that is what keeps "
        "`neck` at his 13.",
    "Talisman of the Sphere":
        "'While holding OR wearing this talisman' — the SRD offers both. Counted "
        "at the neck with its two siblings, which is what Eric's `Cou 13` needs. "
        "The same sentence shape covers Talisman of Pure Good and of Ultimate "
        "Evil ('while you wear or hold it').",
    "Gem of Brightness":
        "NOT a consumable, on the strict rule: 'When all of the gem's charges "
        "are expended, the gem becomes a nonmagical jewel worth 50 GP' — it stops "
        "working, it does not stop existing. Same shape as the Chime of Opening, "
        "which 'cracks and becomes useless'. Both are curios.",
    "Stone of Good Luck (Luckstone)":
        "'On your person' is carried, not worn, so it takes no slot — but it is "
        "a polished agate and could be read as jewellery. Filed as a curio, "
        "because jewellery lands on Eric's 15 without it.",
}

SHELF_OF_TOOL = ("crafting", "tools")

# The document's own counts, and they are a free check: if the transcription
# above drifts, these stop adding up. 16+10+9+8+7+6+6+6+5+5+3+1 = 82.
GEAR_SHELF_COUNT = {
    ("mundane", "containers"): 16,
    ("adventuring", "force-and-trap"): 10,
    ("arcana", "consumables-and-potions"): 9,
    ("adventuring", "ropes-and-climbing"): 8,
    ("adventuring", "packs"): 7,
    ("adventuring", "light-and-fire"): 6,
    ("mundane", "writing-and-reading"): 6,
    ("arcana", "scrolls-foci-components"): 6,
    ("mundane", "clothing"): 5,
    ("adventuring", "watch-and-signal"): 5,
    ("adventuring", "camp"): 3,
    ("armory", "ranged-weapons"): 1,
}

# ---------------------------------------------------------------------------
# `craftable` — posed as the document poses it, and MEASURED
# ---------------------------------------------------------------------------
# A transverse label, not an aisle: an object is shelved somewhere AND carries
# `craftable`. The bases the craft lays magic onto are weapons, armor,
# projectiles and spell scrolls. The first two are a whole record kind; the last
# two are three named rows, which is why they are named here and nowhere else.
CRAFT_BASE_GEAR = ("Ammunition", "Spell Scroll (Cantrip)", "Spell Scroll (Level 1)")
CRAFT_BASE_KINDS = ("weapon", "armor")


# ---------------------------------------------------------------------------
# Axis 1 — the shelf. One entry point, two sources behind it.
# ---------------------------------------------------------------------------
def shelf_of(kind, name, data):
    """(aisle, shelf, provenance) for any of the 416. Never returns None.

    A single function answers "which shelf?" for the whole catalogue: it
    DERIVES for 309 and READS THE TABLE for 107. Two entry points would let the
    two answers drift.
    """
    if kind == "weapon":
        # `weapon_range` is melee or ranged and never absent, and the two
        # shelves it names now say exactly what they hold. The armory's second
        # weapon shelf was *armes de jet* in Eric's document and carried that
        # word until 2026-09-23 — it never held a thrown weapon: its ten
        # members are exactly the ten ranged rows.
        rng = data["weapon_range"]
        if rng not in SHELF_OF_WEAPON_RANGE:
            raise ShelvingError(
                "%r has weapon_range %r, which names no shelf" % (name, rng))
        aisle, shelf = SHELF_OF_WEAPON_RANGE[rng]
        return aisle, shelf, "derived:weapon.weapon_range"

    if kind == "armor":
        # Every armor row, shield included, sits on one shelf. `armor_category`
        # is read here only to prove it is a real value — it is what tells the
        # SLOT axis a shield goes to the hands and a breastplate to the torso.
        if data["armor_category"] not in ("light", "medium", "heavy", "shield"):
            raise ShelvingError(
                "%r has armor_category %r" % (name, data["armor_category"]))
        return "armory", "armor", "derived:armor.armor_category"

    if kind == "tool":
        aisle, shelf = SHELF_OF_TOOL
        return aisle, shelf, "table:rangement 2026-08-22 (all 25 tools)"

    if kind == "gear":
        if name not in SHELF_OF_GEAR:
            raise ShelvingError(
                "the catalogue has a gear row the shelving table does not "
                "name: %r.\n\nThe table is the ONLY source for these — no name "
                "rule may be invented to cover it. Add the row to the vault "
                "document first, then here." % name)
        aisle, shelf = SHELF_OF_GEAR[name]
        return aisle, shelf, "table:rangement 2026-08-22"

    if kind == "item":
        # ⚠️ The VALUE, never the key. `category` is filled 258/258; `subtype`
        # has its key filled 258/258 and its value 52/258, and it is not read
        # here at all — the shelf never needed it.
        category = data["category"]
        if category == "wondrous-item":
            if name not in MARVEL:
                raise ShelvingError(
                    "the catalogue has a marvel the classification does not "
                    "name: %r.\n\nThe 149 were arrested by hand on 2026-08-21. "
                    "Adding a row here without Eric is inventing a decision, "
                    "and the seven counts would stop adding up anyway." % name)
            return "marvels", MARVEL[name][0], "table:marvels 2026-08-21"
        if category not in SHELF_OF_ITEM_CATEGORY:
            raise ShelvingError(
                "%r has category %r, which names no shelf" % (name, category))
        aisle, shelf = SHELF_OF_ITEM_CATEGORY[category]
        return aisle, shelf, "derived:item.category"

    raise ShelvingError("no shelving rule for record kind %r" % kind)


# ---------------------------------------------------------------------------
# Axis 2 — the body slot. Only what is worn, and only where a field says so.
# ---------------------------------------------------------------------------
def slot_of(kind, name, data, shelf):
    """The body slot, as one of four honest answers, each naming itself.

      state="worn"        + slot   something says where it goes
      state="from_base"            a magic weapon or armor: the slot is
                                   whichever base you laid the magic on,
                                   chosen at purchase
      state="not_worn"             something says it is NOT worn — a text that
                                   says held, thrown, poured, ridden, or "on
                                   your person", or a record kind that settles
                                   it
      state="unanswered"  + pending  nobody has answered yet

    🔴 THE THIRD AND FOURTH ARE NOT THE SAME VALUE, and telling them apart is
    the point of this function. An absence is never an answer: a robe that comes
    back `not_worn` because no table mentioned it is a wrong answer wearing the
    costume of a right one.

    ⭐ `state` is written out in full rather than left for a reader to infer
    from a null, because two readers consume it and neither should have to
    guess: the silhouette screen, which draws a doll, and the Soulforge, which
    asks the same question about a gem. Eric asked for one field for both.
    """
    if kind == "weapon":
        return {"state": "worn", "worn": True, "slot": "hands",
                "provenance": "derived:record kind weapon"}

    if kind == "armor":
        if data["armor_category"] == "shield":
            return {"state": "worn", "worn": True, "slot": "hands",
                    "provenance": "derived:armor.armor_category = shield"}
        return {"state": "worn", "worn": True, "slot": "torso",
                "provenance": "derived:armor.armor_category"}

    if kind == "item":
        category = data["category"]
        if category == "ring":
            # 22 rings, and the document's `Doigts` shelf holds 22. The two
            # numbers were arrived at independently and they match.
            return {"state": "worn", "worn": True, "slot": "fingers",
                    "provenance": "derived:item.category = ring"}
        if category in ("weapon", "armor"):
            # The magic is laid on a base, and the base is picked when the item
            # is bought — `Any Simple or Martial` names no single one. The same
            # shape already exists one file over, where `srfh` gives these items
            # a weight `from_base` for exactly this reason.
            return {"state": "from_base", "worn": True, "from_base": True,
                    "provenance": "derived:item.category; the slot is the "
                                  "base's, chosen at purchase"}
        if category == "wondrous-item":
            # Read object by object, and the provenance IS the sentence of the
            # SRD that decided it — 55 of the 127 are worn, 72 are measured NOT
            # worn on their own text. Neither answer is a default.
            _shelf, marvel_slot, why = MARVEL[name]
            if marvel_slot:
                return {"state": "worn", "worn": True, "slot": marvel_slot,
                        "provenance": "srd:" + why}
            return {"state": "not_worn", "worn": False, "provenance": "srd:" + why}
        return {"state": "not_worn", "worn": False,
                "provenance": "derived:item.category = %s" % category}

    if shelf == ("mundane", "clothing"):
        # Fine clothes, traveler's clothes, a costume, a robe. Obviously worn,
        # and the source never says where: its ten slots were read off the 149
        # marvels and it never asked the question of mundane clothing. Saying
        # `worn=False` here would be inventing an answer; saying `torso` would
        # be inventing a different one.
        return {"state": "unanswered", "worn": None,
                "pending": "the source's ten slots were read off the marvels "
                           "and never asked where mundane clothing goes",
                "provenance": "table:silent"}

    return {"state": "not_worn",
            "worn": False, "provenance": "derived:record kind %s" % kind}


def craftable_of(kind, name):
    """Is this a base the craft lays magic onto? With its provenance."""
    if kind in CRAFT_BASE_KINDS:
        return {"value": True, "provenance": "derived:record kind %s" % kind}
    if name in CRAFT_BASE_GEAR:
        return {"value": True,
                "provenance": "table:rangement 2026-08-22 (craft bases)"}
    return {"value": False, "provenance": "derived:record kind %s" % kind}


# ---------------------------------------------------------------------------
# The shape Eric read. A drift here stops the build.
# ---------------------------------------------------------------------------
# Same reasoning as `srfh.RATIFIED`: these are not "expected numbers", they are
# a classification a person arrested by hand. If the catalogue moves under them,
# this layer must not follow in silence — a shelf nobody chose is a shelf nobody
# agreed to.
RATIFIED_TOTAL = 416
RATIFIED_SHELF_COUNT = {
    ("adventuring", "camp"): 3,
    ("adventuring", "force-and-trap"): 10,
    ("adventuring", "light-and-fire"): 6,
    ("adventuring", "packs"): 7,
    ("adventuring", "ropes-and-climbing"): 8,
    ("adventuring", "watch-and-signal"): 5,
    ("arcana", "consumables-and-potions"): 33,
    ("arcana", "scrolls-foci-components"): 7,
    ("arcana", "wands-rods-staves"): 32,
    ("armory", "armor"): 13,
    ("armory", "magic-armor"): 19,
    ("armory", "magic-weapons"): 33,
    ("armory", "melee-weapons"): 28,
    ("armory", "ranged-weapons"): 11,  # 10 armes à distance + la ligne Ammunition
    # ✅ RATIFIÉ PAR ERIC LE 2026-08-24 (« Je valide »). Les quatre entrées de
    # `companions` viennent de SON document de rangement ; deux seulement
    # étaient déclarées, ce qui sortait le rayon à deux crans — sous le minimum
    # de trois, donc « court » à l'écran, ce qu'il a vu et n'aime pas.
    # ⛔ Zéro n'est pas « pas encore répondu » : c'est un rayon DÉCLARÉ et VIDE,
    # et le tambour doit le montrer tel quel. Un rayon qui disparaît quand il se
    # vide fait sauter la roue.
    ("companions", "bespoke"): 0,
    ("companions", "familiars"): 0,
    ("companions", "henchmen"): 0,
    ("companions", "monster-search"): 0,
    ("crafting", "gems"): 0,
    ("crafting", "ingredients"): 0,
    ("crafting", "tools"): 25,
    ("marvels", "clothing"): 32,
    # 15 → 14 le 2026-08-24, ratifié par Eric : la Perle de puissance est partie
    # chez les curios. Un compte qu'une règle nommée déplace n'est pas un compte
    # qu'on rate — le motif entier est à sa ligne dans MARVEL.
    ("marvels", "consumables"): 14,
    ("marvels", "containers-and-vehicles"): 24,
    ("marvels", "foci-and-curios"): 34,
    ("marvels", "helms-and-lenses"): 8,
    ("marvels", "jewellery"): 15,
    ("marvels", "rings"): 22,
    ("mundane", "clothing"): 5,
    ("mundane", "containers"): 16,
    ("mundane", "writing-and-reading"): 6,
}
# The ten slots as the source prints them, PLUS what the source says shares
# them: `torso` also carries the 12 body armors, `hands` also carries the 38
# weapons and the shield. Eric's own line — *Torse 5, robes et les 13 armures* —
# counts the shield among the 13; measured, the shield is in the hands and the
# torso holds 12. Same objects, and this is where the two readings meet.
RATIFIED_SLOT_COUNT = {
    "back": 10,        # 8 cloaks, 1 mantle, 1 pair of wings
    "eyes": 4,         # 3 "eyes" and the goggles
    "feet": 7,         # 6 boots and the slippers
    "fingers": 22,     # the 22 rings, and the only slot left open
    "forearms": 2,     # the 2 bracers
    "hands": 43,       # 4 marvels + 38 weapons + the shield
    "head": 8,         # 4 helms, hat, headband, circlet, ioun stone
    "neck": 13,        # amulets, periapts, talismans, necklaces, medallion, brooch
    "torso": 17,       # 5 robes + 12 body armors
    "waist": 2,        # the 2 belts
}
# 🔴 FOUR NUMBERS, NEVER ONE, and the two in the middle are the ones this lot
# exists to keep apart. `not_worn` is 231 MEASURED refusals; `pending` is 5
# objects nobody has ruled on — the mundane clothes, whose slot the source
# never asked about because its ten slots were read off the marvels.
RATIFIED_SLOT_TALLY = {"decided": 128, "from_base": 52, "pending": 5,
                       "not_worn": 231}
RATIFIED_CRAFTABLE = 54

KINDS = ("armor", "gear", "item", "tool", "weapon")


def _check_table_covers_the_catalogue(names_by_kind):
    """Every table key names a record, and every gear record has a key.

    Both directions, because they fail differently. A key naming nothing is a
    typo or a rename upstream; a record naming no key is an object with no
    shelf, which is the one outcome this lot exists to prevent.
    """
    gear = names_by_kind["gear"]
    unknown = sorted(set(SHELF_OF_GEAR) - gear)
    if unknown:
        raise ShelvingError(
            "%d shelving table key(s) name no gear record:\n%s\n\nEither the "
            "catalogue renamed a row or the transcription has a typo. It is not "
            "safe to guess which."
            % (len(unknown), "\n".join("  " + n for n in unknown)))
    for name in CRAFT_BASE_GEAR:
        if name not in gear:
            raise ShelvingError(
                "the craft base %r names no gear record" % name)
    # Cross-check the document's own per-shelf counts before using the table.
    measured = {}
    for shelf in SHELF_OF_GEAR.values():
        measured[shelf] = measured.get(shelf, 0) + 1
    if measured != GEAR_SHELF_COUNT:
        drift = sorted(set(measured) | set(GEAR_SHELF_COUNT))
        raise ShelvingError(
            "the transcription does not add up to the document's counts:\n"
            + "\n".join(
                "  %-40s transcribed %d, document %d"
                % ("/".join(s), measured.get(s, 0), GEAR_SHELF_COUNT.get(s, 0))
                for s in drift
                if measured.get(s, 0) != GEAR_SHELF_COUNT.get(s, 0)))


def _check_the_marvels_are_erics(wondrous):
    """Both directions, the seven counts, and every quotation checked verbatim.

    ⭐ The last one is the guard that matters. Each of the 149 rows carries the
    SRD sentence that decides it, and that sentence is checked to be REALLY IN
    the record it justifies. A plausible-sounding reason cannot be written here:
    if the book does not contain it, the build stops. That is the difference
    between a classification with evidence and a classification with prose.
    """
    unknown = sorted(set(MARVEL) - set(wondrous))
    if unknown:
        raise ShelvingError(
            "%d marvel row(s) name no record:\n%s"
            % (len(unknown), "\n".join("  " + n for n in unknown)))
    missing = sorted(set(wondrous) - set(MARVEL))
    if missing:
        raise ShelvingError(
            "%d marvel(s) have no shelf:\n%s" % (len(missing),
                                                 "\n".join("  " + n for n in missing)))

    measured = {}
    for shelf, _slot, _why in MARVEL.values():
        measured[shelf] = measured.get(shelf, 0) + 1
    measured["rings"] = MARVEL_SHELF_COUNT["rings"]   # derived, not tabled
    if measured != MARVEL_SHELF_COUNT:
        raise ShelvingError(
            "the split does not land on the seven counts Eric printed on "
            "2026-08-21:\n"
            + "\n".join(
                "  %-26s measured %d, arrested %d" % (k, measured.get(k, 0),
                                                      MARVEL_SHELF_COUNT.get(k, 0))
                for k in sorted(set(measured) | set(MARVEL_SHELF_COUNT))
                if measured.get(k, 0) != MARVEL_SHELF_COUNT.get(k, 0))
            + "\n⛔ Do NOT move an object to make the arithmetic work. Name it, "
              "say where you put it and why, and leave the gap showing.")

    for name, (_shelf, slot, why) in sorted(MARVEL.items()):
        if slot is not None and slot not in SLOTS:
            raise ShelvingError("%r wants slot %r, which is not one of the ten"
                                % (name, slot))
        haystack = " ".join(wondrous[name].split())
        for sentence in [p.strip() for p in why.split(". ") if p.strip()]:
            if sentence.rstrip(".") not in haystack:
                raise ShelvingError(
                    "the reason given for %r is not in the SRD text of %r:\n"
                    "  %s\n\nA justification that the book does not contain is "
                    "not a justification." % (name, name, sentence))

    for name in MARVEL_DOUBT:
        if name not in MARVEL:
            raise ShelvingError("a doubt names %r, which is on no shelf" % name)


def build_shelving(conn, lang="en"):
    """Write the shelving layer. Returns (by_shelf, by_slot, tally, notes)."""
    rows = {}
    names_by_kind = {}
    for kind in KINDS:
        rows[kind] = [
            (r["id"], r["slug"], r["name"], json.loads(r["data"]))
            for r in conn.execute(
                "SELECT id, slug, name, data FROM record"
                " WHERE layer='srd' AND kind=? AND lang=? ORDER BY slug",
                (kind, lang))
        ]
        names_by_kind[kind] = {n for _i, _s, n, _d in rows[kind]}

    _check_table_covers_the_catalogue(names_by_kind)
    _check_the_marvels_are_erics({
        n: d["description"] for _i, _s, n, d in rows["item"]
        if d["category"] == "wondrous-item"})

    by_shelf = {shelf: 0 for aisle in SHELVES for shelf in
                [(aisle, s) for s in SHELVES[aisle]]}
    by_slot = {}
    tally = {"decided": 0, "from_base": 0, "pending": 0, "not_worn": 0}
    source = {"derived": 0, "table": 0}
    craftable_count = 0
    records = []
    notes = []

    for kind in KINDS:
        for srd_id, slug, name, data in rows[kind]:
            aisle, shelf, provenance = shelf_of(kind, name, data)
            if (aisle, shelf) not in by_shelf:
                raise ShelvingError(
                    "%r was shelved on %s/%s, which is in no aisle"
                    % (name, aisle, shelf))
            by_shelf[(aisle, shelf)] += 1
            source["table" if provenance.startswith("table:") else "derived"] += 1

            worn = slot_of(kind, name, data, (aisle, shelf))
            # Counted off the state the record NAMES, never off the shape of
            # what is missing from it. `pending` and `not_worn` are two answers
            # here and they must stay two answers all the way to the export.
            state = worn["state"]
            if state == "worn":
                tally["decided"] += 1
                by_slot[worn["slot"]] = by_slot.get(worn["slot"], 0) + 1
            elif state == "from_base":
                tally["from_base"] += 1
            elif state == "unanswered":
                tally["pending"] += 1
            elif state == "not_worn":
                tally["not_worn"] += 1
            else:
                raise ShelvingError("%r came back in state %r" % (name, state))

            craft = craftable_of(kind, name)
            if craft["value"]:
                craftable_count += 1

            payload = {
                "name": name,
                "extends": srd_id,
                "of_kind": kind,
                "shelf": {
                    "aisle": aisle,
                    "shelf": shelf,
                    "provenance": provenance,
                    # Carried on the record, not only in this module: a reader
                    # holding one exported row must be able to see that the
                    # aisle it names has not been ratified.
                    "aisle_name_provisional": aisle in PROVISIONAL_AISLE,
                    "shelf_provisional": (aisle, shelf) in PROVISIONAL_SHELF,
                },
                "slot": worn,
                "craftable": craft,
            }
            records.append((
                {
                    "id": canon.record_id(LAYER, KIND, lang, slug),
                    "layer": LAYER,
                    "kind": KIND,
                    "lang": lang,
                    "slug": slug,
                    "name": name,
                    "data": canon.canonical_json(payload),
                    "content_hash": canon.content_hash(KIND, lang, name, payload),
                    "source_id": None,
                    "source_locator": "",
                    "srd_version": None,
                    "license": LICENSE,
                    "attribution": ATTRIBUTION,
                },
                srd_id,
            ))

    # ---- reconciliation ---------------------------------------------------
    total = sum(by_shelf.values())
    if total != RATIFIED_TOTAL or total != len(records):
        raise ShelvingError(
            "%d record(s) shelved, %d ratified, %d emitted — the requirement "
            "is every object and no remainder"
            % (total, RATIFIED_TOTAL, len(records)))

    drift = {k: (v, RATIFIED_SHELF_COUNT.get(k))
             for k, v in by_shelf.items() if RATIFIED_SHELF_COUNT.get(k) != v}
    drift.update({("slot", k): (v, RATIFIED_SLOT_COUNT.get(k))
                  for k, v in by_slot.items() if RATIFIED_SLOT_COUNT.get(k) != v})
    drift.update({("tally", k): (v, RATIFIED_SLOT_TALLY[k])
                  for k, v in tally.items() if RATIFIED_SLOT_TALLY[k] != v})
    if craftable_count != RATIFIED_CRAFTABLE:
        drift[("craftable", "")] = (craftable_count, RATIFIED_CRAFTABLE)
    if drift:
        raise ShelvingError(
            "the catalogue moved under a classification Eric arrested by hand "
            "on 2026-08-21/22:\n"
            + "\n".join("  %-46s measured %s, ratified %s"
                        % ("/".join(str(p) for p in k), got, want)
                        for k, (got, want) in sorted(drift.items(), key=str))
            + "\nRe-read the change, then update the ratified counts with his "
              "answer.")

    for rec, _dst in records:
        db.insert_record(conn, rec)
    for rec, dst_id in records:
        conn.execute(
            "INSERT INTO record_link (src_id, dst_id, rel, note) VALUES (?,?,?,?)",
            (rec["id"], dst_id, "extends",
             "SRFH carries the shelf and the body slot the SRD never printed"))
    conn.commit()

    notes.append(
        "shelf: %d derived from a field already in the record, %d read from "
        "the written table" % (source["derived"], source["table"]))
    notes.append(
        "the 149 marvels: %s -- all seven land on the counts Eric arrested on "
        "2026-08-21, and %d of the 127 wondrous rows carry a doubt"
        % (", ".join("%s %d" % (k, v) for k, v in
                     sorted(MARVEL_SHELF_COUNT.items(), key=lambda kv: (-kv[1], kv[0]))),
           len(MARVEL_DOUBT)))
    notes.append(
        "slots: %d placed, %d follow a base chosen at purchase, %d MEASURED not "
        "worn, %d unanswered (the 5 mundane clothes -- the source's ten slots "
        "were read off the marvels and never asked about them). The last two "
        "are different answers and the export says which is which."
        % (tally["decided"], tally["from_base"], tally["not_worn"],
           tally["pending"]))
    notes.append(
        "craftable: %d bases — %d weapons and armor, from the record kind "
        "alone, and %d named gear rows. Rarity plays NO part: all %d are "
        "mundane rows with no rarity at all, so this is not Foundry's "
        "rarity-and-days calculation wearing a different name."
        % (craftable_count, len(rows["weapon"]) + len(rows["armor"]),
           len(CRAFT_BASE_GEAR), craftable_count))
    return by_shelf, by_slot, tally, notes


# ---------------------------------------------------------------------------
# The DECLARED structure, published beside the records
# ---------------------------------------------------------------------------
# 🔴 THE DEFECT THIS CLOSES, and it was measured on 2026-08-24: the export
# carried 416 records and every one of them named an aisle and a shelf — so a
# reader could only ever recover the combinations that HAPPEN TO BE POPULATED.
# That is SIX aisles and TWENTY-SIX shelves. The table above declares SEVEN and
# THIRTY. The whole `companions` aisle (`familiars`, `henchmen`) and
# `crafting/gems` + `crafting/ingredients` were invisible, because zero records
# name them and a count you obtain by grouping records can never produce a zero.
#
# ⛔ AN ABSENCE IS NOT AN ANSWER. An empty shelf is not a shelf that does not
# exist: `gems` and `ingredients` are announced *à créer, « en préparation pour
# le soulforging »* in Eric's own document, and `companions` is a whole aisle he
# still has to fill with statblocks. They are waiting, not missing.
#
# ⭐ AND THE SCREEN CANNOT INVENT THEM. The lot that reads this layer refused to
# type the seven names by hand — *"that would be `ETAGERE_DE` reinstalled one
# storey up"* — and it was right: the classification belongs to the LAYER, not
# to its reader. So the layer says it. Eric arrested on 2026-08-22 that an empty
# aisle STAYS DISPLAYED, because an aisle that appears and disappears with its
# contents makes the bar under it change height as you browse, and a screen that
# moves under your finger is one nobody dares touch.
#
# THE ORDER IS CARRIED BY LISTS, NEVER BY DICT KEYS. `canon.canonical_json`
# sorts keys; a mapping of aisle -> shelves would be re-alphabetised on the way
# out and the declared order would be silently replaced by an accident of
# spelling. Lists survive the writer intact.
#
# ⚠️ ONE MEASURED CONTRADICTION, PUBLISHED AS IT STANDS AND NOT REPAIRED HERE.
# The comment above `SHELVES` says the table is *alphabetical at both levels*.
# Six aisles are. `mundane` is not: it reads `containers, clothing,
# writing-and-reading`, which is the order of Eric's own document (*Contenants ·
# Vêtements · Écrire & lire*), not the alphabet. Re-ordering it would MOVE a
# populated aisle, and this lot's whole claim is that publishing emptiness moves
# nothing — so the deviation is measured, published as declared, and asked in
# QUESTIONS-ARCHITECTE.md rather than settled by a lot that was not asked to.


def declared_structure(records):
    """The seven aisles and thirty shelves, in declared order, counts included.

    `records` is the exported record list — the same objects the file ships, not
    a second query of the table. Counting anywhere else would let the published
    counts and the published records disagree without anything noticing, which
    is the failure this repository already paid for once.
    """
    counted = {(aisle, shelf): 0
               for aisle in SHELVES for shelf in SHELVES[aisle]}
    for record in records:
        shelf = record["data"]["shelf"]
        key = (shelf["aisle"], shelf["shelf"])
        if key not in counted:
            raise ShelvingError(
                "%r is exported on %s/%s, which the declared structure does not "
                "hold. The export and the table disagree; neither is safe to "
                "assume right." % (record["name"], key[0], key[1]))
        counted[key] += 1

    total = sum(counted.values())
    if total != len(records):
        raise ShelvingError(
            "%d record(s) counted onto a shelf, %d exported" % (total, len(records)))

    aisles = []
    for aisle in SHELVES:
        shelves = []
        for shelf in SHELVES[aisle]:
            entry = {"shelf": shelf,
                     "count": counted[(aisle, shelf)],
                     "provisional": (aisle, shelf) in PROVISIONAL_SHELF}
            reason = PROVISIONAL_SHELF.get((aisle, shelf))
            if reason:
                entry["provisional_because"] = reason
            shelves.append(entry)
        aisles.append({
            "aisle": aisle,
            "count": sum(s["count"] for s in shelves),
            # The NAME is provisional, never the aisle: `Arcana` and `Marvels`
            # are proposed and not ratified, and the structure under them is
            # firm. A reader holding this block must be able to tell those two
            # apart without going back to the document.
            "name_provisional": aisle in PROVISIONAL_AISLE,
            "shelves": shelves,
        })

    empty = [(a["aisle"], s["shelf"]) for a in aisles for s in a["shelves"]
             if s["count"] == 0]
    return {
        "structure": {
            "$note": (
                "DECLARED, not observed. Every aisle and every shelf Eric "
                "arrested on 2026-08-21/22 is here IN ORDER and WITH ITS COUNT, "
                "including the ones at zero — an empty shelf is a shelf that is "
                "waiting, not a shelf that does not exist, and grouping the "
                "records below can never produce a zero. The order is the "
                "declared one and it is carried by the lists; do not re-sort it. "
                "`name_provisional` marks an aisle whose NAME is proposed and "
                "not ratified (Arcana, Marvels) — the structure under it is firm."
                "\n\n"
                "⚠️ WHAT THESE COUNTS COUNT, SAID OUT LOUD (2026-08-24). They "
                "count the records THIS FILE SHIPS, and nothing else. They are "
                "not a promise about what any mounted stack will show: a layer "
                "above may DISABLE a record, and then the drum shows fewer. "
                "That is not a disagreement — the two numbers answer different "
                "questions.\n"
                "🔴 IT HAS ALREADY MISLED SOMEONE. `crafting/tools` ships 25 "
                "here; a builder that mounts a house layer disabling "
                "`gaming-set` and `musical-instrument` renders 23, and the gap "
                "was read as a defect in this file. It is not: a consumer that "
                "prints this count beside its OWN list must derive both from "
                "the same reading, or it will be wrong again at the next "
                "difference.\n"
                "⭐ On this side the rule already holds: these counts are taken "
                "from the exported record list itself, never from a second "
                "query — see `declared_structure`."
            ),
            "aisle_count": len(aisles),
            "shelf_count": sum(len(a["shelves"]) for a in aisles),
            "empty_shelf_count": len(empty),
            "empty_shelves": ["%s/%s" % (a, s) for a, s in empty],
            "shelved_total": total,
            "aisles": aisles,
        }
    }
