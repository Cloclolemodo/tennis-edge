"""
Endpoint /health — utilisé par Railway/Fly.io et les load balancers
pour vérifier que l'API est vivante.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)):
    """
    Vérifie :
    - que l'API répond
    - que la connexion DB fonctionne
    """
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
    }
