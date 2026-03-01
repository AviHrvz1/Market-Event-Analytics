#!/usr/bin/env python3
"""
Server unittest to test the actual API endpoint and show detailed debug output
This will help identify why the API returns different data than the internal logic
"""

import sys
import json
import requests
from datetime import datetime, timezone, timedelta

def test_vwap_chart_server():
    """Test the actual API endpoint and show detailed comparison with expected results"""
    
    print("=" * 80)
    print("VWAP CHART SERVER API TEST")
    print("=" * 80)
    print()
    
    base_url = "http://127.0.0.1:8082"
    ticker = "NET"
    bearish_date_str = "2025-11-13"
    
    # Check if server is running
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code != 200:
            print(f"❌ Server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to server. Is it running on port 8082?")
        return False
    
    print("✅ Server is running")
    print()
    
    # Calculate expected values
    from main import LayoffTracker
    tracker = LayoffTracker()
    bearish_date = datetime.strptime(bearish_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    market_close_utc = tracker._get_market_close_time(bearish_date, ticker)
    start_time_utc = market_close_utc - timedelta(hours=3)
    next_trading_day = tracker.get_next_trading_day(bearish_date, ticker)
    next_market_open_utc = tracker._get_market_open_time(next_trading_day, ticker)
    end_time_utc = next_market_open_utc + timedelta(hours=3)
    
    expected_first_timestamp = int(start_time_utc.timestamp())
    expected_last_timestamp = int(end_time_utc.timestamp())
    
    print(f"Expected time range:")
    print(f"  Start: {start_time_utc} (timestamp: {expected_first_timestamp})")
    print(f"  End: {end_time_utc} (timestamp: {expected_last_timestamp})")
    print(f"  Should span: {bearish_date_str} and {next_trading_day.date()}")
    print()
    
    # Test the API endpoint
    url = f"{base_url}/api/vwap-chart-data"
    params = {
        'ticker': ticker,
        'bearish_date': bearish_date_str
    }
    
    print(f"Testing API endpoint: {url}")
    print(f"Parameters: {params}")
    print()
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ ERROR: API returned status {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
        
        # Parse JSON response
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            print(f"❌ ERROR: Invalid JSON response: {e}")
            print(f"Response: {response.text[:500]}")
            return False
        
        print("✅ Received valid JSON response")
        print()
        
        # Check response structure
        if not data.get('success'):
            error_msg = data.get('error', 'Unknown error')
            print(f"❌ ERROR: API returned success=False: {error_msg}")
            return False
        
        candles = data.get('candles', [])
        if not candles:
            print("❌ ERROR: No candles in response")
            return False
        
        print(f"Response summary:")
        print(f"  Candles: {len(candles)}")
        print(f"  VWAP: ${data.get('vwap', 0):.2f}")
        print()
        
        # Analyze candles
        first_candle = candles[0]
        last_candle = candles[-1]
        first_ts = first_candle['timestamp']
        last_ts = last_candle['timestamp']
        
        first_dt = datetime.fromtimestamp(first_ts, tz=timezone.utc)
        last_dt = datetime.fromtimestamp(last_ts, tz=timezone.utc)
        
        print(f"Actual candles:")
        print(f"  First: {first_dt} (timestamp: {first_ts})")
        print(f"  Last: {last_dt} (timestamp: {last_ts})")
        print()
        
        # Check dates
        dates = set()
        for c in candles:
            dt = datetime.fromtimestamp(c['timestamp'], tz=timezone.utc)
            dates.add(dt.date())
        
        print(f"Dates in candles: {sorted(dates)}")
        print()
        
        # Compare with expected
        print("=" * 80)
        print("COMPARISON WITH EXPECTED")
        print("=" * 80)
        print()
        
        issues = []
        
        if first_ts != expected_first_timestamp:
            diff = first_ts - expected_first_timestamp
            hours_diff = diff / 3600
            issues.append(f"❌ First timestamp mismatch: got {first_ts} ({first_dt}), expected {expected_first_timestamp} ({start_time_utc}) - difference: {hours_diff:.1f} hours")
        else:
            print(f"✅ First timestamp matches: {first_ts}")
        
        if last_ts != expected_last_timestamp:
            diff = last_ts - expected_last_timestamp
            hours_diff = diff / 3600
            issues.append(f"❌ Last timestamp mismatch: got {last_ts} ({last_dt}), expected {expected_last_timestamp} ({end_time_utc}) - difference: {hours_diff:.1f} hours")
        else:
            print(f"✅ Last timestamp matches: {last_ts}")
        
        expected_dates = {bearish_date.date(), next_trading_day.date()}
        if dates != expected_dates:
            issues.append(f"❌ Dates mismatch: got {sorted(dates)}, expected {sorted(expected_dates)}")
        else:
            print(f"✅ Dates match: {sorted(dates)}")
        
        if len(candles) < 40:  # Should be around 58 candles (6 hours * 4 candles per hour + some)
            issues.append(f"⚠️  WARNING: Only {len(candles)} candles, expected ~58 (6 hours of data)")
        else:
            print(f"✅ Candle count reasonable: {len(candles)}")
        
        print()
        
        if issues:
            print("ISSUES FOUND:")
            for issue in issues:
                print(f"  {issue}")
            print()
            
            # Show sample candles
            print("Sample candles (first 5 and last 5):")
            for i, c in enumerate(candles[:5] + candles[-5:]):
                dt = datetime.fromtimestamp(c['timestamp'], tz=timezone.utc)
                idx = i+1 if i < 5 else len(candles)-4+i
                print(f"  {idx}. {dt} (date={dt.date()}, timestamp={c['timestamp']})")
            print()
            
            # Check if it looks like old logic (3 hours before/after market open)
            from main import LayoffTracker
            tracker = LayoffTracker()
            market_open_utc = tracker._get_market_open_time(bearish_date, ticker)
            old_start = int((market_open_utc - timedelta(hours=3)).timestamp())
            old_end = int((market_open_utc + timedelta(hours=3)).timestamp())
            
            if first_ts == old_start and last_ts == old_end:
                print("⚠️  DETECTED: API is using OLD logic (3 hours before/after market open)")
                print(f"   Old start: {old_start} ({datetime.fromtimestamp(old_start, tz=timezone.utc)})")
                print(f"   Old end: {old_end} ({datetime.fromtimestamp(old_end, tz=timezone.utc)})")
                print("   This suggests the server is running old code!")
            elif first_ts < expected_first_timestamp:
                print(f"⚠️  DETECTED: First candle starts too early")
                print(f"   Got: {first_ts} ({first_dt})")
                print(f"   Expected: {expected_first_timestamp} ({start_time_utc})")
                print(f"   Difference: {(expected_first_timestamp - first_ts) / 3600:.1f} hours too early")
            
            return False
        else:
            print("✅ SUCCESS: All checks passed!")
            return True
        
    except requests.exceptions.Timeout:
        print(f"❌ ERROR: Request timed out after 30 seconds")
        return False
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_vwap_chart_server()
    sys.exit(0 if success else 1)
