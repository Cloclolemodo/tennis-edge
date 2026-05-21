"""
Endpoints /players — CRUD basique pour démarrer.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import PlayerCreate, PlayerRead
from app.core.config import settings
from app.db.models import Player
from app.db.session import get_db
from app.services.elo import win_probability
from app.services.value_bet import analyze_bet

router = APIRouter()


@router.post("", response_model=PlayerRead, status_code=status.HTTP_201_CREATED)
def create_player(payload: PlayerCreate, db: Session = Depends(get_db)):
    """Crée un joueur avec l'Elo initial par défaut (1500)."""
    player = Player(
        full_name=payload.full_name,
        country=payload.country,
        gender=payload.gender,
        external_id=payload.external_id,
        current_elo=settings.elo_initial_rating,
    )
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


@router.get("", response_model=list[PlayerRead])
def list_players(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Liste paginée des joueurs."""
    return db.query(Player).offset(offset).limit(limit).all()


@router.get("/{player_id}", response_model=PlayerRead)
def get_player(player_id: int, db: Session = Depends(get_db)):
    """Détail d'un joueur."""
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@router.get("/{player_id}/win-probability/{opponent_id}")
def get_win_probability(
    player_id: int,
    opponent_id: int,
    db: Session = Depends(get_db),
):
    """
    Probabilité que `player_id` batte `opponent_id`, selon leurs ratings Elo.

    C'est une CONSULTATION (GET) : on lit les ratings, on calcule, on renvoie.
    Rien n'est modifié en base.

    On renvoie aussi la "cote juste" (fair_odds = 1 / probabilité) :
    c'est la cote que proposerait un bookmaker sans marge. Elle servira
    plus tard à comparer avec les vraies cotes pour détecter les value bets.
    """
    player = db.query(Player).filter(Player.id == player_id).first()
    opponent = db.query(Player).filter(Player.id == opponent_id).first()
    if not player:
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found")
    if not opponent:
        raise HTTPException(status_code=404, detail=f"Player {opponent_id} not found")
    if player_id == opponent_id:
        raise HTTPException(status_code=400, detail="A player cannot face themselves")

    proba = win_probability(player.current_elo, opponent.current_elo)

    return {
        "player": {"id": player.id, "name": player.full_name, "elo": player.current_elo},
        "opponent": {"id": opponent.id, "name": opponent.full_name, "elo": opponent.current_elo},
        "win_probability": round(proba, 4),
        "fair_odds": round(1 / proba, 2),
    }


@router.get("/{player_id}/value-bet/{opponent_id}")
def analyze_value_bet(
    player_id: int,
    opponent_id: int,
    bookmaker_odds: float,
    db: Session = Depends(get_db),
):
    """
    Analyse un pari sur `player_id` face à `opponent_id`.

    Compare la cote du bookmaker (`bookmaker_odds`, à fournir en paramètre)
    avec la cote juste calculée par Elo, et indique si c'est un value bet
    ainsi que la mise conseillée (Kelly fractionné).

    C'est une CONSULTATION (GET) : rien n'est modifié en base.
    """
    player = db.query(Player).filter(Player.id == player_id).first()
    opponent = db.query(Player).filter(Player.id == opponent_id).first()
    if not player:
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found")
    if not opponent:
        raise HTTPException(status_code=404, detail=f"Player {opponent_id} not found")
    if player_id == opponent_id:
        raise HTTPException(status_code=400, detail="A player cannot face themselves")
    if bookmaker_odds <= 1.0:
        raise HTTPException(
            status_code=400,
            detail="bookmaker_odds doit être supérieur à 1.0",
        )

    # Probabilité de victoire selon Elo
    proba = win_probability(player.current_elo, opponent.current_elo)

    # Analyse value bet, avec les seuils définis dans la config
    analysis = analyze_bet(
        probability=proba,
        bookmaker_odds=bookmaker_odds,
        min_edge=settings.value_bet_min_edge,
        kelly_fraction=settings.kelly_fraction,
    )

    return {
        "player": {"id": player.id, "name": player.full_name, "elo": player.current_elo},
        "opponent": {"id": opponent.id, "name": opponent.full_name, "elo": opponent.current_elo},
        "analysis": analysis,
    }