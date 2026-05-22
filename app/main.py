"""
Tennis Edge API — entry point.

Démarre l'application FastAPI et expose les routes.
"""
from fastapi import FastAPI
from app.api import health, players, matches, bets
from app.core.config import settings

app = FastAPI(
    title="Tennis Edge API",
    description="API d'analyse de matchs de tennis avec détection de value bets (Elo + Kelly).",
    version="0.1.0",
)

# Routes
app.include_router(health.router, tags=["health"])
app.include_router(players.router, prefix="/players", tags=["players"])
app.include_router(matches.router, prefix="/matches", tags=["matches"])
app.include_router(bets.router, prefix="/bets", tags=["bets"])


@app.get("/")
def root():
    return {
        "name": "Tennis Edge API",
        "version": "0.1.0",
        "docs": "/docs",
        "environment": settings.environment,
    }