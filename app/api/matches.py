"""
Endpoints /matches — créer, lister, consulter et mettre à jour des matchs.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import MatchCreate, MatchUpdate, MatchRead
from app.core.config import settings
from app.db.models import Match, Player
from app.db.session import get_db
from app.services.elo import update_ratings, win_probability
from app.services.matching import find_player_by_name
from app.services.value_bet import analyze_bet
from app.sources.odds_api import fetch_tennis_odds, OddsAPIError
from app.sources.telegram import send_telegram_message, TelegramError

router = APIRouter()


@router.post("", response_model=MatchRead, status_code=status.HTTP_201_CREATED)
def create_match(payload: MatchCreate, db: Session = Depends(get_db)):
    """
    Crée un match À VENIR (statut "scheduled" par défaut).

    On vérifie d'abord que les deux joueurs existent vraiment en base :
    une clé étrangère pointant vers un joueur inexistant n'aurait aucun sens.
    """
    # Vérification : les deux joueurs existent-ils ?
    player1 = db.query(Player).filter(Player.id == payload.player1_id).first()
    player2 = db.query(Player).filter(Player.id == payload.player2_id).first()
    if not player1:
        raise HTTPException(status_code=404, detail=f"Player {payload.player1_id} not found")
    if not player2:
        raise HTTPException(status_code=404, detail=f"Player {payload.player2_id} not found")

    # Garde-fou métier : un joueur ne joue pas contre lui-même
    if payload.player1_id == payload.player2_id:
        raise HTTPException(status_code=400, detail="A player cannot play against themselves")

    match = Match(
        player1_id=payload.player1_id,
        player2_id=payload.player2_id,
        match_date=payload.match_date,
        tournament=payload.tournament,
        surface=payload.surface,
        external_id=payload.external_id,
        status="scheduled",  # un match créé est toujours "à venir"
    )
    db.add(match)
    db.commit()
    db.refresh(match)
    return match


@router.get("", response_model=list[MatchRead])
def list_matches(
    limit: int = 50,
    offset: int = 0,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Liste paginée des matchs.
    Le paramètre optionnel `status_filter` permet de ne garder que
    les matchs "scheduled" ou "completed".
    """
    query = db.query(Match)
    if status_filter:
        query = query.filter(Match.status == status_filter)
    return query.offset(offset).limit(limit).all()


@router.get("/{match_id}", response_model=MatchRead)
def get_match(match_id: int, db: Session = Depends(get_db)):
    """Détail d'un match précis."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match


@router.patch("/{match_id}", response_model=MatchRead)
def update_match(match_id: int, payload: MatchUpdate, db: Session = Depends(get_db)):
    """
    Enregistre le RÉSULTAT d'un match (gagnant, score, stats).
    Met automatiquement le statut à "completed".

    PATCH (et non PUT) : on ne met à jour que les champs fournis,
    le reste du match est inchangé.
    """
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Si un gagnant est fourni, il doit être l'un des deux joueurs du match
    if payload.winner_id is not None:
        if payload.winner_id not in (match.player1_id, match.player2_id):
            raise HTTPException(
                status_code=400,
                detail="winner_id must be one of the two players of this match",
            )

    # On applique uniquement les champs réellement envoyés par le client
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(match, field, value)

    # --- Mise à jour Elo ---
    # On ne recalcule l'Elo QU'UNE FOIS : seulement si le match n'était pas
    # déjà "completed" avant ce PATCH, et si un gagnant est bien renseigné.
    # Sans ce garde-fou, refaire le PATCH ferait bouger les ratings plusieurs fois.
    was_already_completed = match.status == "completed"

    # Enregistrer un résultat fait passer le match en "completed"
    match.status = "completed"

    if not was_already_completed and match.winner_id is not None:
        # --- Mise à jour des ratings Elo ---
        # On identifie le perdant : c'est l'autre joueur du match.
        loser_id = (
            match.player2_id if match.winner_id == match.player1_id
            else match.player1_id
        )
        winner = db.query(Player).filter(Player.id == match.winner_id).first()
        loser = db.query(Player).filter(Player.id == loser_id).first()

        # Le moteur Elo calcule les nouveaux ratings.
        new_winner_elo, new_loser_elo = update_ratings(
            rating_winner=winner.current_elo,
            rating_loser=loser.current_elo,
            k_factor=settings.elo_k_factor,
        )

        # On écrit les nouveaux ratings et on incrémente le compteur de matchs.
        winner.current_elo = new_winner_elo
        loser.current_elo = new_loser_elo
        winner.matches_played += 1
        loser.matches_played += 1

    db.commit()
    db.refresh(match)
    return match


@router.get("/odds/live")
def get_live_odds():
    """
    Récupère les cotes réelles des matchs de tennis à venir,
    via The Odds API (bookmakers européens).

    ATTENTION : chaque appel consomme 1 requête du quota mensuel (500/mois).

    Si le service de cotes échoue, on renvoie une erreur 503 claire
    ("service indisponible") plutôt qu'une fausse réponse.
    """
    try:
        raw_odds = fetch_tennis_odds(regions="eu")
    except OddsAPIError as exc:
        # 503 = "Service Unavailable" : le code HTTP fait pour ce cas.
        raise HTTPException(status_code=503, detail=str(exc))

    # On renvoie un résumé : nombre de matchs trouvés + les données brutes.
    return {
        "matches_found": len(raw_odds),
        "odds": raw_odds,
    }


def _extract_h2h_odds(match: dict) -> dict | None:
    """
    Extrait, depuis un match The Odds API, la cote h2h de chaque joueur
    chez le premier bookmaker disponible.

    Renvoie {nom_joueur: cote, ...} ou None si aucune cote exploitable.
    """
    bookmakers = match.get("bookmakers", [])
    if not bookmakers:
        return None

    # On prend le premier bookmaker, et son marché "h2h".
    for market in bookmakers[0].get("markets", []):
        if market.get("key") == "h2h":
            outcomes = market.get("outcomes", [])
            return {o["name"]: o["price"] for o in outcomes}
    return None


@router.get("/odds/analyze")
def analyze_live_matches(db: Session = Depends(get_db)):
    """
    Analyse automatique des vrais matchs de tennis à venir.

    Pour chaque match renvoyé par The Odds API :
    - retrouve les deux joueurs dans notre base (matching par nom)
    - si les deux existent : calcule l'analyse value bet
    - sinon : marque le match "non analysable"

    ATTENTION : consomme 1 requête du quota mensuel The Odds API.
    """
    try:
        raw_matches = fetch_tennis_odds(regions="eu")
    except OddsAPIError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    analyzed = []
    skipped = []

    for match in raw_matches:
        home_name = match.get("home_team", "")
        away_name = match.get("away_team", "")

        # Matching : retrouve les joueurs dans notre base.
        home_player = find_player_by_name(home_name, db)
        away_player = find_player_by_name(away_name, db)

        # Cas "non analysable" : un joueur manque -> on signale et on passe.
        if home_player is None or away_player is None:
            skipped.append({
                "match": f"{home_name} vs {away_name}",
                "reason": "joueur(s) absent(s) de la base",
            })
            continue

        # Les cotes du bookmaker pour ce match.
        odds = _extract_h2h_odds(match)
        if not odds or home_name not in odds:
            skipped.append({
                "match": f"{home_name} vs {away_name}",
                "reason": "cotes indisponibles",
            })
            continue

        # Probabilité Elo pour le joueur "home", puis analyse value bet.
        proba = win_probability(home_player.current_elo, away_player.current_elo)
        analysis = analyze_bet(
            probability=proba,
            bookmaker_odds=odds[home_name],
            min_edge=settings.value_bet_min_edge,
            kelly_fraction=settings.kelly_fraction,
        )

        analyzed.append({
            "match": f"{home_name} vs {away_name}",
            "tournament": match.get("sport_title"),
            "analysis": analysis,
        })

    return {
        "analyzed_count": len(analyzed),
        "skipped_count": len(skipped),
        "analyzed": analyzed,
        "skipped": skipped,
    }


@router.get("/alerts/test")
def test_telegram_alert():
    """
    Envoie un message de test sur Telegram.
    Sert à vérifier que les notifications sont bien configurées.
    """
    try:
        send_telegram_message("✅ Test Tennis Edge : les alertes fonctionnent !")
    except TelegramError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"status": "message envoyé"}


@router.get("/alerts/scan")
def scan_and_alert(db: Session = Depends(get_db)):
    """
    Détecteur de value bets avec alerte Telegram.

    Analyse les vrais matchs à venir (comme /odds/analyze) et,
    pour chaque value bet détecté, envoie une alerte Telegram.

    ATTENTION : consomme 1 requête du quota The Odds API.
    À ne pas lancer trop souvent (quota : 500 requêtes/mois).
    """
    try:
        raw_matches = fetch_tennis_odds(regions="eu")
    except OddsAPIError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    value_bets_found = []

    for match in raw_matches:
        home_name = match.get("home_team", "")
        away_name = match.get("away_team", "")

        home_player = find_player_by_name(home_name, db)
        away_player = find_player_by_name(away_name, db)
        if home_player is None or away_player is None:
            continue

        odds = _extract_h2h_odds(match)
        if not odds or home_name not in odds:
            continue

        proba = win_probability(home_player.current_elo, away_player.current_elo)
        analysis = analyze_bet(
            probability=proba,
            bookmaker_odds=odds[home_name],
            min_edge=settings.value_bet_min_edge,
            kelly_fraction=settings.kelly_fraction,
        )

        # Si c'est un value bet : on prépare une alerte.
        if analysis["is_value_bet"]:
            value_bets_found.append({
                "match": f"{home_name} vs {away_name}",
                "analysis": analysis,
            })

    # Envoi des alertes Telegram (une seule fois, groupées).
    alerts_sent = 0
    if value_bets_found:
        lines = ["🎾 <b>Value bets détectés</b>\n"]
        for vb in value_bets_found:
            a = vb["analysis"]
            lines.append(
                f"• {vb['match']}\n"
                f"  edge {a['edge_pct']}% | cote {a['bookmaker_odds']} "
                f"| mise conseillée {a['recommended_stake_pct']}%"
            )
        try:
            send_telegram_message("\n".join(lines))
            alerts_sent = len(value_bets_found)
        except TelegramError as exc:
            raise HTTPException(status_code=503, detail=f"Alerte non envoyée : {exc}")

    return {
        "value_bets_found": len(value_bets_found),
        "alerts_sent": alerts_sent,
        "details": value_bets_found,
    }