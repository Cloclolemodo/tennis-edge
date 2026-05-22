"""
Configuration centralisée — lue depuis les variables d'environnement.

Suit le principe 12-factor : pas de secrets en dur, tout vient de .env ou
des variables d'env de l'hébergeur (Railway, Fly.io, etc.).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Environnement
    environment: str = "development"  # development | production
    debug: bool = True

    # Base de données
    database_url: str = "postgresql+psycopg://tennis:tennis@db:5432/tennis_edge"

    # Sources externes (à remplir dans .env, jamais commiter)
    api_sports_key: str = ""
    odds_api_key: str = ""

    # Notifications Telegram (à remplir dans .env, jamais commiter)
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Paramètres métier
    elo_initial_rating: float = 1500.0
    elo_k_factor: float = 32.0
    value_bet_min_edge: float = 0.05  # 5% minimum pour flagger un value bet
    kelly_fraction: float = 0.25       # 1/4 Kelly (prudent)


settings = Settings()