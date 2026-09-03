# Les clefs de traits d'espèce — la mesure, pas la correction

**Relevé du 2026-08-26 · rafraîchi le 2026-09-03 · siège VERSATILITY**
**⛔ Ce document ne change rien.** Aucune clef, aucun export, aucun record n'a été
touché. Il existe pour qu'un arbitrage cesse d'être indécidable.

Mesuré sur `fhpc` @ `e88430c` (lot 143) et `fh-srd` @ `31d551f`.

---

## Le résultat en une phrase

La transition à froid (§0.13) a migré les **adresses** vers l'anglais ; elle n'a
pas touché aux clefs qui vivent **dans** `data.traits[]`, qui restent celles du
livre de chaque langue. La conséquence n'est **pas** une dérive silencieuse :
c'est un **refus au montage**, nommé, qui rend une pile française + FH
impossible à construire.

> ⚠️ **Toujours vrai au 2026-09-03.** Le test `fhpc/tests/layers-traits-fr.test.mjs`
> est vert sur `e88430c`, et son deuxième cas est précisément *« sous un rendu
> français, la couche FH d'espèces REFUSE de se monter »*. **Un personnage FH en
> français reste impossible à construire.**

---

## 0. LE CADRE — SRD / SRFH / SRFH+, et pourquoi il change la question

⚠️ **Ce relevé a d'abord été écrit sans ce cadre, et il posait donc la mauvaise
question.** Il demandait « faut-il migrer les clefs de traits ? ». La bonne
question est : **cette couche a-t-elle le droit d'écrire là où elle écrit ?**

Le contrat des trois étages est **ratifié par Eric le 2026-08-23**. ⛔ Il ne vit
que dans le vault — `~/obsidian-vault/FH-WEB/FHPC/FHPCv2 SRFH et SRFH+.md` —
et c'est pour ça qu'un `grep` sur les deux dépôts rend zéro. *(Une règle qui
n'atteint pas le corpus n'existe pas pour celui qui la cherche : ce pointeur
est ici pour que le prochain la trouve.)*

| | ce que c'est | la loi |
|---|---|---|
| **SRD** | le livre, copié fidèlement | ⛔ **« On n'y écrit jamais rien de nous »** |
| **SRFH** | la zone grise, *« les petits ajustements quality of life »* | quelqu'un doit pouvoir **jouer du SRD pur** avec elle |
| **SRFH+** | *« la couche Fate's Hand, c'est tout »* | ce qui n'appartient qu'à nous et ne prétend rien être d'autre |

**Le test d'Eric — il porte sur le NOM, pas sur le contenu :** *« Si on change
ça, est-ce que ça s'appelle encore le SRD ? »* Oui → SRD · On ne sait pas →
SRFH · **Non, clairement → SRFH+.**

### ⭐ CE QUE LE TEST DIT DE NOS DIX CHEMINS

Retirer `Resourceful` à l'Humain, réécrire le texte de `Keen Senses`, convertir
« Proficiency Bonus » en échelle écrite : **aucun de ces trois n'est un
ajustement de confort.** Ce sont des règles Fate's Hand. Le test répond « non,
clairement » — ils sont **SRFH+**.

➡️ **Or ils sont écrits DANS des records `srd:`.** Les dix chemins de `§2` sont
des `data.traits[…]` sur `srd:species:en:*`. La couche FH d'espèces écrit donc
du nôtre dans le livre — ⛔ ce que la première ligne du contrat interdit.

⭐ **LA DÉPENDANCE À LA LANGUE N'EST PAS LE PROBLÈME : C'EST LE SYMPTÔME QUI
L'A RÉVÉLÉ.** Une couche qui respecte le contrat vise une **adresse** ; une
couche qui l'enfreint finit par viser un **mot**, et un mot a une langue.

### La ligne exacte, mesurée sur les 89 patches des couches FH

| forme du chemin | nombre | ce qu'elle vise |
|---|---:|---|
| `data[<champ>]`, `data.blurb`, `data.category`… | **79** | un **champ de schéma** — même nom dans les deux langues |
| `data.traits[<clef>]` (`.text`, `.name`, retrait) | **10** | un **élément de contenu**, désigné par un mot |

**Une seule couche produit les dix : `fh-species-en`.** Toutes les autres
(`fh-fiche`, `fh-lore`, `fh-skills`, `fh-spells`, `fh-feats`, `srfh-shelving`)
n'adressent que des champs de schéma, et sont **insensibles à la langue**.

---

## ⚠️ CE QUI A BOUGÉ DEPUIS LA PREMIÈRE MESURE — la dette a grandi

C'est la partie la plus utile de ce document : **le relevé montre sa propre
dérive.** Il n'a pas été rafraîchi parce qu'il était faux, mais parce que le
monde a bougé sous lui, et on sait exactement de combien.

| | 2026-08-26 (lot 108) | 2026-09-03 (après lot 73) | |
|---|---:|---:|---|
| chemins visant une clef de trait | **6** | **10** | +4 |
| espèces concernées | **3** | **7** | +4 |
| espèces divergentes | 9 / 9 | 9 / 9 | — |
| clefs appariées | 0 | 0 | — |

**Ce qui a creusé la dette** : le lot 73 (`fhpc` `6ff5e96`, 27/08) a converti
« Proficiency Bonus » vers l'échelle écrite, sur dictée d'Eric. Quatre textes de
traits de plus sont donc patchés — `breath-weapon`, `stonecunning`,
`giant-ancestry`, `adrenaline-rush`. Ce lot a mis le test à jour lui-même et a
écrit dans son propre message : *« Le relevé de `fh-srd/docs/TRAIT-KEYS.md` est
à rafraîchir en conséquence. »* Ce rafraîchissement est cette révision.

⚠️ **Une correction de compte au passage** : le titre du test dit
« 10 chemins sur **6** espèces ». La liste qu'il assure est juste, le libellé
non — les adresses distinctes sont **7** (dragonborn, dwarf, elf, gnome,
goliath, human, orc). Le compte de ce document fait foi ; le titre du test est
à corriger côté `fhpc`.

---

## 1. Les neuf espèces, clefs côte à côte

Clefs de `data.traits[].id`, couche `srd-5.2.1-en` contre `srd-5.2.1-fr`.

| espèce | clefs EN | clefs FR |
|---|---|---|
| dragonborn | `breath-weapon`, `damage-resistance`, `darkvision`, `draconic-ancestry`, `draconic-flight` | `ascendance-draconique`, `resistance-aux-degats`, `souffle`, `vision-dans-le-noir`, `vol-draconique` |
| dwarf | `darkvision`, `dwarven-resilience`, `dwarven-toughness`, `stonecunning` | `connaissance-de-la-pierre`, `resistance-naine`, `tenacite-naine`, `vision-dans-le-noir` |
| elf | `darkvision`, `elven-lineage`, `fey-ancestry`, `keen-senses`, `trance` | `ascendance-feerique`, `lignage-elfique`, `sens-aiguises`, `transe`, `vision-dans-le-noir` |
| gnome | `darkvision`, `gnomish-cunning`, `gnomish-lineage` | `lignage-gnome`, `ruse-gnome`, `vision-dans-le-noir` |
| goliath | `giant-ancestry`, `large-form`, `powerful-build` | `ascendance-gigante`, `forme-de-geant`, `forte-carrure` |
| halfling | `brave`, `halfling-nimbleness`, `luck`, `naturally-stealthy` | `agilite-halfeline`, **`brave`**, `chance`, `discretion-naturelle` |
| human | `resourceful`, `skillful`, `versatile` | `competent`, `ingenieux`, `polyvalent` |
| orc | `adrenaline-rush`, `darkvision`, `relentless-endurance` | `acharnement`, `poussee-d-adrenaline`, `vision-dans-le-noir` |
| tiefling | `darkvision`, `fiendish-legacy`, `otherworldly-presence` | `heritage-fielon`, `presence-d-outre-monde`, `vision-dans-le-noir` |

**9 espèces, 9 jeux de clefs divergents, 1 clef commune sur 33.**

⚠️ **L'unique homographe est un piège** : le halfling porte `brave` dans les
deux langues. Une clef qui coïncide n'est pas une clef appariée — elle
coïncide. Un rapprochement qui s'appuierait là-dessus marcherait sur 1 espèce
sur 9 et donnerait l'illusion que la méthode tient.

ⓘ Les espèces **propres à FH** (`fh:species:en:araag`, `elestu`…) portent leurs
propres clefs, en anglais et dans une seule langue : `fast-learner`,
`necrotic-resistance`, `soulforged-affinity`. Elles ne divergent de rien, et
n'entrent pas dans ce relevé.

---

## 2. Ce qui s'appuie sur ces clefs — la vraie mesure du coût

Chemins de `fhpc/layers/fh-species-en.layer.json` qui visent une clef de trait,
et présence de cette clef dans chaque langue :

| adresse patchée | chemin | EN | FR | depuis |
|---|---|:--:|:--:|---|
| `srd:species:en:dragonborn` | `data.traits[breath-weapon].text` | ✓ | ✗ | lot 73 |
| `srd:species:en:dwarf` | `data.traits[stonecunning].text` | ✓ | ✗ | lot 73 |
| `srd:species:en:elf` | `data.traits[keen-senses].text` | ✓ | ✗ | lot 108 |
| `srd:species:en:gnome` | `data.traits[gnomish-cunning].name` | ✓ | ✗ | lot 108 |
| `srd:species:en:gnome` | `data.traits[gnomish-lineage].name` | ✓ | ✗ | lot 108 |
| `srd:species:en:gnome` | `data.traits[gnomish-lineage].text` | ✓ | ✗ | lot 108 |
| `srd:species:en:goliath` | `data.traits[giant-ancestry].text` | ✓ | ✗ | lot 73 |
| `srd:species:en:human` | `data.traits[skillful].text` | ✓ | ✗ | lot 108 |
| `srd:species:en:human` | `data.traits[resourceful]` *(retrait)* | ✓ | ✗ | lot 108 |
| `srd:species:en:orc` | `data.traits[adrenaline-rush].text` | ✓ | ✗ | lot 73 |

**10 chemins · 7 espèces.** Les deux autres espèces (halfling, tiefling)
divergent aussi, mais **rien ne s'appuie sur leurs clefs** : leur divergence ne
coûte rien tant qu'aucune couche ne les vise.

### Ce qui N'ÉLARGIT PAS le périmètre — vérifié

La couche `fh-fiche-en` a gagné **45 chemins** sur les espèces (les textes
courts de fiche : `fiche_stats`, `fiche_traits`, `fiche_infos`,
`fiche_lineage_lvl1`, `fiche_trait_text`, `fiche_lineage_text`). **Zéro** ne
vise une clef de trait : ce sont tous des champs plats `data[fiche_*]`.
⛔ Ils n'entrent pas dans cette dette. Mesuré, pas supposé.

---

## 3. Ce qui se passe exactement — mesuré, pas supposé

Trois piles montées, trois résultats. *(Mesure d'origine du 26/08, revérifiée
le 03/09 par la suite verte sur `e88430c`.)*

| pile | résultat |
|---|---|
| `srd-en` + `fh-species-en` *(la pile livrée)* | ✅ monte · humain rendu par `srd-5.2.1-en` · traits `["skillful","versatile"]` · `granted_skill_choice` retiré |
| `srd-en` + `srd-fr` + `fh-species-en` | ⛔ **REFUS AU MONTAGE** |
| `srd-fr` + `fh-species-en` | ⛔ **REFUS AU MONTAGE** |

Le refus nomme la couche, l'espèce, le chemin et la raison :

> `fhpc/layers: la couche « fh-species-en », patch de species « srd:species:en:… »`
> `— « data.traits[…] » n'existe pas dans le record — le chemin « data.traits[…].text »`
> `ne peut pas être créé en profondeur : une couche ne devine pas la forme`
> `qu'elle voudrait trouver.`

⚠️ **L'espèce nommée par le refus a changé** : c'était `elf` /
`data.traits[keen-senses]` au 26/08 ; c'est `dragonborn` /
`data.traits[breath-weapon]` depuis le lot 73, qui est devenu le premier patch
de trait rencontré. Le sens du garde n'a pas bougé.

⭐ **Le refus tombe AVANT tout rendu.** Personne n'obtient une fiche fausse : on
n'obtient pas de fiche du tout.

---

## 4. Les trois gardes existent déjà, et elles sont bruyantes

| garde | où | comportement mesuré |
|---|---|---|
| refus par identité de couche | `assertSrdLayer`, `gen-fh-species-layer.mjs` | `srd-5.2.1-fr` → *« la couche SRD fournie a l'id « srd-5.2.1-fr », attendu « srd-5.2.1-en » »* |
| trait absent au tirage | `liftTrait`, même fichier | nomme le trait, l'espèce, **et liste les traits présents** |
| chemin dans le vide au montage | `applyRemoval` / `descend`, `src/layers/paths.mjs` | *« un retrait dans le vide est un échec, pas un silence (§L7.2) »* |

⛔ **Il n'y a pas de garde à ajouter** — en ajouter une lèverait une exception là
où trois refus nommés tombent déjà. Ce qui manquait était un **test de
régression**, posé dans `fhpc/tests/layers-traits-fr.test.mjs`. ⭐ Il a prouvé sa
valeur : c'est lui qui a fait apparaître les 4 chemins de plus du lot 73, dans
le lot même qui les créait.

---

## 5. Ce que ça coûte vraiment — pour l'arbitrage

**Deux coûts, pas un.**

1. **Une capacité absente** : un personnage FH en français est impossible à
   construire. La couche FH d'espèces refuse de se monter au-dessus du SRD
   français.
2. ⛔ **Une violation de contrat** (§0) : dix règles Fate's Hand sont écrites
   dans des records `srd:`, que la loi réserve au livre.

⭐ **Le second est le vrai.** Le premier disparaît si on répare le second ; la
réciproque est fausse — migrer les clefs rendrait le français constructible en
laissant nos règles dans le livre.

### La courbe — la dette grandit, et on sait comment

Chemins `data.traits[…]` dans `fh-species-en`, relevés commit par commit :

| date | chemins | espèces |
|---|---:|---:|
| 2026-08-08 | 3 | 2 |
| 2026-08-17 | 5 | 3 |
| 2026-08-20 | 6 | 3 |
| **2026-08-27** *(lot 73, conversion PROF)* | **10** | **7** |
| 2026-09-02 | 10 | 7 |

⚠️ **Ce n'est pas un taux, c'est une fonction de l'intention.** La dérive lente
(+3 en 12 jours) est de l'entretien ; le saut (+4 en un lot) est une décision de
règle. ➡️ **La dette croît exactement autant que FH s'écarte du SRD sur les
espèces** — c'est-à-dire autant que le projet fait ce pour quoi il existe.
⛔ Ne rien faire ne stabilise donc pas la dette : ça la laisse suivre le
projet.

### Les routes, chiffrées

| | route | ce qu'elle coûte | ce qu'elle laisse |
|---|---|---|---|
| **A** | ne rien faire | nul | pas de FH en français · ⛔ la violation reste, et grandit |
| **B** | migrer les clefs de `data.traits[]` à l'export | une passe sur l'export `fh-srd` | ✅ le français marche · ⛔ **la violation reste** |
| **C** | réadresser les 10 chemins par langue | à refaire à chaque nouveau chemin | ⛔ la violation reste, et la langue entre dans une couche FH |
| **D** | ⭐ **remettre les 10 règles en `srfh+`**, records à part qui étendent | **une règle de préséance dans le pli** — voir ci-dessous | ✅ le français marche · ✅ la violation disparaît · ✅ la dette cesse de croître |

⛔ **Une cinquième est à écarter d'avance** : rapprocher les clefs par leur nom
affichable. C'est ce que §0.13 interdit, et l'homographe `brave` du halfling
montre pourquoi la méthode aurait l'air de marcher.

### Ce que la route D demande vraiment — mesuré

**① Les consommateurs à toucher : QUATRE sites, dans quatre fichiers.**
`src/build/derive.mjs:1051` · `src/modules/fh/skill-pool.mjs:385` ·
`ui/builder/species-step.mjs:669` et `:1242` · `src/modules/fh/destiny-stat.mjs:230`.
*(`ui/builder/skills-step.mjs` lit `resolved.traits`, en aval de la dérivation —
il ne voit jamais la couche.)*

⭐ **Et TROIS de ces quatre fusionnent DÉJÀ `data.fh_traits` avec `data.traits`.**
Le canal FH, propre et insensible à la langue, **existe et est consommé** —
`gen-fh-species-layer.mjs:465` l'alimente par `changes["data[fh_traits]"]`, un
champ de schéma. ⚠️ Mais fusionner n'est pas remplacer : ce canal sait
**ajouter** un trait, pas en **supplanter** un.

**② `record_link` n'est PAS qu'une doctrine — il porte 710 arêtes.**
Dans `build/srd.sqlite` : **662 `extends`** et **48 `replaces`**, le schéma
autorisant en plus `overrides`, avec un déclencheur qui interdit au SRD
d'amender quoi que ce soit (*« the srd layer never overrides: invert the
edge »*). ⭐ **La sémantique de préséance existe donc déjà, et elle est
éprouvée** — les 48 `replaces` servent les variantes d'objets
(`srfh:item:en:belt-of-giant-strength-fire` → `srd:item:en:belt-of-giant-strength`).
⛔ **Mais zéro arête ne porte sur une espèce** : les 710 sont toutes sur `item`.
Le mécanisme est **prouvé sur les objets, jamais exercé sur les traits** — ça,
c'est la mesure. ⚠️ Et voici la raison de ne pas le tenir pour acquis :
**un mécanisme qui marche sur un genre peut échouer sur un autre.** Les deux
comptent — une raison sans mesure est une opinion, une mesure sans raison ne se
transmet pas. Concrètement, `item` et `species` ne demandent pas la même chose
au `replaces` : une variante d'objet est un record ENTIER qui en remplace un
autre, là où un trait FH veut supplanter **un champ à l'intérieur** d'un record
qui, lui, doit rester.

**③ Ce qui manque, exactement.** Un consommateur générique qui, pour un record
SRD, ramasse les records `srfh+` qui le remplacent et fasse gagner leur texte.
`gen-srfh-layer.mjs:70` le dit de lui-même : *« il lui faut un consommateur qui
suive `data.extends` »*, et le seul qui le fasse aujourd'hui est l'écran
d'équipement, **à la main**. ➡️ **C'est un lot d'architecture, pas un
déplacement de données** — mais il est plus court qu'il n'y paraît : quatre
sites, une sémantique déjà au schéma, et un canal `fh_traits` déjà branché sur
trois d'entre eux.

### ⭐ La question qui reste à Eric, et elle n'a pas bougé

**Veut-il FH en français, un jour ?**
· **Non** → routes A. On classe, en sachant que la violation de contrat reste.
· **Oui** → **route D**, et alors le lot à ouvrir n'est pas « migrer des
clefs » mais **« rendre les règles FH à la couche SRFH+ »**.

## Comment ce relevé a été fait

Clefs lues dans `fhpc/layers/srd-5.2.1-{en,fr}.layer.json`, chemins dans
`fh-species-en.layer.json` et `fh-fiche-en.layer.json`, sur un worktree détaché
d'`origin/main` (`e88430c`). Piles montées via le vrai noyau `fhpc` pour la
mesure d'origine, revérifiées par la suite `layers-traits-fr` sur le `main`
courant. **Aucun chiffre de ce document n'est déduit d'un autre.**

⚠️ **Ce relevé se périme.** Sa ligne de vie est le test
`fhpc/tests/layers-traits-fr.test.mjs` : le jour où sa liste de chemins change,
ce document est faux — et le test est écrit pour le dire.
