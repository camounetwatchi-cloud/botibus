try:
    import duckdb
except ImportError:
    duckdb = None
import psycopg2
from psycopg2.extras import execute_values
import pandas as pd
import numpy as np
import time
import os
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger
from src.config.settings import settings
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Union, Generator
import warnings

class DataStorage:
    """
    Handles data persistence for the trading bot, supporting both PostgreSQL (via Supabase)
    and DuckDB (local) with automatic fallback.
    """
    def __init__(self, db_path: str = "market_data.duckdb", read_only: bool = False):
        """
        Initialize the DataStorage instance.

        Args:
            db_path (str): Filename for the local DuckDB database.
            read_only (bool): If True, opens the database in read-only mode.
        """
        self.db_path = settings.DATA_PATH / "duckdb" / db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.read_only = read_only
        self.use_postgres = settings.DATABASE_URL is not None
        self._postgres_available = True  # Track if PostgreSQL is reachable
        
        self.connection_error: Optional[str] = None  # Store connection error details
        
        if self.use_postgres:
            # Test connection on init
            if self._test_postgres_connection():
                logger.info("Using PostgreSQL (Supabase) storage")
            else:
                logger.warning("PostgreSQL unavailable, falling back to DuckDB")
                self.use_postgres = False
                self._postgres_available = False
        
        if not self.use_postgres:
            if duckdb is None:
                logger.error("DuckDB is not installed and PostgreSQL is unavailable. Storage cannot function.")
                # We can't raise an error here as it might crash the dashboard loop. 
                # Just set a flag that storage is broken.
                self.storage_broken = True
            else:
                logger.info(f"Using local DuckDB storage at {self.db_path}")
                self.storage_broken = False
                self._init_tables()
        else:
            self.storage_broken = False
            self._init_tables()

    @property
    def storage_type(self) -> str:
        """Return a user-friendly string describing the active storage backend."""
        if self.use_postgres:
            return "Supabase (Cloud)"
        return "DuckDB (Local)"

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
                self.connection_error = str(e)  # Capture the error
                logger.warning(f"PostgreSQL connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
        return False

    def _sanitize_value(self, value):
        """Convert numpy/pandas types to native Python types for SQL compatibility.
        
        CRITICAL: psycopg2 cannot handle numpy types directly. This function ensures
        all values passed to SQL queries are native Python types (int, float, str, etc.)
        """
        if value is None:
            return None
            
        # Check for NaN/NaT
        if isinstance(value, float) and pd.isna(value):
            return None
            
        # Handle pandas Timestamp first (before numpy checks)
        if isinstance(value, pd.Timestamp):
            return value.to_pydatetime()
            
        # Handle numpy scalars using .item() method (most reliable)
        if hasattr(value, 'item'):
            try:
                return value.item()
            except (ValueError, AttributeError):
                pass  # Fall through to type-based conversion
            
        # Explicit numpy type checks with forced conversion
        if isinstance(value, (np.integer, np.floating)):
            return value.item()
        
        # Fallback: check type name for numpy types (handles edge cases)
        type_name = type(value).__name__
        if 'float' in type_name and type_name != 'float':
            return float(value)
        if 'int' in type_name and type_name not in ('int', 'integer'):
            return int(value)
            
        # Handle numpy bool
        if type_name == 'bool_' or (hasattr(np, 'bool_') and isinstance(value, np.bool_)):
            return bool(value)
            
        return value

    
    def _sanitize_dict(self, data: dict) -> dict:
        """Sanitize all values in a dictionary for SQL compatibility."""
        return {k: self._sanitize_value(v) for k, v in data.items()}
    
    def _fallback_to_duckdb(self) -> None:
        """
        Switches the storage mechanism from PostgreSQL to DuckDB.
        
        This is typically called when a PostgreSQL connection fails. It disables the
        PostgreSQL flag and initializes DuckDB tables if necessary.
        """
        if self.use_postgres:  # First time switching
            self.use_postgres = False
            logger.info("Initializing DuckDB tables after fallback...")
            self._init_duckdb_tables()
    
    def _init_duckdb_tables(self) -> None:
        """
        Initializes the necessary tables in DuckDB.
        
        Creates 'ohlcv', 'trades', 'balance', and 'bot_status' tables if they do not exist.
        """
        if self.read_only:
            return
        
        # Use a context manager to ensure connection is closed, even if errors occur
        try:
            conn = duckdb.connect(str(self.db_path), read_only=False)
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ohlcv (
                        symbol VARCHAR,
                        exchange VARCHAR,
                        timeframe VARCHAR,
                        timestamp TIMESTAMP,
                        open DOUBLE,
                        high DOUBLE,
                        low DOUBLE,
                        close DOUBLE,
                        volume DOUBLE,
                        PRIMARY KEY (symbol, exchange, timeframe, timestamp)
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS trades (
                        id VARCHAR PRIMARY KEY,
                        symbol VARCHAR,
                        side VARCHAR,
                        type VARCHAR,
                        status VARCHAR,
                        entry_price DOUBLE,
                        exit_price DOUBLE,
                        amount DOUBLE,
                        entry_time TIMESTAMP,
                        exit_time TIMESTAMP,
                        pnl DOUBLE,
                        fee DOUBLE,
                        gross_pnl DOUBLE,
                        net_pnl DOUBLE,
                        entry_fee DOUBLE,
                        exit_fee DOUBLE,
                        rollover_fee DOUBLE,
                        total_fees DOUBLE
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS balance (
                        timestamp TIMESTAMP PRIMARY KEY,
                        total DOUBLE,
                        free DOUBLE,
                        used DOUBLE
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS bot_status (
                        id INTEGER PRIMARY KEY,
                        status VARCHAR,
                        last_heartbeat TIMESTAMP,
                        open_positions INTEGER,
                        exchange VARCHAR,
                        mode VARCHAR
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cooldowns (
                        symbol VARCHAR PRIMARY KEY,
                        last_trade_time TIMESTAMP
                    )
                """)
                logger.info("DuckDB tables initialized successfully")
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Error initializing DuckDB tables: {e}")

    @contextmanager
    def _get_connection(self) -> Generator[Any, None, None]:
        """
        Context manager for database connections.

        Yields:
            Any: A database connection object (PostgreSQL or DuckDB).
        """
        conn = None
        
        # Strategy:
        # 1. Try to connect to Postgres if enabled.
        # 2. If CONNECTION fails, catch it locally, switch to DuckDB, and proceed.
        # 3. If connected successfully, YIELD the connection.
        # 4. If an exception occurs DURING usage (inside the 'with' block), DO NOT catch it here.
        #    Let it propagate. Do NOT try to switch db and yield again (illegal in generator).
        
        if self.use_postgres:
            try:
                conn = psycopg2.connect(
                    settings.DATABASE_URL,
                    connect_timeout=10,
                    options="-c statement_timeout=30000"
                )
            except Exception as e:
                logger.error(f"PostgreSQL Connection Error: {e}")
                logger.warning("Falling back to DuckDB due to connection failure")
                self._fallback_to_duckdb()
                # Fall through to DuckDB logic below
                conn = None

        if not self.use_postgres or conn is None:
            # DuckDB implementation
            max_retries = 5
            retry_delay = 0.5
            for attempt in range(max_retries):
                try:
                    conn = duckdb.connect(str(self.db_path), read_only=self.read_only)
                    break
                except Exception as e:
                    if "used by another process" in str(e) and attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    raise e
                    
        # Now yield the established connection (Postgres or DuckDB)
        try:
            yield conn
        finally:
            if conn:
                conn.close()

    def _init_tables(self) -> None:
        """
        Initializes database tables for the active connection (PostgreSQL or DuckDB).
        """
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
                    fee DOUBLE PRECISION,
                    gross_pnl DOUBLE PRECISION,
                    net_pnl DOUBLE PRECISION,
                    entry_fee DOUBLE PRECISION,
                    exit_fee DOUBLE PRECISION,
                    rollover_fee DOUBLE PRECISION,
                    total_fees DOUBLE PRECISION
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
            
            # Cooldown tracking table for state persistence
            cooldowns_sql = """
                CREATE TABLE IF NOT EXISTS cooldowns (
                    symbol VARCHAR PRIMARY KEY,
                    last_trade_time TIMESTAMP
                )
            """
            
            cursor.execute(ohlcv_sql)
            cursor.execute(trades_sql)
            cursor.execute(balance_sql)
            cursor.execute(bot_status_sql)
            cursor.execute(cooldowns_sql)
            if self.use_postgres:
                conn.commit()

    def save_ohlcv(self, df: pd.DataFrame, symbol: str, exchange: str, timeframe: str) -> None:
        """
        Saves OHLCV (Open, High, Low, Close, Volume) data to the database.

        Args:
            df (pd.DataFrame): DataFrame containing OHLCV data.
            symbol (str): The trading symbol (e.g., 'BTC/USDT').
            exchange (str): The exchange name (e.g., 'binance').
            timeframe (str): The time interval (e.g., '1h').
        """
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
        """
        Loads OHLCV data from the database.

        Args:
            symbol (str): The trading symbol.
            timeframe (str): The time interval.

        Returns:
            pd.DataFrame: DataFrame containing the OHLCV data.
        """
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
                    with warnings.catch_warnings():
                        warnings.filterwarnings("ignore", category=UserWarning, message=".*pandas only supports SQLAlchemy connectable.*")
                        return pd.read_sql(query, conn, params=(symbol, timeframe))
                else:
                    return conn.execute(query, [symbol, timeframe]).df()
        except Exception as e:
            logger.error(f"Error loading OHLCV: {e}")
            return pd.DataFrame()

    def save_trade(self, trade_data: dict) -> None:
        """
        Save or update a trade record.

        Args:
            trade_data (dict): Dictionary containing trade details.
        """
        if self.read_only:
            return
        
        # Sanitize all values to native Python types
        sanitized_data = self._sanitize_dict(trade_data)
            
        keys = sanitized_data.keys()
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
                    cursor.execute(query, list(sanitized_data.values()))
                    conn.commit()
                else:
                    conn.execute(query, list(sanitized_data.values()))
                logger.info(f"Trade {sanitized_data.get('id')} saved/updated.")
        except Exception as e:
            logger.error(f"Error saving trade: {e}")
            # On Postgres query error, fallback to DuckDB and retry
            if self.use_postgres:
                logger.warning("Falling back to DuckDB for this operation")
                self._fallback_to_duckdb()
                try:
                    with self._get_connection() as conn:
                        conn.execute(query.replace("%s", "?"), list(sanitized_data.values()))
                    logger.info(f"Trade {sanitized_data.get('id')} saved/updated via DuckDB.")
                except Exception as e2:
                    logger.error(f"DuckDB fallback also failed: {e2}")

    def update_balance(self, total: float, free: float, used: float) -> None:
        """
        Record current account balance.

        Args:
            total (float): Total account value.
            free (float): Available capital.
            used (float): tied up capital.
        """
        if self.read_only:
            return
        
        # Sanitize values for SQL compatibility
        ts = datetime.now()
        total_val = self._sanitize_value(total)
        free_val = self._sanitize_value(free)
        used_val = self._sanitize_value(used)
        
        try:
            with self._get_connection() as conn:
                if self.use_postgres:
                    query = "INSERT INTO balance (timestamp, total, free, used) VALUES (%s, %s, %s, %s)"
                    cursor = conn.cursor()
                    cursor.execute(query, [ts, total_val, free_val, used_val])
                    conn.commit()
                else:
                    query = "INSERT INTO balance (timestamp, total, free, used) VALUES (?, ?, ?, ?)"
                    conn.execute(query, [ts, total_val, free_val, used_val])
                logger.debug(f"Balance updated: {total}")
        except Exception as e:
            logger.error(f"Error updating balance: {e}")
            # On Postgres query error, fallback to DuckDB and retry
            if self.use_postgres:
                logger.warning("Falling back to DuckDB for balance update")
                self._fallback_to_duckdb()
                try:
                    query = "INSERT INTO balance (timestamp, total, free, used) VALUES (?, ?, ?, ?)"
                    with self._get_connection() as conn:
                        conn.execute(query, [ts, total_val, free_val, used_val])
                    logger.debug(f"Balance updated via DuckDB: {total}")
                except Exception as e2:
                    logger.error(f"DuckDB fallback also failed: {e2}")

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
                    with warnings.catch_warnings():
                        warnings.filterwarnings("ignore", category=UserWarning, message=".*pandas only supports SQLAlchemy connectable.*")
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
        
        # Sanitize timestamp to native Python datetime
        timestamp = datetime.now()
        
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
                    # DuckDB uses ON CONFLICT syntax, not INSERT OR REPLACE
                    conn.execute("""
                        INSERT INTO bot_status (id, status, last_heartbeat, open_positions, exchange, mode)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT (id) DO UPDATE SET
                            status = EXCLUDED.status,
                            last_heartbeat = EXCLUDED.last_heartbeat,
                            open_positions = EXCLUDED.open_positions,
                            exchange = EXCLUDED.exchange,
                            mode = EXCLUDED.mode
                    """, [1, status, timestamp, open_positions, exchange, mode])
                logger.debug(f"Bot status updated: {status}")
        except Exception as e:
            logger.error(f"Error updating bot status: {e}")
            # On Postgres query error, fallback to DuckDB and retry
            if self.use_postgres:
                logger.warning("Falling back to DuckDB for bot status update")
                self._fallback_to_duckdb()
                try:
                    with self._get_connection() as conn:
                        conn.execute("""
                            INSERT INTO bot_status (id, status, last_heartbeat, open_positions, exchange, mode)
                            VALUES (?, ?, ?, ?, ?, ?)
                            ON CONFLICT (id) DO UPDATE SET
                                status = EXCLUDED.status,
                                last_heartbeat = EXCLUDED.last_heartbeat,
                                open_positions = EXCLUDED.open_positions,
                                exchange = EXCLUDED.exchange,
                                mode = EXCLUDED.mode
                        """, [1, status, timestamp, open_positions, exchange, mode])
                    logger.debug(f"Bot status updated via DuckDB: {status}")
                except Exception as e2:
                    logger.error(f"DuckDB fallback also failed: {e2}")

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

    def save_cooldown(self, symbol: str, last_trade_time: datetime) -> None:
        """Save cooldown state for a symbol (persists across restarts)."""
        if self.read_only:
            return
        
        try:
            with self._get_connection() as conn:
                if self.use_postgres:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO cooldowns (symbol, last_trade_time)
                        VALUES (%s, %s)
                        ON CONFLICT (symbol) DO UPDATE SET
                            last_trade_time = EXCLUDED.last_trade_time
                    """, [symbol, last_trade_time])
                    conn.commit()
                else:
                    conn.execute("""
                        INSERT INTO cooldowns (symbol, last_trade_time)
                        VALUES (?, ?)
                        ON CONFLICT (symbol) DO UPDATE SET
                            last_trade_time = EXCLUDED.last_trade_time
                    """, [symbol, last_trade_time])
                logger.debug(f"Saved cooldown for {symbol}")
        except Exception as e:
            logger.error(f"Error saving cooldown: {e}")

    def get_cooldowns(self) -> Dict[str, datetime]:
        """Get all active cooldowns from database."""
        query = "SELECT symbol, last_trade_time FROM cooldowns"
        try:
            with self._get_connection() as conn:
                if self.use_postgres:
                    cursor = conn.cursor()
                    cursor.execute(query)
                    rows = cursor.fetchall()
                else:
                    rows = conn.execute(query).fetchall()
                
                cooldowns = {}
                for row in rows:
                    symbol, last_trade = row
                    if isinstance(last_trade, str):
                        last_trade = pd.to_datetime(last_trade)
                    if hasattr(last_trade, 'replace'):
                        last_trade = last_trade.replace(tzinfo=None)
                    cooldowns[symbol] = last_trade
                return cooldowns
        except Exception as e:
            logger.error(f"Error getting cooldowns: {e}")
        return {}

    def get_balance_history(self, hours: int = 24) -> pd.DataFrame:
        """Get balance history for equity curve visualization.
        
        Args:
            hours: Number of hours of history to retrieve.
            
        Returns:
            DataFrame with timestamp, total, free, used columns.
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        query = """
            SELECT timestamp, total, free, used
            FROM balance
            WHERE timestamp > %s
            ORDER BY timestamp ASC
        """
        if not self.use_postgres:
            query = query.replace("%s", "?")
            
        try:
            with self._get_connection() as conn:
                if self.use_postgres:
                    with warnings.catch_warnings():
                        warnings.filterwarnings("ignore", category=UserWarning, message=".*pandas only supports SQLAlchemy connectable.*")
                        return pd.read_sql(query, conn, params=[cutoff])
                else:
                    return conn.execute(query, [cutoff]).df()
        except Exception as e:
            logger.error(f"Error getting balance history: {e}")
            return pd.DataFrame(columns=["timestamp", "total", "free", "used"])

    def clear_expired_cooldowns(self, cooldown_minutes: int = 5) -> None:
        """Remove cooldowns that have expired."""
        if self.read_only:
            return
        
        try:
            cutoff = datetime.now() - timedelta(minutes=cooldown_minutes)
            with self._get_connection() as conn:
                if self.use_postgres:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM cooldowns WHERE last_trade_time < %s", [cutoff])
                    conn.commit()
                else:
                    conn.execute("DELETE FROM cooldowns WHERE last_trade_time < ?", [cutoff])
                logger.debug("Cleared expired cooldowns")
        except Exception as e:
            logger.error(f"Error clearing cooldowns: {e}")

