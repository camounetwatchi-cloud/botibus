import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from src.config.settings import settings
from src.data.storage import DataStorage
from loguru import logger

def verify_implementation():
    with open("verify_result.log", "w", encoding="utf-8") as f:
        def log(msg):
            print(msg)
            f.write(msg + "\n")
            
        log("--- Verifying Implementation ---")
        
        # Initialize Storage
        log("\nInitializing DataStorage...")
        try:
            storage = DataStorage(read_only=True)
            
            # Check new property
            log(f"\nStorage Type: {storage.storage_type}")
            
            if storage.use_postgres:
                log("✅ Storage initialized with PostgreSQL (Supabase)")
            else:
                log("⚠️ Storage initialized with DuckDB (Local Fallback)")
                
            # Check for connection error
            if storage.connection_error:
                 log(f"Captured Connection Error: {storage.connection_error}")
            else:
                 log("No connection error captured (or connection successful).")

        except Exception as e:
            log(f"❌ Error initializing storage: {e}")

if __name__ == "__main__":
    verify_implementation()
