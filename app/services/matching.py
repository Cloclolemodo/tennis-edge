"""
Matching des joueurs : relier un nom venu de l'extérieur (The Odds API)
à un joueur de notre base.

Le problème : les noms ne correspondent jamais parfaitement
("Carlos  ALCARAZ" vs "carlos alcaraz", accents, espaces multiples...).
La solution : normaliser les deux noms avant de les comparer.
"""
import unicodedata

from sqlalchemy.orm import Session

from app.db.models import Player


def normalize_name(name: str) -> str:
    """
    Nettoie un nom pour le rendre comparable.

    - passe tout en minuscules
    - retire les accents (Djoković -> djokovic)
    - réduit les espaces multiples à un seul

    Ainsi "Carlos  ALCARAZ" et "carlos alcaraz" donnent le même résultat.
    """
    # Décompose les caractères accentués puis retire les accents.
    decomposed = unicodedata.normalize("NFKD", name)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))

    # Minuscules + espaces normalisés (split puis join supprime les espaces multiples).
    return " ".join(without_accents.lower().split())


def find_player_by_name(name: str, db: Session) -> Player | None:
    """
    Cherche en base un joueur dont le nom correspond à `name`.

    On compare les noms NORMALISÉS des deux côtés.
    Renvoie le joueur trouvé, ou None si aucun ne correspond
    (cas "non analysable" : l'appelant devra le gérer).
    """
    target = normalize_name(name)

    # On parcourt les joueurs et on compare les noms normalisés.
    # (Suffisant pour une base de taille raisonnable. Pour une très
    #  grosse base, on stockerait le nom normalisé en colonne indexée.)
    for player in db.query(Player).all():
        if normalize_name(player.full_name) == target:
            return player

    return None