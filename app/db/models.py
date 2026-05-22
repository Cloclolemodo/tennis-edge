"""
Modèles SQLAlchemy.

Pour la V1, on garde simple :
- Player : un joueur de tennis
- Match : un match entre deux joueurs (sera ajouté à l'étape 2)
- Rating : historique des ratings Elo (sera ajouté à l'étape 3)
- Bet : tracking des paris (sera ajouté à l'étape 5)
"""
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, func
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


class Match(Base):
    __tablename__ = "matches"

    # Clé primaire : identifiant unique de chaque match (1, 2, 3...)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # --- Les deux joueurs : clés étrangères vers la table players ---
    # ForeignKey("players.id") = "cette colonne contient un id de la table players".
    # nullable=False : un match a TOUJOURS deux joueurs connus, même à venir.
    player1_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=False
    )
    player2_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=False
    )

    # --- Le gagnant : clé étrangère AUSSI, mais nullable ---
    # nullable=True : un match à venir n'a pas encore de gagnant (NULL).
    # On le remplira avec l'id du vainqueur une fois le match joué.
    winner_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=True
    )

    # --- Contexte du match : connu même pour un match à venir ---
    match_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tournament: Mapped[str] = mapped_column(String(120), nullable=False)
    surface: Mapped[str] = mapped_column(String(20), nullable=False)  # clay / hard / grass

    # Statut : "scheduled" (à venir) ou "completed" (terminé).
    # Permet de distinguer un match à analyser d'un match passé.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduled")

    # --- Score et stats : nullable, vides tant que le match n'est pas joué ---
    score: Mapped[str | None] = mapped_column(String(50), nullable=True)  # ex : "6-4 7-5"

    aces_p1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    aces_p2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    breaks_p1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    breaks_p2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    points_p1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    points_p2: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Référence externe (api-sports.io)
    external_id: Mapped[int | None] = mapped_column(
        Integer, unique=True, nullable=True, index=True
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Match {self.player1_id} vs {self.player2_id} ({self.status})>"


class Bet(Base):
    __tablename__ = "bets"

    # Clé primaire : identifiant unique de chaque pari.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # --- Sur quel match porte le pari : clé étrangère vers matches ---
    match_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("matches.id"), nullable=False
    )

    # --- Sur quel joueur on parie : clé étrangère vers players ---
    # C'est l'un des deux joueurs du match.
    bet_on_player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=False
    )

    # --- Les chiffres du pari ---
    stake: Mapped[float] = mapped_column(Float, nullable=False)  # la mise (ex: 20.0)
    odds: Mapped[float] = mapped_column(Float, nullable=False)   # la cote au moment du pari

    # Statut du pari :
    #   "pending" : en attente, le match n'est pas encore joué
    #   "won"     : pari gagné
    #   "lost"    : pari perdu
    # Un pari créé est toujours "pending" au départ.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    # Date à laquelle le pari a été pris.
    placed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Bet {self.stake}@{self.odds} on player {self.bet_on_player_id} ({self.status})>"