#!/usr/bin/env python3
"""
Debug script to investigate why Nov 14 data isn't being included in VWAP chart
"""

import sys
import json
import requests
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def debug_vwap_chart_data():
    """Debug the VWAP chart data fetching logic"""
    
    print("=" * 80)
    print("VWAP CHART DATA DEBUG")
    print("=" * 80)
    print()
    
    ticker = "NET"
    bearish_date_str = "2025-11-13"
    
    print(f"Ticker: {ticker}")
    print(f"Bearish date: {bearish_date_str}")
    print()
    
    tracker = LayoffTracker()
    
    # Parse bearish_date
    bearish_date = datetime.strptime(bearish_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    
    # Check if it's today
    now_utc = datetime.now(timezone.utc)
    is_today = bearish_date.date() == now_utc.date()
    
    print(f"Is today: {is_today}")
    print()
    
    if is_today:
        print("⚠️  Bearish date is today - skipping debug")
        return
    
    # Calculate market open and close
    market_open_utc = tracker._get_market_open_time(bearish_date, ticker)
    market_close_utc = tracker._get_market_close_time(bearish_date, ticker)
    
    print(f"Market hours for {bearish_date_str}:")
    print(f"  Open (UTC): {market_open_utc}")
    print(f"  Close (UTC): {market_close_utc}")
    print()
    
    # Calculate expected time window
    start_time_utc = market_close_utc - timedelta(hours=3)
    
    # Get next trading day
    next_trading_day = tracker.get_next_trading_day(bearish_date, ticker)
    print(f"Next trading day calculation:")
    print(f"  Input: {bearish_date}")
    print(f"  Result: {next_trading_day}")
    print()
    
    if not next_trading_day:
        print("❌ Could not determine next trading day")
        return
    
    # First 3 hours of next trading day
    next_market_open_utc = tracker._get_market_open_time(next_trading_day, ticker)
    if not next_market_open_utc:
        print("❌ Could not determine next trading day market open")
        return
    
    end_time_utc = next_market_open_utc + timedelta(hours=3)
    
    print(f"Expected time window:")
    print(f"  Start (UTC): {start_time_utc} (last 3h of {bearish_date_str})")
    print(f"  End (UTC): {end_time_utc} (first 3h of {next_trading_day.date()})")
    print()
    
    # Fetch data for both days
    bearish_date_only = bearish_date.replace(hour=0, minute=0, second=0, microsecond=0)
    next_trading_day_only = next_trading_day.replace(hour=0, minute=0, second=0, microsecond=0)
    
    print(f"Fetching intraday data:")
    print(f"  Day 1 ({bearish_date_str}): {bearish_date_only}")
    print(f"  Day 2 ({next_trading_day.date()}): {next_trading_day_only}")
    print()
    
    # Fetch data for bearish_date
    print("Fetching Day 1 data (1min)...")
    intraday_data_day1 = tracker._fetch_intraday_data_for_day(ticker, bearish_date_only, interval='1min')
    print(f"  Result: {intraday_data_day1 is not None}")
    if intraday_data_day1:
        print(f"  Success: {intraday_data_day1.get('success', False)}")
        if 'data' in intraday_data_day1:
            data1 = intraday_data_day1['data']
            timestamps1 = data1.get('timestamp', [])
            print(f"  Timestamps: {len(timestamps1)}")
            if timestamps1:
                first_ts1 = datetime.fromtimestamp(timestamps1[0], tz=timezone.utc)
                last_ts1 = datetime.fromtimestamp(timestamps1[-1], tz=timezone.utc)
                print(f"    Range: {first_ts1} to {last_ts1}")
    
    if not intraday_data_day1:
        print("Fetching Day 1 data (5min fallback)...")
        intraday_data_day1 = tracker._fetch_intraday_data_for_day(ticker, bearish_date_only, interval='5min')
        print(f"  Result: {intraday_data_day1 is not None}")
        if intraday_data_day1:
            print(f"  Success: {intraday_data_day1.get('success', False)}")
    
    print()
    
    # Fetch data for next trading day
    print("Fetching Day 2 data (1min)...")
    intraday_data_day2 = tracker._fetch_intraday_data_for_day(ticker, next_trading_day_only, interval='1min')
    print(f"  Result: {intraday_data_day2 is not None}")
    if intraday_data_day2:
        print(f"  Success: {intraday_data_day2.get('success', False)}")
        if 'data' in intraday_data_day2:
            data2 = intraday_data_day2['data']
            timestamps2 = data2.get('timestamp', [])
            print(f"  Timestamps: {len(timestamps2)}")
            if timestamps2:
                first_ts2 = datetime.fromtimestamp(timestamps2[0], tz=timezone.utc)
                last_ts2 = datetime.fromtimestamp(timestamps2[-1], tz=timezone.utc)
                print(f"    Range: {first_ts2} to {last_ts2}")
    else:
        print("  ⚠️  Day 2 data fetch returned None")
    
    if not intraday_data_day2:
        print("Fetching Day 2 data (5min fallback)...")
        intraday_data_day2 = tracker._fetch_intraday_data_for_day(ticker, next_trading_day_only, interval='5min')
        print(f"  Result: {intraday_data_day2 is not None}")
        if intraday_data_day2:
            print(f"  Success: {intraday_data_day2.get('success', False)}")
            if 'data' in intraday_data_day2:
                data2 = intraday_data_day2['data']
                timestamps2 = data2.get('timestamp', [])
                print(f"  Timestamps: {len(timestamps2)}")
    
    print()
    
    # Check what data we have
    all_timestamps = []
    if intraday_data_day1 and intraday_data_day1.get('success') and 'data' in intraday_data_day1:
        data1 = intraday_data_day1['data']
        timestamps1 = data1.get('timestamp', [])
        all_timestamps.extend(timestamps1)
        print(f"Day 1 timestamps added: {len(timestamps1)}")
    
    if intraday_data_day2 and intraday_data_day2.get('success') and 'data' in intraday_data_day2:
        data2 = intraday_data_day2['data']
        timestamps2 = data2.get('timestamp', [])
        all_timestamps.extend(timestamps2)
        print(f"Day 2 timestamps added: {len(timestamps2)}")
    else:
        print("⚠️  Day 2 data not available or not successful")
        if intraday_data_day2:
            print(f"  Response: {json.dumps(intraday_data_day2, indent=2, default=str)[:500]}")
    
    print(f"Total timestamps: {len(all_timestamps)}")
    print()
    
    # Filter data
    start_timestamp = int(start_time_utc.timestamp())
    end_timestamp = int(end_time_utc.timestamp())
    
    print(f"Filtering timestamps:")
    print(f"  Start timestamp: {start_timestamp} ({start_time_utc})")
    print(f"  End timestamp: {end_timestamp} ({end_time_utc})")
    print()
    
    filtered_timestamps = [ts for ts in all_timestamps if start_timestamp <= ts <= end_timestamp]
    
    print(f"Filtered timestamps: {len(filtered_timestamps)}")
    
    if filtered_timestamps:
        first_filtered = datetime.fromtimestamp(filtered_timestamps[0], tz=timezone.utc)
        last_filtered = datetime.fromtimestamp(filtered_timestamps[-1], tz=timezone.utc)
        
        print(f"  First: {first_filtered}")
        print(f"  Last: {last_filtered}")
        
        # Check dates
        unique_dates = set()
        for ts in filtered_timestamps:
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            unique_dates.add(dt.date())
        
        print(f"  Unique dates: {sorted(unique_dates)}")
        
        # Check how many from each day
        day1_count = sum(1 for ts in filtered_timestamps 
                         if datetime.fromtimestamp(ts, tz=timezone.utc).date() == bearish_date.date())
        day2_count = sum(1 for ts in filtered_timestamps 
                         if datetime.fromtimestamp(ts, tz=timezone.utc).date() == next_trading_day.date())
        
        print(f"  From {bearish_date_str}: {day1_count}")
        print(f"  From {next_trading_day.date()}: {day2_count}")
    else:
        print("  ⚠️  No timestamps in filtered range!")
        print(f"  All timestamps range:")
        if all_timestamps:
            first_all = datetime.fromtimestamp(min(all_timestamps), tz=timezone.utc)
            last_all = datetime.fromtimestamp(max(all_timestamps), tz=timezone.utc)
            print(f"    {first_all} to {last_all}")
    
    print()
    print("=" * 80)

if __name__ == '__main__':
    debug_vwap_chart_data()
