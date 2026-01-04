#!/usr/bin/env python3
"""Full flow unit test with stock price calculation - tests exchange detection"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

print("\n" + "=" * 80)
print("Full Flow Unit Test with Stock Prices")
print("=" * 80)

tracker = LayoffTracker()

# Test 1: US Stock (AAPL)
print("\n[Test 1] Testing US stock (AAPL) with stock price calculation...")
us_article_date = datetime(2025, 12, 1, 14, 30, tzinfo=timezone.utc)  # 2:30 PM UTC = 9:30 AM ET
us_layoff = {
    'company_name': 'Apple Inc.',
    'stock_ticker': 'AAPL',
    'datetime': us_article_date,
    'date': us_article_date.strftime('%Y-%m-%d'),
    'time': us_article_date.strftime('%H:%M:%S'),
    'url': 'https://test.com/aapl',
    'title': 'Apple test article'
}

try:
    stock_changes = tracker.calculate_stock_changes(us_layoff)
    base_price = stock_changes.get('base_price')
    market_was_open = stock_changes.get('market_was_open')
    
    if base_price:
        print(f"✅ PASSED: US stock - Base price: ${base_price:.2f}, Market was open: {market_was_open}")
        
        # Check if we got some interval prices
        intervals_with_prices = sum(1 for i in ['5min', '10min', '30min', '1hr'] if stock_changes.get(f'price_{i}') is not None)
        print(f"   Intervals with prices: {intervals_with_prices}/4")
    else:
        print(f"⚠️  WARNING: US stock - No base price (may be data unavailable)")
except Exception as e:
    print(f"❌ FAILED: US stock calculation error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Hong Kong Stock (BYD - 1211.HK)
print("\n[Test 2] Testing Hong Kong stock (1211.HK) with exchange detection...")
hk_article_date = datetime(2025, 11, 30, 4, 48, tzinfo=timezone.utc)  # Sun, Nov 30, 4:48 AM UTC
hk_layoff = {
    'company_name': 'BYD Company Limited',
    'stock_ticker': '1211.HK',
    'datetime': hk_article_date,
    'date': hk_article_date.strftime('%Y-%m-%d'),
    'time': hk_article_date.strftime('%H:%M:%S'),
    'url': 'https://test.com/byd',
    'title': 'BYD test article'
}

try:
    stock_changes = tracker.calculate_stock_changes(hk_layoff)
    base_price = stock_changes.get('base_price')
    market_was_open = stock_changes.get('market_was_open')
    
    if base_price:
        print(f"✅ PASSED: HK stock - Base price: ${base_price:.2f}, Market was open: {market_was_open}")
        
        # Check if we got interval prices (should work now with exchange detection)
        intervals_with_prices = sum(1 for i in ['5min', '10min', '30min', '1hr'] if stock_changes.get(f'price_{i}') is not None)
        print(f"   Intervals with prices: {intervals_with_prices}/4")
        
        if intervals_with_prices > 0:
            print(f"   ✅ Exchange detection working - got prices for HK stock!")
            # Show sample prices
            for interval in ['5min', '10min', '30min']:
                price = stock_changes.get(f'price_{interval}')
                change = stock_changes.get(f'change_{interval}')
                if price:
                    print(f"      {interval}: ${price:.2f} ({change:+.2f}%)" if change else f"      {interval}: ${price:.2f}")
        else:
            print(f"   ⚠️  No interval prices (may be expected if data unavailable)")
    else:
        print(f"⚠️  WARNING: HK stock - No base price (may be data unavailable)")
except Exception as e:
    print(f"❌ FAILED: HK stock calculation error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Market Open Check with Exchange Detection
print("\n[Test 3] Testing market open check with exchange detection...")
test_times = [
    (datetime(2025, 12, 1, 19, 0, tzinfo=timezone.utc), 'AAPL', True, 'US market 2:00 PM ET'),
    (datetime(2025, 12, 1, 2, 0, tzinfo=timezone.utc), '1211.HK', True, 'HK market 10:00 AM HKT'),
    (datetime(2025, 12, 1, 14, 0, tzinfo=timezone.utc), '1211.HK', False, 'HK market 10:00 PM HKT (closed)'),
]

all_passed = True
for test_time, ticker, expected_open, description in test_times:
    try:
        result = tracker.is_market_open(test_time, ticker)
        if result == expected_open:
            status = "✅ PASSED"
        else:
            status = "❌ FAILED"
            all_passed = False
        print(f"   {status}: {description} - Expected: {expected_open}, Got: {result}")
    except Exception as e:
        print(f"   ❌ FAILED: {description} - Error: {e}")
        all_passed = False

if not all_passed:
    sys.exit(1)

# Test 4: Exchange Detection
print("\n[Test 4] Testing exchange detection...")
test_tickers = [
    ('AAPL', 'US'),
    ('TSLA', 'US'),
    ('1211.HK', 'HK'),
    ('AIR.PA', 'PA'),
    ('BP.L', 'L'),
]

all_passed = True
for ticker, expected_exchange in test_tickers:
    try:
        exchange = tracker._detect_exchange_from_ticker(ticker)
        if exchange == expected_exchange:
            print(f"   ✅ PASSED: {ticker} -> {exchange}")
        else:
            print(f"   ❌ FAILED: {ticker} -> {exchange} (expected {expected_exchange})")
            all_passed = False
    except Exception as e:
        print(f"   ❌ FAILED: {ticker} - Error: {e}")
        all_passed = False

if not all_passed:
    sys.exit(1)

# Test 5: Market Open Check without ticker (backward compatibility)
print("\n[Test 5] Testing market open check without ticker (backward compatibility)...")
try:
    test_time = datetime(2025, 12, 1, 19, 0, tzinfo=timezone.utc)
    result = tracker.is_market_open(test_time)  # No ticker parameter
    print(f"   ✅ PASSED: is_market_open() works without ticker parameter: {result}")
except Exception as e:
    print(f"   ❌ FAILED: Error when calling is_market_open() without ticker: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("✅ All tests completed successfully!")
print("=" * 80)

