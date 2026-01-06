"""
Database Migration Script: Add Fee Columns to trades table.

This script adds the missing fee tracking columns to both PostgreSQL and DuckDB.
Run once to migrate existing databases.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
import duckdb
from loguru import logger
from src.config.settings import settings

# New columns to add to trades table
NEW_COLUMNS = [
    ("gross_pnl", "DOUBLE PRECISION"),
    ("net_pnl", "DOUBLE PRECISION"),
    ("entry_fee", "DOUBLE PRECISION"),
    ("exit_fee", "DOUBLE PRECISION"),
    ("rollover_fee", "DOUBLE PRECISION"),
    ("total_fees", "DOUBLE PRECISION"),
]

def migrate_postgresql():
    """Add missing columns to PostgreSQL trades table."""
    if not settings.DATABASE_URL:
        print("No DATABASE_URL configured, skipping PostgreSQL migration")
        return False
    
    try:
        conn = psycopg2.connect(settings.DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor()
        
        for col_name, col_type in NEW_COLUMNS:
            try:
                cursor.execute(f"ALTER TABLE trades ADD COLUMN IF NOT EXISTS {col_name} {col_type}")
                print(f"[PostgreSQL] Added column: {col_name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"[PostgreSQL] Column {col_name} already exists")
                else:
                    print(f"[PostgreSQL] Error adding {col_name}: {e}")
        
        conn.commit()
        conn.close()
        print("[PostgreSQL] Migration completed successfully!")
        return True
    except Exception as e:
        print(f"[PostgreSQL] Connection/Migration failed: {e}")
        return False

def migrate_duckdb():
    """Add missing columns to DuckDB trades table."""
    db_path = settings.DATA_PATH / "duckdb" / "market_data.duckdb"
    
    if not db_path.exists():
        print(f"[DuckDB] Database not found at {db_path}, skipping")
        return False
    
    try:
        conn = duckdb.connect(str(db_path), read_only=False)
        
        # Get existing columns
        existing = conn.execute("PRAGMA table_info('trades')").fetchall()
        existing_cols = {row[1] for row in existing}
        
        for col_name, col_type in NEW_COLUMNS:
            if col_name not in existing_cols:
                try:
                    # DuckDB uses DOUBLE instead of DOUBLE PRECISION
                    duckdb_type = "DOUBLE" if col_type == "DOUBLE PRECISION" else col_type
                    conn.execute(f"ALTER TABLE trades ADD COLUMN {col_name} {duckdb_type}")
                    print(f"[DuckDB] Added column: {col_name}")
                except Exception as e:
                    print(f"[DuckDB] Error adding {col_name}: {e}")
            else:
                print(f"[DuckDB] Column {col_name} already exists")
        
        conn.close()
        print("[DuckDB] Migration completed successfully!")
        return True
    except Exception as e:
        print(f"[DuckDB] Migration failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Database Migration: Adding Fee Tracking Columns")
    print("=" * 60)
    
    pg_ok = migrate_postgresql()
    duck_ok = migrate_duckdb()
    
    print("\n" + "=" * 60)
    if pg_ok or duck_ok:
        print("Migration completed! You can now restart the trading bot.")
    else:
        print("No migrations were performed.")
    print("=" * 60)
