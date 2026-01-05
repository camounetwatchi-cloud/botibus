"""
Script to fetch top 50 cryptocurrencies available on Kraken
"""
import ccxt
import sys
from pathlib import Path

# Add project root to python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

def get_top_50_kraken_pairs():
    """
    Get top 50 crypto pairs available on Kraken with EUR and USDC
    Based on market cap and liquidity
    """
    
    # Initialize Kraken exchange
    exchange = ccxt.kraken()
    markets = exchange.load_markets()
    
    # Filter for EUR and USDC pairs
    eur_pairs = [s for s in markets.keys() if '/EUR' in s]
    usdc_pairs = [s for s in markets.keys() if '/USDC' in s]
    
    # Top cryptocurrencies by market cap (manually curated list based on CoinMarketCap)
    # This ensures we get the most liquid and established coins
    top_cryptos = [
        'BTC', 'ETH', 'USDT', 'BNB', 'SOL', 'XRP', 'USDC', 'ADA', 'DOGE', 'TRX',
        'AVAX', 'TON', 'LINK', 'DOT', 'MATIC', 'POL', 'SHIB', 'DAI', 'LTC', 'BCH',
        'UNI', 'NEAR', 'ICP', 'APT', 'STX', 'FIL', 'ARB', 'OP', 'IMX', 'ATOM',
        'INJ', 'HBAR', 'SUI', 'RENDER', 'GRT', 'RUNE', 'FET', 'ALGO', 'AAVE', 'ETC',
        'XLM', 'VET', 'FLOW', 'MANA', 'SAND', 'AXS', 'THETA', 'XTZ', 'EOS', 'KAVA',
        'PEPE', 'WIF', 'BONK', 'FLOKI', 'JUP', 'PYTH', 'SEI', 'TIA', 'DYDX', 'BLUR'
    ]
    
    # Build list of available pairs for top cryptos
    available_pairs = []
    
    for crypto in top_cryptos:
        # Prefer EUR pairs for MiCA compliance
        eur_pair = f"{crypto}/EUR"
        usdc_pair = f"{crypto}/USDC"
        
        if eur_pair in eur_pairs:
            available_pairs.append(eur_pair)
        elif usdc_pair in usdc_pairs:
            available_pairs.append(usdc_pair)
    
    # Limit to top 50
    top_50_pairs = available_pairs[:50]
    
    print(f"Found {len(top_50_pairs)} trading pairs from top cryptocurrencies:\n")
    for i, pair in enumerate(top_50_pairs, 1):
        print(f"{i:2d}. {pair}")
    
    print(f"\n\nPython list format for settings.py:")
    print("SYMBOLS: List[str] = [")
    for pair in top_50_pairs:
        print(f'    "{pair}",')
    print("]")
    
    return top_50_pairs

if __name__ == "__main__":
    get_top_50_kraken_pairs()
