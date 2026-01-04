#!/usr/bin/env python3
"""Detailed test for NSANY intraday data"""

from datetime import datetime, timezone, timedelta
from main import LayoffTracker

tracker = LayoffTracker()
article_date = datetime(2025, 12, 1, 17, 17, tzinfo=timezone.utc)  # 12:17 PM ET
article_day = article_date.replace(hour=0, minute=0, second=0, microsecond=0)

print("Fetching intraday data for NSANY on Dec 1, 2025...")
intraday_data = tracker._fetch_intraday_data_for_day('NSANY', article_day, interval='5min')

if intraday_data:
    data = intraday_data.get('data', {})
    timestamps = data.get('timestamp', [])
    closes = data.get('close', [])
    
    print(f"\n✅ Intraday data available: {len(timestamps)} data points")
    
    if timestamps:
        print(f"\nFirst 10 timestamps:")
        for i in range(min(10, len(timestamps))):
            ts = timestamps[i]
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            price = closes[i] if i < len(closes) else None
            print(f"  {i}: {dt.strftime('%Y-%m-%d %H:%M:%S')} UTC = ${price:.2f}" if price else f"  {i}: {dt.strftime('%Y-%m-%d %H:%M:%S')} UTC = None")
        
        if len(timestamps) > 10:
            print(f"\nLast 5 timestamps:")
            for i in range(len(timestamps)-5, len(timestamps)):
                ts = timestamps[i]
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                price = closes[i] if i < len(closes) else None
                print(f"  {i}: {dt.strftime('%Y-%m-%d %H:%M:%S')} UTC = ${price:.2f}" if price else f"  {i}: {dt.strftime('%Y-%m-%d %H:%M:%S')} UTC = None")
        
        # Test extraction for all intervals
        print(f"\n🔍 Testing interval extraction:")
        print(f"Article time: {article_date.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        
        intervals = [
            ('5min', 5),
            ('10min', 10),
            ('30min', 30),
            ('1hr', 60),
            ('1.5hr', 90),
            ('2hr', 120),
            ('2.5hr', 150),
        ]
        
        for interval_name, minutes in intervals:
            target = article_date + timedelta(minutes=minutes)
            price = tracker._extract_intraday_price_from_batch(intraday_data, target)
            
            # Find closest timestamp
            target_ts = int(target.timestamp())
            closest_idx = 0
            min_diff = abs(timestamps[0] - target_ts)
            for i, ts in enumerate(timestamps):
                diff = abs(ts - target_ts)
                if diff < min_diff:
                    min_diff = diff
                    closest_idx = i
            
            closest_dt = datetime.fromtimestamp(timestamps[closest_idx], tz=timezone.utc)
            closest_price = closes[closest_idx] if closest_idx < len(closes) else None
            
            status = f"✅ ${price:.2f}" if price else "❌ None"
            print(f"  {interval_name:6s}: Target {target.strftime('%H:%M')} UTC -> {status}")
            print(f"           Closest: {closest_dt.strftime('%H:%M')} UTC (diff: {min_diff//60}min) = ${closest_price:.2f}" if closest_price else f"           Closest: {closest_dt.strftime('%H:%M')} UTC (diff: {min_diff//60}min) = None")
            if price and min_diff > 30 * 60:
                print(f"           ⚠️  Time difference > 30min, but price extracted anyway")
else:
    print("❌ No intraday data available")

