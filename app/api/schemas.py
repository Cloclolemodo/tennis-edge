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
