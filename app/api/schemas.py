"""
Schémas Pydantic — séparent la couche API de la couche DB.

Bonne pratique : on ne renvoie jamais directement un modèle SQLAlchemy
au client. On passe par un schéma Pydantic qui contrôle exactement
ce qui est exposé.
"""
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class PlayerCreate(BaseModel):
    """Payload pour créer un joueur."""
    full_name: str = Field(..., min_length=2, max_length=120, examples=["Jannik Sinner"])
    country: str | None = Field(None, min_length=2, max_length=3, examples=["ITA"])
    gender: str = Field(..., pattern="^[MF]$", examples=["M"])
    external_id: int | None = None


class PlayerRead(BaseModel):
    """Réponse API pour un joueur."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    country: str | None
    gender: str
    current_elo: float
    matches_played: int
    created_at: datetime
    updated_at: datetime


# --- Schémas Match ---

class MatchCreate(BaseModel):
    """
    Payload pour créer un match À VENIR.
    On ne demande QUE les infos connues à l'avance.
    Pas de gagnant, pas de score : le match n'est pas encore joué.
    """
    player1_id: int = Field(..., examples=[1])
    player2_id: int = Field(..., examples=[2])
    match_date: datetime = Field(..., examples=["2026-06-15T14:00:00Z"])
    tournament: str = Field(..., min_length=2, max_length=120, examples=["Roland-Garros"])
    surface: str = Field(..., pattern="^(clay|hard|grass)$", examples=["clay"])
    external_id: int | None = None


class MatchUpdate(BaseModel):
    """
    Payload pour ENREGISTRER LE RÉSULTAT d'un match déjà joué.
    Tous les champs sont optionnels : on remplit ce qu'on a.
    Mettre à jour un match le fait passer en statut "completed".
    """
    winner_id: int | None = None
    score: str | None = Field(None, examples=["6-4 7-5"])
    aces_p1: int | None = None
    aces_p2: int | None = None
    breaks_p1: int | None = None
    breaks_p2: int | None = None
    points_p1: int | None = None
    points_p2: int | None = None


class MatchRead(BaseModel):
    """Réponse API pour un match : toutes les colonnes."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    player1_id: int
    player2_id: int
    winner_id: int | None
    match_date: datetime
    tournament: str
    surface: str
    status: str
    score: str | None
    aces_p1: int | None
    aces_p2: int | None
    breaks_p1: int | None
    breaks_p2: int | None
    points_p1: int | None
    points_p2: int | None
    created_at: datetime


# --- Schémas Bet ---

class BetCreate(BaseModel):
    """Payload pour enregistrer un nouveau pari."""
    match_id: int = Field(..., examples=[1])
    bet_on_player_id: int = Field(..., examples=[1])
    stake: float = Field(..., gt=0, examples=[20.0])
    odds: float = Field(..., gt=1.0, examples=[1.85])


class BetSettle(BaseModel):
    """Payload pour régler un pari : indiquer s'il est gagné ou perdu."""
    status: str = Field(..., pattern="^(won|lost)$", examples=["won"])


class BetRead(BaseModel):
    """Réponse API pour un pari."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    match_id: int
    bet_on_player_id: int
    stake: float
    odds: float
    status: str
    placed_at: datetime