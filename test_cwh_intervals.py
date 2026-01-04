#!/usr/bin/env python3
"""
Test why CWH shows Closed for +1hr and +3hrs intervals
"""

from datetime import datetime, timezone, timedelta
from main import LayoffTracker

tracker = LayoffTracker()

# CWH article: Tue, Dec 9, 2025 14:30 UTC
cwh_article = datetime(2025, 12, 9, 14, 30, tzinfo=timezone.utc)
ticker = 'CWH'

print(f"Article: {cwh_article} UTC")
print(f"Market was open: {tracker.is_market_open(cwh_article, ticker)}")

# Get market hours
article_day = cwh_article.replace(hour=0, minute=0, second=0, microsecond=0)
market_open_utc = tracker._get_market_open_time(article_day, ticker)
market_close_utc = tracker._get_market_close_time(article_day, ticker)

print(f"\nMarket hours:")
print(f"  Open (UTC): {market_open_utc}")
print(f"  Close (UTC): {market_close_utc}")

# Test intervals
intervals = [
    ('1hr', timedelta(hours=1)),
    ('3hr', timedelta(hours=3)),
]

print(f"\nTesting intervals:")
for interval_name, delta in intervals:
    target_dt = cwh_article + delta
    target_dt_utc = target_dt.astimezone(timezone.utc)
    
    is_after_close = target_dt_utc > market_close_utc
    is_before_open = target_dt_utc < market_open_utc
    
    print(f"\n  {interval_name}:")
    print(f"    Target: {target_dt_utc} UTC")
    print(f"    Market close: {market_close_utc} UTC")
    print(f"    Is after close? {is_after_close}")
    print(f"    Is before open? {is_before_open}")
    print(f"    Would be marked closed? {is_after_close or is_before_open}")
    
    if is_after_close:
        diff = target_dt_utc - market_close_utc
        print(f"    ⚠️  Target is {diff} AFTER market close")
    elif is_before_open:
        diff = market_open_utc - target_dt_utc
        print(f"    ⚠️  Target is {diff} BEFORE market open")

# Now test the actual calculation
print(f"\n\nTesting actual calculate_stock_changes:")
mock_layoff = {
    'company_name': 'Camping World Holdings',
    'stock_ticker': 'CWH',
    'datetime': cwh_article,
    'date': cwh_article.strftime('%Y-%m-%d'),
    'time': cwh_article.strftime('%H:%M:%S'),
    'url': 'https://test.com/cwh',
    'title': 'CWH test article'
}

stock_changes = tracker.calculate_stock_changes(mock_layoff)

print(f"\nResults:")
for interval in ['1hr', '3hr']:
    price = stock_changes.get(f'price_{interval}')
    change = stock_changes.get(f'change_{interval}')
    market_closed = stock_changes.get(f'market_closed_{interval}')
    datetime_val = stock_changes.get(f'datetime_{interval}')
    
    print(f"  {interval}:")
    print(f"    Price: {price}")
    print(f"    Change: {change}")
    print(f"    Market closed: {market_closed}")
    print(f"    Datetime: {datetime_val}")

