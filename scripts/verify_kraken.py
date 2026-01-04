import sys
import os
from pathlib import Path
import ccxt

# Add project root to python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.config.settings import settings

def test_kraken():
    print("--- Kraken Connection Test ---")
    
    # 1. Test Public API
    print("1. Testing Public API (fetch_ticker)...")
    try:
        kraken_public = ccxt.kraken()
        ticker = kraken_public.fetch_ticker('BTC/EUR')
        print(f"   [SUCCESS] Public API OK. BTC/EUR Price: {ticker['last']}")
    except Exception as e:
        print(f"   [FAILED] Public API Error: {e}")
        return

    # 2. Test Private API
    print("\n2. Testing Private API (fetch_balance)...")
    api_key = settings.KRAKEN_API_KEY
    secret = settings.KRAKEN_SECRET_KEY
    
    if not api_key or not secret:
        print("   [SKIP] Keys missing in settings/env. Please add them to .env")
        return

    print(f"   Using API Key: {api_key[:4]}...{api_key[-4:]}")
    
    try:
        exchange = ccxt.kraken({
            'apiKey': api_key,
            'secret': secret,
        })
        balance = exchange.fetch_balance()
        print("   [SUCCESS] Private API OK.")
        # Try to find some balance
        for coin in ['EUR', 'BTC', 'USDC']:
            if coin in balance:
                print(f"   {coin} Balance: {balance[coin]['total']}")
    except Exception as e:
        print(f"   [FAILED] Private API Error: {e}")

if __name__ == "__main__":
    test_kraken()
