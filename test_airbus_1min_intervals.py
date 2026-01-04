#!/usr/bin/env python3
"""Unit test to check if 1min, 2min, 3min, 4min intervals are available for Airbus"""

from main import LayoffTracker
from datetime import datetime, timezone, timedelta

print("=" * 80)
print("Testing 1min, 2min, 3min, 4min Intervals for Airbus (EADSY)")
print("=" * 80)

tracker = LayoffTracker()

# Test with a recent date (within 30 days for 1min data)
# Using Dec 2, 2025 05:33 UTC (same as previous tests)
article_datetime = datetime(2025, 12, 2, 5, 33, tzinfo=timezone.utc)

print(f"\n📰 Article Details:")
print(f"   Company: Airbus")
print(f"   Ticker: EADSY")
print(f"   Published: {article_datetime.strftime('%a, %b %d, %Y %H:%M')} UTC")
print(f"   Published ET: {(article_datetime - timedelta(hours=5)).strftime('%a, %b %d, %Y %H:%M')} ET")

mock_layoff = {
    'company_name': 'Airbus',
    'stock_ticker': 'EADSY',
    'datetime': article_datetime,
    'date': article_datetime.strftime('%Y-%m-%d'),
    'time': article_datetime.strftime('%H:%M:%S'),
    'url': 'https://test.com/airbus',
    'title': 'Airbus test article'
}

# Check if 1min data is available from Prixe.io
print(f"\n🔍 Step 1: Checking if 1min data is available from Prixe.io...")
next_trading_day = tracker.get_next_trading_day(article_datetime, 'EADSY')
if next_trading_day:
    print(f"   Next trading day: {next_trading_day.strftime('%Y-%m-%d')}")
    
    # Try to fetch 1min data
    print(f"   Attempting to fetch 1min intraday data...")
    intraday_1min = tracker._fetch_intraday_data_for_day('EADSY', next_trading_day, interval='1min')
    
    if intraday_1min and intraday_1min.get('success'):
        data = intraday_1min.get('data', {})
        timestamps = data.get('timestamp', [])
        if timestamps:
            print(f"   ✅ 1min data IS available from Prixe.io")
            print(f"      Data points: {len(timestamps)}")
            print(f"      First timestamp: {datetime.fromtimestamp(timestamps[0], tz=timezone.utc).strftime('%H:%M')} UTC")
            print(f"      Last timestamp: {datetime.fromtimestamp(timestamps[-1], tz=timezone.utc).strftime('%H:%M')} UTC")
            has_1min_data = True
        else:
            print(f"   ❌ 1min data returned but has no timestamps")
            has_1min_data = False
    else:
        print(f"   ❌ 1min data is NOT available from Prixe.io")
        if intraday_1min:
            print(f"      Response: {intraday_1min.get('message', 'Unknown error')}")
        has_1min_data = False
    
    # Try to fetch 5min data as fallback
    print(f"\n🔍 Step 2: Checking 5min data availability (fallback)...")
    intraday_5min = tracker._fetch_intraday_data_for_day('EADSY', next_trading_day, interval='5min')
    
    if intraday_5min and intraday_5min.get('success'):
        data = intraday_5min.get('data', {})
        timestamps = data.get('timestamp', [])
        if timestamps:
            print(f"   ✅ 5min data IS available from Prixe.io")
            print(f"      Data points: {len(timestamps)}")
            has_5min_data = True
        else:
            print(f"   ❌ 5min data returned but has no timestamps")
            has_5min_data = False
    else:
        print(f"   ❌ 5min data is NOT available from Prixe.io")
        has_5min_data = False

# Now test the actual calculation
print(f"\n🔍 Step 3: Testing calculate_stock_changes...")
try:
    stock_changes = tracker.calculate_stock_changes(mock_layoff)
    
    print(f"\n📊 Results:")
    print(f"   Base price: ${stock_changes.get('base_price'):.2f}" if stock_changes.get('base_price') else "   Base price: None")
    print(f"   Market was open: {stock_changes.get('market_was_open')}")
    
    print(f"\n📋 Interval Results:")
    intervals_to_check = ['1min', '2min', '3min', '4min', '5min', '10min', '30min']
    
    for interval in intervals_to_check:
        price = stock_changes.get(f'price_{interval}')
        change = stock_changes.get(f'change_{interval}')
        datetime_str = stock_changes.get(f'datetime_{interval}')
        market_closed = stock_changes.get(f'market_closed_{interval}')
        no_intraday_data = stock_changes.get(f'no_intraday_data_{interval}')
        is_daily_close = stock_changes.get(f'is_daily_close_{interval}')
        
        if price is not None:
            dt_str = datetime_str[:16] if datetime_str else 'N/A'
            print(f"   ✅ {interval:6s}: ${price:.2f} ({change:+.2f}%) at {dt_str}")
        else:
            reasons = []
            if market_closed:
                reasons.append("Market closed")
            if no_intraday_data:
                reasons.append("No intraday data")
            if is_daily_close:
                reasons.append("Daily close fallback")
            reason_str = f" ({', '.join(reasons)})" if reasons else ""
            print(f"   ❌ {interval:6s}: None{reason_str}")
    
    print(f"\n{'='*80}")
    print("ANALYSIS:")
    print(f"{'='*80}")
    
    # Check if 1min intervals have data
    has_1min_intervals = all(stock_changes.get(f'price_{interval}') is not None for interval in ['1min', '2min', '3min', '4min'])
    has_5min_intervals = stock_changes.get('price_5min') is not None
    
    if has_1min_intervals:
        print("✅ All 1min, 2min, 3min, 4min intervals have data")
        print("   → Prixe.io provides 1min data, and extraction is working correctly")
    else:
        print("❌ 1min, 2min, 3min, 4min intervals are missing data")
        if has_5min_intervals:
            print("   → 5min interval has data, but 1-4min don't")
            print("   → This suggests Prixe.io doesn't have 1min data for this date")
            print("   → OR the code is correctly skipping 1-4min when only 5min data is available")
        else:
            print("   → Even 5min interval is missing data")
            print("   → This suggests no intraday data is available for this date")
    
    # Check specific intervals
    print(f"\nDetailed Status:")
    for interval in ['1min', '2min', '3min', '4min']:
        price = stock_changes.get(f'price_{interval}')
        no_data = stock_changes.get(f'no_intraday_data_{interval}')
        if price is None and no_data:
            print(f"   {interval}: Correctly marked as 'no_intraday_data' (expected when only 5min data available)")
        elif price is not None:
            print(f"   {interval}: Has data (1min data was available)")
        else:
            print(f"   {interval}: Missing data (unexpected)")
    
    print(f"\n{'='*80}")
    print("CONCLUSION:")
    print(f"{'='*80}")
    
    if has_1min_intervals:
        print("✅ 1min, 2min, 3min, 4min intervals ARE available for Airbus")
        print("   The UI should show prices for these intervals")
    else:
        print("❌ 1min, 2min, 3min, 4min intervals are NOT available for Airbus")
        print("   This is expected if:")
        print("   1. Prixe.io doesn't have 1min data for this date (outside 30-day limit)")
        print("   2. Only 5min data is available, and the code correctly skips 1-4min intervals")
        print("   The UI showing 'N/A' is CORRECT behavior")
    
except Exception as e:
    print(f"\n❌ Error during calculation: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)

