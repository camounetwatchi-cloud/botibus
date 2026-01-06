import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from src.config.settings import settings
from src.data.storage import DataStorage
from loguru import logger

def debug_connection():
    print("--- Debugging Connection ---")
    
    # Check if DATABASE_URL is set in settings
    db_url = settings.DATABASE_URL
    if db_url:
        # Basic masking
        print(f"DATABASE_URL is set (starts with {db_url[:15]}...)")
    else:
        print("DATABASE_URL is NOT set in settings.")
        
    print(f"DATA_PATH: {settings.DATA_PATH}")
    
    # Initialize Storage
    print("\nInitializing DataStorage...")
    try:
        storage = DataStorage(read_only=True)
        
        if storage.use_postgres:
            print("✅ Storage initialized with PostgreSQL (Supabase)")
            print("Connection successful.")
            
            # Try to fetch latest bot status
            status = storage.get_bot_status()
            print(f"\nBot Status from DB: {status}")
            
            # Fetch latest balance
            balance = storage.get_latest_balance()
            print(f"Latest Balance from DB: {balance}")
            
        else:
            print("⚠️ Storage initialized with DuckDB (Local Fallback)")
            print("This explains why you see old data if the bot is running in the cloud.")
            print(f"Local DuckDB path: {storage.db_path}")
            
    except Exception as e:
        print(f"❌ Error initializing storage: {e}")

if __name__ == "__main__":
    debug_connection()
