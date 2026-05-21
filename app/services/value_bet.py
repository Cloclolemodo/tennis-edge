"""
Détection de value bet et calcul de mise.

Un VALUE BET = un pari où la cote du bookmaker est plus haute que
ce que le pari "vaut" vraiment (selon notre probabilité Elo).
On le mesure avec l'edge.

La MISE est calculée avec le critère de Kelly, en version fractionnée
(prudente) pour limiter la variance.

Logique de calcul pure : pas d'accès base, facile à tester.
"""


def compute_edge(probability: float, bookmaker_odds: float) -> float:
    """
    Calcule l'edge (l'avantage) d'un pari.

        edge = (probabilité × cote_bookmaker) - 1

    - edge > 0  : value bet (gain attendu positif sur le long terme)
    - edge <= 0 : mauvais pari (on ne parie pas)

    Exemple : proba 0.60, cote 1.85 -> (0.60 × 1.85) - 1 = +0.11 (+11 %).
    """
    return (probability * bookmaker_odds) - 1


def kelly_stake(
    probability: float,
    bookmaker_odds: float,
    fraction: float = 0.25,
) -> float:
    """
    Calcule la fraction de bankroll à miser, selon le critère de Kelly.

        kelly = edge / (cote - 1)

    Kelly "plein" est très agressif. On applique une FRACTION (1/4 par
    défaut) pour réduire fortement la variance tout en gardant l'essentiel
    de la croissance.

    Renvoie un pourcentage de bankroll (ex : 0.03 = miser 3 % de la bankroll).
    Renvoie 0 si le pari n'a pas de valeur (edge négatif) : on ne mise pas.
    """
    edge = compute_edge(probability, bookmaker_odds)

    # Pas de value -> pas de mise. (Kelly négatif voudrait dire "parier contre",
    # ce qu'on ne fait pas ici : on se contente de ne pas parier.)
    if edge <= 0:
        return 0.0

    full_kelly = edge / (bookmaker_odds - 1)
    fractional_kelly = full_kelly * fraction

    return fractional_kelly


def analyze_bet(
    probability: float,
    bookmaker_odds: float,
    min_edge: float = 0.05,
    kelly_fraction: float = 0.25,
) -> dict:
    """
    Analyse complète d'un pari : assemble edge, détection et mise.

    - min_edge : seuil minimal pour qualifier un value bet (5 % par défaut).
      On exige une marge de sécurité : un edge de +1 % est trop fragile
      (notre probabilité Elo n'est pas parfaite).

    Renvoie un dictionnaire prêt à être affiché.
    """
    edge = compute_edge(probability, bookmaker_odds)
    is_value_bet = edge >= min_edge

    # On ne conseille une mise que si le value bet passe le seuil.
    stake = kelly_stake(probability, bookmaker_odds, kelly_fraction) if is_value_bet else 0.0

    return {
        "probability": round(probability, 4),
        "bookmaker_odds": bookmaker_odds,
        "fair_odds": round(1 / probability, 2) if probability > 0 else None,
        "edge": round(edge, 4),
        "edge_pct": round(edge * 100, 2),
        "is_value_bet": is_value_bet,
        "recommended_stake_pct": round(stake * 100, 2),
    }