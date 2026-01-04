# 🚀 Antigravity Trading Bot - Guide Utilisateur

## 🎯 Démarrage Rapide

### Lancement Automatique (Recommandé)

Double-cliquez simplement sur le fichier **`start_trading_app.bat`** dans le dossier racine du projet.

Le script va automatiquement :
1. ✅ Démarrer le bot de trading (dans une fenêtre séparée)
2. ✅ Lancer le dashboard de monitoring (dans votre navigateur)
3. ✅ Ouvrir l'interface web automatiquement

**Aucune validation nécessaire !** Tout est automatique.

---

## 📊 Interface Dashboard - Fonctionnalités

### Navigation Principale

L'interface dispose de **4 menus principaux** accessibles depuis la barre latérale :

#### 1. 📈 Dashboard (Page d'accueil)
**Fonctionnalités actives :**
- ✅ Affichage en temps réel du solde, capital libre, PnL total et taux de réussite
- ✅ Tableau des positions actives avec heure d'entrée
- ✅ Bouton **"📤 Export Positions"** - Exporte les positions au format CSV
- ✅ Bouton **"🔔 Set Alert"** - Configuration des alertes (à venir)
- ✅ Graphique chandelier interactif pour BTC/USDT, ETH/USDT, SOL/USDT
- ✅ Sélecteur de symbole fonctionnel
- ✅ Distribution PnL par actif (graphique circulaire)
- ✅ Flux d'événements récents avec codes couleur

#### 2. 📜 Trade History (Historique des transactions)
**Fonctionnalités actives :**
- ✅ **Filtres avancés** :
  - Filtre par symbole (BTC/USDT, ETH/USDT, etc.)
  - Filtre par côté (achat/vente)
  - Filtre par résultat (Profitable/Perte/Tous)
- ✅ Tableau complet de l'historique
- ✅ Bouton **"📥 Export Trade History"** - Télécharge les données filtrées en CSV

#### 3. 📐 Analytics (Analyses avancées)
**Fonctionnalités actives :**
- ✅ Courbe de PnL cumulée en temps réel
- ✅ **Statistiques détaillées** :
  - Nombre total de trades
  - Trades gagnants/perdants
  - Gain moyen par trade gagnant
  - Perte moyenne par trade perdant
- ✅ **Performance par symbole** :
  - PnL total par crypto
  - Nombre de trades par symbole
  - PnL moyen

#### 4. ⚙️ Settings (Paramètres)
**Fonctionnalités actives :**
- ✅ **Préférences d'affichage** :
  - Sélecteur de thème (Dark/Light)
  - Activation/désactivation des notifications
- ✅ **Gestion des données** :
  - Bouton **"🧹 Clear Cache"** - Vide le cache de l'application
  - Bouton **"📊 Export All Data"** - Lien vers la page d'export
- ✅ **À propos** - Informations sur l'application
- ✅ **Statut système** - Indicateurs de connexion en temps réel

### Contrôles de la Barre Latérale

**Tous les boutons suivants sont fonctionnels :**
- ✅ **Navigation** (4 menus) - Changement de page instantané
- ✅ **Auto Refresh** (checkbox) - Active/désactive le rafraîchissement automatique
- ✅ **Refresh rate** (slider) - Règle l'intervalle de rafraîchissement (2-60 secondes)
- ✅ **🔄 Force Refresh** - Actualise immédiatement les données
- ✅ **🛑 EMERGENCY STOP** - Bouton d'arrêt d'urgence (simulé en mode démo)

---

## 🔧 Structure des Fichiers

```
tradingllm/
├── start_trading_app.bat       ← FICHIER DE LANCEMENT PRINCIPAL
├── scripts/
│   └── live_trade.py            ← Bot de trading
├── src/
│   └── monitoring/
│       ├── dashboard.py         ← Interface Streamlit
│       └── dashboard.css        ← Styles personnalisés
└── data/                        ← Stockage des données de trading
```

---

## 🎮 Utilisation

### Méthode 1 : Lancement automatique (Recommandé)
```
Double-clic sur start_trading_app.bat
```

### Méthode 2 : Lancement manuel (pour développeurs)
```powershell
# Terminal 1 - Bot de trading
$env:PYTHONPATH="."; .\venv\Scripts\python.exe scripts/live_trade.py

# Terminal 2 - Dashboard
$env:PYTHONPATH="."; .\venv\Scripts\python.exe -m streamlit run src/monitoring/dashboard.py
```

---

## ✨ Fonctionnalités Livrées

### ✅ 100% Opérationnel

1. **Lancement automatique** - Un seul clic, pas de validation
2. **Dashboard temps réel** - Mise à jour automatique des données
3. **Tous les boutons fonctionnels** - Export, filtres, navigation
4. **4 menus complets** - Dashboard, Trade History, Analytics, Settings
5. **Contrôles interactifs** - Auto-refresh configurable, emergency stop
6. **Export de données** - CSV pour positions et historique
7. **Filtres avancés** - Par symbole, côté, résultat
8. **Analytics détaillées** - Statistiques et graphiques
9. **Gestion du cache** - Optimisation des performances

### 🎨 Interface Professionnelle

- Design moderne avec thème sombre
- Graphiques interactifs (Plotly)
- Indicateurs de performance en couleur
- Navigation intuitive
- Responsive et optimisé

---

## ☁️ Déploiement 24/7 (100% Gratuit)

### Option Recommandée : GitHub Actions + Supabase

**Avantage** : Aucune carte bancaire requise !

#### 1. Base de données Supabase
1. Créez un compte sur [Supabase](https://supabase.com/) via GitHub
2. Nouveau projet → Nom: `TradingBot`, mot de passe fort (notez-le !)
3. **Settings → Database → Connection String → URI**
4. Copiez l'URL et remplacez `[YOUR-PASSWORD]` par votre mot de passe

#### 2. GitHub Secrets
Dans votre repo : **Settings → Secrets → Actions**

| Secret | Valeur |
|--------|--------|
| `KRAKEN_API_KEY` | Votre clé API Kraken |
| `KRAKEN_SECRET_KEY` | Votre secret Kraken |
| `DATABASE_URL` | L'URL Supabase complète |

#### 3. Activation
Le bot se lance automatiquement via GitHub Actions (`.github/workflows/`).

---

## 📞 Support

Pour toute question ou problème :
1. Vérifiez que le fichier `.env` est configuré correctement
2. Assurez-vous que l'environnement virtuel est activé
3. Consultez les logs dans les fenêtres de terminal

**Fichiers de dépannage** : `TROUBLESHOOTING.md`, `VERIFICATION_CHECKLIST.md`

---

**Version :** 1.1  
**Statut :** Production Ready ✅  
**Dernière mise à jour :** 2026-01-03
