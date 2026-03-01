#!/usr/bin/env python3
"""
Unit test to verify VWAP chart data endpoint calculates correct time range
for past dates (last 3 hours of bearish_date + first 3 hours of next trading day)
"""

import sys
import json
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_vwap_chart_time_range():
    """Test that VWAP chart endpoint calculates correct time window for past dates"""
    
    print("=" * 80)
    print("VWAP CHART TIME RANGE TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Test with Nov 13, 2025 (a Thursday)
    bearish_date_str = "2025-11-13"
    ticker = "NET"  # Cloudflare
    
    print(f"Test Case: {ticker} on {bearish_date_str}")
    print("-" * 80)
    
    # Parse bearish_date
    bearish_date = datetime.strptime(bearish_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    
    # Check if it's today
    now_utc = datetime.now(timezone.utc)
    is_today = bearish_date.date() == now_utc.date()
    
    print(f"Bearish date: {bearish_date}")
    print(f"Is today: {is_today}")
    print()
    
    if is_today:
        print("⚠️  Skipping test - bearish_date is today. Use a past date for this test.")
        return
    
    # Calculate market open and close for bearish_date
    market_open_utc = tracker._get_market_open_time(bearish_date, ticker)
    market_close_utc = tracker._get_market_close_time(bearish_date, ticker)
    
    if not market_open_utc or not market_close_utc:
        print(f"❌ Could not determine market hours for {ticker}")
        return
    
    print(f"Market hours for {bearish_date_str}:")
    print(f"  Open (UTC): {market_open_utc}")
    print(f"  Close (UTC): {market_close_utc}")
    print()
    
    # Calculate expected time window
    # Last 3 hours of bearish_date
    start_time_utc = market_close_utc - timedelta(hours=3)
    
    # Get next trading day
    next_trading_day = tracker.get_next_trading_day(bearish_date, ticker)
    if not next_trading_day:
        print(f"❌ Could not determine next trading day")
        return
    
    print(f"Next trading day: {next_trading_day}")
    
    # First 3 hours of next trading day
    next_market_open_utc = tracker._get_market_open_time(next_trading_day, ticker)
    if not next_market_open_utc:
        print(f"❌ Could not determine next trading day market open")
        return
    
    end_time_utc = next_market_open_utc + timedelta(hours=3)
    
    print()
    print(f"Expected time window:")
    print(f"  Start (UTC): {start_time_utc} (last 3h of {bearish_date_str})")
    print(f"  End (UTC): {end_time_utc} (first 3h of {next_trading_day.date()})")
    print()
    
    # Convert to ET for readability
    def utc_to_et(utc_dt):
        """Convert UTC to ET (approximate)"""
        month = utc_dt.month
        offset_hours = -4 if (month >= 3 and month <= 10) else -5
        return utc_dt + timedelta(hours=offset_hours)
    
    start_et = utc_to_et(start_time_utc)
    end_et = utc_to_et(end_time_utc)
    
    print(f"Expected time window (ET):")
    print(f"  Start (ET): {start_et.strftime('%Y-%m-%d %H:%M:%S')} ET")
    print(f"  End (ET): {end_et.strftime('%Y-%m-%d %H:%M:%S')} ET")
    print()
    
    # Convert to IST for readability (UTC+2 or UTC+3)
    def utc_to_ist(utc_dt):
        """Convert UTC to IST (approximate)"""
        month = utc_dt.month
        offset_hours = 3 if (month >= 4 and month <= 10) else 2  # IDT: Apr-Oct, IST: Nov-Mar
        return utc_dt + timedelta(hours=offset_hours)
    
    start_ist = utc_to_ist(start_time_utc)
    end_ist = utc_to_ist(end_time_utc)
    
    print(f"Expected time window (IST):")
    print(f"  Start (IST): {start_ist.strftime('%Y-%m-%d %H:%M:%S')} IST")
    print(f"  End (IST): {end_ist.strftime('%Y-%m-%d %H:%M:%S')} IST")
    print()
    
    # Fetch data for both days
    bearish_date_only = bearish_date.replace(hour=0, minute=0, second=0, microsecond=0)
    next_trading_day_only = next_trading_day.replace(hour=0, minute=0, second=0, microsecond=0) if hasattr(next_trading_day, 'replace') else next_trading_day
    
    print(f"Fetching intraday data...")
    print(f"  Day 1 ({bearish_date_str}): {bearish_date_only}")
    print(f"  Day 2 ({next_trading_day.date()}): {next_trading_day_only}")
    print()
    
    # Fetch data for bearish_date
    intraday_data_day1 = tracker._fetch_intraday_data_for_day(ticker, bearish_date_only, interval='1min')
    if not intraday_data_day1:
        intraday_data_day1 = tracker._fetch_intraday_data_for_day(ticker, bearish_date_only, interval='5min')
    
    # Fetch data for next trading day
    intraday_data_day2 = tracker._fetch_intraday_data_for_day(ticker, next_trading_day_only, interval='1min')
    if not intraday_data_day2:
        intraday_data_day2 = tracker._fetch_intraday_data_for_day(ticker, next_trading_day_only, interval='5min')
    
    print(f"Data fetch results:")
    print(f"  Day 1 data available: {intraday_data_day1 is not None and intraday_data_day1.get('success', False)}")
    print(f"  Day 2 data available: {intraday_data_day2 is not None and intraday_data_day2.get('success', False)}")
    print()
    
    # Check if we have data
    all_timestamps = []
    if intraday_data_day1 and intraday_data_day1.get('success') and 'data' in intraday_data_day1:
        data1 = intraday_data_day1['data']
        timestamps1 = data1.get('timestamp', [])
        all_timestamps.extend(timestamps1)
        print(f"  Day 1 timestamps: {len(timestamps1)}")
        if timestamps1:
            first_ts1 = datetime.fromtimestamp(timestamps1[0], tz=timezone.utc)
            last_ts1 = datetime.fromtimestamp(timestamps1[-1], tz=timezone.utc)
            print(f"    Range: {first_ts1} to {last_ts1}")
    
    if intraday_data_day2 and intraday_data_day2.get('success') and 'data' in intraday_data_day2:
        data2 = intraday_data_day2['data']
        timestamps2 = data2.get('timestamp', [])
        all_timestamps.extend(timestamps2)
        print(f"  Day 2 timestamps: {len(timestamps2)}")
        if timestamps2:
            first_ts2 = datetime.fromtimestamp(timestamps2[0], tz=timezone.utc)
            last_ts2 = datetime.fromtimestamp(timestamps2[-1], tz=timezone.utc)
            print(f"    Range: {first_ts2} to {last_ts2}")
    
    print()
    
    if not all_timestamps:
        print("❌ No intraday data available for either day")
        return
    
    # Filter data to expected time window
    start_timestamp = int(start_time_utc.timestamp())
    end_timestamp = int(end_time_utc.timestamp())
    
    filtered_timestamps = [ts for ts in all_timestamps if start_timestamp <= ts <= end_timestamp]
    
    print(f"Filtering results:")
    print(f"  Total timestamps: {len(all_timestamps)}")
    print(f"  Filtered timestamps: {len(filtered_timestamps)}")
    print(f"  Expected range: {start_timestamp} to {end_timestamp}")
    print()
    
    if filtered_timestamps:
        first_filtered = datetime.fromtimestamp(filtered_timestamps[0], tz=timezone.utc)
        last_filtered = datetime.fromtimestamp(filtered_timestamps[-1], tz=timezone.utc)
        
        first_filtered_ist = utc_to_ist(first_filtered)
        last_filtered_ist = utc_to_ist(last_filtered)
        
        print(f"Filtered data range:")
        print(f"  First (UTC): {first_filtered}")
        print(f"  Last (UTC): {last_filtered}")
        print(f"  First (IST): {first_filtered_ist.strftime('%Y-%m-%d %H:%M:%S')} IST")
        print(f"  Last (IST): {last_filtered_ist.strftime('%Y-%m-%d %H:%M:%S')} IST")
        print()
        
        # Verify the range
        expected_start_ist = start_ist.strftime('%Y-%m-%d %H')
        expected_end_ist = end_ist.strftime('%Y-%m-%d %H')
        actual_start_ist = first_filtered_ist.strftime('%Y-%m-%d %H')
        actual_end_ist = last_filtered_ist.strftime('%Y-%m-%d %H')
        
        print(f"Verification:")
        print(f"  Expected start hour (IST): {expected_start_ist}")
        print(f"  Actual start hour (IST): {actual_start_ist}")
        print(f"  Expected end hour (IST): {expected_end_ist}")
        print(f"  Actual end hour (IST): {actual_end_ist}")
        print()
        
        # Check if we have data from both days
        day1_count = sum(1 for ts in filtered_timestamps if datetime.fromtimestamp(ts, tz=timezone.utc).date() == bearish_date.date())
        day2_count = sum(1 for ts in filtered_timestamps if datetime.fromtimestamp(ts, tz=timezone.utc).date() == next_trading_day.date())
        
        print(f"Data distribution:")
        print(f"  Timestamps from {bearish_date_str}: {day1_count}")
        print(f"  Timestamps from {next_trading_day.date()}: {day2_count}")
        print()
        
        if day1_count == 0:
            print("❌ ERROR: No data from bearish_date (should have last 3 hours)")
        elif day2_count == 0:
            print("❌ ERROR: No data from next trading day (should have first 3 hours)")
        elif expected_start_ist[:13] != actual_start_ist[:13]:  # Compare date and hour
            print(f"❌ ERROR: Start time mismatch! Expected ~{expected_start_ist}, got {actual_start_ist}")
        elif expected_end_ist[:13] != actual_end_ist[:13]:  # Compare date and hour
            print(f"❌ ERROR: End time mismatch! Expected ~{expected_end_ist}, got {actual_end_ist}")
        else:
            print("✅ PASS: Time range looks correct!")
    else:
        print("❌ ERROR: No data in expected time range!")
        print(f"  This could mean:")
        print(f"    1. Data is not available for these dates")
        print(f"    2. Time window calculation is wrong")
        print(f"    3. Data timestamps are in wrong timezone")
    
    print()
    print("=" * 80)
    print("TIME LABEL CONVERSION TEST")
    print("=" * 80)
    print()
    
    # Test time label conversion
    # Test a few sample timestamps
    test_timestamps = [
        (1763056800, "2025-11-13 18:00:00 UTC", "Should be Nov 13 20:00 IST"),
        (1763141400, "2025-11-14 17:30:00 UTC", "Should be Nov 14 19:30 IST"),
    ]
    
    print("Testing time label conversion:")
    for ts, utc_str, expected in test_timestamps:
        dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
        is_israel_dst = 4 <= dt_utc.month <= 10
        israel_offset_hours = 3 if is_israel_dst else 2
        israel_dt = dt_utc + timedelta(hours=israel_offset_hours)
        
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        month = month_names[israel_dt.month - 1]
        day = israel_dt.day
        hour = israel_dt.hour
        minute = israel_dt.minute
        time_label = f"{month} {day} {hour:02d}:{minute:02d}"
        
        print(f"  {utc_str}")
        print(f"    -> {time_label} IST")
        print(f"    Expected: {expected}")
        print()
    
    print("=" * 80)

if __name__ == '__main__':
    test_vwap_chart_time_range()
