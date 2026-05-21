"""
Endpoints /matches — créer, lister, consulter et mettre à jour des matchs.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import MatchCreate, MatchUpdate, MatchRead
from app.core.config import settings
from app.db.models import Match, Player
from app.db.session import get_db
from app.services.elo import update_ratings

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