"""
Client The Odds API — récupère les cotes réelles des bookmakers.

C'est la couche "sources" : tout ce qui parle à un service externe.

ATTENTION QUOTA : le plan gratuit est limité à 500 requêtes/mois.
Chaque appel à `fetch_tennis_odds()` consomme 1 requête. À utiliser
avec parcimonie (ne pas appeler en boucle).
"""
import httpx

from app.core.config import settings


# URL de base de l'API. Le sport "tennis" couvre les principaux tournois ATP/WTA.
BASE_URL = "https://api.the-odds-api.com/v4"


class OddsAPIError(Exception):
    """
    Erreur levée quand l'appel à The Odds API échoue.
    On préfère une erreur claire et explicite plutôt qu'une réponse
    fausse ou un plantage silencieux.
    """
    pass


def fetch_tennis_odds(regions: str = "eu") -> list[dict]:
    """
    Récupère les cotes des matchs de tennis à venir.

    - regions="eu" : bookmakers européens (cohérent avec Betclic, Winamax...).
    - Renvoie la liste brute des matchs avec leurs cotes.

    Lève OddsAPIError si quelque chose se passe mal (clé invalide,
    quota dépassé, service injoignable...). L'appelant devra gérer ça.
    """
    # Garde-fou : sans clé configurée, inutile d'appeler quoi que ce soit.
    if not settings.odds_api_key:
        raise OddsAPIError("Aucune clé The Odds API configurée (ODDS_API_KEY vide).")

    url = f"{BASE_URL}/sports/tennis/odds"
    params = {
        "apiKey": settings.odds_api_key,
        "regions": regions,
        "markets": "h2h",       # h2h = "head to head" : cote de victoire de chaque joueur
        "oddsFormat": "decimal", # cotes décimales (format européen : 1.85, 2.20...)
    }

    try:
        # timeout : si le service ne répond pas en 10s, on abandonne
        # plutôt que d'attendre indéfiniment.
        response = httpx.get(url, params=params, timeout=10.0)
    except httpx.RequestError as exc:
        # Problème réseau : service injoignable, DNS, timeout...
        raise OddsAPIError(f"Service de cotes injoignable : {exc}") from exc

    # The Odds API renvoie un code HTTP différent de 200 en cas de souci
    # (401 = clé invalide, 429 = quota dépassé, etc.)
    if response.status_code != 200:
        raise OddsAPIError(
            f"The Odds API a répondu {response.status_code} : {response.text[:200]}"
        )

    try:
        return response.json()
    except ValueError as exc:
        raise OddsAPIError("Réponse de The Odds API illisible (JSON invalide).") from exc