#!/usr/bin/env python3
"""Detailed test to compare system calculations with UI data"""

from main import LayoffTracker
from datetime import datetime, timezone, timedelta

print("=" * 80)
print("Airbus EADSY Detailed Data Verification")
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

stock_changes = tracker.calculate_stock_changes(mock_layoff)

print(f"\n📊 System Calculations:")
print(f"   Base price: ${stock_changes.get('base_price'):.2f}")
print(f"   Market was open: {stock_changes.get('market_was_open')}")

# UI shows this data
ui_data = [
    {'label': 'Article time', 'price': 57.84, 'change': 3.51, 'vol': 0.00, 'date': 'Tue, Dec 2, 2025 05:33'},
    {'label': '5min', 'price': 57.86, 'change': 3.54, 'vol': 87.37, 'date': 'Wed, Dec 3, 2025 09:35'},
    {'label': '10min', 'price': 58.00, 'change': 3.79, 'vol': -79.22, 'date': 'Wed, Dec 3, 2025 09:40'},
    {'label': '30min', 'price': 57.83, 'change': 3.49, 'vol': -90.56, 'date': 'Wed, Dec 3, 2025 10:00'},
    {'label': '1hr', 'price': 57.78, 'change': 3.40, 'vol': -96.77, 'date': 'Wed, Dec 3, 2025 10:30'},
    {'label': '1.5hr', 'price': 57.71, 'change': 3.27, 'vol': 645.91, 'date': 'Wed, Dec 3, 2025 11:00'},
    {'label': '2hr', 'price': 57.75, 'change': 3.35, 'vol': 36.16, 'date': 'Wed, Dec 3, 2025 11:30'},
    {'label': '2.5hr', 'price': 57.72, 'change': 3.29, 'vol': -34.18, 'date': 'Wed, Dec 3, 2025 12:00'},
]

print(f"\n🔍 Comparison: System vs UI")
print(f"{'='*80}")

# Check article time price
base_price = stock_changes.get('base_price', 0)
ui_article_price = 57.84
ui_article_change = 3.51

print(f"\nArticle Time Price:")
print(f"   UI shows: ${ui_article_price:.2f} (+{ui_article_change:.2f}%)")
print(f"   System base: ${base_price:.2f}")
calculated_change_from_base = ((ui_article_price - base_price) / base_price * 100) if base_price else 0
print(f"   If UI price is from base: {calculated_change_from_base:+.2f}% (UI shows +{ui_article_change:.2f}%)")
print(f"   {'✅' if abs(calculated_change_from_base - ui_article_change) < 0.1 else '❌'} Match: {abs(calculated_change_from_base - ui_article_change) < 0.1}")

# Check intervals
print(f"\nIntervals (System vs UI):")
interval_map = {
    '5min': '5min',
    '10min': '10min', 
    '30min': '30min',
    '1hr': '1hr',
    '1.5hr': '1.5hr',
    '2hr': '2hr',
    '2.5hr': '2.5hr'
}

for ui_entry in ui_data[1:]:  # Skip article time, start with 5min
    interval_name = ui_entry['label']
    if interval_name in interval_map:
        sys_price = stock_changes.get(f'price_{interval_name}')
        sys_change = stock_changes.get(f'change_{interval_name}')
        sys_vol = stock_changes.get(f'volume_change_{interval_name}')
        sys_date = stock_changes.get(f'date_{interval_name}')
        
        price_match = sys_price and abs(sys_price - ui_entry['price']) < 0.02
        change_match = sys_change and abs(sys_change - ui_entry['change']) < 0.05
        vol_match = sys_vol is not None and abs(sys_vol - ui_entry['vol']) < 1.0
        date_match = sys_date == '2025-12-03'
        
        all_match = price_match and change_match and vol_match and date_match
        status = "✅" if all_match else "❌"
        
        print(f"\n   {interval_name}:")
        print(f"      Price: {status} System ${sys_price:.2f} vs UI ${ui_entry['price']:.2f} (diff: ${abs(sys_price - ui_entry['price']):.2f})" if sys_price else f"      Price: ❌ System None vs UI ${ui_entry['price']:.2f}")
        print(f"      Change: {status} System {sys_change:+.2f}% vs UI {ui_entry['change']:+.2f}% (diff: {abs(sys_change - ui_entry['change']):.2f}%)" if sys_change else f"      Change: ❌ System None vs UI {ui_entry['change']:+.2f}%")
        print(f"      Volume: {status} System {sys_vol:+.2f}% vs UI {ui_entry['vol']:+.2f}% (diff: {abs(sys_vol - ui_entry['vol']):.2f}%)" if sys_vol is not None else f"      Volume: ❌ System None vs UI {ui_entry['vol']:+.2f}%")
        print(f"      Date: {'✅' if date_match else '❌'} System {sys_date} vs UI {ui_entry['date']}")

print(f"\n{'='*80}")
print("CONCLUSION:")
print(f"{'='*80}")

# Check if UI article time price matches system's 5min interval
sys_5min_price = stock_changes.get('price_5min')
sys_5min_change = stock_changes.get('change_5min')

if sys_5min_price and abs(sys_5min_price - ui_article_price) < 0.01:
    print("✅ UI 'Article time' price matches System's 5min interval")
    print(f"   This suggests UI is showing first interval price at article time")
else:
    print("❌ UI 'Article time' price does NOT match System's 5min interval")
    print(f"   UI shows: ${ui_article_price:.2f}")
    print(f"   System 5min: ${sys_5min_price:.2f}")

# Check if intervals are shifted
print(f"\nInterval Alignment Check:")
if sys_5min_price:
    if abs(sys_5min_price - ui_data[1]['price']) < 0.02:  # UI 5min vs System 5min
        print("✅ Intervals are aligned correctly")
    elif abs(sys_5min_price - ui_article_price) < 0.02:  # System 5min matches UI article time
        print("⚠️  Intervals appear shifted: System 5min = UI article time")
        print("   This suggests UI is showing intervals one step ahead")

print("\n" + "=" * 80)

