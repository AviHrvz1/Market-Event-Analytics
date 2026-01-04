#!/usr/bin/env python3
"""Test price extraction for BYD to understand why it returns same price"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

print("=" * 80)
print("BYD Price Extraction Debug")
print("=" * 80)

tracker = LayoffTracker()

# Article date: Sun, Nov 30, 2025 04:48 UTC
article_date = datetime(2025, 11, 30, 4, 48, tzinfo=timezone.utc)

# Get intraday data for Dec 1 (next trading day)
dec1 = datetime(2025, 12, 1, 0, 0, tzinfo=timezone.utc)
intraday_data = tracker._fetch_intraday_data_for_day('1211.HK', dec1, interval='5min')

if intraday_data:
    data = intraday_data.get('data', {})
    timestamps = data.get('timestamp', [])
    closes = data.get('close', [])
    
    print(f"\n📊 Intraday Data Summary:")
    print(f"  Total data points: {len(timestamps)}")
    print(f"  First timestamp: {datetime.fromtimestamp(timestamps[0], tz=timezone.utc)}")
    print(f"  Last timestamp: {datetime.fromtimestamp(timestamps[-1], tz=timezone.utc)}")
    print(f"  Price range: ${min(closes):.2f} - ${max(closes):.2f}")
    
    # Test extracting prices at specific times
    print(f"\n🔍 Testing Price Extraction:")
    
    # Article was on Sunday 04:48 UTC, so intervals should be:
    # 5min: Mon Dec 1 09:35 ET = 14:35 UTC (9:30 AM ET + 5 min)
    # But wait, if article was Sunday, intervals should be calculated from Monday market open
    
    # Let's test what the system calculates
    test_times = [
        datetime(2025, 12, 1, 9, 35, tzinfo=timezone.utc),   # 9:35 UTC
        datetime(2025, 12, 1, 14, 35, tzinfo=timezone.utc),  # 14:35 UTC (9:35 ET)
        datetime(2025, 12, 1, 10, 0, tzinfo=timezone.utc),   # 10:00 UTC
        datetime(2025, 12, 1, 15, 0, tzinfo=timezone.utc),   # 15:00 UTC (10:00 ET)
    ]
    
    for test_time in test_times:
        price = tracker._extract_intraday_price_from_batch(intraday_data, test_time)
        print(f"  {test_time.strftime('%Y-%m-%d %H:%M')} UTC: ${price:.2f}" if price else f"  {test_time.strftime('%Y-%m-%d %H:%M')} UTC: None")
        
        # Also check what timestamp it's matching to
        if price:
            target_ts = int(test_time.timestamp())
            closest_idx = 0
            min_diff = abs(timestamps[0] - target_ts)
            for i, ts in enumerate(timestamps):
                diff = abs(ts - target_ts)
                if diff < min_diff:
                    min_diff = diff
                    closest_idx = i
            
            matched_ts = timestamps[closest_idx]
            matched_time = datetime.fromtimestamp(matched_ts, tz=timezone.utc)
            matched_price = closes[closest_idx]
            print(f"    → Matched to: {matched_time.strftime('%Y-%m-%d %H:%M')} UTC (diff: {min_diff}s), price: ${matched_price:.2f}")
    
    # Now test what calculate_stock_changes actually does
    print(f"\n🔍 Testing calculate_stock_changes intervals:")
    mock_layoff = {
        'company_name': 'BYD Company Limited',
        'stock_ticker': '1211.HK',
        'datetime': article_date,
        'date': article_date.strftime('%Y-%m-%d'),
        'time': article_date.strftime('%H:%M:%S'),
        'url': 'https://test.com/byd',
        'title': 'BYD test article'
    }
    
    stock_changes = tracker.calculate_stock_changes(mock_layoff)
    
    # Check what datetimes are stored for intervals
    for interval in ['5min', '10min', '30min', '1hr']:
        price = stock_changes.get(f'price_{interval}')
        dt_str = stock_changes.get(f'datetime_{interval}')
        if dt_str:
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            print(f"  {interval}: ${price:.2f} at {dt.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        else:
            print(f"  {interval}: ${price:.2f} (no datetime)")

