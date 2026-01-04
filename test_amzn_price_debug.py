#!/usr/bin/env python3
"""
Debug test to check why AMZN daily open/close prices can't be retrieved
for Nov 28, 2025 (the Amazon recall event date)
"""

from main import LayoffTracker
from datetime import datetime, timezone, timedelta
import json

def test_amzn_daily_price_extraction():
    """Test what Prixe.io returns for AMZN daily prices around Nov 28, 2025"""
    
    tracker = LayoffTracker()
    
    print("="*80)
    print("AMZN Daily Price Data Debug Test")
    print("="*80)
    
    # Amazon article was published: Fri, Nov 28, 2025 14:16 (2:16 PM ET)
    announcement_dt = datetime(2025, 11, 28, 14, 16, 0, tzinfo=timezone.utc)
    
    # Convert to ET to verify
    import pytz
    et_tz = pytz.timezone('America/New_York')
    announcement_et = announcement_dt.astimezone(et_tz)
    print(f"\nArticle published: {announcement_et.strftime('%A, %B %d, %Y %H:%M %Z')}")
    print(f"Market should be: OPEN (2:16 PM ET, market closes at 4:00 PM ET)")
    
    # Calculate date range: 5 days before to 3 days after
    start_date = announcement_dt - timedelta(days=5)
    end_date = announcement_dt + timedelta(days=3)
    
    print(f"\nFetching daily price data from Prixe.io...")
    print(f"Date range: {start_date.date()} to {end_date.date()}")
    print(f"Ticker: AMZN")
    
    # Fetch daily price data
    daily_price_data = tracker._fetch_price_data_batch('AMZN', start_date, end_date, '1d')
    
    if not daily_price_data:
        print("\n❌ ERROR: No daily price data returned from Prixe.io API")
        print("Possible reasons:")
        print("  - API call failed")
        print("  - API returned None")
        print("  - API returned success: false")
        return
    
    print("\n✓ Daily price data received from Prixe.io")
    
    # Check response structure
    print("\n" + "="*80)
    print("API Response Structure Analysis")
    print("="*80)
    
    print(f"\nResponse keys: {list(daily_price_data.keys())}")
    print(f"Success: {daily_price_data.get('success')}")
    
    if 'data' not in daily_price_data:
        print("\n❌ ERROR: 'data' key not found in response")
        print(f"Full response: {json.dumps(daily_price_data, indent=2, default=str)}")
        return
    
    data = daily_price_data['data']
    print(f"\nData keys: {list(data.keys())}")
    
    # Check what price fields are available
    price_fields = ['open', 'close', 'high', 'low', 'price']
    available_fields = [field for field in price_fields if field in data]
    missing_fields = [field for field in price_fields if field not in data]
    
    print(f"\n✓ Available price fields: {available_fields}")
    if missing_fields:
        print(f"❌ Missing price fields: {missing_fields}")
    
    # Check timestamps
    timestamps = data.get('timestamp', [])
    print(f"\nTotal timestamps in response: {len(timestamps)}")
    
    if not timestamps:
        print("❌ ERROR: No timestamps in response")
        return
    
    # Show first and last timestamps
    from datetime import datetime as dt
    if timestamps:
        first_ts = dt.fromtimestamp(timestamps[0], tz=timezone.utc)
        last_ts = dt.fromtimestamp(timestamps[-1], tz=timezone.utc)
        print(f"First timestamp: {first_ts} ({first_ts.astimezone(et_tz).strftime('%A, %B %d, %Y')})")
        print(f"Last timestamp: {last_ts} ({last_ts.astimezone(et_tz).strftime('%A, %B %d, %Y')})")
    
    # Check if Nov 28, 2025 is in the timestamps
    article_day = announcement_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    target_timestamp = int(article_day.timestamp())
    
    print(f"\n" + "="*80)
    print("Looking for Nov 28, 2025 in response")
    print("="*80)
    print(f"Target timestamp: {target_timestamp} ({article_day.date()})")
    
    # Find closest timestamp
    closest_idx = 0
    min_diff = abs(timestamps[0] - target_timestamp)
    for i, ts in enumerate(timestamps):
        diff = abs(ts - target_timestamp)
        if diff < min_diff:
            min_diff = diff
            closest_idx = i
    
    closest_ts = timestamps[closest_idx]
    closest_date = dt.fromtimestamp(closest_ts, tz=timezone.utc)
    diff_days = abs((closest_date.date() - article_day.date()).days)
    
    print(f"Closest timestamp: {closest_ts} ({closest_date.date()})")
    print(f"Difference: {diff_days} days")
    
    if diff_days > 0:
        print(f"⚠️  WARNING: Closest timestamp is {diff_days} days away from target date")
        print(f"   This might be why open/close prices can't be extracted")
    
    # Try to extract open and close prices
    print(f"\n" + "="*80)
    print("Attempting to Extract Open/Close Prices")
    print("="*80)
    
    open_price = tracker._extract_price_from_batch(daily_price_data, article_day, 'open')
    close_price = tracker._extract_price_from_batch(daily_price_data, article_day, 'close')
    
    print(f"\nOpen price: {open_price}")
    print(f"Close price: {close_price}")
    
    if open_price is None:
        print("\n❌ Open price extraction failed")
        if 'open' not in data:
            print("   Reason: 'open' field not in API response")
        else:
            opens = data['open']
            print(f"   'open' field exists with {len(opens)} values")
            if closest_idx < len(opens):
                print(f"   Value at closest_idx ({closest_idx}): {opens[closest_idx]}")
            else:
                print(f"   closest_idx ({closest_idx}) is out of range (array length: {len(opens)})")
    
    if close_price is None:
        print("\n❌ Close price extraction failed")
        if 'close' not in data:
            print("   Reason: 'close' field not in API response")
        else:
            closes = data['close']
            print(f"   'close' field exists with {len(closes)} values")
            if closest_idx < len(closes):
                print(f"   Value at closest_idx ({closest_idx}): {closes[closest_idx]}")
            else:
                print(f"   closest_idx ({closest_idx}) is out of range (array length: {len(closes)})")
    
    # Show sample data around the target date
    print(f"\n" + "="*80)
    print("Sample Data Around Target Date")
    print("="*80)
    
    # Show 3 days before and after
    start_idx = max(0, closest_idx - 3)
    end_idx = min(len(timestamps), closest_idx + 4)
    
    print(f"\nShowing indices {start_idx} to {end_idx-1}:")
    print(f"{'Index':<8} {'Date':<15} {'Open':<12} {'Close':<12} {'High':<12} {'Low':<12}")
    print("-" * 80)
    
    for i in range(start_idx, end_idx):
        date_str = dt.fromtimestamp(timestamps[i], tz=timezone.utc).strftime('%Y-%m-%d')
        open_val = data.get('open', [None] * len(timestamps))[i] if 'open' in data else None
        close_val = data.get('close', [None] * len(timestamps))[i] if 'close' in data else None
        high_val = data.get('high', [None] * len(timestamps))[i] if 'high' in data else None
        low_val = data.get('low', [None] * len(timestamps))[i] if 'low' in data else None
        
        marker = " <-- TARGET" if i == closest_idx else ""
        print(f"{i:<8} {date_str:<15} {str(open_val):<12} {str(close_val):<12} {str(high_val):<12} {str(low_val):<12}{marker}")
    
    print("\n" + "="*80)
    print("Summary")
    print("="*80)
    
    if open_price and close_price:
        print("✓ SUCCESS: Both open and close prices extracted successfully")
    elif open_price is None and close_price is None:
        print("❌ FAILURE: Both open and close prices failed to extract")
        if 'open' not in data or 'close' not in data:
            print("   → Prixe.io API doesn't return 'open' and 'close' fields for daily data")
            print("   → This is why the code marks all intervals as 'Closed'")
        elif diff_days > 0:
            print(f"   → Target date not in response (closest is {diff_days} days away)")
            print("   → This might be a market holiday or data gap")
    else:
        print("⚠️  PARTIAL: One price extracted, one failed")
        if open_price is None:
            print("   → Open price missing")
        if close_price is None:
            print("   → Close price missing")

if __name__ == '__main__':
    test_amzn_daily_price_extraction()

