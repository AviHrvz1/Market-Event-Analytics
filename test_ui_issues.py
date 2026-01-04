#!/usr/bin/env python3
"""
Diagnostic script to check why:
1. CWH shows "Closed" for +1hr and +3hrs intervals
2. ABG still shows "Closed (Tue)" for all intervals
3. ATI and BRK.A show "N/A"
"""

from datetime import datetime, timezone, timedelta
from main import LayoffTracker

tracker = LayoffTracker()

print(f"\n{'='*80}")
print("Diagnosing UI Issues")
print(f"{'='*80}\n")

# Test 1: CWH - Article published Tue, Dec 9, 2025 14:30 (market open)
print("Test 1: CWH (Camping World Holdings)")
print("-" * 80)
cwh_article = datetime(2025, 12, 9, 14, 30, tzinfo=timezone.utc)
print(f"Article published: {cwh_article} UTC")
print(f"Market was open: {tracker.is_market_open(cwh_article, 'CWH')}")

article_day = cwh_article.replace(hour=0, minute=0, second=0, microsecond=0)
market_open_utc = tracker._get_market_open_time(article_day, 'CWH')
market_close_utc = tracker._get_market_close_time(article_day, 'CWH')

print(f"Market open (UTC): {market_open_utc}")
print(f"Market close (UTC): {market_close_utc}")

# Check intervals
intervals_to_check = [
    ('5min', timedelta(minutes=5)),
    ('10min', timedelta(minutes=10)),
    ('30min', timedelta(minutes=30)),
    ('1hr', timedelta(hours=1)),
    ('3hr', timedelta(hours=3)),
]

for interval_name, delta in intervals_to_check:
    target_dt = cwh_article + delta
    is_after_close = target_dt > market_close_utc
    is_before_open = target_dt < market_open_utc
    
    print(f"\n  {interval_name}:")
    print(f"    Target: {target_dt} UTC")
    print(f"    After close? {is_after_close}")
    print(f"    Before open? {is_before_open}")
    print(f"    Would be marked closed? {is_after_close or is_before_open}")

# Test 2: ABG - Article published Mon, Dec 8, 2025 16:15 (market closed)
print(f"\n\nTest 2: ABG (Asbury Automotive Group)")
print("-" * 80)
abg_article = datetime(2025, 12, 8, 16, 15, tzinfo=timezone.utc)
print(f"Article published: {abg_article} UTC")
print(f"Market was open: {tracker.is_market_open(abg_article, 'ABG')}")

# Get next trading day
next_trading_day = tracker.get_next_trading_day(abg_article, 'ABG')
print(f"Next trading day: {next_trading_day}")

if next_trading_day:
    # Check if next trading day has data
    article_day = abg_article.replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = abg_article - timedelta(days=5)
    end_date = abg_article + timedelta(days=3)
    daily_price_data = tracker._fetch_price_data_batch('ABG', start_date, end_date, '1d')
    
    now = datetime.now(timezone.utc)
    next_day_date = next_trading_day.date() if hasattr(next_trading_day, 'date') else next_trading_day.replace(hour=0, minute=0, second=0, microsecond=0).date()
    is_today = next_day_date == now.date()
    
    print(f"Next trading day date: {next_day_date}")
    print(f"Is today? {is_today}")
    print(f"Current date: {now.date()}")
    
    has_data = tracker.has_trading_data_for_date('ABG', next_trading_day, daily_price_data)
    print(f"Has data in batch? {has_data}")
    
    if not has_data and is_today:
        print("  Trying fresh check...")
        has_data = tracker.has_trading_data_for_date('ABG', next_trading_day, None)
        print(f"  Has data after fresh check? {has_data}")
    
    if has_data:
        market_open_utc = tracker._get_market_open_time(next_trading_day, 'ABG')
        market_close_utc = tracker._get_market_close_time(next_trading_day, 'ABG')
        print(f"Market open (UTC): {market_open_utc}")
        print(f"Market close (UTC): {market_close_utc}")
        
        # Check intervals (should be from market open)
        intervals = [
            ('5min', 5/60.0),
            ('10min', 10/60.0),
            ('30min', 30/60.0),
            ('1hr', 1.0),
        ]
        
        for interval_name, hours_after_open in intervals:
            target_dt = market_open_utc + timedelta(hours=hours_after_open)
            print(f"\n  {interval_name}:")
            print(f"    Target: {target_dt} UTC")
            print(f"    After close? {target_dt > market_close_utc}")

# Test 3: ATI and BRK.A - Check if tickers are valid
print(f"\n\nTest 3: Ticker Validation")
print("-" * 80)
tickers_to_check = ['ATI', 'BRK.A']
for ticker in tickers_to_check:
    print(f"\n{ticker}:")
    # Check if ticker is in Prixe.io
    test_date = datetime(2025, 12, 8, 0, 0, 0, tzinfo=timezone.utc)
    test_data = tracker._fetch_price_data_batch(ticker, test_date, test_date, '1d')
    if test_data and test_data.get('success'):
        print(f"  ✓ Ticker exists in Prixe.io")
        data = test_data.get('data', {})
        timestamps = data.get('timestamp', [])
        print(f"  Data points: {len(timestamps)}")
    else:
        print(f"  ✗ Ticker not found or no data in Prixe.io")

