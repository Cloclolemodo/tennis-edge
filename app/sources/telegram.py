"""
Client Telegram — envoie des notifications via un bot Telegram.

Sert à prévenir l'utilisateur quand l'API détecte un value bet.
C'est une couche "source" : elle parle à un service externe (l'API Telegram).
"""
import httpx

from app.core.config import settings


class TelegramError(Exception):
    """Erreur levée quand l'envoi d'un message Telegram échoue."""
    pass


def send_telegram_message(text: str) -> None:
    """
    Envoie un message texte sur la conversation Telegram configurée.

    Utilise le token du bot et le chat ID définis dans le .env.
    Lève TelegramError si l'envoi échoue (token absent, service injoignable...).
    """
    # Garde-fou : sans configuration, on ne tente rien.
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        raise TelegramError(
            "Telegram non configuré (TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID vide)."
        )

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": text,
        "parse_mode": "HTML",  # permet un peu de mise en forme (gras, etc.)
    }

    try:
        response = httpx.post(url, json=payload, timeout=10.0)
    except httpx.RequestError as exc:
        raise TelegramError(f"Service Telegram injoignable : {exc}") from exc

    if response.status_code != 200:
        raise TelegramError(
            f"Telegram a répondu {response.status_code} : {response.text[:200]}"
        )