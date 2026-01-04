#!/usr/bin/env python3
"""Unit test to reproduce and fix the market_open_et error for BYD"""

from main import LayoffTracker
from datetime import datetime, timezone

print("=" * 80)
print("BYD market_open_et Error Test")
print("=" * 80)

tracker = LayoffTracker()

# Create a mock BYD layoff that would trigger the error
# BYD ticker is 1211.HK (Hong Kong exchange)
mock_layoff = {
    'company_name': 'BYD Company Ltd.',
    'stock_ticker': '1211.HK',
    'datetime': datetime(2025, 11, 30, 4, 48, tzinfo=timezone.utc),  # Sunday 4:48 UTC = market closed
    'date': '2025-11-30',
    'time': '04:48:00',
    'url': 'https://test.com/byd',
    'title': 'BYD test article'
}

print(f"\n📰 Testing BYD stock changes calculation...")
print(f"   Company: {mock_layoff['company_name']}")
print(f"   Ticker: {mock_layoff['stock_ticker']}")
print(f"   Date: {mock_layoff['date']} {mock_layoff['time']}")

try:
    stock_changes = tracker.calculate_stock_changes(mock_layoff)
    print(f"\n✅ Successfully calculated stock changes")
    print(f"   Base price: ${stock_changes.get('base_price'):.2f}" if stock_changes.get('base_price') else "   Base price: None")
    print(f"   Market was open: {stock_changes.get('market_was_open')}")
    
    # Check a few intervals
    for interval in ['5min', '10min', '30min', '1hr']:
        price = stock_changes.get(f'price_{interval}')
        market_closed = stock_changes.get(f'market_closed_{interval}')
        if price:
            print(f"   {interval}: ${price:.2f}")
        elif market_closed:
            print(f"   {interval}: Market Closed")
        else:
            print(f"   {interval}: N/A")
            
except NameError as e:
    if 'market_open_et' in str(e):
        print(f"\n❌ ERROR REPRODUCED: {e}")
        print(f"\n   This confirms the bug - market_open_et is not defined")
        print(f"   Need to fix line 3036 in main.py")
    else:
        print(f"\n❌ NameError: {e}")
        import traceback
        traceback.print_exc()
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)

