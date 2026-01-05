"""
Test script to verify all 50 trading pairs work with Kraken API
"""
import sys
from pathlib import Path

# Add project root to python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

import ccxt
from src.config.settings import settings

def test_all_pairs():
    print(f"=== Testing {len(settings.SYMBOLS)} Trading Pairs ===\n")
    
    exchange = ccxt.kraken()
    
    successful = []
    failed = []
    
    for i, pair in enumerate(settings.SYMBOLS, 1):
        try:
            ticker = exchange.fetch_ticker(pair)
            price = ticker['last']
            successful.append((pair, price))
            print(f"✓ {i:2d}. {pair:15s} - Prix: {price:>12,.2f} EUR")
        except Exception as e:
            failed.append((pair, str(e)))
            print(f"✗ {i:2d}. {pair:15s} - ERREUR: {e}")
    
    print(f"\n{'='*60}")
    print(f"Résultats:")
    print(f"  ✓ Succès: {len(successful)}/{len(settings.SYMBOLS)}")
    print(f"  ✗ Échecs: {len(failed)}/{len(settings.SYMBOLS)}")
    
    if failed:
        print(f"\nPaires en échec:")
        for pair, error in failed:
            print(f"  - {pair}: {error}")
    
    return len(failed) == 0

if __name__ == "__main__":
    success = test_all_pairs()
    sys.exit(0 if success else 1)
