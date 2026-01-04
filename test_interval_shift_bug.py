#!/usr/bin/env python3
"""Investigate interval shift bug - why UI shows 5min price at article time"""

from main import LayoffTracker
from datetime import datetime, timezone, timedelta

print("=" * 80)
print("Interval Shift Bug Investigation")
print("=" * 80)

tracker = LayoffTracker()
article_datetime = datetime(2025, 12, 2, 5, 33, tzinfo=timezone.utc)

print(f"\n📰 Article Details:")
print(f"   Published: {article_datetime.strftime('%a, %b %d, %Y %H:%M')} UTC")
print(f"   Market was open: {tracker.is_market_open(article_datetime, 'EADSY')}")

# Since market was closed, intervals should be on next trading day
next_trading_day = tracker.get_next_trading_day(article_datetime, 'EADSY')
print(f"   Next trading day: {next_trading_day.strftime('%a, %b %d, %Y') if next_trading_day else 'None'}")

if next_trading_day:
    market_open_utc = tracker._get_market_open_time(next_trading_day, 'EADSY')
    print(f"   Market open: {market_open_utc.strftime('%H:%M')} UTC ({(market_open_utc - timedelta(hours=5)).strftime('%H:%M')} ET)")
    
    print(f"\n📋 Expected Intervals (from market open):")
    intervals = {
        '5min': market_open_utc + timedelta(minutes=5),
        '10min': market_open_utc + timedelta(minutes=10),
        '30min': market_open_utc + timedelta(minutes=30),
        '1hr': market_open_utc + timedelta(hours=1),
    }
    
    for name, dt in intervals.items():
        et = dt - timedelta(hours=5)
        print(f"   {name}: {dt.strftime('%H:%M')} UTC ({et.strftime('%H:%M')} ET)")

# Test actual calculation
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

print(f"\n📊 System Calculated Intervals:")
for interval in ['5min', '10min', '30min', '1hr', '1.5hr', '2hr', '2.5hr']:
    price = stock_changes.get(f'price_{interval}')
    datetime_str = stock_changes.get(f'datetime_{interval}')
    date_str = stock_changes.get(f'date_{interval}')
    
    if datetime_str:
        dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        et = dt - timedelta(hours=5)
        print(f"   {interval}: ${price:.2f} at {dt.strftime('%H:%M')} UTC ({et.strftime('%H:%M')} ET) on {date_str}")

# Check what UI shows
print(f"\n📱 UI Shows:")
print(f"   Article time: $57.84 (+3.51%)")
print(f"   5min: $57.86 (+3.54%) at 09:35 ET")
print(f"   10min: $58.00 (+3.79%) at 09:40 ET")

# Compare
sys_5min_price = stock_changes.get('price_5min')
sys_5min_datetime = stock_changes.get('datetime_5min')

if sys_5min_price and sys_5min_datetime:
    dt_5min = datetime.fromisoformat(sys_5min_datetime.replace('Z', '+00:00'))
    et_5min = dt_5min - timedelta(hours=5)
    
    print(f"\n🔍 Comparison:")
    print(f"   System 5min: ${sys_5min_price:.2f} at {et_5min.strftime('%H:%M')} ET")
    print(f"   UI Article time: $57.84")
    print(f"   {'✅' if abs(sys_5min_price - 57.84) < 0.01 else '❌'} Match: {abs(sys_5min_price - 57.84) < 0.01}")
    
    if abs(sys_5min_price - 57.84) < 0.01:
        print(f"\n   ⚠️  BUG IDENTIFIED:")
        print(f"   UI is showing System's 5min interval price at 'article time'")
        print(f"   Then UI's 5min = System's 10min (shifted by one interval)")

print("\n" + "=" * 80)

