#!/usr/bin/env python3
"""
Unittest to diagnose why the -6.57% drop for DOCN on Nov 13, 2025 is not visible in the VWAP chart
"""

import sys
import json
import requests
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_docn_vwap_chart():
    """Test VWAP chart data for DOCN on Nov 13, 2025"""
    
    print("=" * 80)
    print("VWAP CHART DIAGNOSIS - DOCN Nov 13, 2025")
    print("=" * 80)
    print()
    
    ticker = "DOCN"
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
        print("⚠️  Bearish date is today - using today path")
    else:
        print("📅 Using past date path")
    
    # Calculate market open and close
    market_open_utc = tracker._get_market_open_time(bearish_date, ticker)
    market_close_utc = tracker._get_market_close_time(bearish_date, ticker)
    
    print(f"\nMarket hours for {bearish_date_str}:")
    print(f"  Open (UTC): {market_open_utc}")
    print(f"  Close (UTC): {market_close_utc}")
    
    if market_open_utc:
        # Convert to ET and Israel time for reference
        et_offset = -5 if bearish_date.month < 3 or bearish_date.month > 10 else -4  # EST vs EDT
        market_open_et = market_open_utc + timedelta(hours=-et_offset)
        print(f"  Open (ET): {market_open_et.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Israel time (rough estimate)
        israel_offset = 2 if bearish_date.month < 4 or bearish_date.month > 10 else 3  # IST vs IDT
        market_open_ist = market_open_utc + timedelta(hours=israel_offset)
        print(f"  Open (Israel time, approx): {market_open_ist.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print()
    
    # Test the API endpoint
    print("=" * 80)
    print("TESTING API ENDPOINT")
    print("=" * 80)
    print()
    
    url = f"http://127.0.0.1:8082/api/vwap-chart-data?ticker={ticker}&bearish_date={bearish_date_str}"
    print(f"URL: {url}")
    print()
    
    try:
        response = requests.get(url, timeout=30)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success')}")
            
            if data.get('success'):
                candles = data.get('candles', [])
                time_labels = data.get('time_labels', [])
                vwap_points = data.get('vwap_points', [])
                
                print(f"\nCandles returned: {len(candles)}")
                print(f"Time labels: {len(time_labels)}")
                print(f"VWAP points: {len(vwap_points)}")
                
                if candles:
                    # Check first and last candles
                    first_candle = candles[0]
                    last_candle = candles[-1]
                    
                    first_ts = first_candle['timestamp']
                    last_ts = last_candle['timestamp']
                    
                    first_dt_utc = datetime.fromtimestamp(first_ts, tz=timezone.utc)
                    last_dt_utc = datetime.fromtimestamp(last_ts, tz=timezone.utc)
                    
                    print(f"\nFirst candle:")
                    print(f"  Timestamp: {first_ts}")
                    print(f"  UTC: {first_dt_utc}")
                    print(f"  ET: {(first_dt_utc + timedelta(hours=-et_offset)).strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"  Israel time (approx): {(first_dt_utc + timedelta(hours=israel_offset)).strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"  Time label: {time_labels[0] if time_labels else 'N/A'}")
                    print(f"  Open: ${first_candle['open']:.2f}, High: ${first_candle['high']:.2f}, Low: ${first_candle['low']:.2f}, Close: ${first_candle['close']:.2f}")
                    
                    print(f"\nLast candle:")
                    print(f"  Timestamp: {last_ts}")
                    print(f"  UTC: {last_dt_utc}")
                    print(f"  ET: {(last_dt_utc + timedelta(hours=-et_offset)).strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"  Israel time (approx): {(last_dt_utc + timedelta(hours=israel_offset)).strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"  Time label: {time_labels[-1] if time_labels else 'N/A'}")
                    print(f"  Open: ${last_candle['open']:.2f}, High: ${last_candle['high']:.2f}, Low: ${last_candle['low']:.2f}, Close: ${last_candle['close']:.2f}")
                    
                    # Check if we're missing data from market open
                    if market_open_utc:
                        expected_start_ts = int(market_open_utc.timestamp())
                        if first_ts > expected_start_ts:
                            missing_seconds = first_ts - expected_start_ts
                            missing_minutes = missing_seconds / 60
                            print(f"\n⚠️  WARNING: Missing {missing_minutes:.0f} minutes ({missing_seconds} seconds) of data from market open!")
                            print(f"   Expected start: {market_open_utc} UTC (timestamp: {expected_start_ts})")
                            print(f"   Actual start: {first_dt_utc} UTC (timestamp: {first_ts})")
                        else:
                            print(f"\n✅ Data starts at or before market open")
                    
                    # Check price range
                    all_lows = [c['low'] for c in candles]
                    all_highs = [c['high'] for c in candles]
                    min_price = min(all_lows)
                    max_price = max(all_highs)
                    price_range = max_price - min_price
                    price_drop_pct = ((min_price - max_price) / max_price) * 100
                    
                    print(f"\nPrice analysis:")
                    print(f"  Min price: ${min_price:.2f}")
                    print(f"  Max price: ${max_price:.2f}")
                    print(f"  Price range: ${price_range:.2f}")
                    print(f"  Max drop: {price_drop_pct:.2f}%")
                    print(f"  Expected drop: -6.57%")
                    
                    if abs(price_drop_pct - 6.57) > 1.0:
                        print(f"\n⚠️  WARNING: Chart shows {price_drop_pct:.2f}% drop, but expected -6.57%")
                        print(f"   This suggests the drop occurred before the chart's start time!")
                    
                    # Show first 5 and last 5 time labels
                    print(f"\nFirst 5 time labels:")
                    for i, label in enumerate(time_labels[:5]):
                        if i < len(candles):
                            candle = candles[i]
                            print(f"  {label}: Open=${candle['open']:.2f}, Close=${candle['close']:.2f}")
                    
                    print(f"\nLast 5 time labels:")
                    for i, label in enumerate(time_labels[-5:]):
                        idx = len(time_labels) - 5 + i
                        if idx < len(candles):
                            candle = candles[idx]
                            print(f"  {label}: Open=${candle['open']:.2f}, Close=${candle['close']:.2f}")
                
                # Check debug info if available
                if 'debug_info' in data:
                    print(f"\nDebug info:")
                    for key, value in data['debug_info'].items():
                        print(f"  {key}: {value}")
            else:
                print(f"Error: {data.get('error', 'Unknown error')}")
        else:
            print(f"Error: HTTP {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Is it running on port 8082?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    print("=" * 80)
    return True

if __name__ == '__main__':
    test_docn_vwap_chart()
