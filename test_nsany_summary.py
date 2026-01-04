#!/usr/bin/env python3
"""Summary test for NSANY issue"""

from datetime import datetime, timezone, timedelta
from main import LayoffTracker

print("=" * 80)
print("NSANY Bug Analysis")
print("=" * 80)

tracker = LayoffTracker()
article_date = datetime(2025, 12, 1, 17, 17, tzinfo=timezone.utc)  # 12:17 PM ET
article_day = article_date.replace(hour=0, minute=0, second=0, microsecond=0)

print(f"\n📰 Article: Mon, Dec 1, 2025 12:17 PM ET = {article_date.strftime('%H:%M')} UTC")

# Get intraday data
intraday_data = tracker._fetch_intraday_data_for_day('NSANY', article_day, interval='5min')

if intraday_data:
    data = intraday_data.get('data', {})
    timestamps = data.get('timestamp', [])
    closes = data.get('close', [])
    
    print(f"\n📊 Prixe.io Data:")
    print(f"   Total data points: {len(timestamps)}")
    print(f"   ⚠️  VERY SPARSE DATA - Only {len(timestamps)} points for entire day!")
    
    print(f"\n   Available timestamps:")
    for i, ts in enumerate(timestamps):
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        price = closes[i] if i < len(closes) else None
        et_time = dt - timedelta(hours=5)  # EST
        print(f"     {dt.strftime('%H:%M')} UTC ({et_time.strftime('%H:%M')} ET) = ${price:.2f}")
    
    print(f"\n🔍 Interval Analysis:")
    intervals = [
        ('5min', 5, '12:22'),
        ('10min', 10, '12:27'),
        ('30min', 30, '12:47'),
        ('1hr', 60, '13:17'),
        ('1.5hr', 90, '13:47'),
        ('2hr', 120, '14:17'),
        ('2.5hr', 150, '14:47'),  # This one shows price in UI
    ]
    
    for interval_name, minutes, et_time_str in intervals:
        target = article_date + timedelta(minutes=minutes)
        target_et = target - timedelta(hours=5)  # EST
        
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
        min_diff_minutes = min_diff // 60
        
        status = "✅ HAS PRICE" if price else "❌ NO PRICE"
        reason = ""
        if not price:
            if min_diff_minutes > 30:
                reason = f" (Too far: {min_diff_minutes}min > 30min threshold)"
            else:
                reason = " (Other reason)"
        
        print(f"   {interval_name:6s} ({et_time_str} ET): {status}{reason}")
        if price:
            print(f"            Price: ${price:.2f}")
        else:
            print(f"            Closest data: {closest_dt.strftime('%H:%M')} UTC ({min_diff_minutes}min away) = ${closest_price:.2f}")
    
    print(f"\n💡 Issue Identified:")
    print(f"   - Prixe.io only has data at END of trading day (3:35 PM - 4:00 PM ET)")
    print(f"   - Article was at 12:17 PM ET")
    print(f"   - All intervals before 3:35 PM are > 30 minutes from available data")
    print(f"   - 30-minute threshold in _extract_intraday_price_from_batch() rejects them")
    print(f"   - But 2.5hr interval (14:47 ET) is 48min from first data (20:35 UTC)")
    print(f"   - This should also be rejected, but UI shows price...")
    print(f"\n   ⚠️  Possible causes:")
    print(f"      1. UI might be using daily close price as fallback")
    print(f"      2. 30-minute threshold might not be working correctly")
    print(f"      3. Different logic path for 2.5hr interval")

else:
    print("❌ No intraday data available")

print("\n" + "=" * 80)

