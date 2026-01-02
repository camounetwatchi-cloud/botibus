import duckdb
from pathlib import Path

db_path = Path("data/duckdb/market_data.duckdb")

if db_path.exists():
    print(f"Connecting to {db_path}...")
    conn = duckdb.connect(str(db_path))
    try:
        print("Clearing trades table...")
        conn.execute("DELETE FROM trades")
        print("Clearing balance table...")
        conn.execute("DELETE FROM balance")
        print("Vacuuming database...")
        conn.execute("VACUUM")
        print("✅ Database reset successful.")
    except Exception as e:
        print(f"❌ Error resetting database: {e}")
    finally:
        conn.close()
else:
    print("Database file not found, nothing to reset.")
