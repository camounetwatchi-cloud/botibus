import duckdb
import psycopg2
from psycopg2.extras import execute_values
import pandas as pd
import time
import os
from pathlib import Path
from loguru import logger
from src.config.settings import settings
from contextlib import contextmanager

class DataStorage:
    def __init__(self, db_path: str = "market_data.duckdb", read_only: bool = False):
        self.db_path = settings.DATA_PATH / "duckdb" / db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.read_only = read_only
        self.use_postgres = settings.DATABASE_URL is not None
        self._postgres_available = True  # Track if PostgreSQL is reachable
        
        if self.use_postgres:
            # Test connection on init
            if self._test_postgres_connection():
                logger.info("Using PostgreSQL (Supabase) storage")
            else:
                logger.warning("PostgreSQL unavailable, falling back to DuckDB")
                self.use_postgres = False
                self._postgres_available = False
        
        if not self.use_postgres:
            logger.info(f"Using local DuckDB storage at {self.db_path}")
            
        self._init_tables()

    def _test_postgres_connection(self) -> bool:
        """Test PostgreSQL connection with retry logic."""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                conn = psycopg2.connect(
                    settings.DATABASE_URL,
                    connect_timeout=10,
                    options="-c statement_timeout=30000"
                )
                conn.close()
                return True
            except Exception as e:
                logger.warning(f"PostgreSQL connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
        return False

    @contextmanager
    def _get_connection(self):
        """Context manager to handle database connections."""
        conn = None
        if self.use_postgres:
            try:
                conn = psycopg2.connect(
                    settings.DATABASE_URL,
                    connect_timeout=10,
                    options="-c statement_timeout=30000"
                )
                yield conn
            except Exception as e:
                logger.error(f"PostgreSQL Connection Error: {e}")
                # Fallback to DuckDB for this operation
                logger.warning("Falling back to DuckDB for this operation")
                self.use_postgres = False
                conn = duckdb.connect(str(self.db_path), read_only=self.read_only)
                yield conn
            finally:
                if conn:
                    conn.close()
        else:
            # DuckDB implementation
            max_retries = 5
            retry_delay = 0.5
            for attempt in range(max_retries):
                try:
                    conn = duckdb.connect(str(self.db_path), read_only=self.read_only)
                    yield conn
                    break
                except Exception as e:
                    if "used by another process" in str(e) and attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    raise e
                finally:
                    if conn:
                        conn.close()

    def _init_tables(self):
        if self.read_only:
            return
            
        with self._get_connection() as conn:
            cursor = conn.cursor() if self.use_postgres else conn
            
            # OHLCV Table
            ohlcv_sql = """
                CREATE TABLE IF NOT EXISTS ohlcv (
                    symbol VARCHAR,
                    exchange VARCHAR,
                    timeframe VARCHAR,
                    timestamp TIMESTAMP,
                    open DOUBLE PRECISION,
                    high DOUBLE PRECISION,
                    low DOUBLE PRECISION,
                    close DOUBLE PRECISION,
                    volume DOUBLE PRECISION,
                    PRIMARY KEY (symbol, exchange, timeframe, timestamp)
                )
            """
            
            # Trades Table
            trades_sql = """
                CREATE TABLE IF NOT EXISTS trades (
                    id VARCHAR PRIMARY KEY,
                    symbol VARCHAR,
                    side VARCHAR,
                    type VARCHAR,
                    status VARCHAR,
                    entry_price DOUBLE PRECISION,
                    exit_price DOUBLE PRECISION,
                    amount DOUBLE PRECISION,
                    entry_time TIMESTAMP,
                    exit_time TIMESTAMP,
                    pnl DOUBLE PRECISION,
                    fee DOUBLE PRECISION
                )
            """
            
            # Account Balance Table
            balance_sql = """
                CREATE TABLE IF NOT EXISTS balance (
                    timestamp TIMESTAMP PRIMARY KEY,
                    total DOUBLE PRECISION,
                    free DOUBLE PRECISION,
                    used DOUBLE PRECISION
                )
            """
            
            # Bot Status Table (for cloud heartbeat)
            bot_status_sql = """
                CREATE TABLE IF NOT EXISTS bot_status (
                    id INTEGER PRIMARY KEY,
                    status VARCHAR,
                    last_heartbeat TIMESTAMP,
                    open_positions INTEGER,
                    exchange VARCHAR,
                    mode VARCHAR
                )
            """
            
            cursor.execute(ohlcv_sql)
            cursor.execute(trades_sql)
            cursor.execute(balance_sql)
            cursor.execute(bot_status_sql)
            if self.use_postgres:
                conn.commit()

    def save_ohlcv(self, df: pd.DataFrame, symbol: str, exchange: str, timeframe: str):
        if df.empty or self.read_only:
            return
            
        df_copy = df.copy()
        df_copy['symbol'] = symbol
        df_copy['exchange'] = exchange
        df_copy['timeframe'] = timeframe
        
        try:
            with self._get_connection() as conn:
                if self.use_postgres:
                    cursor = conn.cursor()
                    # Prepare values for execute_values
                    values = [
                        (r.symbol, r.exchange, r.timeframe, r.timestamp, r.open, r.high, r.low, r.close, r.volume)
                        for r in df_copy.itertuples()
                    ]
                    sql = """
                        INSERT INTO ohlcv (symbol, exchange, timeframe, timestamp, open, high, low, close, volume)
                        VALUES %s
                        ON CONFLICT (symbol, exchange, timeframe, timestamp) DO UPDATE SET
                            open = EXCLUDED.open,
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            close = EXCLUDED.close,
                            volume = EXCLUDED.volume
                    """
                    execute_values(cursor, sql, values)
                    conn.commit()
                else:
                    conn.register('df_view', df_copy)
                    conn.execute("""
                        INSERT INTO ohlcv 
                        SELECT symbol, exchange, timeframe, timestamp, open, high, low, close, volume 
                        FROM df_view
                        ON CONFLICT (symbol, exchange, timeframe, timestamp) DO UPDATE SET
                            open = EXCLUDED.open,
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            close = EXCLUDED.close,
                            volume = EXCLUDED.volume
                    """)
                logger.info(f"Saved {len(df)} rows for {symbol} {timeframe}")
        except Exception as e:
            logger.error(f"Error saving data: {e}")
            
    def load_ohlcv(self, symbol: str, timeframe: str) -> pd.DataFrame:
        query = f"""
            SELECT timestamp, open, high, low, close, volume
            FROM ohlcv
            WHERE symbol = %s AND timeframe = %s
            ORDER BY timestamp
        """
        if not self.use_postgres:
            query = query.replace("%s", "?")
            
        try:
            with self._get_connection() as conn:
                if self.use_postgres:
                    return pd.read_sql(query, conn, params=(symbol, timeframe))
                else:
                    return conn.execute(query, [symbol, timeframe]).df()
        except Exception as e:
            logger.error(f"Error loading OHLCV: {e}")
            return pd.DataFrame()

    def save_trade(self, trade_data: dict):
        """Save or update a trade record."""
        if self.read_only:
            return
            
        keys = trade_data.keys()
        columns = ", ".join(keys)
        
        if self.use_postgres:
            placeholders = ", ".join(["%s" for _ in keys])
            updates = ", ".join([f"{k} = EXCLUDED.{k}" for k in keys if k != 'id'])
            query = f"INSERT INTO trades ({columns}) VALUES ({placeholders}) ON CONFLICT (id) DO UPDATE SET {updates}"
        else:
            placeholders = ", ".join(["?" for _ in keys])
            updates = ", ".join([f"{k} = EXCLUDED.{k}" for k in keys if k != 'id'])
            query = f"INSERT INTO trades ({columns}) VALUES ({placeholders}) ON CONFLICT (id) DO UPDATE SET {updates}"
            
        try:
            with self._get_connection() as conn:
                if self.use_postgres:
                    cursor = conn.cursor()
                    cursor.execute(query, list(trade_data.values()))
                    conn.commit()
                else:
                    conn.execute(query, list(trade_data.values()))
                logger.info(f"Trade {trade_data.get('id')} saved/updated.")
        except Exception as e:
            logger.error(f"Error saving trade: {e}")

    def update_balance(self, total: float, free: float, used: float):
        """Record current account balance."""
        if self.read_only:
            return
            
        timestamp = pd.Timestamp.now()
        placeholder = "%s" if self.use_postgres else "?"
        query = f"INSERT INTO balance (timestamp, total, free, used) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})"
        
        try:
            with self._get_connection() as conn:
                if self.use_postgres:
                    cursor = conn.cursor()
                    cursor.execute(query, [timestamp, total, free, used])
                    conn.commit()
                else:
                    conn.execute(query, [timestamp, total, free, used])
                logger.debug(f"Balance updated: {total}")
        except Exception as e:
            logger.error(f"Error updating balance: {e}")

    def get_trades(self, status: str = None) -> pd.DataFrame:
        """Retrieve trades, optionally filtered by status."""
        query = "SELECT * FROM trades"
        params = []
        if status:
            query += " WHERE status = %s"
            params.append(status)
        query += " ORDER BY entry_time DESC"
        
        if not self.use_postgres:
            query = query.replace("%s", "?")
            
        try:
            with self._get_connection() as conn:
                if self.use_postgres:
                    return pd.read_sql(query, conn, params=params)
                else:
                    return conn.execute(query, params).df()
        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            return pd.DataFrame()

    def get_latest_balance(self) -> dict:
        """Get the most recent balance entry."""
        query = "SELECT * FROM balance ORDER BY timestamp DESC LIMIT 1"
        try:
            with self._get_connection() as conn:
                if self.use_postgres:
                    cursor = conn.cursor()
                    cursor.execute(query)
                    res = cursor.fetchone()
                else:
                    res = conn.execute(query).fetchone()
                    
                if res:
                    cols = ["timestamp", "total", "free", "used"]
                    return dict(zip(cols, res))
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
        return {"total": 0, "free": 0, "used": 0}

    def update_bot_status(self, status: str, open_positions: int, exchange: str = "kraken", mode: str = "paper"):
        """Update bot status heartbeat for cloud monitoring."""
        if self.read_only:
            return
            
        timestamp = pd.Timestamp.now()
        
        try:
            with self._get_connection() as conn:
                if self.use_postgres:
                    cursor = conn.cursor()
                    # Upsert bot status (id=1 always)
                    cursor.execute("""
                        INSERT INTO bot_status (id, status, last_heartbeat, open_positions, exchange, mode)
                        VALUES (1, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            status = EXCLUDED.status,
                            last_heartbeat = EXCLUDED.last_heartbeat,
                            open_positions = EXCLUDED.open_positions,
                            exchange = EXCLUDED.exchange,
                            mode = EXCLUDED.mode
                    """, [status, timestamp, open_positions, exchange, mode])
                    conn.commit()
                else:
                    conn.execute("""
                        INSERT OR REPLACE INTO bot_status (id, status, last_heartbeat, open_positions, exchange, mode)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, [1, status, timestamp, open_positions, exchange, mode])
                logger.debug(f"Bot status updated: {status}")
        except Exception as e:
            logger.error(f"Error updating bot status: {e}")

    def get_bot_status(self) -> dict:
        """Get current bot status for dashboard."""
        query = "SELECT status, last_heartbeat, open_positions, exchange, mode FROM bot_status WHERE id = 1"
        try:
            with self._get_connection() as conn:
                if self.use_postgres:
                    cursor = conn.cursor()
                    cursor.execute(query)
                    res = cursor.fetchone()
                else:
                    res = conn.execute(query).fetchone()
                    
                if res:
                    cols = ["status", "last_heartbeat", "open_positions", "exchange", "mode"]
                    return dict(zip(cols, res))
        except Exception as e:
            logger.error(f"Error getting bot status: {e}")
        return {"status": "unknown", "last_heartbeat": None, "open_positions": 0, "exchange": "", "mode": ""}
