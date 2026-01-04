#!/usr/bin/env python3
"""
Test if ticker format "NYSE: ATI" is causing issues
"""

from datetime import datetime, timezone
from main import LayoffTracker

tracker = LayoffTracker()

print(f"\n{'='*80}")
print("Testing Ticker Format Issues")
print(f"{'='*80}\n")

# Test different ticker formats
ticker_variants = [
    'NYSE: ATI',
    'ATI',
    'BRK.A',
    'BRK-A',
    'SKAB.ST',
    'SKAB',
]

for ticker_variant in ticker_variants:
    print(f"\nTesting: '{ticker_variant}'")
    print("-" * 80)
    
    # Clean ticker (remove exchange prefix if present)
    clean_ticker = ticker_variant
    if ':' in ticker_variant:
        clean_ticker = ticker_variant.split(':')[-1].strip()
        print(f"  Cleaned ticker: '{clean_ticker}'")
    
    # Test if ticker is valid
    is_valid = tracker._is_valid_ticker(clean_ticker)
    print(f"  Valid in SEC EDGAR: {is_valid}")
    
    # Test Prixe.io
    test_date = datetime(2025, 12, 8, 0, 0, 0, tzinfo=timezone.utc)
    test_data = tracker._fetch_price_data_batch(clean_ticker, test_date, test_date, '1d')
    
    if test_data and test_data.get('success'):
        print(f"  ✓ Exists in Prixe.io")
        data = test_data.get('data', {})
        timestamps = data.get('timestamp', [])
        closes = data.get('close', [])
        print(f"    Data points: {len(timestamps)}")
        if timestamps and closes:
            print(f"    Latest close: ${closes[0]:.2f}")
    else:
        print(f"  ✗ NOT found in Prixe.io")
        if test_data:
            print(f"    Response: {test_data.get('success', False)}")
    
    # Test exchange detection
    exchange = tracker._detect_exchange_from_ticker(clean_ticker)
    print(f"  Detected exchange: {exchange}")
    
    # Test market hours
    market_open = tracker._get_market_open_time(test_date, clean_ticker)
    market_close = tracker._get_market_close_time(test_date, clean_ticker)
    print(f"  Market open (UTC): {market_open}")
    print(f"  Market close (UTC): {market_close}")

