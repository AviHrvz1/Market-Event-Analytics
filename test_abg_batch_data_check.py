#!/usr/bin/env python3
"""
Diagnostic script to check why has_trading_data_for_date returns False for Dec 9, 2025
This simulates what the actual code does
"""

from datetime import datetime, timezone, timedelta
from main import LayoffTracker
import json

# Initialize tracker
tracker = LayoffTracker()

# Simulate the scenario: Article published Dec 8, 2025 at 16:15
announcement_dt = datetime(2025, 12, 8, 16, 15, tzinfo=timezone.utc)
ticker = 'ABG'

print(f"\n{'='*80}")
print(f"Diagnostic: Why Dec 9, 2025 shows as 'Closed' for {ticker}")
print(f"{'='*80}\n")

# Step 1: Calculate date range (same as in calculate_stock_changes)
start_date = announcement_dt - timedelta(days=5)
end_date = announcement_dt + timedelta(days=3)

print(f"Step 1: Date range calculation")
print(f"  Announcement: {announcement_dt}")
print(f"  Start date: {start_date.date()}")
print(f"  End date: {end_date.date()}")
print()

# Step 2: Fetch batch data
print(f"Step 2: Fetching batch data from Prixe.io...")
batch_data = tracker._fetch_price_data_batch(ticker, start_date, end_date, '1d')

if batch_data:
    print(f"  ✓ Batch data fetched successfully")
    data = batch_data.get('data', {})
    timestamps = data.get('timestamp', [])
    closes = data.get('close', [])
    
    print(f"  Timestamps in batch: {len(timestamps)}")
    print(f"  Dates in batch:")
    for i, ts in enumerate(timestamps):
        from datetime import datetime as dt
        # Check both timezone-naive and timezone-aware
        ts_date_naive = dt.fromtimestamp(ts).date()
        ts_date_utc = dt.fromtimestamp(ts, tz=timezone.utc).date()
        print(f"    [{i}] Timestamp: {ts}")
        print(f"        Naive date: {ts_date_naive}")
        print(f"        UTC date: {ts_date_utc}")
        print(f"        Close: {closes[i] if i < len(closes) else 'N/A'}")
        print()
else:
    print(f"  ✗ Failed to fetch batch data")
    print()

# Step 3: Check has_trading_data_for_date for Dec 9, 2025
target_date = datetime(2025, 12, 9, 0, 0, 0, tzinfo=timezone.utc)
print(f"Step 3: Checking has_trading_data_for_date for {target_date.date()}")
print(f"  Target date: {target_date}")
print(f"  Target date (date only): {target_date.date()}")
print()

if batch_data:
    # Simulate what has_trading_data_for_date does
    print(f"  Checking batch data...")
    data = batch_data.get('data', {})
    timestamps = data.get('timestamp', [])
    target_date_only = target_date.date()
    
    print(f"  Looking for date: {target_date_only}")
    print(f"  Checking {len(timestamps)} timestamps...")
    
    found = False
    for i, ts in enumerate(timestamps):
        from datetime import datetime as dt
        # This is what the code does (timezone-naive)
        ts_date_naive = dt.fromtimestamp(ts).date()
        # This is what it should do (timezone-aware)
        ts_date_utc = dt.fromtimestamp(ts, tz=timezone.utc).date()
        
        if ts_date_naive == target_date_only:
            print(f"    ✓ MATCH (naive): Timestamp {ts} -> {ts_date_naive}")
            found = True
        elif ts_date_utc == target_date_only:
            print(f"    ✓ MATCH (UTC): Timestamp {ts} -> {ts_date_utc}")
            if not found:
                print(f"    ⚠️  But naive comparison failed! This is the bug!")
                found = True
        else:
            if i < 3:  # Only show first 3 for brevity
                print(f"    - No match: {ts} -> naive:{ts_date_naive}, UTC:{ts_date_utc}")
    
    print()
    result = tracker.has_trading_data_for_date(ticker, target_date, batch_data)
    print(f"  has_trading_data_for_date result: {result}")
    
    if not result:
        print(f"  ❌ BUG FOUND: has_trading_data_for_date returned False even though data exists!")
        print(f"     This is likely due to timezone-naive timestamp conversion in the function")
    else:
        print(f"  ✓ has_trading_data_for_date returned True (correct)")
else:
    print(f"  Cannot check - no batch data")

# Step 4: Check is_future_date
print(f"\nStep 4: Checking is_future_date")
now = datetime.now(timezone.utc)
is_future = tracker.is_future_date(target_date)
print(f"  Current time: {now}")
print(f"  Target date: {target_date}")
print(f"  Is future? {is_future}")
print()

# Step 5: Check what the actual code path does at line 3059
print(f"Step 5: Simulating code at line 3059")
print(f"  This is where the bug occurs - checking has_trading_data_for_date")
target_datetime_utc = datetime(2025, 12, 9, 14, 30, 0, tzinfo=timezone.utc)  # 9:30 AM ET = 14:30 UTC
target_date_only = target_datetime_utc.replace(hour=0, minute=0, second=0, microsecond=0)
print(f"  target_datetime_utc: {target_datetime_utc}")
print(f"  target_date_only: {target_date_only}")
print(f"  Calling has_trading_data_for_date({ticker}, {target_date_only}, batch_data)...")

if batch_data:
    result = tracker.has_trading_data_for_date(ticker, target_date_only, batch_data)
    print(f"  Result: {result}")
    if not result:
        print(f"  ❌ This causes the code to mark Dec 9 as 'Closed' at line 3065")
    else:
        print(f"  ✓ This should allow Dec 9 data to be used")

