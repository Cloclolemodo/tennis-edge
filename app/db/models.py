"""
Modèles SQLAlchemy.

Pour la V1, on garde simple :
- Player : un joueur de tennis
- Match : un match entre deux joueurs (sera ajouté à l'étape 2)
- Rating : historique des ratings Elo (sera ajouté à l'étape 3)
- Bet : tracking des paris (sera ajouté à l'étape 5)
"""
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Identité
    full_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    country: Mapped[str | None] = mapped_column(String(3), nullable=True)  # code ISO
    gender: Mapped[str] = mapped_column(String(1), nullable=False)  # 'M' ou 'F'

    # Référence externe (api-sports.io)
    external_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True, index=True)

    # Elo courant (mis à jour après chaque match)
    # Note : on garde aussi un historique dans la table `ratings` (étape 3)
    current_elo: Mapped[float] = mapped_column(Float, nullable=False, default=1500.0)
    matches_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Player {self.full_name} (Elo {self.current_elo:.0f})>"
