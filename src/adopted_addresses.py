"""Les trois adresses que le français seul portait — ADOPTÉES, pas inventées.

Le glossaire français imprime trois entrées que l'anglais ne lui donne pas :
`Vitesse d'escalade`, `Vitesse de nage`, `Vitesse de vol`. Elles n'ont donc
aucune adresse anglaise à qui emprunter la leur, et la transition à froid ne
laisse plus d'adresse française à personne.

**Eric a tranché le 2026-08-24 : « Les inventer oui ».**

## ⭐ ET LA MESURE A TROUVÉ QU'ON N'A RIEN À INVENTER

L'autorisation était donnée ; elle n'a pas servi. **Le livre ANGLAIS imprime
déjà ces trois termes — 74 fois.** Il ne leur donne simplement pas d'entrée de
glossaire :

    Fly Speed      37 occurrences   (broom-of-flying, et 36 autres)
    Swim Speed     22               (apparatus-of-the-crab…)
    Climb Speed    15               (cloak-of-arachnida…)
    ────
    Swimming Speed · Flying Speed · Climbing Speed :  ZÉRO

⭐ **ET LE QUATRIÈME MEMBRE DE LA FAMILLE PROUVE LA FORME DU SLUG.** `Burrow
Speed` a, LUI, son entrée anglaise (`srd:glossary:en:burrow-speed`), et son
jumeau français `Vitesse de fouissement` est apparié par la correspondance. La
famille a donc un patron attesté des deux côtés ; trois de ses quatre membres
ne sont simplement pas imprimés comme entrées côté anglais.

⚠️ **ET C'EST POURQUOI « DÉRIVÉE » N'EST PAS « CHOISIE AU GOÛT ».** Le premier
réflexe était `climbing-speed`, calqué sur l'entrée `Climbing` qui existe. Le
livre écrit **`Climb Speed`**, jamais `Climbing Speed` — zéro occurrence. Une
adresse choisie au goût aurait été fausse, et rien ne l'aurait dit.

## 🔴 LA COLLISION, VÉRIFIÉE ET PAS SUPPOSÉE

L'anglais porte **déjà** `Climbing`, `Swimming`, `Flying` — et ce sont des
entrées **DISTINCTES** : elles décrivent le MODE DE DÉPLACEMENT (« chaque mètre
coûte un mètre de plus »), pas la VITESSE (« remplace la Vitesse pour traverser
une surface verticale »). ⛔ Une adresse qui écraserait l'une des trois serait
un défaut, pas un raccourci. Les trois adoptées sont libres, et
`assert_no_collision()` le revérifie à chaque construction sur les records
réels — jamais sur une liste recopiée ici.

## La provenance le dit, et elle dit la vérité

`adopted:english-book` — ⛔ **pas `invented`**. Une adresse fabriquée doit se
reconnaître comme telle dix ans plus tard ; une adresse **prise dans le livre**
doit se reconnaître comme telle aussi, et pour la même raison. Dire « inventée »
d'un terme que le livre imprime 74 fois serait une fausse modestie qui coûterait
à la personne qui relira.
"""

#: ⚠️ CLEFÉ SUR LE MOT DU LIVRE — `<genre>:<slug français>` —, jamais sur une
#: adresse française : après la transition à froid, il n'en existe plus une
#: seule dans le dépôt. Même forme que `sources/correspondence-*.json`, et pour
#: la même raison : un slug est un mot, une adresse serait un mensonge.
ADOPTED_BY_SLUG = {
    "glossary:vitesse-d-escalade": "srd:glossary:en:climb-speed",
    "glossary:vitesse-de-nage": "srd:glossary:en:swim-speed",
    "glossary:vitesse-de-vol": "srd:glossary:en:fly-speed",
}

#: Les mêmes, ré-adressés vers la base de TRAVAIL (gitignorée), où les records
#: français existent encore le temps que les routes de correspondance tournent.
ADOPTED = {"srd:%s:fr:%s" % tuple(k.split(":", 1)): v
           for k, v in ADOPTED_BY_SLUG.items()}

PROVENANCE = "adopted:english-book"

#: Le témoin de la famille : lui EST imprimé des deux côtés, et c'est lui qui
#: donne la forme du slug. ⛔ Ne pas le retirer de cette liste sans mesurer à
#: nouveau : sans lui, les trois adresses redeviennent un choix de goût.
WITNESS = "srd:glossary:en:burrow-speed"

#: Ce que ces adresses NE DOIVENT PAS écraser — le mode de déplacement, qui
#: n'est pas la vitesse.
MUST_NOT_COLLIDE = (
    "srd:glossary:en:climbing",
    "srd:glossary:en:swimming",
    "srd:glossary:en:flying",
    "srd:glossary:en:speed",
)


class AddressError(Exception):
    """Une adresse adoptée écrase un record existant, ou son témoin a disparu."""


def assert_no_collision(english_ids):
    """Refuse si une adresse adoptée existe déjà, ou si le témoin a disparu.

    `english_ids` : les identifiants anglais RÉELS de la construction en cours.
    ⛔ Jamais une liste recopiée : c'est la donnée qui doit répondre.
    """
    ids = set(english_ids)

    occupees = sorted(a for a in ADOPTED.values() if a in ids)
    if occupees:
        raise AddressError(
            "adresse(s) adoptée(s) DÉJÀ PRISES par un record anglais — %s. "
            "Le livre anglais a gagné une entrée depuis la mesure du "
            "2026-08-24 : c'est une bonne nouvelle, pas un conflit à forcer. "
            "Le français a maintenant un vrai vis-à-vis, et il se PAIRE au "
            "lieu de s'adopter. Refusé, pas écrasé." % ", ".join(occupees)
        )

    if WITNESS not in ids:
        raise AddressError(
            "le témoin %r a disparu des records anglais. C'est lui qui prouve "
            "la forme du slug (`<X> Speed` → `<x>-speed`) : sans lui, les trois "
            "adresses adoptées redeviennent un choix de goût. Refusé." % WITNESS
        )

    manquants = sorted(m for m in MUST_NOT_COLLIDE if m not in ids)
    if manquants:
        raise AddressError(
            "les entrées que les adresses adoptées ne doivent pas écraser ont "
            "disparu — %s. La preuve qu'elles sont DISTINCTES de la vitesse ne "
            "tient plus : remesurer avant de continuer." % ", ".join(manquants)
        )
    return True
