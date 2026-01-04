#!/usr/bin/env python3
"""
Test if intraday data is being fetched correctly for Dec 9, 2025
"""

from datetime import datetime, timezone, timedelta
from main import LayoffTracker

tracker = LayoffTracker()
ticker = 'ABG'
target_date = datetime(2025, 12, 9, 0, 0, 0, tzinfo=timezone.utc)

print(f"\n{'='*80}")
print(f"Testing intraday data fetch for {ticker} on {target_date.date()}")
print(f"{'='*80}\n")

# Test 1: Check if date is within 30-day limit
now = datetime.now(timezone.utc)
days_ago = (now - target_date).days
print(f"Step 1: Date check")
print(f"  Current time: {now}")
print(f"  Target date: {target_date}")
print(f"  Days ago: {days_ago}")
print(f"  Within 30-day limit for 1min data? {days_ago <= 30}")
print()

# Test 2: Fetch 1min intraday data
print(f"Step 2: Fetching 1min intraday data...")
intraday_1min = tracker._fetch_intraday_data_for_day(ticker, target_date, interval='1min')

if intraday_1min:
    print(f"  ✓ 1min data fetched successfully")
    data = intraday_1min.get('data', {})
    timestamps = data.get('timestamp', [])
    closes = data.get('close', [])
    print(f"  Timestamps: {len(timestamps)}")
    if timestamps:
        print(f"  First timestamp: {datetime.fromtimestamp(timestamps[0], tz=timezone.utc)}")
        print(f"  Last timestamp: {datetime.fromtimestamp(timestamps[-1], tz=timezone.utc)}")
        print(f"  First 3 prices: {closes[:3] if len(closes) >= 3 else closes}")
else:
    print(f"  ✗ Failed to fetch 1min data")
print()

# Test 3: Fetch 5min intraday data
print(f"Step 3: Fetching 5min intraday data...")
intraday_5min = tracker._fetch_intraday_data_for_day(ticker, target_date, interval='5min')

if intraday_5min:
    print(f"  ✓ 5min data fetched successfully")
    data = intraday_5min.get('data', {})
    timestamps = data.get('timestamp', [])
    closes = data.get('close', [])
    print(f"  Timestamps: {len(timestamps)}")
    if timestamps:
        print(f"  First timestamp: {datetime.fromtimestamp(timestamps[0], tz=timezone.utc)}")
        print(f"  Last timestamp: {datetime.fromtimestamp(timestamps[-1], tz=timezone.utc)}")
        print(f"  First 3 prices: {closes[:3] if len(closes) >= 3 else closes}")
else:
    print(f"  ✗ Failed to fetch 5min data")
print()

# Test 4: Check market open/close times
print(f"Step 4: Market hours calculation")
market_open = tracker._get_market_open_time(target_date, ticker)
market_close = tracker._get_market_close_time(target_date, ticker)
print(f"  Market open (UTC): {market_open}")
print(f"  Market close (UTC): {market_close}")
if market_open and market_close:
    print(f"  Trading hours: {market_close - market_open}")
print()

# Test 5: Simulate the exact code path at line 3059
print(f"Step 5: Simulating code at line 3059 (checking has_trading_data_for_date)")
# This is what happens when market was closed on announcement day
next_trading_day = target_date  # Dec 9, 2025

# Fetch daily batch data (same as in calculate_stock_changes)
announcement_dt = datetime(2025, 12, 8, 16, 15, tzinfo=timezone.utc)
start_date = announcement_dt - timedelta(days=5)
end_date = announcement_dt + timedelta(days=3)
daily_price_data = tracker._fetch_price_data_batch(ticker, start_date, end_date, '1d')

print(f"  Next trading day: {next_trading_day.date()}")
print(f"  Daily batch data available: {daily_price_data is not None}")

if daily_price_data:
    target_date_only = next_trading_day.replace(hour=0, minute=0, second=0, microsecond=0)
    print(f"  Checking has_trading_data_for_date({ticker}, {target_date_only}, daily_price_data)...")
    result = tracker.has_trading_data_for_date(ticker, target_date_only, daily_price_data)
    print(f"  Result: {result}")
    
    if not result:
        print(f"  ❌ This would cause line 3065 to mark all intervals as 'Closed'")
    else:
        print(f"  ✓ This should allow data to be fetched")
        print(f"  But if intraday_data is None, intervals would still show N/A")
        print(f"  Intraday data available: {intraday_5min is not None}")

