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

## 🔴 RÉVISION DU 2026-08-24 — LES ADRESSES DE CE FICHIER N'EXISTENT PLUS

Ce fichier cite des records par leur adresse **française**. Depuis la
transition à froid (lot 104), il n'y en a plus une seule dans le dépôt : un
record a UNE adresse, anglaise, et le français est un patch de mots posé
dessus.

⛔ **Les arguments ci-dessous ne sont pas retouchés** — un dépôt qui garde le
code sans garder l'argument rejoue le débat dans six mois, et c'est la raison
d'être de ce fichier. Les records sont donc nommés par leur **slug français**,
qui est un mot du livre et n'a pas bougé, au lieu d'une adresse qui, elle, a
disparu. ⭐ *Ce qui a été décidé le 2026-08-08 l'a été ; ce que ça adressait a
changé de nom.*

⚠️ Et deux affirmations de ce fichier sont devenues fausses **le 2026-08-23**,
au lot 98, sans que rien ne le signale : les monstres français ne clefent plus
`for`/`sag`, et les clefs de ressource ne sont plus langue-natives. Elles sont
laissées telles quelles avec cette mise en garde — les corriger effacerait la
mesure qui les a démenties.

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
| `skill « athletisme »` | `for` | `str` |
| `skill « dressage »` | `sag` | `wis` |
| `skill « intuition »` | `sag` | `wis` |
| `skill « medecine »` | `sag` | `wis` |
| `skill « perception »` | `sag` | `wis` |
| `skill « survie »` | `sag` | `wis` |

`data.ability` continue de dire « Sagesse » — le mot affichable ne bouge pas, et
une assertion le vérifie. `srd:skill:en:*` est **byte-identique** : l'anglais
était déjà canonique. les profils de monstres français ne sont **pas** touchés : les
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

`{"from": ["<tool « boite-de-jeux », adresse d'alors>"]}`, et le consommateur lit `variants` sur
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
"feat_id": "<feat « initie-a-la-magie », adresse d'alors>",
"feat_option": { "kind": "class", "id": "<class « magicien », adresse d'alors>" }
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

`class « occultiste »` niveau 9 dit `"Communication avec"` au lieu de
`"Communication avec le protecteur"` ; `class « guerrier »` niveau 11 dit
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

## Q12 — `srd:item:en:armor-of-resistance` : **RÉSOLU par le lot 18** ✅

REWRITTEN
*(Le tableau et la conclusion ci-dessous ont été réécrits par le lot
`18-srd-ancrage`. La question posée par le lot 11 — « c'est faisable, mais
c'est une règle que le SRD n'énonce pas, dis-moi si tu la veux » — a reçu sa
réponse : la règle **est** énoncée par la source, deux fois, et c'est ce qui
la rend implémentable sans rien inventer. L'ancien tableau décrivait l'état
publié entre le lot 11 et le lot 18 ; il est faux depuis le rebuild du lot 18
et il est remplacé, pas supprimé.)*

EN p. 210 : le tableau « Apparatus of the Crab Levers » est imprimé **en bas de
page, pleine largeur**, sous les deux colonnes. L'ordre de lecture vrai le place
donc après la dernière entrée de la colonne de droite — qui est *Armor of
Resistance*, pas *Apparatus of the Crab*.

| record | lot 11 (publié) | lot 18 (maintenant) |
|---|---|---|
| `en:animated-shield` | **propre** (432 car.) | **inchangé, byte-identique** (432 car.) |
| `en:apparatus-of-the-crab` | propre mais **sans son tableau** (1376 car.) | **porte son tableau entier, dans l'ordre** (1376 → 2672 car.) |
| `en:armor-of-resistance` | portait le tableau **entier, d'un autre objet** (1581 car.) | **propre** (1581 → 285 car.) |

Les 285 caractères ne sont pas la prose nue : *Armor of Resistance* garde sa
**propre** table 1d10 des types de dégâts, imprimée dans sa propre colonne sous
sa propre phrase (« determines it randomly by rolling on the following table »).
Elle lui a toujours appartenu.

Ce n'était **pas** un défaut d'ordre de lecture : l'ordre était celui de la
page. C'était un problème d'**ancrage de flottant**, et la source énonce
l'appartenance **deux fois** — c'est la conjonction des deux qui est
implémentable sans inventer de règle (loi §0.10) :

1. **La légende nomme l'entrée, typographiquement.** « Apparatus of the Crab
   Levers » commence par « Apparatus of the Crab », imprimé sur la même page en
   `GillSans-SemiBold` 12 pt — la fonte et le corps que la source réserve aux
   titres d'entrée (1373 lignes en EN, 1377 en FR, toutes des titres d'entrée).
2. **L'entrée nomme la légende, dans sa propre prose.** « Each lever, from left
   to right, functions as shown in the *Apparatus of the Crab Levers* table. »

**Pourquoi les deux, mesuré sur les deux PDF.** Le signal 1 seul se déclenche 3
fois et 2 sont faux (« Shield (Utilize Action to Don or Doff) » et « Bouclier
(s'enfile ou se retire…) » sont des **sous-titres internes** au tableau des
armures, qui commencent par le nom de l'entrée Bouclier imprimée plus haut) : il
les arracherait au tableau pour les coller dans le record Bouclier. Le signal 2
seul se déclenche 24 fois, et l'un d'eux — FR p. 91 « Héritages fiélons » — est
**déjà correctement placé** : l'entrée Tieffelin occupe les deux colonnes et sa
référence croisée est dans celle de gauche, donc s'ancrer sur la référence aurait
poussé le tableau **au milieu** du record qu'il termine déjà. Ensemble : **1 seul
déclenchement sur 744 pages et 66 blocs pleine largeur.**

Implémentation : `extract.float_anchors()`. Témoin : `tests/test_float_anchoring.py`,
qui re-dérive la règle des PDF (pas des exports), balaye les 66 blocs, exige que
tout flottant ré-ancré soit **nommé**, mesure ce que chaque signal ferait seul, et
**échoue** si les PDF manquent. Deux records ont bougé, les 2611 autres sont
byte-identiques (`python3 src/compare_exports.py <exports_avant>`).

⚠️ **Ce que le lot 18 n'a PAS fait, et laisse à l'architecte :** deux entrées
qui revendiqueraient une même légende lèvent une `ExtractorError` au lieu de
choisir. Le cas n'existe sur aucune des deux sources épinglées ; si une source
future le crée, le build s'arrête. C'est délibéré, mais c'est une décision de
politique — dis si tu préfères qu'il laisse le flottant en place et le signale.

---

## Q13 — `traits[].id` et `lineages[].id` : quel vocabulaire ?

Le contrat donne la **forme** (`{id, name, text}`) et pas le **vocabulaire des
identifiants**. J'ai pris `canon.slugify(nom imprimé)`, donc **propre à la
langue** :

| | EN | FR |
|---|---|---|
| trait | `darkvision` | `vision-dans-le-noir` |
| lignage | `wood-elf` | `elfe-sylvestre` |

C'est la convention du `slug` de record (`species « elfe »`), et elle
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

## Q16 — `build.py` pouvait perdre un genre entier en sortant 0 ✅ (CORRIGÉ par le lot 12, `41c1d5d`)

> 🔧 **Ligne de statut rectifiée le 2026-08-08 par l'architecte.** Elle disait
> encore « défaut trouvé, non corrigé » alors que le lot `12-build-gardes` l'a
> bouché le jour même, avec **deux** gardes : un genre enregistré qui ne rend
> rien arrête le build **en le nommant** (code 4, et il distingue « il n'a rien
> vu » de « il a tout rejeté »), et un export que la passe n'a pas réécrit fait
> **refuser** le build plutôt que d'être supprimé (code 5) — effacer la preuve
> rendrait le build vert, c'est le même défaut un étage plus bas.
> Signalé par le lot `18-srd-ancrage`, qui a eu raison de ne pas y toucher :
> son changement ne rendait pas cette ligne fausse, elle l'était déjà.

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

### ✅ RÉSOLU par le lot 12 — 2026-08-08. Les deux, avec attaque.

**Garde 1 — `build.check_every_genre_yielded`, sortie 4.** Un genre enregistré
qui rend 0 record arrête le build **en le nommant**, et le message distingue les
deux cas : « aucun record, aucune anomalie, aucun conflit » (le silence pur du
08-08) et « il a tout rejeté : N anomalies » (le parseur a essayé). La fixture
est **exemptée, étroitement** : `tests/fixtures/pages.json` est un talon
synthétique de six pages qui ne porte que des sorts, donc 13 des 14 genres FR y
rendent légitimement 0. C'est pour ça que l'attaque tourne contre une **source
épinglée réelle** — l'exemption ne peut pas être ce qui fait passer le test.

**Garde 2 — `export_json.check_no_orphans`, sortie 5.** L'export **refuse**
avant d'écrire quoi que ce soit si l'arbre contient un `.json` que cette
exécution ne produirait pas, et il le nomme. **Il refuse au lieu de supprimer**,
et c'est délibéré : supprimer rendrait le build vert en effaçant la preuve, une
octave plus bas. Un genre qui quitte le catalogue est une décision — elle doit
tenir dans un commit, pas se déduire d'un résultat de requête vide. Seuls les
`.json` comptent : `exports/README.md` est écrit à la main.

**Ce que l'attaque a vraiment confronté** (`tests/test_build_guards.py`, 12
assertions) : un parseur réel (`en/weapon`, qui rend 38 records) forcé à rendre
`([], [], [])` contre le PDF épinglé réel ; le **statut de sortie du processus**
vérifié dans un vrai sous-processus, pas seulement la valeur de retour de
`main()` — parce que c'est « le build a sorti 0 » qui a échoué le 08-08 ; un
export périmé posé à la main ; l'incident **complet** (genre muet + export
périmé sur le disque) ; et la preuve que l'arbre n'est pas touché par un refus.

**Un point mérite d'être noté, parce qu'il montre que le garde 2 n'est pas un
doublon** : la suite asserte que `verify_manifest` **ne voit pas** l'export
périmé. Le manifeste demande « chaque fichier que j'ai listé est-il intact ? »,
jamais « y a-t-il ici un fichier que je n'ai pas listé ? ». Le mécanisme qui
existait déjà était structurellement aveugle à ce défaut.

---

# QUATRIÈME ADDENDUM — 2026-08-24, lot 100 (les listes de choix de classe)

## Q17 — Le nom du genre : **UNE SEULE QUESTION, ET ELLE TIENT EN UNE LIGNE** ⏳

> **Le genre s'appelle `class-option` — tu gardes ce nom, ou tu en veux un
> autre ?**

Tout le reste est décidé et posé. Ce qui suit n'est là que pour que la réponse
se donne en connaissance de cause ; **rien n'attend cette réponse**, et c'est
délibéré.

**Ce qui est ratifié et que j'ai suivi.** *« Ce n'est pas "invocation" ni
"métamagie" qu'il faut décrire, c'est une liste dans laquelle une classe
choisit. Le SRD en remplit deux ; qui possède Eberron en ajoute une troisième ;
un homebrew en ajoute une quatrième. La catégorie reste ouverte, jamais
énumérée dans le schéma. »* Donc : un genre, une catégorie **ouverte**,
`CATEGORIES` dans `src/class_options.py` n'est que la liste des sections que
**cette source-ci** imprime, et **rien ne valide un record contre elle**.

**Les deux mesures qui bornent la question et n'en tranchent aucune :**

- les styles de combat **sont déjà des dons** ici, avec
  `category: "fighting-style"` — l'édition 2024 en a fait des feats ;
- **mais** le genre `feat` est **borné au chapitre des Dons** par les ancres de
  son propre parseur (`Feats` → le SECOND `Equipment`), et ces 28 + 10 sont
  imprimées dans le **chapitre des Classes**. Les verser dans `feat` demanderait
  de déborder ces ancres.

**Pourquoi `class-option` et pas autre chose.** Il nomme la forme et pas le
contenu, il se lit à côté de `class-progression` qui existe déjà, et il ne dit
ni « invocation » ni « métamagie ». Ce n'est pas un argument décisif — c'est
pour ça que c'est une question.

**⭐ Et pourquoi la donnée pouvait partir avant l'arbitrage :** un renommage de
genre déplace un identifiant, pas un enregistrement. Les 76 records portent les
mêmes noms, les mêmes prérequis, les mêmes coûts et les mêmes textes quel que
soit le mot retenu. Le motif est écrit **dans le module lui-même**
(`src/class_options.py`, premier paragraphe) pour qu'il ne se perde pas si ce
fichier-ci n'est pas relu.

**Si tu changes le nom**, ce qui bouge : `class_options.KIND`, la clef dans
`build.PARSERS` (deux langues), `build_web.KINDS` + `KIND_LABEL` +
`GENERIC_ORDER`, les noms de fichiers d'export, et les identifiants
`srd:class-option:<lang>:<slug>`. Rien d'autre — et `fhpc` refuse déjà le genre
par son nom, donc il faudra de toute façon l'y ouvrir une fois (voir plus bas).

---

## Ce que le lot 100 a REFUSÉ de faire, et pourquoi

**1. Aucun champ « quelle classe ».** Un record ne dit pas qu'il appartient à
l'Occultiste ou à l'Ensorceleur. La liaison est réelle — la liste est imprimée
dans le chapitre de la classe — mais la déduire demanderait soit d'encoder
l'appartenance à un chapitre, soit d'écrire à la main
`Warlock`↔`Occultiste`/`Sorcerer`↔`Ensorceleur`, c'est-à-dire **exactement la
table inter-langues que ce dépôt refuse d'écrire à la main**. La `category` dit
déjà de quelle liste il s'agit ; le lien vers la classe est une **jointure**, et
elle appartient à l'enregistrement `class` (l'aptitude *Niveau 2 : Métamagie*,
*Niveau 1 : Manifestations occultes*), pas ici.

**2. Aucune empreinte de correspondance.** `correspond.py` porte le genre en
**`no-fingerprint`** : 38 EN, 38 FR, 1 groupe en attente de 38. C'est la posture
que le module prévoit lui-même (*« Not an error. An unanswered question, carried
in the open »*). Mesuré avant de renoncer : le **coût** ne discrimine pas (8
métamagies à 1 point contre 2 à 2 points, la même distribution des deux côtés),
et le **niveau minimal** du prérequis pas davantage (2+ ×9, 5+ ×8, 9+ ×3, 7+/12+/15+ ×1,
sans prérequis ×5 — les mêmes effectifs dans les deux langues). Une empreinte
faible ne produit pas de faux appariements, mais elle ne produit presque rien
non plus. ⭐ **La route qui marcherait est ailleurs, et elle est chiffrée** : **15 des
28 manifestations nomment un sort du catalogue, dans chaque langue** (*Mage
Armor* / *armure du mage*, *Disguise Self* / *Déguisement*), et les sorts sont
déjà appariés — c'est une `OCCURRENCE_ROUTE`, du travail de `correspond.py`,
pas d'un extracteur. Le lot 99 travaille dans ce fichier ; je
n'y ai pas touché.

**3. Aucun coût numérique.** `cost` porte la clause imprimée
(`"2 Sorcery Points"`, `"2 points de Sorcellerie"`), pas un entier. En faire un
nombre est de la **dérivation** (`derive_mechanics`), pas de l'extraction, et
personne ne l'a demandé.

**4. Aucune infusion d'Artificier.** La classe n'est pas au SRD 5.2.1. Un test
échoue si les mots `infusion`, `artificer` ou `artificier` apparaissent dans ces
records.

**5. `Arcanum mystique` n'est pas un `class-option`.** C'est une **aptitude** de
l'Occultiste (FR p. 70, EN p. 72) qui fait choisir un **sort** dans la liste de
l'Occultiste — un genre que cette base porte déjà. Elle n'imprime aucune liste
propre.

---

## 📌 Ce qui va mordre en aval, et ce n'est pas un défaut

`fhpc` **refusera `class-option`** tant que le genre n'est pas ouvert à son
contrat : depuis le lot 93, un genre inconnu y est **refusé et nommé**, jamais
sauté en silence. C'est le comportement attendu. Ce n'est pas le travail de ce
lot-ci et je n'y ai pas touché — c'est signalé, pas corrigé.

---

## Q18 — Les 14 outils Fate's Hand n'ont **aucune étagère**, et ce n'est pas à moi de les ranger ⏳

**Mesuré le 2026-08-24.** `srfh` est bâtie sur le SRD seul : elle range 416
objets, dont les **25 outils** du livre. Or `fhpc` publie une couche
`fh-skills-en` qui **désactive** deux de ces 25 outils et les remplace par des
outils plus fins, plus quatre familles que le SRD n'a jamais portées.
**Résultat : 14 outils Fate's Hand que le rangement n'a jamais vus.**

| # | outil (`fh:tool:en:…`) | nom | famille | d'où il vient |
|---|---|---|---|---|
| 1 | `gaming-set-dice` | Dice Set | **Jeux** | éclat de `srd:tool:en:gaming-set` (**désactivé**) |
| 2 | `gaming-set-cards` | Card Set | **Jeux** | idem |
| 3 | `gaming-set-dragonchess` | Dragonchess Set | **Jeux** | idem |
| 4 | `gaming-set-three-dragon` | Three-Dragon Ante | **Jeux** | idem |
| 5 | `instrument-wind` | Instrument (Wind) | **Instruments** | éclat de `srd:tool:en:musical-instrument` (**désactivé**) |
| 6 | `instrument-strings` | Instrument (Strings) | **Instruments** | idem |
| 7 | `instrument-other` | Instrument (Other) | **Instruments** | idem |
| 8 | `vehicles-land` | Vehicles (Land) | **Véhicules** | maison — aucun équivalent SRD |
| 9 | `vehicles-water` | Vehicles (Water) | **Véhicules** | maison |
| 10 | `vehicles-air` | Vehicles (Air) | **Véhicules** | maison |
| 11 | `mount-land` | Mount (Land) | **Montures** | maison |
| 12 | `mount-water` | Mount (Water) | **Montures** | maison |
| 13 | `mount-air` | Mount (Air) | **Montures** | maison |
| 14 | `soulforging` | Soulforging | **Soulforging** | maison |

⛔ **Je ne les ai pas rangés, et c'est délibéré.** Le rangement est celui d'Eric,
arrêté à la main les 21 et 22 août ; deux de ces familles (**véhicules**,
**montures**) n'ont aucune étagère évidente parmi les trente, et le
**Soulforging** est un chantier à lui seul. Les ranger d'office reviendrait à
décider à sa place — exactement ce que ce dépôt refuse de faire ailleurs.

⚠️ **Et le trou se voit à l'écran, pas seulement dans les données** : les deux
outils SRD désactivés (`gaming-set`, `musical-instrument`) SONT rangés en
`crafting/tools`. Sur un écran qui monte les deux couches, cette étagère
annonce **25** et n'en affiche que **23**, pendant que les 14 outils de Fate's
Hand n'apparaissent nulle part. La couche maison a raffiné, le rangement n'a
pas suivi.

**Trois issues, et c'est à Eric :** leur donner une étagère parmi les trente ·
ouvrir une étagère de plus dans un rayon existant · ou assumer qu'un outil
Fate's Hand ne se range pas et le dire, ce qui est aussi une réponse.

---

## Q19 — `mundane` est la seule des sept rangées **hors alphabet** ⏳

Le commentaire au-dessus de `SHELVES` dit que la table est *alphabetical at
both levels*. **Mesuré : six rayons sur sept le sont, `mundane` ne l'est pas.**

```
mundane   déclaré      containers, clothing, writing-and-reading
          alphabétique clothing, containers, writing-and-reading
```

L'ordre déclaré est celui du document d'Eric (*Contenants · Vêtements · Écrire &
lire*) ; les six autres rayons ont été alphabétisés, celui-là non. **C'est donc
soit un oubli de transcription, soit un ordre voulu — et rien dans le code ne
permet de trancher.**

⛔ **Publié tel qu'il est déclaré, pas réparé.** Ce lot ne publie que du vide, et
sa preuve tient en une phrase : *les 26 étagères peuplées gardent exactement le
même contenu et le même ordre*. Réordonner `mundane` déplacerait un rayon
peuplé, et mélangerait une décision non demandée à une correction mesurée.

---

## Q20 — Publier `companions` fait tomber un rayon sous le minimum de la roue ⚠️

**Ce n'est pas une objection au lot, c'est sa conséquence chiffrée**, et le
document d'Eric la prévoit déjà : *« Un niveau de roue a besoin de TROIS crans
pour être une roue »* — en dessous, le tambour bascule en `data-court`, la piste
se rembourre et l'étage ne s'aligne plus.

| rayon | crans **avant** ce lot | crans **après** |
|---|---|---|
| `crafting` | **1** (`tools` seule — en `data-court`) | **3** ✅ |
| `companions` | **0** (invisible) | **2** ⚠️ `data-court` |

⭐ **Le lot en répare un et en révèle un autre.** `crafting` sort de
`data-court` : ses trois étagères existent enfin toutes les trois. `companions`
y entre, parce qu'il n'a que **deux** étagères déclarées.

📌 **Et le document en porte peut-être déjà la réponse** : il donne quatre
entrées à Companions — *Familiers · Hommes de main · **Sur mesure** (import
statblock) · **Recherche dans les monstres*** — les deux dernières sans compte
(`—`). `src/shelving.py` n'en déclare que deux, et il fait foi ici. Si ces deux
dernières sont des **étagères** et pas des mécanismes d'écran, Companions passe
à quatre crans et le problème n'existe plus. **C'est une ligne dans `SHELVES`,
et c'est la décision d'Eric, pas la mienne.**

---

## 📌 Ce que le lot 103 a laissé en aval — mesuré, nommé, pas corrigé

**Le bloc `structure` est publié, mais il ne traverse pas encore `fhpc`.**
`src/tools/gen-srfh-layer.mjs` recopie les **records** d'un export dans la
couche `fh-layer/1` (`toAddEntry`) ; il lit `kind`, `lang`, `layer`, `records`,
`license` et `license_url`, et **ignore toute autre clef d'en-tête**. La clef
`structure` est donc inerte pour lui : elle ne casse rien — vérifié, aucune
validation de schéma ne s'applique au document source, et la porte ② de ce
générateur compte des **fichiers** sous `srfh/en/`, or ce lot n'en ajoute
aucun — mais elle **n'arrive pas** dans `layers/srfh-shelving-en.layer.json`, et
l'écran lit la couche, pas l'export.

➡️ **Il reste un geste, et il est chez `fhpc`, pas ici** : porter le bloc de
l'export vers le document de couche. ⛔ Ce n'est **pas** un genre à ouvrir :
ouvrir un genre au contrat `fh-layer/1` désarme une des quatre portes de
`gen-srd-layer.mjs` (leçon du 24/08, écrite dans le fichier lui-même). C'est une
clef de couche, pas un genre.

⭐ **Et c'est le seul geste qui reste** : la donnée existe, elle est ordonnée,
comptée, zéro compris, et elle est vérifiée par le MANIFEST comme le reste.
