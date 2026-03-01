#!/usr/bin/env python3
"""
Internal unittest to test VWAP chart data logic directly and show debug output
This tests the same logic as the API endpoint but shows detailed logs
"""

import sys
import json
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_vwap_chart_internal_logic():
    """Test the VWAP chart data logic directly (same as API endpoint)"""
    
    print("=" * 80)
    print("VWAP CHART INTERNAL LOGIC TEST")
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
    
    if is_today:
        print("⚠️  Bearish date is today - skipping test")
        return False
    
    # Calculate market open and close
    market_open_utc = tracker._get_market_open_time(bearish_date, ticker)
    market_close_utc = tracker._get_market_close_time(bearish_date, ticker)
    
    if not market_open_utc or not market_close_utc:
        print("❌ Could not determine market hours")
        return False
    
    print(f"Market hours:")
    print(f"  Open (UTC): {market_open_utc}")
    print(f"  Close (UTC): {market_close_utc}")
    print()
    
    # Calculate expected time window
    start_time_utc = market_close_utc - timedelta(hours=3)
    
    # Get next trading day
    next_trading_day = tracker.get_next_trading_day(bearish_date, ticker)
    if not next_trading_day:
        print("❌ Could not determine next trading day")
        return False
    
    print(f"Next trading day: {next_trading_day}")
    
    # First 3 hours of next trading day
    next_market_open_utc = tracker._get_market_open_time(next_trading_day, ticker)
    if not next_market_open_utc:
        print("❌ Could not determine next trading day market open")
        return False
    
    end_time_utc = next_market_open_utc + timedelta(hours=3)
    
    print(f"Time window:")
    print(f"  Start (UTC): {start_time_utc} (last 3h of {bearish_date_str})")
    print(f"  End (UTC): {end_time_utc} (first 3h of {next_trading_day.date()})")
    print()
    
    # Fetch data for both days
    bearish_date_only = bearish_date.replace(hour=0, minute=0, second=0, microsecond=0)
    if next_trading_day.tzinfo is None:
        next_trading_day = next_trading_day.replace(tzinfo=timezone.utc)
    next_trading_day_only = next_trading_day.replace(hour=0, minute=0, second=0, microsecond=0)
    
    print("Fetching intraday data...")
    
    # Fetch data for bearish_date
    intraday_data_day1 = tracker._fetch_intraday_data_for_day(ticker, bearish_date_only, interval='1min')
    if not intraday_data_day1:
        intraday_data_day1 = tracker._fetch_intraday_data_for_day(ticker, bearish_date_only, interval='5min')
    
    # Fetch data for next trading day
    intraday_data_day2 = tracker._fetch_intraday_data_for_day(ticker, next_trading_day_only, interval='1min')
    if not intraday_data_day2:
        intraday_data_day2 = tracker._fetch_intraday_data_for_day(ticker, next_trading_day_only, interval='5min')
    
    print(f"Day 1 data: {intraday_data_day1 is not None and intraday_data_day1.get('success', False)}")
    print(f"Day 2 data: {intraday_data_day2 is not None and intraday_data_day2.get('success', False)}")
    print()
    
    # Combine data from both days
    all_timestamps = []
    all_opens = []
    all_highs = []
    all_lows = []
    all_closes = []
    all_volumes = []
    
    if intraday_data_day1 and intraday_data_day1.get('success') and 'data' in intraday_data_day1:
        data1 = intraday_data_day1['data']
        all_timestamps.extend(data1.get('timestamp', []))
        all_opens.extend(data1.get('open', []))
        all_highs.extend(data1.get('high', []))
        all_lows.extend(data1.get('low', []))
        all_closes.extend(data1.get('close', []))
        all_volumes.extend(data1.get('volume', []))
    
    if intraday_data_day2 and intraday_data_day2.get('success') and 'data' in intraday_data_day2:
        data2 = intraday_data_day2['data']
        all_timestamps.extend(data2.get('timestamp', []))
        all_opens.extend(data2.get('open', []))
        all_highs.extend(data2.get('high', []))
        all_lows.extend(data2.get('low', []))
        all_closes.extend(data2.get('close', []))
        all_volumes.extend(data2.get('volume', []))
    
    if not all_timestamps:
        print("❌ No intraday data available")
        return False
    
    # Debug: Check data before filtering
    day1_count_before = sum(1 for ts in all_timestamps 
                           if datetime.fromtimestamp(ts, tz=timezone.utc).date() == bearish_date.date())
    day2_count_before = sum(1 for ts in all_timestamps 
                           if datetime.fromtimestamp(ts, tz=timezone.utc).date() == next_trading_day.date())
    print(f"[DEBUG] Before filtering: {len(all_timestamps)} total, {day1_count_before} from {bearish_date_str}, {day2_count_before} from {next_trading_day.date()}")
    
    # Filter data to the time window
    start_timestamp = int(start_time_utc.timestamp())
    end_timestamp = int(end_time_utc.timestamp())
    
    print(f"[DEBUG] Filter range: {start_timestamp} ({start_time_utc}) to {end_timestamp} ({end_time_utc})")
    
    filtered_data = []
    for i, ts in enumerate(all_timestamps):
        if start_timestamp <= ts <= end_timestamp:
            filtered_data.append({
                'timestamp': ts,
                'open': all_opens[i] if i < len(all_opens) else None,
                'high': all_highs[i] if i < len(all_highs) else None,
                'low': all_lows[i] if i < len(all_lows) else None,
                'close': all_closes[i] if i < len(all_closes) else None,
                'volume': all_volumes[i] if i < len(all_volumes) else 0
            })
    
    # Debug: Check data after filtering
    day1_count_after = sum(1 for d in filtered_data 
                          if datetime.fromtimestamp(d['timestamp'], tz=timezone.utc).date() == bearish_date.date())
    day2_count_after = sum(1 for d in filtered_data 
                          if datetime.fromtimestamp(d['timestamp'], tz=timezone.utc).date() == next_trading_day.date())
    print(f"[DEBUG] After filtering: {len(filtered_data)} total, {day1_count_after} from {bearish_date_str}, {day2_count_after} from {next_trading_day.date()}")
    
    if not filtered_data:
        print("❌ No data in filtered range")
        return False
    
    # Check for None values
    none_count = sum(1 for d in filtered_data if d['open'] is None or d['high'] is None or d['low'] is None or d['close'] is None)
    print(f"[DEBUG] Data points with None values: {none_count} out of {len(filtered_data)}")
    
    # Show sample of filtered data
    print(f"[DEBUG] Sample filtered data (first 3 and last 3):")
    for i, d in enumerate(filtered_data[:3] + filtered_data[-3:]):
        dt = datetime.fromtimestamp(d['timestamp'], tz=timezone.utc)
        has_none = d['open'] is None or d['high'] is None or d['low'] is None or d['close'] is None
        print(f"  {i+1 if i < 3 else len(filtered_data)-2+i}. {dt} (date={dt.date()}, has_none={has_none})")
    print()
    
    # Now simulate the aggregation logic
    print("=" * 80)
    print("AGGREGATION SIMULATION")
    print("=" * 80)
    print()
    
    # Sort filtered data by timestamp
    filtered_data.sort(key=lambda x: x['timestamp'])
    
    # Group into 15-minute periods
    current_15min_start = None
    current_15min_data = []
    candles_15min = []
    skipped_count = 0
    skipped_dates = set()
    processed_dates = set()
    
    for data_point in filtered_data:
        ts = data_point['timestamp']
        dt_check = datetime.fromtimestamp(ts, tz=timezone.utc)
        processed_dates.add(dt_check.date())
        
        open_price = data_point['open']
        high = data_point['high']
        low = data_point['low']
        close = data_point['close']
        volume = data_point['volume']
        
        if open_price is None or high is None or low is None or close is None:
            skipped_count += 1
            skipped_dates.add(dt_check.date())
            continue
        
        # Convert timestamp to datetime for grouping
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        
        # Round down to nearest 15 minutes
        minute = dt.minute
        rounded_minute = (minute // 15) * 15
        candle_start = dt.replace(minute=rounded_minute, second=0, microsecond=0)
        
        if current_15min_start is None or candle_start != current_15min_start:
            # Save previous candle if exists
            if current_15min_data:
                candle_open = current_15min_data[0]['open']
                candle_high = max(d['high'] for d in current_15min_data)
                candle_low = min(d['low'] for d in current_15min_data)
                candle_close = current_15min_data[-1]['close']
                candle_volume = sum(d['volume'] for d in current_15min_data)
                
                candles_15min.append({
                    'timestamp': int(current_15min_start.timestamp()),
                    'open': candle_open,
                    'high': candle_high,
                    'low': candle_low,
                    'close': candle_close,
                    'volume': candle_volume
                })
            
            # Start new candle
            current_15min_start = candle_start
            current_15min_data = [data_point]
        else:
            current_15min_data.append(data_point)
    
    # Don't forget the last candle
    if current_15min_data:
        candle_open = current_15min_data[0]['open']
        candle_high = max(d['high'] for d in current_15min_data)
        candle_low = min(d['low'] for d in current_15min_data)
        candle_close = current_15min_data[-1]['close']
        candle_volume = sum(d['volume'] for d in current_15min_data)
        
        candles_15min.append({
            'timestamp': int(current_15min_start.timestamp()),
            'open': candle_open,
            'high': candle_high,
            'low': candle_low,
            'close': candle_close,
            'volume': candle_volume
        })
    
    print(f"[DEBUG] Aggregation stats:")
    print(f"  Processed: {len(filtered_data)} data points")
    print(f"  Skipped (None values): {skipped_count} (dates: {sorted(skipped_dates)})")
    print(f"  Processed dates: {sorted(processed_dates)}")
    print(f"  Created candles: {len(candles_15min)}")
    print()
    
    # Check final candles
    if candles_15min:
        first_candle_dt = datetime.fromtimestamp(candles_15min[0]['timestamp'], tz=timezone.utc)
        last_candle_dt = datetime.fromtimestamp(candles_15min[-1]['timestamp'], tz=timezone.utc)
        unique_candle_dates = set()
        for c in candles_15min:
            dt = datetime.fromtimestamp(c['timestamp'], tz=timezone.utc)
            unique_candle_dates.add(dt.date())
        
        print(f"[DEBUG] Final candles:")
        print(f"  Count: {len(candles_15min)}")
        print(f"  Dates: {sorted(unique_candle_dates)}")
        print(f"  First: {first_candle_dt} (timestamp={candles_15min[0]['timestamp']})")
        print(f"  Last: {last_candle_dt} (timestamp={candles_15min[-1]['timestamp']})")
        print()
        
        # Show first and last few candles
        print("First 3 candles:")
        for i, c in enumerate(candles_15min[:3]):
            dt = datetime.fromtimestamp(c['timestamp'], tz=timezone.utc)
            print(f"  {i+1}. {dt} (date={dt.date()})")
        print("Last 3 candles:")
        for i, c in enumerate(candles_15min[-3:]):
            dt = datetime.fromtimestamp(c['timestamp'], tz=timezone.utc)
            print(f"  {len(candles_15min)-2+i}. {dt} (date={dt.date()})")
        print()
        
        # Verify
        if len(unique_candle_dates) == 1:
            print(f"❌ ERROR: All candles are from same day ({sorted(unique_candle_dates)})")
            print(f"   Expected: Both {bearish_date_str} and {next_trading_day.date()}")
            return False
        elif bearish_date.date() in unique_candle_dates and next_trading_day.date() in unique_candle_dates:
            print("✅ SUCCESS: Candles span both days!")
            return True
        else:
            print(f"⚠️  WARNING: Unexpected dates in candles: {sorted(unique_candle_dates)}")
            return False
    else:
        print("❌ ERROR: No candles created")
        return False

if __name__ == '__main__':
    success = test_vwap_chart_internal_logic()
    sys.exit(0 if success else 1)
