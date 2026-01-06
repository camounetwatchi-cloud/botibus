# 🤖 Bot de Trading Crypto - Plan de Développement

> **Objectif** : Bot de trading automatisé, efficace, auto-apprenant, pour du swing trading agressif.
> 
> **Dernière mise à jour** : 2026-01-06 | **Version** : 3.2
> **Dernier Audit Technique** : 2026-01-06 ✅

---

## 📊 État Actuel du Projet

| Composant | Statut | Notes |
|-----------|--------|-------|
| **Infrastructure de base** | ✅ Complet | Structure projet, config, dépendances |
| **Trading Engine** | ✅ Opérationnel | `OptimizedTradingBot` en production |
| **Dashboard Monitoring** | ✅ Opérationnel | Streamlit avec 4 pages |
| **Stockage Données** | ✅ Opérationnel | PostgreSQL (Supabase) + DuckDB fallback |
| **GitHub Actions** | ⚠️ Fix en cours | Problème de permissions cache TA-Lib |
| **Gestion des Risques** | ✅ Opérationnel | Stop-loss, take-profit, trailing stop |
| **Frais Trading Réels** | ✅ Opérationnel | Frais margin Kraken: opening, rollover, trading |
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
│       └── trading_bot.yml      ⚠️ Fix cache permissions
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
│   └── strategies/              ✅ SwingStrategy intégrée via Orchestrator
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
- [x] GitHub Actions workflow (fix TA-Lib cache)
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

### Module 9: Auto-Apprentissage & Intelligence Active ✅ PARTIEL
**Objectif** : Transformer le bot statique en agent adaptatif.

- [x] **Performance Analyzer** : Calcul du Win Rate/Ratio par crypto (Derniers 10/50 trades).
- [x] **Dynamic Weights** : Ajustement auto de la confiance (Miser plus sur ce qui marche).
- [x] **Regime Detection** : Identification de l'état du marché (Trend vs Range) via ADX/BB.
- [ ] **Feedback Loop** : Le bot ajuste ses seuils de déclenchement selon ses résultats réels.

### Module 10: Optimisation Financière ("Smart Aggression") ✅ PARTIEL
**Objectif** : Maximiser les gains exponentiels tout en protégeant le capital.

- [x] **Critère de Kelly (Half-Kelly)** : Taille de position basée sur l'espérance mathématique de gain.
- [x] **Pyramiding** : Ajouter à une position gagnante (scale-in) si le trend se confirme + SL Break-even.
- [ ] **Yield Farming** : (Exploratoire) Placer le capital "dormant" en staking flexible (si possible via API).
- [ ] **Smart Re-entry** : Ré-entrer rapidement après une "mèche" de liquidation si le signal reste valide.

---

## 🎯 Priorités Stratégiques (Revisées)

### 🔴 Priorité Immédiate : Le "Cerveau Financier"
**Pourquoi ?** Pour qu'il arrête de trader "bêtement" et commence à gérer le capital comme un pro.

1. **Fix GitHub Actions** (TA-Lib Cache)
   - Fichier : `.github/workflows/trading_bot.yml`
   - Action : Installer TA-Lib localement pour éviter les erreurs de permission.

2. **Implémenter `RiskManager` 2.0 (Kelly + Pyramiding)**
   - Fichiers : `src/trading/risk_manager.py`
   - Action : Remplacer sizing statique par dynamique.

3. **Créer le module `ActiveLearning`**
   - Fichiers : `src/learning/performance.py`
   - Action : Feedback loop qui lit la DB et update les configs.

4. **Backtesting Rapide**
   - Fichiers : `src/backtest/simple_runner.py`
   - Action : Valider que le Kelly Criterion n'est pas trop agressif.

### 🟡 Priorité Secondaire : Raffinement
5. **Alertes Telegram Interactives** (pour valider les décisions "agressives" en temps réel).
6. **Amélioration du Dashboard** (Voir les métriques d'apprentissage : "Je suis confiant sur SOL, méfiant sur XRP").

---

## 📋 Roadmap Technique

### Phase 1 : Maintenance et Stabilité (Aujourd'hui)
- [/] Réparer le cache TA-Lib dans GitHub Actions.
- [x] Coder `SafetyChecks` pour le pyramiding (éviter le sur-levier).
- [x] Intégrer la formule de Kelly dans `calculate_position_size`.
- [x] Activer le "Breakeven Stop" automatique pour les positions pyramidées.

### Phase 2 : Conscience de Soi (Semaine pro)
- [ ] Le bot doit savoir : "Je suis en Drawdown de 5%, je réduis mon risque de moitié".
- [ ] Le bot doit savoir : "Le marché est en range, je désactive les stratégies de breakout".

---

## 🛡️ Règle d'Or (Le Credo du Bot)
> "Je suis agressif quand je gagne, paranoïaque quand je perds."
> - Si un asset performe ➡️ J'augmente l'exposition (Pyramide).
> - Si un asset sous-performe ➡️ Je le blackliste temporairement (Cooldown dynamique).

---

## 📚 Commandes Utiles
Same as before...
```powershell
.\start_trading_app.bat
```
---
*Plan mis à jour le 2026-01-06 - Version "Directeur Financier AI"*