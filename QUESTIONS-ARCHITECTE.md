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
