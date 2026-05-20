FROM python:3.11-slim

# On évite les fichiers .pyc et on bufferise pas stdout (logs lisibles)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dépendances système minimales (psycopg a besoin de libpq en runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install des deps Python en premier (cache Docker efficace)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Code applicatif
COPY . .

EXPOSE 8000

# En prod, on bascule sur gunicorn + workers. Pour la V1 dev : uvicorn --reload.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
