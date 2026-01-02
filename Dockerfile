# Dockerfile pour le Trading Bot
FROM python:3.11-slim-bullseye

# Définir les variables d'environnement
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /app

# Répertoire de travail
WORKDIR /app

# Installer les dépendances système pour TA-Lib et Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    curl \
    git \
    libta-lib-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Installer TA-Lib (source) car le package libta-lib-dev ne suffit pas toujours pour pandas-ta
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib*

# Copier les fichiers de dépendances
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copier le reste du code
COPY . .

# Créer les répertoires nécessaires
RUN mkdir -p data/duckdb logs models/production

# Exposer le port de Streamlit
EXPOSE 8501

# Commande par défaut (sera surchargée par docker-compose)
CMD ["python", "scripts/live_trade.py"]
