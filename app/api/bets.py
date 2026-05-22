"""
Endpoints /bets — enregistrer, lister, régler ses paris, et voir son ROI.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import BetCreate, BetSettle, BetRead
from app.db.models import Bet, Match, Player
from app.db.session import get_db
from app.services.value_bet import bet_profit

router = APIRouter()


@router.post("", response_model=BetRead, status_code=status.HTTP_201_CREATED)
def create_bet(payload: BetCreate, db: Session = Depends(get_db)):
    """
    Enregistre un nouveau pari.

    Vérifie que le match et le joueur existent, et que le joueur
    sur lequel on parie fait bien partie de ce match.
    Le pari démarre toujours en statut "pending".
    """
    match = db.query(Match).filter(Match.id == payload.match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail=f"Match {payload.match_id} not found")

    player = db.query(Player).filter(Player.id == payload.bet_on_player_id).first()
    if not player:
        raise HTTPException(
            status_code=404, detail=f"Player {payload.bet_on_player_id} not found"
        )

    # Garde-fou : on ne peut parier que sur un des deux joueurs du match.
    if payload.bet_on_player_id not in (match.player1_id, match.player2_id):
        raise HTTPException(
            status_code=400,
            detail="Le joueur choisi ne fait pas partie de ce match",
        )

    bet = Bet(
        match_id=payload.match_id,
        bet_on_player_id=payload.bet_on_player_id,
        stake=payload.stake,
        odds=payload.odds,
        status="pending",  # un pari créé est toujours en attente
    )
    db.add(bet)
    db.commit()
    db.refresh(bet)
    return bet


@router.get("", response_model=list[BetRead])
def list_bets(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Liste les paris. Filtre optionnel par statut (pending / won / lost).
    """
    query = db.query(Bet)
    if status_filter:
        query = query.filter(Bet.status == status_filter)
    return query.order_by(Bet.placed_at.desc()).all()


@router.patch("/{bet_id}", response_model=BetRead)
def settle_bet(bet_id: int, payload: BetSettle, db: Session = Depends(get_db)):
    """
    Règle un pari : le marque comme gagné (won) ou perdu (lost),
    une fois le match joué.
    """
    bet = db.query(Bet).filter(Bet.id == bet_id).first()
    if not bet:
        raise HTTPException(status_code=404, detail="Bet not found")

    bet.status = payload.status
    db.commit()
    db.refresh(bet)
    return bet


@router.get("/stats")
def get_betting_stats(db: Session = Depends(get_db)):
    """
    Statistiques globales de tes paris : le bilan de ta stratégie.

    Le ROI (Return On Investment) est LE chiffre qui compte :
        ROI = profit total / total misé

    Calculé uniquement sur les paris RÉGLÉS (won/lost),
    pas sur les paris encore en attente.
    """
    all_bets = db.query(Bet).all()

    settled = [b for b in all_bets if b.status in ("won", "lost")]
    pending = [b for b in all_bets if b.status == "pending"]

    total_staked = sum(b.stake for b in settled)
    total_profit = sum(bet_profit(b.stake, b.odds, b.status) for b in settled)

    won_count = sum(1 for b in settled if b.status == "won")

    # ROI en pourcentage. On évite la division par zéro si aucun pari réglé.
    roi_pct = (total_profit / total_staked * 100) if total_staked > 0 else 0.0

    return {
        "total_bets": len(all_bets),
        "settled_bets": len(settled),
        "pending_bets": len(pending),
        "won": won_count,
        "lost": len(settled) - won_count,
        "win_rate_pct": round(won_count / len(settled) * 100, 2) if settled else 0.0,
        "total_staked": round(total_staked, 2),
        "total_profit": round(total_profit, 2),
        "roi_pct": round(roi_pct, 2),
    }