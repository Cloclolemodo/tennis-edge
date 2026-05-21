"""
Script d'import des matchs ATP depuis un CSV (format Jeff Sackmann).

Ce script :
  1. lit le CSV des matchs
  2. crée les joueurs manquants dans la base
  3. crée chaque match et rejoue le résultat dans le moteur Elo
     -> les ratings se calibrent dans l'ordre chronologique

USAGE (depuis le conteneur) :
    docker-compose exec api python -m app.scripts.import_matches

MÉTHODE PRUDENTE : la constante LIMITE permet de tester sur un petit
échantillon avant de lancer sur tout le fichier.
  - LIMITE = 20    -> importe seulement 20 matchs (pour tester)
  - LIMITE = None  -> importe tout le fichier
"""
import csv
from datetime import datetime

from app.db.session import SessionLocal
from app.db.models import Player, Match
from app.services.elo import update_ratings
from app.core.config import settings

# --- Réglage : mets 20 pour tester, None pour tout importer ---
LIMITE = None

CSV_PATH = "data/atp_matches_2024.csv"


def get_or_create_player(db, name: str, country: str | None) -> Player:
    """Renvoie le joueur s'il existe déjà, sinon le crée."""
    player = db.query(Player).filter(Player.full_name == name).first()
    if player:
        return player
    player = Player(
        full_name=name,
        country=country if country else None,
        gender="M",  # fichier ATP = tennis masculin
        current_elo=settings.elo_initial_rating,
    )
    db.add(player)
    db.flush()  # pour obtenir son id sans commit complet
    return player


def parse_date(raw: str) -> datetime:
    """Le format Sackmann est AAAAMMJJ, ex : 20240115."""
    return datetime.strptime(raw, "%Y%m%d")


def run_import():
    db = SessionLocal()
    players_created_before = db.query(Player).count()
    matches_imported = 0

    try:
        with open(CSV_PATH, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for i, row in enumerate(reader):
                # Garde-fou échantillon : on s'arrête à LIMITE.
                if LIMITE is not None and i >= LIMITE:
                    break

                # Certaines lignes peuvent être incomplètes : on les saute.
                if not row.get("winner_name") or not row.get("loser_name"):
                    continue

                winner = get_or_create_player(
                    db, row["winner_name"], row.get("winner_ioc")
                )
                loser = get_or_create_player(
                    db, row["loser_name"], row.get("loser_ioc")
                )

                # Création du match (déjà terminé : statut "completed").
                match = Match(
                    player1_id=winner.id,
                    player2_id=loser.id,
                    winner_id=winner.id,
                    match_date=parse_date(row["tourney_date"]),
                    tournament=row.get("tourney_name", "Inconnu"),
                    surface=(row.get("surface") or "hard").lower(),
                    status="completed",
                    score=row.get("score"),
                )
                db.add(match)

                # On rejoue le résultat dans le moteur Elo.
                new_w, new_l = update_ratings(
                    rating_winner=winner.current_elo,
                    rating_loser=loser.current_elo,
                    k_factor=settings.elo_k_factor,
                )
                winner.current_elo = new_w
                loser.current_elo = new_l
                winner.matches_played += 1
                loser.matches_played += 1

                matches_imported += 1

        db.commit()

        # --- Résumé ---
        players_total = db.query(Player).count()
        print("=" * 50)
        print(f"Import terminé.")
        print(f"  Matchs importés     : {matches_imported}")
        print(f"  Joueurs créés       : {players_total - players_created_before}")
        print(f"  Joueurs en base     : {players_total}")
        print()
        print("Top 10 Elo après import :")
        top = (
            db.query(Player)
            .order_by(Player.current_elo.desc())
            .limit(10)
            .all()
        )
        for rank, p in enumerate(top, start=1):
            print(f"  {rank:2}. {p.full_name:25} Elo {p.current_elo:7.1f}  ({p.matches_played} matchs)")
        print("=" * 50)

    except Exception as exc:
        db.rollback()
        print(f"ERREUR pendant l'import : {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_import()