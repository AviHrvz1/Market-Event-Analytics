#!/usr/bin/env python3
"""Test if backend returns data for new intervals (1min, 2min, 3min, 4min)"""

from main import LayoffTracker
from datetime import datetime, timezone

print("=" * 80)
print("Testing New Intervals (1min, 2min, 3min, 4min)")
print("=" * 80)

tracker = LayoffTracker()
article_datetime = datetime(2025, 12, 2, 5, 33, tzinfo=timezone.utc)

mock_layoff = {
    'company_name': 'Airbus',
    'stock_ticker': 'EADSY',
    'datetime': article_datetime,
    'date': article_datetime.strftime('%Y-%m-%d'),
    'time': article_datetime.strftime('%H:%M:%S'),
    'url': 'https://test.com/airbus',
    'title': 'Airbus test article'
}

print(f"\n📊 Calculating stock changes...")
try:
    stock_changes = tracker.calculate_stock_changes(mock_layoff)
    
    print(f"\n✅ Calculation successful")
    print(f"\n📋 Checking new intervals:")
    
    new_intervals = ['1min', '2min', '3min', '4min']
    for interval in new_intervals:
        price = stock_changes.get(f'price_{interval}')
        change = stock_changes.get(f'change_{interval}')
        datetime_str = stock_changes.get(f'datetime_{interval}')
        
        if price is not None:
            print(f"   ✅ {interval}: ${price:.2f} ({change:+.2f}%) at {datetime_str}")
        else:
            print(f"   ❌ {interval}: No data (price is None)")
    
    print(f"\n📋 Checking existing intervals (for comparison):")
    existing_intervals = ['5min', '10min', '30min']
    for interval in existing_intervals:
        price = stock_changes.get(f'price_{interval}')
        change = stock_changes.get(f'change_{interval}')
        datetime_str = stock_changes.get(f'datetime_{interval}')
        
        if price is not None:
            print(f"   ✅ {interval}: ${price:.2f} ({change:+.2f}%) at {datetime_str}")
        else:
            print(f"   ❌ {interval}: No data (price is None)")
    
    print(f"\n{'='*80}")
    print("CONCLUSION:")
    print(f"{'='*80}")
    
    new_intervals_have_data = all(stock_changes.get(f'price_{interval}') is not None for interval in new_intervals)
    if new_intervals_have_data:
        print("✅ All new intervals (1min, 2min, 3min, 4min) have data!")
    else:
        print("❌ Some new intervals are missing data")
        print("   This might be because:")
        print("   1. Prixe.io doesn't have 1min data for this date")
        print("   2. The date is outside the 30-day limit for 1min data")
        print("   3. The market was closed")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)

