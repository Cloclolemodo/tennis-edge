# Tennis Edge API

API d'analyse de matchs de tennis avec détection de **value bets**, basée sur le système de classement Elo et le critère de Kelly fractionné.

> ⚠️ **Disclaimer** : ce projet est un outil d'analyse, pas un oracle. L'espérance de gain réaliste d'un parieur amateur, même avec un bon modèle, tourne autour de 0 à +2% de ROI sur le long terme, avec une variance importante. À utiliser avec discipline de bankroll.

## Stack

- **API** : FastAPI (Python 3.11)
- **DB** : PostgreSQL 16 + SQLAlchemy 2 + Alembic
- **Conteneurisation** : Docker + docker-compose
- **Tests** : pytest

## Structure du projet

```
tennis-edge/
├── app/
│   ├── api/         # Routes FastAPI (health, players, ...)
│   ├── services/    # Logique métier (Elo, value bet, Kelly)
│   ├── adapters/    # Abstraction multi-sports (Tennis V1, Football V2)
│   ├── sources/     # Clients externes (api-sports, The Odds API)
│   ├── db/          # Modèles SQLAlchemy + session
│   └── core/        # Config, settings
├── alembic/         # Migrations DB
├── tests/           # Tests pytest
├── Dockerfile
└── docker-compose.yml
```

## Démarrage rapide

### 1. Cloner et configurer

```bash
cp .env.example .env
# Édite .env si tu as déjà tes clés API (pas obligatoire pour démarrer)
```

### 2. Lancer avec Docker

```bash
docker-compose up --build
```

L'API est dispo sur **http://localhost:8000** et la doc Swagger sur **http://localhost:8000/docs**.

### 3. Créer la première migration

Dans un autre terminal, une fois les containers démarrés :

```bash
docker-compose exec api alembic revision --autogenerate -m "create players table"
docker-compose exec api alembic upgrade head
```

### 4. Tester

```bash
# Créer un joueur
curl -X POST http://localhost:8000/players \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Jannik Sinner", "country": "ITA", "gender": "M"}'

# Lister
curl http://localhost:8000/players
```

## Roadmap

- ✅ **V1.0** — Squelette : structure, DB, endpoints CRUD joueurs
- 🔜 **V1.1** — Modèles Match, Rating, Bet
- 🔜 **V1.2** — Moteur Elo (calcul + batch sur historique)
- 🔜 **V1.3** — Intégration api-sports.io + The Odds API
- 🔜 **V1.4** — Endpoint /matches/analyze (edge + Kelly)
- 🔮 **V2** — Elo par surface, K-factor dynamique, foot

## Notes pédagogiques

### Pourquoi Elo ?
Système éprouvé depuis 1960, simple, auto-correctif, marche bien au tennis (1v1, beaucoup de matchs/an, pas de nul). Limites : aveugle au contexte (motivation, blessures naissantes), réagit lentement aux changements brusques.

### Pourquoi Kelly fractionné (1/4) ?
Kelly "plein" maximise la croissance théorique du bankroll, mais a une variance énorme : un drawdown de -50% est attendu en cours de route. 1/4 Kelly garde 75% de la croissance espérée avec une variance bien plus supportable.

### Pourquoi ne pas espérer battre les bookmakers ?
Les bookmakers ont des modèles entraînés sur des millions de matchs, ajustés en temps réel par les flux d'argent. Leur marge intégrée est de 4-7%. Pour gagner, ton modèle doit être mieux calibré qu'eux d'au moins 5-8%, ce qui est très difficile. Les inefficacités exploitables se trouvent sur les tournois mineurs (ITF, Challenger) où les bookmakers grand public sont moins réactifs.
