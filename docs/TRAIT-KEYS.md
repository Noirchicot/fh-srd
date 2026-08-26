# Les clefs de traits d'espèce — la mesure, pas la correction

**Relevé du 2026-08-26 · siège VERSATILITY · lot 108**
**⛔ Ce document ne change rien.** Aucune clef, aucun export, aucun record n'a été
touché. Il existe pour qu'un arbitrage cesse d'être indécidable.

---

## Le résultat en une phrase

La transition à froid (§0.13) a migré les **adresses** vers l'anglais ; elle n'a
pas touché aux clefs qui vivent **dans** `data.traits[]`, qui restent celles du
livre de chaque langue. La conséquence n'est **pas** une dérive silencieuse :
c'est un **refus au montage**, nommé, qui rend une pile française + FH
impossible à construire aujourd'hui.

> **La dette est plus petite que le chiffre « 9 espèces sur 9 » ne le laissait
> croire, et son échec est plus propre.** Ce que 9/9 mesurait, c'est la
> divergence des clefs. Ce qui coûte, c'est le nombre de chemins qui s'appuient
> dessus : **6 chemins, sur 3 espèces**.

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

**9 espèces, 9 jeux de clefs divergents, 0 apparié.**

⚠️ **Un seul homographe, et il est un piège** : le halfling porte `brave` dans les
deux langues. Une clef qui coïncide n'est pas une clef appariée — elle coïncide.
Un rapprochement qui s'appuierait là-dessus marcherait sur 1 espèce sur 9 et
donnerait l'illusion que la méthode tient.

---

## 2. Ce qui s'appuie sur ces clefs — la vraie mesure du coût

Chemins de `layers/fh-species-en.layer.json` qui visent une clef de trait,
et présence de cette clef dans chaque langue :

| adresse patchée | chemin | EN | FR |
|---|---|:--:|:--:|
| `srd:species:en:elf` | `data.traits[keen-senses].text` | ✓ | ✗ |
| `srd:species:en:gnome` | `data.traits[gnomish-cunning].name` | ✓ | ✗ |
| `srd:species:en:gnome` | `data.traits[gnomish-lineage].name` | ✓ | ✗ |
| `srd:species:en:gnome` | `data.traits[gnomish-lineage].text` | ✓ | ✗ |
| `srd:species:en:human` | `data.traits[skillful].text` | ✓ | ✗ |
| `srd:species:en:human` | `data.traits[resourceful]` *(retrait)* | ✓ | ✗ |

**6 chemins · 3 espèces** (elf, gnome, human). Les six autres espèces divergent
aussi, mais **rien ne s'appuie sur leurs clefs** : leur divergence ne coûte rien
tant qu'aucune couche ne les vise.

---

## 3. Ce qui se passe exactement — mesuré, pas supposé

Trois piles montées, trois résultats.

| pile | résultat |
|---|---|
| `srd-en` + `fh-species-en` *(la pile livrée)* | ✅ monte · humain rendu par `srd-5.2.1-en` · traits `["skillful","versatile"]` · `granted_skill_choice` retiré |
| `srd-en` + `srd-fr` + `fh-species-en` | ⛔ **REFUS AU MONTAGE** |
| `srd-fr` + `fh-species-en` | ⛔ **REFUS AU MONTAGE** |

Le refus, mot pour mot :

> `fhpc/layers: la couche « fh-species-en », patch de species « srd:species:en:elf »`
> `— « data.traits[keen-senses] » n'existe pas dans le record — le chemin`
> `« data.traits[keen-senses].text » ne peut pas être créé en profondeur : une`
> `couche ne devine pas la forme qu'elle voudrait trouver.`

⭐ **Il nomme la couche, l'espèce, le chemin et la raison, et il tombe AVANT tout
rendu.** Personne n'obtient une fiche fausse : on n'obtient pas de fiche du tout.

---

## 4. Les trois gardes existent déjà, et elles sont bruyantes

La question posée était : *« `gen-fh-species-layer.mjs:105` déréférence par
`trait.id` sans dire ce qu'il fait quand il ne trouve rien »*. **Mesuré : il le
dit.** Et il n'est pas seul.

| garde | où | comportement mesuré |
|---|---|---|
| refus par identité de couche | `assertSrdLayer`, `gen-fh-species-layer.mjs:78` | `srd-5.2.1-fr` → *« la couche SRD fournie a l'id « srd-5.2.1-fr », attendu « srd-5.2.1-en » »* |
| trait absent au tirage | `liftTrait`, `gen-fh-species-layer.mjs:105` | nomme le trait, l'espèce, **et liste les traits présents** |
| chemin dans le vide au montage | `applyRemoval` / `descend`, `src/layers/paths.mjs:238` | *« un retrait dans le vide est un échec, pas un silence (§L7.2) »* |

⛔ **Il n'y a donc pas de garde à ajouter** — et en ajouter une lèverait une
exception là où trois refus nommés tombent déjà. La réparation utile n'est pas
une garde de plus : c'est un **test de régression** qui épingle ce refus, pour
qu'un futur assouplissement des chemins ne le transforme pas en silence.
Ce test est posé dans `fhpc` : `tests/layers-traits-fr.test.mjs`.

---

## 5. Ce que ça coûte vraiment — pour l'arbitrage

**Le coût n'est pas un risque de corruption. C'est une capacité absente :**
aujourd'hui, **un personnage FH en français est impossible à construire**, parce
que la couche FH d'espèces refuse de se monter au-dessus du SRD français.

Trois routes, si Eric veut trancher :

1. **Ne rien faire.** Le français reste un rendu du SRD nu ; FH reste anglais.
   Coût : nul. Perte : pas de FH en français.
2. **Migrer les clefs de `data.traits[]` à l'export `fh-srd`.** Les clefs
   deviennent anglaises dans les deux langues, les 6 chemins retombent sur leurs
   pieds, et le refus disparaît. ⚠️ Change une couche que trois écrans lisent.
3. **Réadresser les 6 chemins par langue.** Ne touche pas l'export, mais fait
   entrer la langue dans une couche FH qui n'en avait pas — et il faudra le
   refaire à chaque nouveau chemin.

⛔ **Une quatrième route est à écarter d'avance** : rapprocher les clefs par leur
nom affichable. C'est ce que §0.13 interdit, et l'homographe `brave` du halfling
montre pourquoi la méthode aurait l'air de marcher.

---

## Comment ce relevé a été fait

Piles montées via `layers.register` sur le vrai noyau `fhpc`, worktree
`108-mesure-traits` sur `3210e90`. Clefs lues dans `layers/srd-5.2.1-en.layer.json`
et `layers/srd-5.2.1-fr.layer.json`, chemins lus dans
`layers/fh-species-en.layer.json`. Aucun chiffre de ce document n'est déduit
d'un autre.
