# 🤖 Bot de Trading Crypto - Swing Trading avec Auto-Apprentissage ML

> **Objectif** : Bot de trading gratuit, efficace, auto-apprenant, pour du swing trading (positions de quelques heures à quelques jours).

---

## 📋 Résumé Exécutif

| Critère | Décision |
|---------|----------|
| **Type de trading** | Swing Trading (1h - 7 jours) |
| **Coût** | 100% Gratuit (infrastructure locale) |
| **Langage principal** | Python (simplicité + écosystème ML) |
| **ML Framework** | PyTorch + Stable-Baselines3 |
| **Auto-apprentissage** | Oui - ré-entraînement continu |
| **Hardware** | PC local avec 2 GPUs |
| **Exchanges** | Binance, Bybit (via CCXT) |

---

## 🏗️ Architecture Globale

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TRADING BOT ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │ DATA         │───▶│ FEATURE      │───▶│ ML ENGINE    │              │
│  │ COLLECTOR    │    │ ENGINEERING  │    │ (Training)   │              │
│  │              │    │              │    │              │              │
│  │ • CCXT       │    │ • TA-Lib     │    │ • PyTorch    │              │
│  │ • WebSocket  │    │ • Polars     │    │ • RL (PPO)   │              │
│  │ • DuckDB     │    │ • Custom     │    │ • XGBoost    │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│         │                   │                   │                       │
│         ▼                   ▼                   ▼                       │
│  ┌──────────────────────────────────────────────────────┐              │
│  │                    DATA STORAGE                       │              │
│  │  DuckDB (OHLCV) + Parquet (Historical) + Redis (Hot) │              │
│  └──────────────────────────────────────────────────────┘              │
│         │                                                               │
│         ▼                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │ BACKTESTER   │───▶│ PAPER        │───▶│ LIVE         │              │
│  │              │    │ TRADING      │    │ TRADING      │              │
│  │ • VectorBT   │    │              │    │              │              │
│  │ • Walk-fwd   │    │ • Simulation │    │ • CCXT       │              │
│  │ • Metrics    │    │ • Real data  │    │ • Risk Mgmt  │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│         │                   │                   │                       │
│         └───────────────────┴───────────────────┘                       │
│                             │                                           │
│                             ▼                                           │
│  ┌──────────────────────────────────────────────────────┐              │
│  │                    MONITORING                         │              │
│  │  Telegram Bot + Streamlit Dashboard + Logs (Rich)    │              │
│  └──────────────────────────────────────────────────────┘              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Stack Technique Détaillé

### 1. Langage et Environnement

```yaml
Runtime:
  python: "3.11+"  # Performances optimales
  package_manager: "uv"  # Beaucoup plus rapide que pip
  virtual_env: "venv"

IDE:
  recommended: "VSCode ou PyCharm"
  extensions:
    - Python
    - Jupyter
    - GitLens
```

### 2. Dépendances Python

```txt
# requirements.txt

# === Data Collection ===
ccxt>=4.0.0                # API exchanges unifié
websocket-client>=1.6.0    # WebSocket connections
aiohttp>=3.9.0             # Async HTTP

# === Data Storage ===
duckdb>=0.9.0              # Base de données analytique ultra-rapide
polars>=0.20.0             # DataFrames 10-100x plus rapide que Pandas
pyarrow>=14.0.0            # Format Parquet
redis>=5.0.0               # Cache en mémoire (optionnel)

# === Feature Engineering ===
ta-lib>=0.4.28             # Indicateurs techniques (nécessite install système)
pandas-ta>=0.3.14b         # Alternative pure Python à TA-Lib
numpy>=1.26.0
numba>=0.58.0              # JIT compilation pour vitesse

# === Machine Learning ===
torch>=2.1.0               # Deep Learning (GPU)
stable-baselines3>=2.2.0   # Reinforcement Learning
gymnasium>=0.29.0          # Environnements RL
xgboost>=2.0.0             # Gradient Boosting
lightgbm>=4.1.0            # Alternative à XGBoost
optuna>=3.4.0              # Hyperparameter tuning
ray[tune]>=2.8.0           # Distributed training

# === Backtesting ===
vectorbt>=0.26.0           # Backtesting vectorisé ultra-rapide

# === Monitoring ===
python-telegram-bot>=20.0  # Alertes Telegram
streamlit>=1.29.0          # Dashboard web local
rich>=13.0.0               # Logs colorés terminal
loguru>=0.7.0              # Logging amélioré

# === Utils ===
pydantic>=2.5.0            # Validation de données
python-dotenv>=1.0.0       # Variables d'environnement
schedule>=1.2.0            # Scheduling de tâches
typer>=0.9.0               # CLI
```

### 3. Structure du Projet

```
tradingllm/
├── config/
│   ├── settings.py          # Configuration globale
│   ├── exchanges.yaml       # Config exchanges
│   └── strategies.yaml      # Config stratégies
│
├── src/
│   ├── __init__.py
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── collector.py     # Collecte données OHLCV
│   │   ├── websocket.py     # Stream temps réel
│   │   ├── storage.py       # DuckDB + Parquet
│   │   └── symbols.py       # Gestion des paires
│   │
│   ├── features/
│   │   ├── __init__.py
│   │   ├── technical.py     # Indicateurs TA
│   │   ├── orderbook.py     # Features orderbook
│   │   ├── sentiment.py     # Sentiment (optionnel)
│   │   └── pipeline.py      # Feature pipeline
│   │
│   ├── ml/
│   │   ├── __init__.py
│   │   ├── environment.py   # Gym environment pour RL
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── rl_agent.py  # PPO/SAC agents
│   │   │   ├── ensemble.py  # Ensemble de modèles
│   │   │   └── xgb_model.py # XGBoost baseline
│   │   ├── trainer.py       # Training loop
│   │   ├── evaluator.py     # Evaluation metrics
│   │   └── self_trainer.py  # Auto-apprentissage continu
│   │
│   ├── backtest/
│   │   ├── __init__.py
│   │   ├── engine.py        # VectorBT wrapper
│   │   ├── metrics.py       # Sharpe, Sortino, etc.
│   │   └── validation.py    # Walk-forward
│   │
│   ├── trading/
│   │   ├── __init__.py
│   │   ├── executor.py      # Execution des ordres
│   │   ├── paper.py         # Paper trading
│   │   ├── live.py          # Live trading
│   │   └── risk.py          # Risk management
│   │
│   ├── monitoring/
│   │   ├── __init__.py
│   │   ├── telegram_bot.py  # Alertes Telegram
│   │   ├── dashboard.py     # Streamlit app
│   │   └── logger.py        # Logging config
│   │
│   └── utils/
│       ├── __init__.py
│       ├── time_utils.py
│       └── math_utils.py
│
├── models/                   # Modèles sauvegardés
│   ├── checkpoints/
│   └── production/
│
├── data/                     # Données locales
│   ├── raw/                  # OHLCV brut
│   ├── processed/            # Features calculées
│   └── duckdb/               # Base DuckDB
│
├── notebooks/                # Jupyter pour recherche
│   ├── 01_data_exploration.ipynb
│   ├── 02_feature_analysis.ipynb
│   └── 03_model_experiments.ipynb
│
├── tests/
│   ├── test_data/
│   ├── test_features/
│   ├── test_ml/
│   └── test_trading/
│
├── scripts/
│   ├── collect_data.py      # Script collecte
│   ├── train_model.py       # Script training
│   ├── run_backtest.py      # Script backtest
│   ├── paper_trade.py       # Script paper trading
│   └── live_trade.py        # Script live trading
│
├── .env.example              # Template variables
├── .gitignore
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## 📊 Module 1 : Collecte des Données

### 1.1 Sources de Données (Gratuites)

| Source | Type | Limite Gratuite |
|--------|------|-----------------|
| **Binance API** | OHLCV, Orderbook | 1200 req/min |
| **Bybit API** | OHLCV, Orderbook | 600 req/min |
| **CoinGecko** | Market cap, volume | 30 req/min |
| **Fear & Greed Index** | Sentiment | Illimité |
| **Reddit API** | Sentiment | 60 req/min |

### 1.2 Données à Collecter

```python
# Timeframes pour Swing Trading
TIMEFRAMES = ["15m", "1h", "4h", "1d"]

# Paires principales (haute liquidité)
SYMBOLS = [
    "BTC/USDT",
    "ETH/USDT", 
    "SOL/USDT",
    "BNB/USDT",
    "XRP/USDT",
    "ADA/USDT",
    "AVAX/USDT",
    "DOGE/USDT",
    "LINK/USDT",
    "DOT/USDT",
]

# Données OHLCV
OHLCV_COLUMNS = [
    "timestamp",
    "open", 
    "high", 
    "low", 
    "close", 
    "volume",
    "quote_volume",
    "trades_count",
]

# Données Orderbook (snapshot)
ORDERBOOK_DEPTH = 20  # Top 20 bids/asks
```

### 1.3 Schéma DuckDB

```sql
-- Table principale OHLCV
CREATE TABLE ohlcv (
    id INTEGER PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    exchange VARCHAR NOT NULL,
    timeframe VARCHAR NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open DOUBLE NOT NULL,
    high DOUBLE NOT NULL,
    low DOUBLE NOT NULL,
    close DOUBLE NOT NULL,
    volume DOUBLE NOT NULL,
    quote_volume DOUBLE,
    trades_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(symbol, exchange, timeframe, timestamp)
);

-- Index pour requêtes rapides
CREATE INDEX idx_ohlcv_symbol_time ON ohlcv(symbol, timestamp);
CREATE INDEX idx_ohlcv_timeframe ON ohlcv(timeframe, timestamp);

-- Table features calculées
CREATE TABLE features (
    id INTEGER PRIMARY KEY,
    ohlcv_id INTEGER REFERENCES ohlcv(id),
    -- Indicateurs techniques
    sma_20 DOUBLE,
    sma_50 DOUBLE,
    sma_200 DOUBLE,
    ema_12 DOUBLE,
    ema_26 DOUBLE,
    rsi_14 DOUBLE,
    macd DOUBLE,
    macd_signal DOUBLE,
    macd_hist DOUBLE,
    bb_upper DOUBLE,
    bb_middle DOUBLE,
    bb_lower DOUBLE,
    atr_14 DOUBLE,
    adx_14 DOUBLE,
    obv DOUBLE,
    -- Features custom
    price_momentum DOUBLE,
    volume_momentum DOUBLE,
    volatility DOUBLE,
    trend_strength DOUBLE,
    support_distance DOUBLE,
    resistance_distance DOUBLE
);

-- Table trades exécutés
CREATE TABLE trades (
    id INTEGER PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    side VARCHAR NOT NULL,  -- 'buy' or 'sell'
    entry_price DOUBLE NOT NULL,
    exit_price DOUBLE,
    quantity DOUBLE NOT NULL,
    entry_time TIMESTAMP NOT NULL,
    exit_time TIMESTAMP,
    pnl DOUBLE,
    pnl_percent DOUBLE,
    fees DOUBLE,
    status VARCHAR DEFAULT 'open',  -- 'open', 'closed', 'cancelled'
    strategy VARCHAR,
    model_version VARCHAR,
    is_paper BOOLEAN DEFAULT TRUE
);

-- Table performance modèles
CREATE TABLE model_performance (
    id INTEGER PRIMARY KEY,
    model_version VARCHAR NOT NULL,
    trained_at TIMESTAMP NOT NULL,
    backtest_sharpe DOUBLE,
    backtest_sortino DOUBLE,
    backtest_max_drawdown DOUBLE,
    backtest_win_rate DOUBLE,
    paper_sharpe DOUBLE,
    paper_pnl DOUBLE,
    live_sharpe DOUBLE,
    live_pnl DOUBLE,
    status VARCHAR DEFAULT 'testing'  -- 'testing', 'production', 'retired'
);
```

---

## 🔧 Module 2 : Feature Engineering

### 2.1 Indicateurs Techniques

```python
# Catégories de features
FEATURES = {
    # Trend Indicators
    "trend": [
        "sma_20", "sma_50", "sma_200",
        "ema_12", "ema_26", "ema_50",
        "macd", "macd_signal", "macd_hist",
        "adx", "plus_di", "minus_di",
        "aroon_up", "aroon_down",
        "supertrend",
    ],
    
    # Momentum Indicators
    "momentum": [
        "rsi_14", "rsi_7",
        "stoch_k", "stoch_d",
        "williams_r",
        "cci_20",
        "mfi_14",
        "roc_10",
    ],
    
    # Volatility Indicators
    "volatility": [
        "bb_upper", "bb_middle", "bb_lower",
        "bb_width", "bb_percent",
        "atr_14", "atr_7",
        "keltner_upper", "keltner_lower",
        "donchian_upper", "donchian_lower",
    ],
    
    # Volume Indicators
    "volume": [
        "obv",
        "vwap",
        "volume_sma_20",
        "volume_ratio",
        "accumulation_distribution",
    ],
    
    # Price Action Features
    "price_action": [
        "candle_body_size",
        "candle_wick_ratio",
        "higher_high", "lower_low",
        "pivot_points",
        "support_levels",
        "resistance_levels",
    ],
    
    # Multi-timeframe Features
    "mtf": [
        "trend_1h", "trend_4h", "trend_1d",
        "rsi_1h", "rsi_4h", "rsi_1d",
        "volume_ratio_1h", "volume_ratio_4h",
    ],
    
    # Market Structure
    "market": [
        "btc_correlation",
        "btc_dominance",
        "total_market_cap_change",
        "fear_greed_index",
    ],
}
```

### 2.2 Feature Pipeline

```python
# Pipeline de transformation
FEATURE_PIPELINE = [
    # 1. Calcul indicateurs bruts
    ("technical_indicators", TechnicalIndicatorTransformer()),
    
    # 2. Normalisation
    ("normalize", RobustScaler()),  # Résistant aux outliers
    
    # 3. Lag features (éviter data leakage!)
    ("lag_features", LagTransformer(lags=[1, 2, 3, 5, 10])),
    
    # 4. Rolling statistics
    ("rolling_stats", RollingStatsTransformer(windows=[5, 10, 20])),
    
    # 5. Target encoding (pour catégories)
    ("target_encode", TargetEncoder()),
    
    # 6. Feature selection
    ("select_features", FeatureSelector(method="mutual_info", k=50)),
]
```

### 2.3 Prévention Data Leakage ⚠️

```python
# RÈGLES CRITIQUES pour éviter le data leakage

# ❌ INTERDIT : Utiliser des données futures
# ❌ INTERDIT : Normaliser sur tout le dataset
# ❌ INTERDIT : Feature selection sur tout le dataset

# ✅ CORRECT : Pipeline pour chaque fold
class SafeFeaturePipeline:
    def fit_transform(self, X_train, y_train):
        """Fit uniquement sur train, jamais sur test/validation"""
        self.scaler.fit(X_train)
        self.selector.fit(X_train, y_train)
        return self.transform(X_train)
    
    def transform(self, X):
        """Transform sans refit - pour validation/test"""
        return self.selector.transform(
            self.scaler.transform(X)
        )
```

---

## 🧠 Module 3 : Machine Learning

### 3.1 Approche Multi-Modèles

```
┌─────────────────────────────────────────────────────────┐
│                    ENSEMBLE STRATEGY                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│   │   XGBoost   │  │   LightGBM  │  │  RL Agent   │    │
│   │  (Baseline) │  │  (Fast)     │  │  (PPO/SAC)  │    │
│   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │
│          │                │                │            │
│          └────────────────┼────────────────┘            │
│                           ▼                             │
│                  ┌─────────────┐                        │
│                  │ META-LEARNER│                        │
│                  │ (Weighted   │                        │
│                  │  Ensemble)  │                        │
│                  └──────┬──────┘                        │
│                         │                               │
│                         ▼                               │
│                  ┌─────────────┐                        │
│                  │   SIGNAL    │                        │
│                  │  BUY/SELL/  │                        │
│                  │    HOLD     │                        │
│                  └─────────────┘                        │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Modèle 1 : XGBoost Baseline

```python
# Configuration XGBoost pour classification
XGBOOST_CONFIG = {
    "objective": "multi:softprob",
    "num_class": 3,  # Buy, Sell, Hold
    "eval_metric": "mlogloss",
    
    # Hyperparamètres
    "max_depth": 6,
    "learning_rate": 0.05,
    "n_estimators": 500,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    
    # Régularisation
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    
    # GPU
    "tree_method": "gpu_hist",
    "device": "cuda",
    
    # Early stopping
    "early_stopping_rounds": 50,
}

# Labels pour classification
TARGET_LABELS = {
    0: "HOLD",
    1: "BUY",   # Prix monte > 2% dans les X prochaines heures
    2: "SELL",  # Prix baisse > 2% dans les X prochaines heures
}
```

### 3.3 Modèle 2 : Reinforcement Learning

```python
# Configuration environnement RL
RL_ENVIRONMENT_CONFIG = {
    # State space
    "state_features": [
        "normalized_price",
        "returns_1h", "returns_4h", "returns_1d",
        "rsi", "macd", "bb_percent",
        "volume_ratio",
        "position_size",  # Current position
        "unrealized_pnl",  # Current P&L
        "portfolio_value",
    ],
    
    # Action space
    "actions": {
        0: ("HOLD", 0.0),
        1: ("BUY_SMALL", 0.25),   # 25% du capital
        2: ("BUY_MEDIUM", 0.50),  # 50% du capital
        3: ("BUY_LARGE", 0.75),   # 75% du capital
        4: ("SELL_SMALL", 0.25),
        5: ("SELL_MEDIUM", 0.50),
        6: ("SELL_ALL", 1.0),
    },
    
    # Reward function
    "reward_config": {
        "base_reward": "pnl_percent",  # % de gain/perte
        "risk_penalty_factor": 0.5,     # Pénalise volatilité
        "drawdown_penalty": 2.0,        # Pénalise drawdown
        "holding_penalty": 0.001,       # Léger coût d'inaction
        "transaction_cost": 0.001,      # 0.1% par trade
    },
}

# Configuration agent PPO
PPO_CONFIG = {
    "policy": "MlpPolicy",
    "learning_rate": 3e-4,
    "n_steps": 2048,
    "batch_size": 64,
    "n_epochs": 10,
    "gamma": 0.99,
    "gae_lambda": 0.95,
    "clip_range": 0.2,
    "ent_coef": 0.01,
    "vf_coef": 0.5,
    "max_grad_norm": 0.5,
    
    # Network architecture
    "policy_kwargs": {
        "net_arch": [
            {"pi": [256, 256], "vf": [256, 256]}
        ],
        "activation_fn": "torch.nn.ReLU",
    },
    
    # Training
    "total_timesteps": 1_000_000,
    "device": "cuda",
}
```

### 3.4 Auto-Apprentissage Continu ⭐

```python
# Configuration self-training
SELF_TRAINING_CONFIG = {
    # Scheduling
    "retrain_frequency": "weekly",  # Ré-entraînement hebdomadaire
    "evaluation_frequency": "daily",  # Évaluation quotidienne
    
    # Data windows
    "training_window_days": 180,  # 6 mois de données pour training
    "validation_window_days": 30,  # 1 mois pour validation
    "min_samples": 5000,  # Minimum de samples pour retraining
    
    # Performance thresholds
    "min_sharpe_ratio": 1.0,
    "max_drawdown": 0.15,  # 15% max drawdown
    "min_win_rate": 0.45,
    
    # Model selection
    "selection_metric": "sharpe_ratio",
    "comparison_window_days": 7,  # Comparer sur 7 jours
    
    # A/B Testing
    "ab_test_capital_split": 0.2,  # 20% capital pour nouveau modèle
    "ab_test_min_trades": 20,
    "ab_test_confidence": 0.95,
    
    # Rollback
    "rollback_drawdown_trigger": 0.10,  # Rollback si -10%
    "keep_n_checkpoints": 5,
}

# Pipeline auto-training
SELF_TRAINING_PIPELINE = """
┌─────────────────────────────────────────────────────────┐
│             CONTINUOUS LEARNING PIPELINE                 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. COLLECT NEW DATA (Daily)                            │
│     └─ Fetch last 24h of market data                    │
│     └─ Calculate features                               │
│     └─ Store in DuckDB                                  │
│                                                          │
│  2. EVALUATE CURRENT MODEL (Daily)                      │
│     └─ Calculate live performance metrics               │
│     └─ Compare to benchmarks (BUY & HOLD)               │
│     └─ Check for regime change                          │
│                                                          │
│  3. TRIGGER RETRAINING (If conditions met)              │
│     └─ Performance below threshold?                     │
│     └─ Scheduled retraining day?                        │
│     └─ Regime change detected?                          │
│                                                          │
│  4. TRAIN NEW MODEL (When triggered)                    │
│     └─ Prepare training data (rolling window)           │
│     └─ Hyperparameter tuning (Optuna)                   │
│     └─ Train on GPU                                     │
│     └─ Validate with walk-forward                       │
│                                                          │
│  5. A/B TEST NEW MODEL (Paper trading)                  │
│     └─ Run both models in parallel                      │
│     └─ Compare performance over N trades                │
│     └─ Statistical significance test                    │
│                                                          │
│  6. PROMOTE OR REJECT                                   │
│     └─ If new model better: promote to production       │
│     └─ If worse: keep current, save checkpoint          │
│     └─ Log decision and metrics                         │
│                                                          │
│  7. MONITOR (Continuous)                                │
│     └─ Track live performance                           │
│     └─ Alert on anomalies                               │
│     └─ Emergency rollback if needed                     │
│                                                          │
└─────────────────────────────────────────────────────────┘
"""
```

---

## 📈 Module 4 : Backtesting

### 4.1 Configuration VectorBT

```python
# Configuration backtesting
BACKTEST_CONFIG = {
    # Frais réalistes (CRUCIAL)
    "fees": {
        "maker": 0.0002,   # 0.02% avec réduction VIP
        "taker": 0.0004,   # 0.04% avec réduction VIP
        "slippage": 0.0005, # 0.05% slippage estimé
    },
    
    # Timeframe principal
    "timeframe": "1h",
    
    # Période de backtest
    "start_date": "2023-01-01",
    "end_date": "2024-12-31",
    
    # Capital initial
    "initial_capital": 10000,  # $10,000 USDT simulé
    
    # Position sizing
    "max_position_pct": 0.20,  # Max 20% par position
    "max_positions": 5,        # Max 5 positions simultanées
    
    # Risk management
    "stop_loss_pct": 0.03,     # Stop loss à 3%
    "take_profit_pct": 0.06,   # Take profit à 6%
    "trailing_stop_pct": 0.02, # Trailing stop 2%
}

# Métriques à calculer
BACKTEST_METRICS = [
    "total_return",
    "sharpe_ratio",
    "sortino_ratio",
    "calmar_ratio",
    "max_drawdown",
    "max_drawdown_duration",
    "win_rate",
    "profit_factor",
    "avg_win",
    "avg_loss",
    "total_trades",
    "avg_trade_duration",
    "exposure_time",
]
```

### 4.2 Walk-Forward Validation

```python
# Configuration walk-forward
WALK_FORWARD_CONFIG = {
    "n_splits": 5,
    "train_size_days": 120,   # 4 mois training
    "test_size_days": 30,     # 1 mois test
    "gap_days": 1,            # 1 jour de gap (éviter leakage)
    
    # Chaque split
    # Split 1: Train [0-120] -> Test [121-150]
    # Split 2: Train [30-150] -> Test [151-180]
    # Split 3: Train [60-180] -> Test [181-210]
    # ...
}
```

---

## ⚠️ Module 5 : Risk Management

### 5.1 Règles de Gestion du Risque

```python
RISK_MANAGEMENT = {
    # Position Limits
    "max_position_size_pct": 0.20,  # Max 20% du capital par trade
    "max_portfolio_risk_pct": 0.10,  # Max 10% risque total
    "max_correlation": 0.7,  # Éviter positions trop corrélées
    
    # Daily Limits
    "max_daily_loss_pct": 0.05,  # Stop trading si -5% journalier
    "max_daily_trades": 10,
    "max_consecutive_losses": 5,
    
    # Drawdown Limits
    "max_drawdown_pct": 0.15,  # Pause si -15% drawdown
    "drawdown_recovery_days": 7,  # Attendre 7 jours avant reprendre
    
    # Volatility Adjustment
    "high_volatility_reduction": 0.5,  # Réduire taille 50% en haute vol
    "volatility_threshold": 2.0,  # Seuil = 2x volatilité normale
    
    # Exposure Limits
    "max_long_exposure": 0.8,  # Max 80% long
    "max_short_exposure": 0.3,  # Max 30% short (si applicable)
    
    # Circuit Breakers
    "pause_on_exchange_error": True,
    "pause_on_api_rate_limit": True,
    "pause_on_high_spread": 0.01,  # Pause si spread > 1%
}
```

### 5.2 Position Sizing Dynamique

```python
# Kelly Criterion modifié
def calculate_position_size(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    current_volatility: float,
    max_position: float = 0.20
) -> float:
    """
    Position sizing basé sur Kelly Criterion avec ajustement volatilité
    """
    # Kelly formula
    kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
    
    # Fractional Kelly (plus conservateur)
    fractional_kelly = kelly * 0.25  # Utiliser 25% du Kelly
    
    # Ajustement volatilité
    vol_adjustment = 1.0 / (1.0 + current_volatility)
    
    # Position finale
    position = min(
        fractional_kelly * vol_adjustment,
        max_position
    )
    
    return max(0, position)
```

---

## 📱 Module 6 : Monitoring

### 6.1 Telegram Bot

```python
# Configuration Telegram
TELEGRAM_CONFIG = {
    "enabled": True,
    "bot_token": "${TELEGRAM_BOT_TOKEN}",  # Depuis .env
    "chat_id": "${TELEGRAM_CHAT_ID}",
    
    # Notifications
    "notify_on": {
        "trade_open": True,
        "trade_close": True,
        "daily_summary": True,
        "drawdown_warning": True,  # Si drawdown > 5%
        "error": True,
        "model_update": True,
    },
    
    # Commandes
    "commands": [
        "/status",     # Status du bot
        "/balance",    # Balance actuelle
        "/positions",  # Positions ouvertes
        "/pnl",        # P&L du jour
        "/stop",       # Arrêter le trading
        "/start",      # Reprendre le trading
    ],
}
```

### 6.2 Dashboard Streamlit

```python
# Pages du dashboard
DASHBOARD_PAGES = [
    "Overview",       # Résumé général
    "Positions",      # Positions ouvertes
    "Trades",         # Historique trades
    "Performance",    # Métriques performance
    "Backtest",       # Résultats backtest
    "Models",         # Versions modèles
    "Logs",           # Logs en temps réel
    "Settings",       # Configuration
]
```

---

## 🚀 Module 7 : Déploiement

### 7.1 Environnement de Production (Local)

```yaml
# Configuration production locale
production:
  hardware:
    cpu: "Multi-core (8+)"
    ram: "32GB+"
    gpu: "2x NVIDIA (training)"
    storage: "500GB+ SSD"
  
  processes:
    - name: "data_collector"
      description: "Collecte données en continu"
      restart: "always"
      
    - name: "feature_pipeline"
      description: "Calcul features temps réel"
      restart: "always"
      
    - name: "trading_engine"
      description: "Exécution des trades"
      restart: "always"
      priority: "high"
      
    - name: "self_trainer"
      description: "Ré-entraînement périodique"
      schedule: "weekly"
      gpu: true
      
    - name: "monitor"
      description: "Dashboard + Telegram"
      restart: "always"

  # Gestion des processus
  process_manager: "systemd"  # ou supervisord
```

### 7.2 Variables d'Environnement

```bash
# .env.example

# === Exchange API Keys ===
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET_KEY=your_secret_key_here
BYBIT_API_KEY=your_api_key_here
BYBIT_SECRET_KEY=your_secret_key_here

# === Telegram ===
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# === Database ===
DUCKDB_PATH=./data/duckdb/trading.db
REDIS_URL=redis://localhost:6379

# === Trading ===
TRADING_MODE=paper  # paper | live
INITIAL_CAPITAL=10000
MAX_POSITION_PCT=0.20

# === ML ===
MODEL_PATH=./models/production/latest.pt
DEVICE=cuda
```

---

## 📅 Plan d'Implémentation

### Phase 1 : Foundation (Semaine 1-2)
- [ ] Setup environnement Python avec uv
- [ ] Créer structure projet
- [ ] Implémenter data collector (CCXT)
- [ ] Setup DuckDB + schéma

### Phase 2 : Features (Semaine 3)
- [ ] Implémenter indicateurs techniques
- [ ] Créer feature pipeline
- [ ] Tests unitaires features

### Phase 3 : ML Baseline (Semaine 4-5)
- [ ] Implémenter XGBoost baseline
- [ ] Créer environnement RL
- [ ] Setup training avec GPU
- [ ] Hyperparameter tuning avec Optuna

### Phase 4 : Backtesting (Semaine 6)
- [ ] Implémenter VectorBT wrapper
- [ ] Walk-forward validation
- [ ] Générer rapports métriques

### Phase 5 : Paper Trading (Semaine 7-10)
- [ ] Implémenter paper trading engine
- [ ] Connecter à exchange (lecture seule)
- [ ] 4 semaines minimum de paper trading
- [ ] Analyser résultats et ajuster

### Phase 6 : Self-Training (Semaine 11-12)
- [ ] Implémenter boucle d'auto-apprentissage
- [ ] A/B testing pipeline
- [ ] Model versioning

### Phase 7 : Monitoring (Semaine 13)
- [ ] Telegram bot
- [ ] Streamlit dashboard
- [ ] Alerting

### Phase 8 : Live Trading (Semaine 14+)
- [ ] Tests avec micro-capital (100€)
- [ ] Monitoring intensif
- [ ] Scale-up progressif

---

## ⚠️ Avertissements Importants

> [!CAUTION]
> **Le trading de crypto-monnaies comporte des risques significatifs de perte en capital.**
> - Ne jamais investir plus que ce que vous pouvez vous permettre de perdre
> - Les performances passées ne garantissent pas les résultats futurs
> - Le backtesting est optimiste par nature (overfitting, data leakage)
> - Les marchés peuvent changer, rendant les modèles obsolètes

> [!WARNING]
> **Avant de passer en live :**
> - Minimum 1 mois de paper trading profitable
> - Sharpe ratio > 1.0 en paper
> - Drawdown max < 15%
> - Comprendre chaque composant du système

> [!IMPORTANT]
> **API Keys Security :**
> - Ne jamais commit les clés dans Git
> - Utiliser des clés avec permissions minimales
> - Activer IP whitelist sur exchanges
> - Désactiver le retrait via API

---

## 📚 Ressources

### Documentation
- [CCXT Documentation](https://docs.ccxt.com/)
- [VectorBT Documentation](https://vectorbt.dev/)
- [Stable Baselines3](https://stable-baselines3.readthedocs.io/)
- [DuckDB Documentation](https://duckdb.org/docs/)

### Livres Recommandés
- "Advances in Financial Machine Learning" - Marcos López de Prado
- "Machine Learning for Asset Managers" - Marcos López de Prado
- "Algorithmic Trading" - Ernest Chan

---

*Plan créé le 2026-01-02 - Version 2.0 (Swing Trading Focus)*