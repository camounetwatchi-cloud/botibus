
import sys
import os

# Add src to path
sys.path.append(os.getcwd())

print("Verifying imports...")

try:
    print("Importing src.monitoring.dashboard...")
    from src.monitoring import dashboard
    print("Dashboard imported.")
except Exception as e:
    print(f"Failed to import dashboard: {e}")
    sys.exit(1)

try:
    print("Importing src.data.storage...")
    from src.data.storage import DataStorage
    print("DataStorage imported.")
except Exception as e:
    print(f"Failed to import storage: {e}")
    sys.exit(1)

try:
    print("Importing src.trading.executor...")
    from src.trading.executor import TradeExecutor
    print("TradeExecutor imported.")
except Exception as e:
    print(f"Failed to import executor: {e}")
    sys.exit(1)

print("All modules imported successfully. Syntax is correct.")
