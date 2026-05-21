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