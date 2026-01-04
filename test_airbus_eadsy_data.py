#!/usr/bin/env python3
"""Unit test to verify Airbus EADSY data correctness"""

from main import LayoffTracker
from datetime import datetime, timezone, timedelta

print("=" * 80)
print("Airbus EADSY Data Verification Test")
print("=" * 80)

tracker = LayoffTracker()

# Article published: Tue, Dec 2, 2025 05:33 (Market Closed)
# This is 05:33 UTC = 00:33 ET (EST) - market is closed
article_datetime = datetime(2025, 12, 2, 5, 33, tzinfo=timezone.utc)

print(f"\n📰 Article Details:")
print(f"   Company: Airbus")
print(f"   Ticker: EADSY")
print(f"   Published: {article_datetime.strftime('%a, %b %d, %Y %H:%M')} UTC")
print(f"   Published ET: {(article_datetime - timedelta(hours=5)).strftime('%a, %b %d, %Y %H:%M')} ET")
print(f"   Market Status: Closed (published before market open)")

mock_layoff = {
    'company_name': 'Airbus',
    'stock_ticker': 'EADSY',
    'datetime': article_datetime,
    'date': article_datetime.strftime('%Y-%m-%d'),
    'time': article_datetime.strftime('%H:%M:%S'),
    'url': 'https://test.com/airbus',
    'title': 'Airbus test article'
}

print(f"\n🔍 Calculating stock changes...")
try:
    stock_changes = tracker.calculate_stock_changes(mock_layoff)
    
    print(f"\n✅ Calculation successful")
    print(f"\n📊 Results:")
    print(f"   Base price: ${stock_changes.get('base_price'):.2f}" if stock_changes.get('base_price') else "   Base price: None")
    print(f"   Market was open: {stock_changes.get('market_was_open')}")
    
    # Expected data from UI
    expected_data = {
        'base_price': 57.84,
        'base_change': 3.51,
        'intervals': {
            '5min': {'price': 57.86, 'change': 3.54, 'vol_change': 87.37, 'date': '2025-12-03', 'time': '09:35'},
            '10min': {'price': 58.00, 'change': 3.79, 'vol_change': -79.22, 'date': '2025-12-03', 'time': '09:40'},
            '30min': {'price': 57.83, 'change': 3.49, 'vol_change': -90.56, 'date': '2025-12-03', 'time': '10:00'},
            '1hr': {'price': 57.78, 'change': 3.40, 'vol_change': -96.77, 'date': '2025-12-03', 'time': '10:30'},
            '1.5hr': {'price': 57.71, 'change': 3.27, 'vol_change': 645.91, 'date': '2025-12-03', 'time': '11:00'},
            '2hr': {'price': 57.75, 'change': 3.35, 'vol_change': 36.16, 'date': '2025-12-03', 'time': '11:30'},
            '2.5hr': {'price': 57.72, 'change': 3.29, 'vol_change': -34.18, 'date': '2025-12-03', 'time': '12:00'},
        }
    }
    
    print(f"\n🔍 Verifying against expected data:")
    print(f"   Expected base price: ${expected_data['base_price']:.2f}")
    
    # Check base price
    actual_base = stock_changes.get('base_price')
    if actual_base:
        base_diff = abs(actual_base - expected_data['base_price'])
        base_match = base_diff < 0.01
        print(f"   Actual base price: ${actual_base:.2f}")
        print(f"   {'✅' if base_match else '❌'} Base price match: {base_match} (diff: ${base_diff:.2f})")
    else:
        print(f"   ❌ Base price is None")
    
    # Check intervals
    print(f"\n📋 Interval Verification:")
    all_match = True
    
    for interval_name, expected in expected_data['intervals'].items():
        actual_price = stock_changes.get(f'price_{interval_name}')
        actual_change = stock_changes.get(f'change_{interval_name}')
        actual_vol_change = stock_changes.get(f'volume_change_{interval_name}')
        actual_date = stock_changes.get(f'date_{interval_name}')
        actual_datetime = stock_changes.get(f'datetime_{interval_name}')
        
        price_match = actual_price and abs(actual_price - expected['price']) < 0.01
        change_match = actual_change and abs(actual_change - expected['change']) < 0.01
        vol_match = actual_vol_change and abs(actual_vol_change - expected['vol_change']) < 0.01
        
        status = "✅" if (price_match and change_match and vol_match) else "❌"
        if not (price_match and change_match and vol_match):
            all_match = False
        
        print(f"\n   {interval_name} ({expected['time']} ET):")
        if actual_price:
            print(f"      Price: {status} ${actual_price:.2f} (expected ${expected['price']:.2f}, diff: ${abs(actual_price - expected['price']):.2f})")
        else:
            print(f"      Price: ❌ None (expected ${expected['price']:.2f})")
            all_match = False
        
        if actual_change:
            print(f"      Change: {status} {actual_change:+.2f}% (expected {expected['change']:+.2f}%, diff: {abs(actual_change - expected['change']):.2f}%)")
        else:
            print(f"      Change: ❌ None (expected {expected['change']:+.2f}%)")
            all_match = False
        
        if actual_vol_change is not None:
            print(f"      Volume: {status} {actual_vol_change:+.2f}% (expected {expected['vol_change']:+.2f}%, diff: {abs(actual_vol_change - expected['vol_change']):.2f}%)")
        else:
            print(f"      Volume: ❌ None (expected {expected['vol_change']:+.2f}%)")
            all_match = False
        
        if actual_date:
            date_match = actual_date == expected['date']
            print(f"      Date: {'✅' if date_match else '❌'} {actual_date} (expected {expected['date']})")
            if not date_match:
                all_match = False
    
    print(f"\n{'='*80}")
    if all_match:
        print("✅✅✅ ALL DATA MATCHES EXPECTED VALUES!")
    else:
        print("❌❌❌ SOME DATA DOES NOT MATCH - CHECK DIFFERENCES ABOVE")
    print(f"{'='*80}")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)

