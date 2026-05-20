"""
Endpoints /players — CRUD basique pour démarrer.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import PlayerCreate, PlayerRead
from app.core.config import settings
from app.db.models import Player
from app.db.session import get_db

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
