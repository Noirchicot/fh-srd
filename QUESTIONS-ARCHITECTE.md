# Questions à l'architecte — lot `8-srd-mecanique`

Six questions. **Aucune n'a bloqué le lot** : conformément à l'amendement de
session (Eric absent, un arrêt franc gèlerait la nuit), tout ce qui n'en dépend
pas est fait, livré et vert. Mais **rien n'a été inventé** : là où une décision
manquait, j'ai pris la lecture la plus littérale du contrat, je l'ai écrite
noir sur blanc, et je la pose ici.

Les quatre irrégularités arbitrées du §4 (Barde, Soldat, sarbacane, bouclier)
ne sont pas dans cette liste : elles ont été transportées telles quelles,
comme demandé.

---

## Q1 — Les clefs de caractéristique ne joignent pas entre les deux genres ⚠️

**C'est la plus importante.** Deux conventions cohabitent maintenant dans la
couche FR, et un consommateur qui les joint naïvement obtient du vide :

| genre | champ | valeur FR |
|---|---|---|
| `skill` (lot 6) | `ability_key` | `sag`, `for` — les abréviations que le PDF FR imprime |
| `class` (lot 8) | `saving_throw_keys` | `wis`, `str` — les clefs canoniques |
| `background` (lot 8) | `ability_keys` | `wis`, `str` — idem |

**Ce que j'ai fait et pourquoi.** Le contrat §3 écrit `["int","wis"]` pour
`saving_throw_keys` et `["con","int","wis"]` pour `background.ability_keys` —
et ce second exemple **est le Sage français** (Constitution, Intelligence,
Sagesse). Le test d'acceptation de mon lot exige explicitement « un Magicien
rend `saving_throw_keys: ["int","wis"]` … en FR **et** en EN ». J'ai donc émis
les clefs canoniques dans les deux langues.

Le lot 6 avait décidé l'inverse pour `skill.ability_key`, avec un argument
explicite (`docs/RECORD-SHAPES.md` §1) : « si `fhpc` veut une clef canonique
inter-langues, ce mapping appartient à la couche FH, pas ici ».

**Les deux positions sont défendables ; elles ne peuvent pas être vraies en
même temps.** À trancher :

- (a) `skill.ability_key` devient canonique aussi → un champ existant change,
  ce que mon lot n'avait pas le droit de faire, mais qui est une ligne ;
- (b) `skill` reçoit un `ability_key_canonical` **à côté** (même règle qu'ici) ;
- (c) on assume la divergence et `fhpc` porte la table de correspondance.

En attendant, c'est documenté dans `docs/DERIVED-FIELDS.md` et dans le
docstring de `src/derive_mechanics.py`, avec un contrôle négatif dans la suite
d'acceptation qui vérifie que le FR **n'est pas** `for`/`sag`.

---

## Q2 — `tool_choice.from` : ma lecture est-elle la bonne ?

Le contrat dit `tool_choice` = `{from}`, sans dire ce que `from` contient.

Le Soldat imprime `"Choisissez un type de boîte de jeux"`. Les *types* de boîte
de jeux (cartes à jouer, dés, échecs draconiques, jeu des dragons) ne sont pas
des records : ils vivent dans le champ `variants` du record `srd:tool:fr:boite-de-jeux`.

**Émis :** `{"from": ["srd:tool:fr:boite-de-jeux"]}` — une liste d'ids d'outils,
symétrique de `skill_choice.from`, pointant sur le record que la source nomme,
et dont le consommateur lit `variants` pour présenter le choix.

**L'alternative** serait un `from` qui énumère les quatre variantes en clair —
mais ce ne seraient pas des identifiants, et ça ferait de `from` deux types
différents selon le genre. Confirme, ou dis-moi la forme que tu veux.

---

## Q3 — L'option du don n'est portée par aucun champ

`"Initié à la magie (Clerc)"` (Acolyte) et `"Initié à la magie (Magicien)"`
(Sage) rendent **le même** `feat_id`. Le contrat ne définit que `feat_id`, donc
je n'ai pas nommé de champ pour l'option — la chaîne imprimée la porte encore,
mais un constructeur qui lit `feat_id` seul ne distingue pas les deux.

C'est une perte réelle et le seul endroit du lot où de l'information mécanique
présente dans la source n'atteint pas un champ. Deux magiciens niveau 1 avec
ces deux arrière-plans reçoivent des listes de sorts différentes.

**Il manque un nom.** `feat_option` ? `feat_choice` ? Dis lequel et c'est un
commit.

---

## Q4 — `PIPELINE_VERSION` : je ne l'ai pas bougé, dis-moi si tu veux

`canon.PIPELINE_VERSION` est à `1.0.0`. Son commentaire dit : « bumped whenever
a change **here** would alter the bytes of an existing export » — or `canon.py`
n'a pas été touché.

**Je ne l'ai pas bumpé, et c'est un choix argumenté :** `PIPELINE_VERSION` entre
dans `run_id`, qui est un champ de tête de **chaque** fichier d'export. Le
bumper aurait fait bouger les 28 fichiers, y compris les 18 des neuf genres
auxquels je n'ai rien ajouté — et détruit la preuve la plus forte que je peux
offrir : *ces neuf genres sont byte-identiques à ce qu'ils étaient*.

Le changement reste visible au registre : les `content_hash` des records
dérivés ont bougé, et `MANIFEST.json` porte les nouveaux sha256.

Si tu préfères la trace explicite au registre, c'est une ligne (`1.1.0`) et un
rebuild.

---

## Q5 — Deux records FR portent encore un nom d'aptitude tronqué

Signalé par le lot 6 (`docs/RECORD-SHAPES.md`, dernière section) et **toujours
là** : `srd:class:fr:occultiste` niveau 9 dit `"Communication avec"` au lieu de
`"Communication avec le protecteur"`, et `srd:class:fr:guerrier` niveau 11 dit
`"Double attaque"` au lieu de `"Double attaque supplémentaire"`. Titre coupé sur
un retour à la ligne dans `parse_classes_fr.py`.

Je ne l'ai pas corrigé : ça reshape des records existants, donc c'est une
décision de contrat, pas de lot. Mais un constructeur qui joindra les aptitudes
par nom entre `class` et `class-progression` tombera dessus. Le lot 6 le disait
déjà ; je le redis parce que le lot 9 est précisément le lot qui joint.

---

## Q6 — Les descriptions d'espèce se contaminent entre records

Découvert en mesurant le groupe B, **pas causé par ce lot** :
`srd:species:en:human` se termine par le tableau du **Tiefling**
(`"Fiendish Legacies"`, `Legacy Level 1 Level 3 Level 5`, `Abyssal…`,
`Infernal…`). La mise en page à deux colonnes est aplatie et le texte d'un
record déborde sur son voisin.

Côté FR, vérifié : **pas de débordement d'un record sur l'autre** (`humain` est
propre, le tableau des héritages reste chez `tieffelin`). Mais le tableau y est
aplati de la même façon, en fragments non rattachables — `srd:species:fr:elfe`
place sa `"Vision dans le noir."` **après** le tableau des lignages, et rend les
sorts de niveau 3 et 5 de l'Elfe sylvestre comme
`"grande foulée passage sans trace"`, deux noms sans séparateur. Le défaut EN
est plus grave ; le FR est inexploitable pour la même raison.

C'est la raison mesurée pour laquelle j'ai **refusé** `traits` et les lignages
(détail dans `docs/DERIVED-FIELDS.md`). Ça n'affecte aucun champ que j'émets —
`senses` et `granted_skill_choice` sont ancrés sur la phrase du trait, et j'ai
vérifié qu'aucune contamination ne les déclenche.

Mais **la prose publiée est fausse aujourd'hui** sur le site public pour cette
espèce, et le sera pour tout consommateur qui lit `description`. Réparer
`parse_species_en.py` / `_fr.py` reshape neuf records par langue : décision de
contrat. Si tu veux les lignages structurés un jour, c'est le préalable — pas
un meilleur parseur de prose.
