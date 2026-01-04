#!/usr/bin/env python3
"""Test to debug why intervals show Closed when market was open"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

print("\n" + "=" * 80)
print("Testing Market Open Bug")
print("=" * 80)

tracker = LayoffTracker()

# Test case: Amazon article published during market hours
# Thu, Dec 4, 2025 11:49 AM ET = 16:49 UTC (EST) or 15:49 UTC (EDT)
# Let's use EST (Dec is winter)
article_date = datetime(2025, 12, 4, 16, 49, tzinfo=timezone.utc)  # 11:49 AM ET

print(f"\n📰 Article Date: {article_date.strftime('%a, %b %d, %Y %H:%M')} UTC")
print(f"   This should be: Thu, Dec 4, 2025 11:49 AM ET")

# Check if market is open
is_open = tracker.is_market_open(article_date, 'AMZN')
print(f"   Market is open: {is_open}")

# Get market open/close times for this day
article_day = article_date.replace(hour=0, minute=0, second=0, microsecond=0)
market_open_utc = tracker._get_market_open_time(article_day, 'AMZN')
market_close_utc = tracker._get_market_close_time(article_day, 'AMZN')

print(f"\n📊 Market Hours (UTC):")
print(f"   Open:  {market_open_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
print(f"   Close: {market_close_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")

# Test intervals
print(f"\n🔍 Testing Intervals:")
intervals = [
    ('5min', 5),
    ('10min', 10),
    ('30min', 30),
    ('1hr', 60),
]

for interval_name, minutes in intervals:
    target_datetime = article_date + timedelta(minutes=minutes)
    target_utc = target_datetime.astimezone(timezone.utc)
    
    is_after_close = target_utc > market_close_utc
    is_before_open = target_utc < market_open_utc
    
    print(f"\n   {interval_name} ({minutes} min after article):")
    print(f"      Target: {target_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"      After close: {is_after_close}")
    print(f"      Before open: {is_before_open}")
    print(f"      Would be marked closed: {is_after_close or is_before_open}")

# Now test the actual calculation
print(f"\n🔍 Testing calculate_stock_changes:")
mock_layoff = {
    'company_name': 'Amazon.com Inc',
    'stock_ticker': 'AMZN',
    'datetime': article_date,
    'date': article_date.strftime('%Y-%m-%d'),
    'time': article_date.strftime('%H:%M:%S'),
    'url': 'https://test.com/amzn',
    'title': 'Amazon test article'
}

try:
    stock_changes = tracker.calculate_stock_changes(mock_layoff)
    
    print(f"\n📊 Results:")
    print(f"   Base price: ${stock_changes.get('base_price'):.2f}" if stock_changes.get('base_price') else "   Base price: None")
    print(f"   Market was open: {stock_changes.get('market_was_open')}")
    
    for interval in ['5min', '10min', '30min', '1hr']:
        price = stock_changes.get(f'price_{interval}')
        market_closed = stock_changes.get(f'market_closed_{interval}')
        dt_str = stock_changes.get(f'datetime_{interval}')
        
        status = "❌ CLOSED" if market_closed else ("✅ HAS PRICE" if price else "⚠️  NO PRICE")
        print(f"   {interval}: {status} - Price: ${price:.2f}" if price else f"   {interval}: {status}")
        if dt_str:
            print(f"      Datetime: {dt_str}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

