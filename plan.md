# 🤖 Bot de Trading Crypto - Plan de Développement

> **Objectif** : Bot de trading automatisé, efficace, auto-apprenant, pour du swing trading agressif.
> 
> **Dernière mise à jour** : 2026-01-07 | **Version** : 4.0 (ML Ready)
> **Dernier Audit Technique** : 2026-01-07 ✅

---

## 📊 État Actuel du Projet

| Composant | Statut | Notes |
|-----------|--------|-------|
| **Infrastructure** | ✅ Complet | Structure, Config, Logging, **Async I/O** |
| **Trading Engine** | ✅ Opérationnel | **Optimisé (Non-blocking)**, Cycle 'Fresh Data' |
| **Dashboard** | ✅ Opérationnel | Streamlit, Métriques Live, Sync Supabase |
| **Stockage Données** | ✅ Opérationnel | Postgres + DuckDB (Async writes) |
| **Gestion Risques** | ✅ Avancé | **Kelly Criterion + Pyramiding + Breakeven** |
| **Signaux ML** | ✅ Complet | XGBoost pipeline prêt (train_model.py) |
| **GitHub Actions** | ✅ Opérationnel | **Cron 5min (Public Repo)** |
| **Backtesting** | ✅ Complet | VectorBT + engine.py (550 lignes) |
| **Apprentissage** | ✅ Complet | AutoLearner + Blacklist + Confidence Adj |

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

## 📁 Structure du Projet (Mise à jour)

```
tradingllm/
├── scripts/
│   ├── live_trade.py            ✅ Bot Optimisé (Async/Non-blocking)
│   ├── check_positions.py       ✅ Diagnostic fiable
│   └── ...
├── src/
│   ├── data/
│   │   ├── collector.py         ✅ Collecte Optimisée (Limit=50)
│   │   └── storage.py           ✅ Writes Async (Thread-safe)
│   ├── trading/
│   │   ├── executor.py          ✅ Async Execution (Zero-blocking)
│   │   └── risk_manager.py      ✅ Kelly + Pyramiding Logic
│   └── ...
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

### Module 1-3 : Core & Data ✅ COMPLET
- [x] Infrastructure Async
- [x] Stockage Non-bloquant
- [x] Collecte Optimisée

### Module 4 : Signaux & ML ✅ COMPLET
- [x] Structure SignalGenerator
- [x] Score Heuristique (Pattern Recognition)
- [x] **Pipeline XGBoost (train_model.py)**
- [x] **Intégration modèle automatique**
- [ ] Modèle RL (Futur optionnel)

### Module 5 : Risk Management 2.0 ✅ COMPLET
- [x] Critère de Kelly (Position Sizing)
- [x] Pyramiding (Scale-in winners)
- [x] Stop-Loss Breakeven automatique
- [x] Checks de volatilité (ATR)

### Module 6-7 : Exécution & Monitoring ✅ COMPLET
- [x] Trading Live/Paper sans latence
- [x] Dashboard Temps Réel
- [x] Fix "Stale Data" (SL vérifié sur prix frais)

### Module 8 : Backtesting ✅ COMPLET
- [x] Engine VectorBT (550 lignes)
- [x] Validation stratégies sur historique
- [x] Stress-tests (crash_2022, rally_2021)
- [x] Rapports HTML auto-générés

### Module 9 : Auto-Apprentissage ✅ COMPLET
- [x] AutoLearner (analyse quotidienne)
- [x] Blacklist dynamique par symbole
- [x] Ajustement confiance basé historique
- [x] Alertes Telegram intégrées

---

## 🎯 Priorités Stratégiques (Mise à jour 2026-01-07)

### ✅ COMPLÉTÉ

1.  **Training ML (XGBoost)** ✅
    *   `scripts/train_model.py` (420 lignes)
    *   Pipeline complet: fetch → features → labeling → Optuna → model
    *   Intégration automatique dans `SignalGenerator`

2.  **Backtesting & Validation** ✅
    *   `src/backtest/engine.py` (550 lignes)
    *   Stress-tests: crash_2022, rally_2021, sideways_2023
    *   Rapports HTML avec métriques complètes

3.  **Boucle d'Auto-Amélioration** ✅
    *   `src/learning/auto_learner.py` (300 lignes)
    *   Blacklist dynamique + Confidence adjustment

4.  **Alertes Telegram** ✅
    *   `src/monitoring/telegram_notifier.py` (240 lignes)

### 🟡 Prochaines Étapes
5.  **Entraîner le modèle**: `python scripts/train_model.py`
6.  **Valider par backtest**: `python scripts/run_backtest.py --period 6m`
7.  **Déployer en production**

---

## 📋 Roadmap Technique

### Phase 1 : Fiabilisation & Socle ✅
- [x] Fix Blocking I/O (Database & API)
- [x] Fix "Stale Data" logic (Check SL sur prix frais)
- [x] Implémentation Kelly & Pyramiding
- [x] Optimisation bande passante (Limit 50)

### Phase 2 : Construction du Cerveau ✅
- [x] **Data Pipeline** : train_model.py (fetch + features)
- [x] **Training** : XGBoost avec Optuna
- [x] **Backtest** : engine.py + run_backtest.py
- [x] **Auto-Learning** : auto_learner.py

### Phase 3 : Production 🟡 En cours
- [x] Alertes Telegram
- [ ] Entraîner le modèle sur 6 mois
- [ ] Paper trading 48h
- [ ] Déploiement live

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