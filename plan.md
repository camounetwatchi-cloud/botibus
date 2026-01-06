# 🤖 Bot de Trading Crypto - Plan de Développement

> **Objectif** : Bot de trading automatisé, efficace, auto-apprenant, pour du swing trading agressif.
> 
> **Dernière mise à jour** : 2026-01-06 | **Version** : 3.1
> **Dernier Audit Technique** : 2026-01-06 ✅

---

## 📊 État Actuel du Projet

| Composant | Statut | Notes |
|-----------|--------|-------|
| **Infrastructure de base** | ✅ Complet | Structure projet, config, dépendances |
| **Trading Engine** | ✅ Opérationnel | `OptimizedTradingBot` en production |
| **Dashboard Monitoring** | ✅ Opérationnel | Streamlit avec 4 pages |
| **Stockage Données** | ✅ Opérationnel | PostgreSQL (Supabase) + DuckDB fallback |
| **GitHub Actions** | ✅ Opérationnel | Exécution toutes les 15 minutes |
| **Gestion des Risques** | ✅ Opérationnel | Stop-loss, take-profit, trailing stop |
| **Signaux ML** | ⚠️ Partiellement | Heuristiques actives, ML réel à implémenter |
| **Backtesting** | ❌ Non implémenté | VectorBT prévu |
| **Auto-apprentissage** | ❌ Non implémenté | Ré-entraînement automatique prévu |

---

## 🏗️ Architecture Actuelle

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TRADING BOT ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │ DATA         │───▶│ FEATURE      │───▶│ SIGNAL       │              │
│  │ COLLECTOR    │    │ ENGINEERING  │    │ GENERATOR    │              │
│  │              │    │              │    │              │              │
│  │ • CCXT       │    │ • pandas-ta  │    │ • Heuristic  │              │
│  │ • Kraken API │    │ • Technical  │    │ • XGBoost    │              │
│  │              │    │   Indicators │    │   (future)   │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│         │                   │                   │                       │
│         ▼                   ▼                   ▼                       │
│  ┌──────────────────────────────────────────────────────┐              │
│  │                    DATA STORAGE                       │              │
│  │  PostgreSQL (Supabase) + DuckDB (fallback local)     │              │
│  └──────────────────────────────────────────────────────┘              │
│         │                                                               │
│         ▼                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │ RISK         │───▶│ TRADE        │───▶│ GITHUB       │              │
│  │ MANAGER      │    │ EXECUTOR     │    │ ACTIONS      │              │
│  │              │    │              │    │              │              │
│  │ • Position   │    │ • Paper Mode │    │ • Cron 15min │              │
│  │   Sizing     │    │ • Live Mode  │    │ • 24/7       │              │
│  │ • SL/TP      │    │ • Kraken     │    │ • Auto-deploy│              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│         │                   │                   │                       │
│         └───────────────────┴───────────────────┘                       │
│                             │                                           │
│                             ▼                                           │
│  ┌──────────────────────────────────────────────────────┐              │
│  │                    MONITORING                         │              │
│  │           Streamlit Dashboard (4 pages)               │              │
│  │  • Dashboard • Trade History • Analytics • Settings   │              │
│  └──────────────────────────────────────────────────────┘              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Structure du Projet (Implémentée)

```
tradingllm/
├── .github/
│   └── workflows/
│       └── trading_bot.yml      ✅ Workflow GitHub Actions
│
├── scripts/
│   ├── live_trade.py            ✅ Bot principal (OptimizedTradingBot)
│   ├── gh_actions_trade.py      ✅ Script pour GitHub Actions
│   ├── check_positions.py       ✅ Diagnostic des positions
│   ├── check_status.py          ✅ Vérification statut bot
│   ├── full_diagnostic.py       ✅ Diagnostic complet
│   ├── get_top_cryptos.py       ✅ Récupération top cryptos
│   ├── reset_session.py         ✅ Reset session trading
│   └── verify_kraken.py         ✅ Test API Kraken
│
├── src/
│   ├── config/
│   │   └── settings.py          ✅ Configuration centralisée
│   │
│   ├── data/
│   │   ├── collector.py         ✅ Collecte données CCXT
│   │   └── storage.py           ✅ PostgreSQL + DuckDB
│   │
│   ├── features/
│   │   └── technical.py         ✅ Indicateurs techniques (pandas-ta)
│   │
│   ├── ml/
│   │   └── signal_generator.py  ✅ Génération signaux (heuristique)
│   │
│   ├── trading/
│   │   ├── executor.py          ✅ Exécution ordres CCXT
│   │   └── risk_manager.py      ✅ Gestion risques complète
│   │
│   ├── monitoring/
│   │   ├── dashboard.py         ✅ Dashboard Streamlit
│   │   └── dashboard.css        ✅ Styling personnalisé
│   │
│   └── strategies/              ⚠️ Prévu mais non utilisé
│
├── tests/
│   ├── test_risk_manager.py     ✅ Tests Risk Manager
│   ├── verify_dashboard_logic.py ✅ Tests Dashboard
│   └── debug_storage_repro.py   ✅ Debug Storage
│
├── data/                         ✅ Stockage local DuckDB
├── logs/                         ✅ Logs rotatifs
│
├── start_trading_app.bat        ✅ Lanceur Windows
├── start_trading_app.ps1        ✅ Lanceur PowerShell
├── requirements.txt             ✅ Dépendances Python
├── pyproject.toml               ✅ Config projet
├── .env.example                 ✅ Template variables env
├── README.md                    ✅ Documentation utilisateur
├── GUIDE_UTILISATEUR.md         ✅ Guide complet
├── TROUBLESHOOTING.md           ✅ Guide dépannage
└── VERIFICATION_CHECKLIST.md    ✅ Checklist vérification
```

---

## ⚙️ Configuration Actuelle

### Paramètres de Trading (settings.py)

| Paramètre | Valeur | Description |
|-----------|--------|-------------|
| `MAX_POSITION_PERCENT` | 10% | Max par position |
| `MIN_TRADE_VALUE` | 10€ | Minimum par trade |
| `RISK_PER_TRADE` | 1.5% | Risque par trade |
| `DEFAULT_STOP_LOSS` | 2.5% | Stop-loss par défaut |
| `DEFAULT_TAKE_PROFIT` | 4.5% | Take-profit de base |
| `MAX_OPEN_POSITIONS` | 30 | Positions simultanées (paper) |
| `MAX_OPEN_POSITIONS_LIVE` | 15 | Positions simultanées (live) |
| `COOLDOWN_MINUTES` | 1 min | Délai entre trades même symbole |
| `TRAILING_STOP_ACTIVATION` | +2% | Activation trailing stop |
| `TRAILING_STOP_DISTANCE` | 1% | Distance trailing stop |
| `MIN_SIGNAL_CONFIDENCE` | 20% | Seuil signal minimum |
| `TRADING_CYCLE_SECONDS` | 15s | Fréquence analyse |

### Cryptomonnaies Monitorées (Kraken EUR)

```python
SYMBOLS = [
    "BTC/EUR",   # Bitcoin
    "ETH/EUR",   # Ethereum
    "SOL/EUR",   # Solana
    "XRP/EUR",   # Ripple
    "BNB/EUR",   # Binance Coin
    "ADA/EUR",   # Cardano
    "DOGE/EUR",  # Dogecoin
    "AVAX/EUR",  # Avalanche
    "LINK/EUR",  # Chainlink
    "DOT/EUR",   # Polkadot
]
```

---

## 📈 Progression des Modules

### Module 1 : Infrastructure ✅ COMPLET

- [x] Structure projet Python
- [x] Configuration centralisée (pydantic-settings)
- [x] Gestion environnement (.env)
- [x] Logging avec rotation (loguru)
- [x] GitHub Actions workflow (cron 15min)
- [x] Scripts de lancement Windows (.bat, .ps1)

### Module 2 : Collecte de Données ✅ COMPLET

- [x] Intégration CCXT pour Kraken
- [x] Collecte OHLCV multi-timeframes
- [x] Stockage PostgreSQL (Supabase cloud)
- [x] Fallback automatique DuckDB (local)
- [x] Gestion des cooldowns persistante
- [x] Heartbeat status bot

### Module 3 : Feature Engineering ✅ COMPLET

- [x] Indicateurs de tendance (SMA, EMA, MACD, ADX)
- [x] Indicateurs momentum (RSI, Stochastic, Williams %R)
- [x] Indicateurs volatilité (Bollinger Bands, ATR, Keltner)
- [x] Indicateurs volume (OBV, VWAP, Volume Ratio)
- [x] Features custom (momentum, volatilité relative)
- [ ] Features multi-timeframe (prévu, non utilisé)

### Module 4 : Génération de Signaux ⚠️ PARTIELLEMENT COMPLET

- [x] Architecture SignalGenerator
- [x] Score technique basé sur indicateurs
- [x] Score heuristique ML-like (pattern recognition)
- [x] Score volume/momentum
- [x] Agrégation pondérée (40% tech + 40% ML + 20% vol)
- [ ] **Modèle XGBoost réel** ❌ Non entraîné
- [ ] **Modèle RL (PPO/SAC)** ❌ Non implémenté
- [ ] **Ensemble de modèles** ❌ Non implémenté

### Module 5 : Gestion des Risques ✅ COMPLET

- [x] Position sizing dynamique
- [x] Multiplicateurs selon confidence
- [x] Stop-loss fixe et trailing
- [x] Take-profit dynamique (basé ATR)
- [x] Limite positions simultanées
- [x] Limite perte journalière
- [x] Cooldown par symbole
- [x] Suivi drawdown

### Module 6 : Exécution Trades ✅ COMPLET

- [x] Mode Paper Trading
- [x] Mode Live Trading (Kraken)
- [x] Exécution via CCXT
- [x] Logging détaillé des trades
- [x] Gestion fermeture positions (SL/TP/Trailing)
- [x] Cycle trading async parallélisé

### Module 7 : Monitoring ✅ COMPLET

- [x] Dashboard Streamlit (4 pages)
- [x] Métriques temps réel
- [x] Graphiques Plotly
- [x] Export CSV
- [x] Filtres avancés
- [x] Bot start/stop depuis UI
- [x] Auto-refresh configurable
- [ ] **Alertes Telegram** ❌ Non implémenté

### Module 8 : Backtesting ❌ NON IMPLÉMENTÉ

- [ ] VectorBT wrapper
- [ ] Walk-forward validation
- [ ] Métriques (Sharpe, Sortino, Calmar)
- [ ] Rapports automatisés

### Module 9 : Auto-Apprentissage ❌ NON IMPLÉMENTÉ

- [ ] Pipeline ré-entraînement
- [ ] Évaluation automatique performance
- [ ] A/B testing modèles
- [ ] Model versioning
- [ ] Rollback automatique

---

## 🎯 Axes d'Amélioration Prioritaires

### 🔴 Priorité Haute

#### 1. Implémentation ML Réel
**État** : Le bot utilise actuellement des heuristiques pour simuler le ML.

**Actions requises** :
- [ ] Collecter historique trades pour dataset
- [ ] Entraîner XGBoost avec features techniques
- [ ] Implémenter évaluation walk-forward
- [ ] Comparer performance heuristique vs ML
- [ ] Déployer modèle si meilleur

**Fichiers concernés** :
- `src/ml/signal_generator.py` - Intégrer vrai modèle
- `src/ml/models/xgb_model.py` - À créer
- `scripts/train_model.py` - À créer

#### 2. Backtesting Framework
**État** : Aucun backtesting disponible.

**Actions requises** :
- [ ] Installer et configurer VectorBT
- [ ] Créer wrapper pour stratégie actuelle
- [ ] Implémenter walk-forward validation
- [ ] Générer rapports métriques
- [ ] Valider avant passage live

**Fichiers concernés** :
- `src/backtest/engine.py` - À créer
- `src/backtest/metrics.py` - À créer
- `scripts/run_backtest.py` - À créer

#### 3. Alertes Telegram
**État** : Configuration prévue mais non implémentée.

**Actions requises** :
- [ ] Créer bot Telegram
- [ ] Implémenter envoi alertes
- [ ] Notifications pour: trades, daily summary, erreurs
- [ ] Commandes: /status, /balance, /positions

**Fichiers concernés** :
- `src/monitoring/telegram_bot.py` - À créer

### 🟡 Priorité Moyenne

#### 4. Optimisation Performance Bot
**État** : Améliorations appliquées le 2026-01-06.

**Actions réalisées** :
- [x] Retry avec backoff exponentiel (collector.py)
- [x] Cache TA-Lib sur GitHub Actions
- [x] Timeout explicite workflow (10 min)
- [ ] Cache mémoire pour indicateurs
- [ ] Monitoring temps d'exécution

#### 5. Analyse Post-Trade
**État** : Données collectées mais non analysées.

**Actions possibles** :
- [ ] Analyse win/loss par heure, jour, symbole
- [ ] Identification patterns gagnants
- [ ] Détection drift performance
- [ ] Recommandations automatiques

#### 6. Multi-Exchange Support
**État** : Kraken uniquement.

**Actions possibles** :
- [ ] Ajouter Binance
- [ ] Ajouter Bybit
- [ ] Arbitrage cross-exchange

### 🟢 Priorité Basse

#### 7. Interface Mobile
- [ ] Version responsive dashboard
- [ ] App mobile (React Native)

#### 8. Stratégies Multiples
- [ ] Framework stratégie pluggable
- [ ] Stratégie mean-reversion
- [ ] Stratégie breakout

---

## 📋 Prochaines Étapes Recommandées

### Court Terme (1-2 semaines)
1. **Collecter plus de données de trades** pour analyse
2. **Implémenter alertes Telegram** pour monitoring à distance
3. **Ajouter métriques dashboard** : temps en position, ratio gain/perte

### Moyen Terme (3-4 semaines)
1. **Implémenter backtesting VectorBT**
2. **Entraîner premier modèle XGBoost**
3. **Comparer ML vs heuristiques en paper trading**

### Long Terme (2+ mois)
1. **Auto-apprentissage continu**
2. **Multi-exchange**
3. **Stratégies additionnelles**

---

## 🛡️ Points de Vigilance

> [!CAUTION]
> **Risques Financiers**
> - Le trading crypto comporte des risques de perte significatifs
> - Ne jamais investir plus que ce que vous pouvez perdre
> - Performances passées ≠ résultats futurs

> [!WARNING]
> **Avant Passage Live**
> - Minimum 1 mois paper trading profitable
> - Sharpe ratio > 1.0
> - Drawdown max < 15%
> - Backtesting validé

> [!IMPORTANT]
> **Sécurité API Keys**
> - Jamais commit dans Git
> - Permissions minimales (trade only, no withdraw)
> - IP whitelist activée sur exchange
> - Secrets GitHub configurés

---

## 📚 Commandes Utiles

### Lancement Local
```powershell
# Lancement complet (bot + dashboard)
.\start_trading_app.bat

# Dashboard seul
streamlit run src\monitoring\dashboard.py

# Bot seul
python scripts\live_trade.py
```

### Diagnostics
```powershell
# Vérifier positions
python scripts\check_positions.py

# Status complet
python scripts\check_status.py

# Diagnostic full
python scripts\full_diagnostic.py

# Test API Kraken
python scripts\verify_kraken.py
```

### GitHub Actions
```bash
# Voir workflows récents
gh run list --workflow=trading_bot.yml

# Voir logs d'un run
gh run view <run-id> --log

# Déclencher manuellement
gh workflow run trading_bot.yml
```

---

## 📊 Métriques de Suivi

| Métrique | Objectif | Actuel |
|----------|----------|--------|
| Uptime GitHub Actions | >99% | À mesurer |
| Trades/jour | >5 | À mesurer |
| Win Rate | >50% | À mesurer |
| Sharpe Ratio (paper) | >1.0 | À mesurer |
| Max Drawdown | <15% | À mesurer |
| Temps moyen en position | 1-48h | À mesurer |

---

*Plan restructuré le 2026-01-06 - Version 3.0 (Suivi précis de l'état d'implémentation)*