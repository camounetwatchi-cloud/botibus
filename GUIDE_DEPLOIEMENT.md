## 🥇 Option RECOMMANDÉE (Sans Carte Bancaire) : GitHub Actions + Supabase
C'est la solution la plus simple, 100% gratuite, et qui ne demande aucune vérification de carte.

### 1. Création de la Base de Données (Supabase)
- Allez sur [Supabase](https://supabase.com/) et créez un compte (via GitHub/Email, pas de carte).
- Créez un nouveau projet "Trading Bot".
- Dans **Project Settings > Database**, récupérez votre **Connection String** (en mode `URI`). Elle ressemble à : `postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres`.

### 2. Configuration sur GitHub
- Allez dans les paramètres de votre repository GitHub (**Settings > Secrets and variables > Actions**).
- Ajoutez les "Repository secrets" suivants :
    - `BINANCE_API_KEY` : Votre clé API Binance.
    - `BINANCE_SECRET_KEY` : Votre secret API Binance.
    - `DATABASE_URL` : L'URI récupérée sur Supabase.
    - `TELEGRAM_BOT_TOKEN` : (Optionnel) Pour les alertes.
    - `TELEGRAM_CHAT_ID` : (Optionnel).

### 3. Activation
- Le bot tournera automatiquement toutes les heures grâce au fichier `.github/workflows/trading_bot.yml` que j'ai créé.
- Vous pouvez aussi le lancer manuellement dans l'onglet **Actions** de GitHub.

---

## 🥈 Option 2 : Serveur Dédié (Oracle Cloud Free Tier)
Oracle propose un niveau gratuit "à vie" très puissant, mais **exige une carte bancaire** pour la vérification.

### 1. Création du compte
- Allez sur [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/).
- Inscrivez-vous (nécessite une carte bancaire pour vérification d'identité, mais rien ne sera débité).
- Choisissez une région proche de vous ou de l'exchange (ex: `Frankfurt` ou `London` pour Binance).

### 2. Création de l'instance (Serveur)
- Choisissez une instance **Ampere (ARM)**.
- Configuration recommandée : **4 OCPUs** et **24 Go de RAM**.
- Téléchargez la clé SSH (indispensable pour vous connecter).
- Dans le réseau, ouvrez le port **8501** (Ingress Rule) pour voir votre Dashboard Streamlit.

---

## ☁️ Alternatives (Gratuites 1 an)
Si Oracle n'est pas disponible dans votre région :
1. **AWS Free Tier** : Instance `t3.micro` gratuite pendant 12 mois.
2. **Google Cloud** : Instance `e2-micro` gratuite à vie (mais très faible en RAM).

---

## 🛠️ Installation sur le serveur
Une fois connecté en SSH à votre serveur :

```bash
# 1. Mise à jour du système
sudo apt update && sudo apt upgrade -y

# 2. Installation de Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 3. Cloner votre projet (ou le transférer via SCP/SFTP)
git clone <votre_repo> tradingllm
cd tradingllm

# 4. Configurer vos clés API
cp .env.example .env
nano .env  # Remplissez vos clés BINANCE_API_KEY, etc.

# 5. Lancer le bot et le dashboard
sudo docker-compose up -d --build
```

---

## 📊 Accès au Dashboard
Une fois lancé, votre dashboard sera disponible sur :
`http://<IP_DU_SERVEUR>:8501`

---

## 💡 Conseils de Pro
- **Logs** : Surveillez les logs avec `sudo docker-compose logs -f trading-bot`.
- **Auto-restart** : Docker est configuré pour relancer le bot automatiquement si le serveur redémarre.
- **Sécurité** : Ne donnez jamais vos accès SSH ou vos fichiers `.env` à personne.
