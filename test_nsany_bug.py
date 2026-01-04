#!/usr/bin/env python3
"""Unit test to debug NSANY (Nissan) showing N/A for most intervals"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

print("\n" + "=" * 80)
print("NSANY (Nissan) Bug Investigation")
print("=" * 80)

tracker = LayoffTracker()

# Article published: Mon, Dec 1, 2025 12:17 (Market Open)
# This is 12:17 PM ET = 17:17 UTC (EST) or 16:17 UTC (EDT)
# Dec 1, 2025 - should be EST (UTC-5), so 12:17 PM ET = 17:17 UTC
article_date = datetime(2025, 12, 1, 17, 17, tzinfo=timezone.utc)

print(f"\n📰 Article Date: {article_date.strftime('%a, %b %d, %Y %H:%M')} UTC")
print(f"   This should be: Mon, Dec 1, 2025 12:17 PM ET")

# Check if market is open
is_open = tracker.is_market_open(article_date, 'NSANY')
print(f"   Market is open: {is_open}")

# Get market open/close times
article_day = article_date.replace(hour=0, minute=0, second=0, microsecond=0)
market_open_utc = tracker._get_market_open_time(article_day, 'NSANY')
market_close_utc = tracker._get_market_close_time(article_day, 'NSANY')

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
    ('1.5hr', 90),
    ('2hr', 120),
    ('2.5hr', 150),  # This one shows price in UI
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
    print(f"      Within hours: {not (is_after_close or is_before_open)}")

# Check intraday data availability
print(f"\n🔍 Checking Intraday Data Availability:")
intraday_data = tracker._fetch_intraday_data_for_day('NSANY', article_day, interval='5min')

if intraday_data:
    data = intraday_data.get('data', {})
    timestamps = data.get('timestamp', [])
    closes = data.get('close', [])
    
    if timestamps and closes:
        print(f"   ✅ Intraday data available")
        print(f"   Data points: {len(timestamps)}")
        print(f"   First timestamp: {datetime.fromtimestamp(timestamps[0], tz=timezone.utc)}")
        print(f"   Last timestamp: {datetime.fromtimestamp(timestamps[-1], tz=timezone.utc)}")
        
        # Check if we have data for the intervals
        for interval_name, minutes in intervals:
            target_datetime = article_date + timedelta(minutes=minutes)
            price = tracker._extract_intraday_price_from_batch(intraday_data, target_datetime)
            if price:
                print(f"   ✅ {interval_name}: ${price:.2f}")
            else:
                print(f"   ❌ {interval_name}: No price extracted")
    else:
        print(f"   ⚠️  No price data in response")
else:
    print(f"   ❌ No intraday data available")

# Now test the actual calculation
print(f"\n🔍 Testing calculate_stock_changes:")
mock_layoff = {
    'company_name': 'Nissan Motor Co.',
    'stock_ticker': 'NSANY',
    'datetime': article_date,
    'date': article_date.strftime('%Y-%m-%d'),
    'time': article_date.strftime('%H:%M:%S'),
    'url': 'https://test.com/nissan',
    'title': 'Nissan test article'
}

try:
    stock_changes = tracker.calculate_stock_changes(mock_layoff)
    
    print(f"\n📊 Results:")
    print(f"   Base price: ${stock_changes.get('base_price'):.2f}" if stock_changes.get('base_price') else "   Base price: None")
    print(f"   Market was open: {stock_changes.get('market_was_open')}")
    
    for interval in ['5min', '10min', '30min', '1hr', '1.5hr', '2hr', '2.5hr']:
        price = stock_changes.get(f'price_{interval}')
        change = stock_changes.get(f'change_{interval}')
        market_closed = stock_changes.get(f'market_closed_{interval}')
        no_data = stock_changes.get(f'no_intraday_data_{interval}')
        dt_str = stock_changes.get(f'datetime_{interval}')
        
        if market_closed:
            status = "❌ MARKET CLOSED"
        elif price:
            status = f"✅ HAS PRICE: ${price:.2f} ({change:+.2f}%)" if change else f"✅ HAS PRICE: ${price:.2f}"
        elif no_data:
            status = "⚠️  NO INTRADAY DATA"
        else:
            status = "❌ N/A"
        
        print(f"   {interval}: {status}")
        if dt_str:
            print(f"      Datetime: {dt_str}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)

