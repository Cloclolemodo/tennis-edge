"""
Configuration SQLAlchemy : engine, session, base déclarative.

`get_db` est une dépendance FastAPI qui fournit une session par requête
et la ferme proprement à la fin.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # évite les connexions mortes après inactivité
    echo=settings.debug,  # log les SQL en dev
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base déclarative pour tous les modèles SQLAlchemy."""
    pass


def get_db():
    """Dépendance FastAPI : une session DB par requête."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
