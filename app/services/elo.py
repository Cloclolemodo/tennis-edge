"""
Moteur Elo — le "cerveau" de l'API.

Deux opérations fondamentales :
1. AVANT un match : calculer la probabilité de victoire à partir des ratings.
2. APRÈS un match : ajuster les ratings selon le résultat.

C'est de la logique métier pure (des calculs), sans accès à la base :
facile à tester, facile à comprendre.
"""


def win_probability(rating_a: float, rating_b: float) -> float:
    """
    Probabilité que le joueur A batte le joueur B.

    Formule Elo classique :
        P(A gagne) = 1 / (1 + 10^((rating_B - rating_A) / 400))

    Le 400 est une convention historique (héritée des échecs).
    Exemples de résultats :
        écart 0   -> 0.50  (50 %)
        écart 100 -> 0.64
        écart 200 -> 0.76
        écart 400 -> 0.91
    """
    exponent = (rating_b - rating_a) / 400
    return 1 / (1 + 10 ** exponent)


def update_ratings(
    rating_winner: float,
    rating_loser: float,
    k_factor: float = 32.0,
) -> tuple[float, float]:
    """
    Calcule les nouveaux ratings après un match.

    Formule de mise à jour :
        nouveau = ancien + K × (résultat - probabilité_attendue)

    - résultat = 1 pour le gagnant, 0 pour le perdant
    - K = amplitude maximale d'ajustement (32 par défaut)

    Le gagnant gagne exactement ce que le perdant perd : le total est conservé.

    Renvoie un tuple : (nouveau_rating_gagnant, nouveau_rating_perdant).
    """
    # Probabilité que le gagnant l'emporte, estimée AVANT le match.
    expected_winner = win_probability(rating_winner, rating_loser)

    # Le gagnant a "résultat = 1". L'écart (1 - expected) mesure la surprise :
    #   - favori qui gagne  -> expected ~0.9 -> (1 - 0.9) = 0.1 -> petit ajustement
    #   - outsider qui gagne -> expected ~0.1 -> (1 - 0.1) = 0.9 -> gros ajustement
    delta = k_factor * (1 - expected_winner)

    new_winner = rating_winner + delta
    new_loser = rating_loser - delta  # le perdant perd exactement ce que le gagnant gagne

    return new_winner, new_loser