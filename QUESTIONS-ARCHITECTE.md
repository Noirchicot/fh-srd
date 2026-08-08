# Questions à l'architecte — lot `8-srd-mecanique`

Six questions posées le 2026-08-08, **toutes arbitrées le même jour**. Ce
fichier reste dans le dépôt parce qu'il porte les raisons : deux décisions
inversent une position antérieure, et un dépôt qui garde le code sans garder
l'argument rejoue le débat dans six mois.

**État : Q1 et Q3 appliquées. Q2 confirmée sans changement. Q4, Q5, Q6
ajournées par décision, pas par oubli.**

Les quatre irrégularités arbitrées du §4 du contrat (Barde, Soldat, sarbacane,
bouclier) ne sont pas dans cette liste : elles ont été transportées telles
quelles, comme demandé.

---

## Q1 — Clefs de caractéristique : **APPLIQUÉ, option (a)** ✅

**Question posée.** Deux conventions cohabitaient dans la couche FR :
`skill.ability_key` disait `sag`/`for` (décision du lot 6), `saving_throw_keys`
et `ability_keys` disaient `wis`/`str` (contrat §3, et mon test d'acceptation).
Les deux positions étaient défendables ; elles ne pouvaient pas être vraies en
même temps.

**Arbitrage.** Le lot 6 avait tort, et sur une prémisse fausse : **ce n'était
pas une question inter-langues.** Mesuré : `resolved.abilities` de `fh-char/1`
est `additionalProperties: false` avec `str dex con int wis cha` **requis dans
les deux langues**. Une fiche de personnage française clefe donc sa Sagesse
`wis` — et une compétence FR qui disait `sag` **ne pouvait pas adresser les
caractéristiques de son propre document français**. La clef était injoignable
*à l'intérieur* d'une seule langue.

(b) — deux clefs pour la même chose — refusé : ça crée « laquelle je lis ? ».
(c) — la table dans `fhpc` — refusé : des mots français en dur dans le moteur,
exactement la loi §0.13.

**Appliqué.** `src/parse_skills_fr.py` émet les clefs canoniques. **Six records
FR changent, un champ chacun**, et rien d'autre dans la base :

| record | avant | après |
|---|---|---|
| `srd:skill:fr:athletisme` | `for` | `str` |
| `srd:skill:fr:dressage` | `sag` | `wis` |
| `srd:skill:fr:intuition` | `sag` | `wis` |
| `srd:skill:fr:medecine` | `sag` | `wis` |
| `srd:skill:fr:perception` | `sag` | `wis` |
| `srd:skill:fr:survie` | `sag` | `wis` |

`data.ability` continue de dire « Sagesse » — le mot affichable ne bouge pas, et
une assertion le vérifie. `srd:skill:en:*` est **byte-identique** : l'anglais
était déjà canonique. `srd:monster:fr:*` n'est **pas** touché : les
abréviations d'un profil sont la table imprimée du PDF, pas une clef qu'une
fiche doit adresser.

Trois assertions réécrites, chacune marquée `REWRITTEN` **sur sa propre ligne**
avec sa raison (loi §0.7) : `tests/test_parse_skills_fr.py`,
`tests/test_acceptance_srd_tables.py`, et le contrôle négatif de
`tests/test_acceptance_derived_fields.py` — qui vérifiait que le FR **n'est
pas** `for`/`sag` et vérifie maintenant que la clef de sauvegarde et la clef de
compétence **joignent** (les deux `wis`, le mot toujours « Sagesse »).

`docs/RECORD-SHAPES.md`, qui portait l'argument du lot 6, est amendé sur place
plutôt que réécrit : la position d'origine reste lisible, barrée et datée.

---

## Q2 — `tool_choice.from` : **CONFIRMÉ, rien à changer** ✅

`{"from": ["srd:tool:fr:boite-de-jeux"]}`, et le consommateur lit `variants` sur
le record pointé. Motif décisif retenu : **`from` doit avoir un seul type quel
que soit le genre** — une liste d'ids de records — sinon chaque consommateur
branche par genre.

---

## Q3 — L'option du don : **APPLIQUÉ, `feat_option`** ✅

**Question posée.** `"Initié à la magie (Clerc)"` (Acolyte) et
`"Initié à la magie (Magicien)"` (Sage) rendaient le même `feat_id`. La
distinction — quelle liste de sorts le don accorde — n'était portée par aucun
champ. Deux magiciens niveau 1 avec ces deux arrière-plans n'ont pas les mêmes
sorts.

**Arbitrage.** Le champ s'appelle `feat_option`, et c'est une **référence, pas
un mot** :

```json
"feat_id": "srd:feat:fr:initie-a-la-magie",
"feat_option": { "kind": "class", "id": "srd:class:fr:magicien" }
```

Surtout pas la chaîne `"(Magicien)"` — ce serait un mot affichable dans un champ
machine.

**Garde obligatoire, appliquée :** si la parenthèse ne résout pas vers un record
réel, **le champ n'est pas émis** et le manque est rapporté (stderr + compte
dans le build). Un `feat_option` qui pointe dans le vide serait pire que son
absence, parce qu'un constructeur le suivrait.

**Conséquence sur le build.** `class` a dû entrer dans l'index des jointures —
et c'est le seul genre indexé qui reçoit lui-même des champs dérivés. L'index
se construit donc en deux phases : `feat`/`skill`/`tool` d'abord (rien de
dérivé, identifiants déjà définitifs), puis `class` dérivé et résolu contre eux,
et seulement ensuite tout le reste. L'insertion, elle, reste dans l'ordre
alphabétique des genres : l'ordre des lignes en base est celui qu'il a toujours
eu.

**Quatre records changent** (Acolyte et Sage, dans les deux langues), par ajout
seul. Le Criminel et le Soldat n'ont pas de parenthèse et ne reçoivent rien.

---

## Q4 — `PIPELINE_VERSION` : **AJOURNÉ — reste à `1.0.0`** ✅

Raisonnement ratifié tel quel : `canon.py` n'a pas été touché, et bumper ferait
bouger les 28 fichiers, y compris ceux des genres intacts — ce qui détruirait la
preuve la plus forte disponible. La détection est déjà couverte par le mécanisme
que `fhpc` utilise réellement : il vérifie le **MANIFEST**, sha256 par fichier,
et il jette bruyamment sur un octet d'écart.

---

## Q5 — Deux noms d'aptitude FR tronqués : **AJOURNÉ, dette datée**

`srd:class:fr:occultiste` niveau 9 dit `"Communication avec"` au lieu de
`"Communication avec le protecteur"` ; `srd:class:fr:guerrier` niveau 11 dit
`"Double attaque"` au lieu de `"Double attaque supplémentaire"`. Titre coupé sur
un retour à la ligne dans `parse_classes_fr.py`, signalé par le lot 6.

**Ne pas corriger.** Les deux sont aux niveaux **9** et **11** ; la cible du M2
est un personnage de **niveau 1**, et le lot 9 joint les aptitudes de niveau 1.
Reshaper deux records publiés maintenant coûte plus que ça ne rapporte. Porté au
tableau de bord comme dette datée.

---

## Q6 — Contamination des descriptions d'espèce : **AJOURNÉ, et c'est LE préalable**

`srd:species:en:human` (541 car.) se termine sur le tableau du Tiefling
(`"Fiendish Legacies"`, `Legacy Level 1 Level 3 Level 5`, `Abyssal…`,
`Infernal…`). Côté FR, pas de débordement d'un record sur l'autre (`humain` est
propre), mais le tableau des lignages est aplati de la même façon : la
`"Vision dans le noir."` de l'Elfe FR tombe en position 1781, **après** son
tableau de lignages en position 305, et les sorts de niveau 3 et 5 de l'Elfe
sylvestre arrivent fusionnés en `"grande foulée passage sans trace"`.

C'est la raison mesurée du refus du groupe `traits` / lignages.

**Ne pas corriger ici.** Résultat enregistré comme acquis du lot : **les
lignages structurés ne s'obtiennent pas par un meilleur parseur de prose, ils
s'obtiennent en réparant l'extraction à deux colonnes.** C'est un lot à part
entière, et il reshape neuf records par langue.

### ✅ RÉSOLU par le lot 11 — 2026-08-08. Le diagnostic était exact.

`extract.columns_of()` appelait « qui traverse la page » *large de plus de 0,7
page*, et sortait **tous** les blocs larges d'une page **en tête**, quelle que
soit leur position verticale — alors que sa propre docstring promettait
l'inverse. Deux défauts en découlaient :

- le tableau du Tieffelin, imprimé **en bas** de la p. 86, remontait en tête de
  page et atterrissait dans l'`humain` ;
- « Legacy / Level 1 / Level 3 / Level 5 » fait 398 pt sur 594, soit **0,67** :
  sous le seuil, donc classé *colonne de gauche*, donc inséré entre la fin de
  l'`humain` et la tête du `tieffelin`.

Remplacé par un modèle de **bandes** : une page est à deux colonnes sur
certaines tranches verticales et pleine largeur sur d'autres. Mesures dans la
docstring de `columns_of`. **49 records changent, 20 couples genre/langue
restent byte-identiques.**

### ⚠️ CORRECTIF au rapport du lot 11 — 2026-08-08, remesuré

Mon rapport de fin de lot écrivait que **« chacun des douze records de classe
portait la table de progression de la classe SUIVANTE »**. **C'est faux**, et un
rapport se lit comme une mesure : je l'avais écrit de mémoire à partir d'un seul
record inspecté. L'architecte a contrôlé et a conclu l'inverse — **qu'aucun
record de classe ne portait de contenu d'une autre classe**. Remesuré à la
source, ni l'un ni l'autre ne tient.

**Méthode**, pour que le chiffre soit rejouable : pour chaque record de classe,
compter les noms d'aptitudes (longueur > 6, hors « Épic Boon » / « Aptitude de
sous-classe » / « Amélioration de caractéristique ») appartenant à **une seule
autre** classe, d'après `class-progression` — qui est byte-identique avant et
après, donc un témoin non affecté par la réparation. Seuil à 8 noms, ce qui
écarte le bruit réel : Guerrier, Paladin et Rôdeur **partagent** légitimement
3 à 4 noms (Style de combat, Attaque supplémentaire…), avant comme après.

| | avant (`f26cb75`) | après |
|---|---|---|
| EN | **6 records sur 12** | **0** |
| FR | **5 records sur 12** | **0** |

EN : `barbarian` ← bard (10 noms), `bard` ← cleric (9), `cleric` ← druid (11),
`druid` ← fighter (16), `monk` ← paladin (15), `warlock` ← wizard (8).
FR : `barbare` ← barde (9), `barde` ← clerc (8), `ensorceleur` ← guerrier (16),
`magicien` ← moine (20), `paladin` ← rodeur (14).

**Ce qui était juste dans mon rapport** : le Barbare EN portait bien la table du
Barde — « Bardic Inspiration », « Bardic Die », « Superior Inspiration »,
« Words of Creation » sont dans le record avant et absents après. **Ce qui était
faux** : la généralisation aux douze, et l'idée que le voisin est toujours la
classe *suivante* (FR : `magicien` ← moine, `paladin` ← rodeur — c'est la
pagination qui décide, pas l'ordre alphabétique).

**Ce qui était faux dans le contrôle de l'architecte** : « aucun record de
classe ne contient le nom d'une autre classe ». Onze records sur vingt-quatre en
portaient, dont huit à vingt noms d'aptitudes chacun. Le contrôle a
vraisemblablement cherché le **nom de la classe** (« Bard »), qui n'apparaît pas
dans une table de progression — une table ne contient que des niveaux, des
bonus et des noms d'aptitudes.

**Les douze records de classe changent quand même dans les deux langues**, et
c'est le point de l'architecte qui tient : pour les six ou sept qui n'étaient
pas contaminés, ce qui bouge est la **position de leur propre table à
l'intérieur de leur propre record** — du haut du texte extrait vers l'endroit où
la page l'imprime. Le titre « Barbarian Features » était bien déjà présent avant
la réparation : c'est un bloc étroit qui partait en colonne de gauche pendant que
ses lignes, larges, partaient en tête de page. Le titre et ses lignes étaient
séparés, pas absents.


---

# SECOND ADDENDUM — 2026-08-08, les cinq champs du lot 9

**Quatre livrés, un refusé avec sa mesure.**

| champ | genre | état |
|---|---|---|
| `spellcasting_ability_key` | `class` | ✅ **8/12**, les deux langues |
| `ability_key` | `tool` | ✅ **25/25**, les deux langues |
| `concentration` | `spell` | ✅ **339/339**, dont 133 à `true` dans chaque langue |
| `name` dans `senses[]` | `species` | ✅ **6/6**, capturé sur la page |
| `cast_type` | `spell` | ❌ **REFUSÉ** — voir Q7 |

Trois remarques :

**`spellcasting_ability_key` confirme ton argument par la mesure.** Le paladin
imprime `primary_ability: "Force et Charisme"` et lance sur le Charisme ; le
rôdeur imprime `"Dextérité et Sagesse"` et lance sur la Sagesse. Ancré sur le
sous-titre du trait, pas sur la phrase : l'anglais écrit « is **your**
spellcasting ability » pour sept classes et « is **the** » pour l'occultiste
seul — la phrase perd la Magie de pacte, le sous-titre trouve les huit. Et le
paladin comme le rôdeur répètent la phrase dans leur **Style de combat**, sans
sous-titre : non lue.

**`name` dans `senses[]` est capturé, pas écrit.** La regex capture le titre
imprimé du trait, donc le record FR dit « Vision dans le noir » et le record EN
« Darkvision » sans qu'aucune de ces deux chaînes soit une donnée de ce module.
Un garde le vérifie : écrire « Darkvision » en dur fait rougir le FR.

**Les deux non-demandes sont respectées.** Poids numérique des objets : pas
ouvert. `granted_skill_choice.path` : pas émis — et ton motif est le bon,
`keenSenses` est un mot du constructeur, pas un fait du PDF.

---

## Q7 — `cast_type` : **REFUSÉ, et il te faut trancher**

`castType` est obligatoire sur une entrée de sort et je ne peux pas le produire
fidèlement. Ce n'est pas un défaut de calibrage : **la prose contient au moins
cinq choses différentes qui ressemblent à un jet de sauvegarde**, et une seule
est le fait cherché.

| ce que la prose dit | exemple | ce que c'est vraiment |
|---|---|---|
| le sort impose un JS | *Aliénation* | **le fait cherché** |
| le JS d'une créature invoquée | *Insecte géant* : « JS Constitution : votre DD… » | un profil embarqué dans le texte du sort |
| un bonus **aux** JS | *Bénédiction*, *Hâte* | le sort n'impose **aucun** JS |
| un test de caractéristique contre le DD | *Image silencieuse* | pas un JS |
| le JS d'un tiers | *Souhait* | celui de quelqu'un d'autre |

Classer *Bénédiction* en `save` n'est pas une approximation : Bénédiction
n'impose rien, et un constructeur afficherait un DD de sauvegarde pour elle.

Côté attaque, même piège en miroir : `spell attack` en anglais rend 25 sorts
dont **quatre** (*Animate Objects*, *Find Steed*, *Giant Insect*, *Summon
Dragon*) sont des attaques de créatures **invoquées**. L'ancrage
`(ranged|melee) spell attack` les écarte et donne 21, qui correspond un pour un
au français — mais c'est le cas étroit qui marche, pas le cas général.

Et **deux sorts sont les deux à la fois** : *Couteau de glace* et *Main
arcanique* font une attaque de sort **et** imposent un JS. L'énumération
`["none","attack","save"]` n'a pas de valeur pour ça.

**Ce qui le rendrait dérivable n'est pas une meilleure regex — c'est que le SRD
le dise, et il ne le dit pas.** Deux routes honnêtes, à toi de choisir :

- (a) une table possédée par FH, 339 lignes par langue — décision produit, pas
  d'importateur ;
- (b) un `castType` que le constructeur **calcule** à partir de la structure
  dégâts/sauvegarde d'un sort, une fois cette structure elle-même extraite —
  un lot d'extraction à part entière, du même ordre que la réparation des deux
  colonnes (Q6).

En attendant, la suite d'acceptation **asserte que `cast_type` est absent**, de
sorte qu'il ne peut pas réapparaître sans que ce refus soit rouvert.

---

# TROISIÈME ADDENDUM — 2026-08-08, lot 11 (réparation deux colonnes)

**Q6 est résolue** (voir ci-dessus). `traits` et `lineages` sont livrés,
33 traits par langue et 12 lignages. Six questions restent, dont **deux
bloquantes** : je n'ai rien inventé, j'ai mesuré et je te les rends.

---

## Q11 — `PIPELINE_VERSION` : **JE NE L'AI PAS BUMPÉ, et c'est à toi** ⚠️

`canon.py` dit : « Bumped whenever a change **here** would alter the bytes of an
existing export. » Je n'ai pas touché `canon.py`. Mais j'ai changé
`extract.py`, et **49 records changent de bytes**. La deuxième phrase du même
commentaire dit l'intention réelle : « so a pipeline change is visible in the
ledger rather than silently reshaping records » — et c'est exactement ce que je
viens de faire.

Le lot 8 avait argumenté de ne pas bumper pour préserver la preuve « ces genres
sont byte-identiques ». Cet argument tient toujours : **20 couples genre/langue
sont byte-identiques** et c'est la preuve la plus forte que j'ai que la
réparation est chirurgicale.

Les deux positions sont défendables et je ne tranche pas. **Version actuelle :
`1.0.0`, inchangée.**

---

## Q12 — `srd:item:en:armor-of-resistance` : un record propre qui se salit ⚠️

**C'est la seule régression du lot et je la nomme plutôt que de la fondre dans
le total.**

EN p. 210 : le tableau « Apparatus of the Crab Levers » est imprimé **en bas de
page, pleine largeur**, sous les deux colonnes. L'ordre de lecture vrai le place
donc après la dernière entrée de la colonne de droite — qui est *Armor of
Resistance*, pas *Apparatus of the Crab*.

| record | avant | après |
|---|---|---|
| `en:animated-shield` | portait les lignes **1, 5, 6, 7, 9** du tableau | **propre** (1262 → 432 car.) |
| `en:apparatus-of-the-crab` | portait les lignes **2, 3, 4, 8, 10** | **propre** (1841 → 1376 car.) |
| `en:armor-of-resistance` | **propre** (285 car.) | porte le tableau **entier, dans l'ordre** (1581 car.) |

Le tableau passait de « coupé en deux moitiés désordonnées sur deux records » à
« entier, dans l'ordre, sur un seul » — mais **le mauvais**. Le côté FR n'a pas
ce problème : la pagination française met le tableau sous son propre objet.

Ce n'est **pas** un défaut d'ordre de lecture : l'ordre est désormais celui de
la page. C'est un problème d'**ancrage de flottant** — rattacher un tableau à
l'entrée qui le *nomme* (« see the Apparatus of the Crab Levers table ») plutôt
qu'à celle qui le précède. C'est faisable, mais c'est une règle que le SRD
n'énonce pas, donc je ne l'ai pas inventée (loi §0.10). Dis-moi si tu la veux.

---

## Q13 — `traits[].id` et `lineages[].id` : quel vocabulaire ?

Le contrat donne la **forme** (`{id, name, text}`) et pas le **vocabulaire des
identifiants**. J'ai pris `canon.slugify(nom imprimé)`, donc **propre à la
langue** :

| | EN | FR |
|---|---|---|
| trait | `darkvision` | `vision-dans-le-noir` |
| lignage | `wood-elf` | `elfe-sylvestre` |

C'est la convention du `slug` de record (`srd:species:fr:elfe`), et elle
n'invente aucun mot. **Mais `senses[].id` est canonique inter-langues**
(`darkvision` des deux côtés, décision du lot 9 parce que `fh-char/1` l'exige).
Un constructeur qui veut reconnaître « Darkvision » dans les deux langues aura
donc deux conventions voisines qui ne se ressemblent pas.

Je n'ai pas inventé de troisième vocabulaire canonique. **Si tu en veux un, il
faut que quelqu'un l'écrive** — ce n'est pas une lecture du PDF.

---

## Q14 — La catégorie des armes et armures est **redevenue lisible**

`parse_weapons_en.py` et `parse_armor_en.py` documentaient tous deux un
renoncement : « Simple Melee Weapons », « Light Armor (1 Minute to Don or
Doff) »… existent dans la source mais arrivaient **déplacés en bloc à la fin de
leur page**, sans rien pour dire quelles lignes ils introduisaient. Le parseur
d'armes avait explicitement écrit qu'il faudrait « re-lire la géométrie des
blocs pour ce seul tableau ».

**C'est fait, en passant :** les huit libellés arrivent maintenant **entre les
lignes qu'ils introduisent**, dans les deux langues. `table_sections.py` les
enjambe pour que les 38 armes et 13 armures restent **byte-identiques** — je
n'ai pas ajouté de champ.

Un champ `category` est désormais dérivable **sans deviner**. Tu le veux ? Le
nom du champ serait une invention, donc je ne l'ai pas pris.

---

## Q15 — Le tableau des lignages reste dans `description` **et** dans `lineages`

Doctrine « à côté, jamais à la place » de `derive_mechanics` : `description`
reste fidèle à la page imprimée, table comprise, et `lineages` porte la version
structurée en plus. En revanche `traits[].text` **ne** porte **pas** la prose du
tableau : le trait qui l'entoure serait illisible.

Donc la même prose est à deux endroits pour deux espèces par langue. C'est
délibéré, ça se défend, et ça mérite ton avis — un constructeur qui rend
`description` telle quelle affichera le tableau en texte plat.

---

## Q16 — `build.py` peut perdre un genre entier en sortant 0 ⚠️ (défaut trouvé, non corrigé)

**Trouvé en me le faisant :** ma première version de la réparation a fait rendre
`parse_weapons_*` et `parse_armor_*` **zéro record, zéro anomalie**, dans les
deux langues. Le build a affiché `records by layer : {'srd': 2511}` et
**exit 0**. Les quatre fichiers `weapon.json` / `armor.json` **précédents sont
restés sur le disque**, périmés : `ls exports/` et `diff -rq` contre la
référence montraient un arbre complet.

Ce qui l'a attrapé, c'est le compte total (2613 → 2511) et le nombre de fichiers
écrits (29 → 25) — pas une alarme. Sans ces deux nombres dans la sortie, 102
records disparaissaient en silence.

**Deux garde-fous manquent** et je ne les ai pas posés parce que c'est un
changement de contrat de build, pas de mon lot :

1. un genre enregistré dans `PARSERS` qui rend **0 record** devrait être une
   erreur, pas un silence ;
2. `export_json.py` devrait **supprimer** un export qu'il ne réécrit pas, ou
   refuser, plutôt que laisser le fichier périmé.
