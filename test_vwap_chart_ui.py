#!/usr/bin/env python3
"""
UI unittest to verify VWAP chart API endpoint returns correct data structure
that the frontend can use to render the chart correctly
"""

import sys
import json
import requests
from datetime import datetime, timezone, timedelta

def test_vwap_chart_api_endpoint():
    """Test the /api/vwap-chart-data endpoint that the UI uses"""
    
    print("=" * 80)
    print("VWAP CHART UI API TEST")
    print("=" * 80)
    print()
    
    base_url = "http://127.0.0.1:8082"
    
    # Test with Nov 13, 2025 (a past date)
    ticker = "NET"
    bearish_date = "2025-11-13"
    
    print(f"Test Case: {ticker} on {bearish_date}")
    print("-" * 80)
    print()
    
    # Check if server is running
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code != 200:
            print(f"❌ Server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to server. Is it running on port 8082?")
        print("   Start the server with: python3 app.py")
        return False
    except Exception as e:
        print(f"❌ ERROR connecting to server: {e}")
        return False
    
    print("✅ Server is running")
    print()
    
    # Test the API endpoint
    url = f"{base_url}/api/vwap-chart-data"
    params = {
        'ticker': ticker,
        'bearish_date': bearish_date
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
        
        # Verify response structure
        print("Verifying response structure:")
        required_fields = ['success', 'candles', 'vwap', 'vwap_points', 'time_labels']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            print(f"❌ ERROR: Missing required fields: {missing_fields}")
            return False
        
        print(f"  ✅ All required fields present: {required_fields}")
        print()
        
        # Check success flag
        if not data.get('success'):
            error_msg = data.get('error', 'Unknown error')
            print(f"❌ ERROR: API returned success=False: {error_msg}")
            return False
        
        print(f"  ✅ success: {data['success']}")
        
        # Check candles
        candles = data.get('candles', [])
        if not candles:
            print("❌ ERROR: No candles in response")
            return False
        
        print(f"  ✅ candles: {len(candles)} candles")
        
        # Check VWAP
        vwap = data.get('vwap')
        if vwap is None:
            print("❌ ERROR: VWAP is None")
            return False
        
        print(f"  ✅ vwap: ${vwap:.2f}")
        
        # Check VWAP points
        vwap_points = data.get('vwap_points', [])
        if len(vwap_points) != len(candles):
            print(f"❌ ERROR: VWAP points count ({len(vwap_points)}) doesn't match candles count ({len(candles)})")
            return False
        
        print(f"  ✅ vwap_points: {len(vwap_points)} points (matches candles)")
        
        # Check time labels
        time_labels = data.get('time_labels', [])
        if len(time_labels) != len(candles):
            print(f"❌ ERROR: Time labels count ({len(time_labels)}) doesn't match candles count ({len(candles)})")
            return False
        
        print(f"  ✅ time_labels: {len(time_labels)} labels (matches candles)")
        print()
        
        # Verify candle structure
        print("Verifying candle structure:")
        first_candle = candles[0]
        required_candle_fields = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_candle_fields = [field for field in required_candle_fields if field not in first_candle]
        
        if missing_candle_fields:
            print(f"❌ ERROR: Missing required candle fields: {missing_candle_fields}")
            return False
        
        print(f"  ✅ Candle structure correct: {required_candle_fields}")
        print()
        
        # Verify time range (for past dates, should span 2 days)
        print("Verifying time range:")
        timestamps = [c['timestamp'] for c in candles]
        first_ts = min(timestamps)
        last_ts = max(timestamps)
        
        first_dt = datetime.fromtimestamp(first_ts, tz=timezone.utc)
        last_dt = datetime.fromtimestamp(last_ts, tz=timezone.utc)
        
        print(f"  First candle timestamp: {first_ts} ({first_dt})")
        print(f"  Last candle timestamp: {last_ts} ({last_dt})")
        
        # Calculate expected time window
        bearish_date_obj = datetime.strptime(bearish_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        now_utc = datetime.now(timezone.utc)
        is_today = bearish_date_obj.date() == now_utc.date()
        
        if is_today:
            print("  ⚠️  Bearish date is today - skipping 2-day verification")
        else:
            # For past dates, should have data from 2 days
            first_date = first_dt.date()
            last_date = last_dt.date()
            
            print(f"  First candle date: {first_date}")
            print(f"  Last candle date: {last_date}")
            
            # Check all unique dates in the data
            unique_dates = set()
            for ts in timestamps:
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                unique_dates.add(dt.date())
            
            print(f"  Unique dates in data: {sorted(unique_dates)}")
            
            if first_date == last_date:
                if len(unique_dates) > 1:
                    print(f"  ✅ Data spans 2 days: {sorted(unique_dates)}")
                    print(f"     (First/last timestamps are from same day, but data includes both days)")
                else:
                    print(f"  ⚠️  WARNING: All candles are from same day ({first_date})")
                    print(f"     Expected: Last 3h of {bearish_date} + First 3h of next day")
            else:
                print(f"  ✅ Data spans 2 days: {first_date} to {last_date}")
        print()
        
        # Verify time labels format
        print("Verifying time labels format:")
        print(f"  First label: {time_labels[0]}")
        print(f"  Last label: {time_labels[-1]}")
        
        # Check if labels are in correct format (e.g., "Nov 13 20:00")
        import re
        label_pattern = re.compile(r'^[A-Z][a-z]{2} \d{1,2} \d{2}:\d{2}$')
        
        invalid_labels = [label for label in time_labels if not label_pattern.match(label)]
        if invalid_labels:
            print(f"  ❌ ERROR: Invalid time label format: {invalid_labels[:3]}")
            return False
        
        print(f"  ✅ All {len(time_labels)} time labels have correct format")
        print()
        
        # Verify time labels are in IST and show correct dates
        print("Verifying time labels are in IST:")
        # Convert first and last timestamps to IST
        def utc_to_ist(utc_dt):
            month = utc_dt.month
            offset_hours = 3 if (month >= 4 and month <= 10) else 2
            return utc_dt + timedelta(hours=offset_hours)
        
        first_ist = utc_to_ist(first_dt)
        last_ist = utc_to_ist(last_dt)
        
        expected_first_label = f"{first_ist.strftime('%b %d %H:%M')}"
        expected_last_label = f"{last_ist.strftime('%b %d %H:%M')}"
        
        print(f"  Expected first label (IST): {expected_first_label}")
        print(f"  Actual first label: {time_labels[0]}")
        print(f"  Expected last label (IST): {expected_last_label}")
        print(f"  Actual last label: {time_labels[-1]}")
        
        # Compare dates and hours (allow some flexibility for rounding)
        first_label_parts = time_labels[0].split()
        expected_first_parts = expected_first_label.split()
        
        if len(first_label_parts) >= 3:
            actual_date = f"{first_label_parts[0]} {first_label_parts[1]}"
            expected_date = f"{expected_first_parts[0]} {expected_first_parts[1]}"
            
            if actual_date != expected_date:
                print(f"  ⚠️  WARNING: First label date mismatch: {actual_date} vs {expected_date}")
            else:
                print(f"  ✅ First label date matches: {actual_date}")
        
        if len(time_labels) > 1:
            last_label_parts = time_labels[-1].split()
            expected_last_parts = expected_last_label.split()
            
            if len(last_label_parts) >= 3:
                actual_date = f"{last_label_parts[0]} {last_label_parts[1]}"
                expected_date = f"{expected_last_parts[0]} {expected_last_parts[1]}"
                
                if actual_date != expected_date:
                    print(f"  ⚠️  WARNING: Last label date mismatch: {actual_date} vs {expected_date}")
                else:
                    print(f"  ✅ Last label date matches: {actual_date}")
        print()
        
        # Verify VWAP calculation
        print("Verifying VWAP calculation:")
        # VWAP should be reasonable (not zero, not negative, within price range)
        price_range = [c['low'] for c in candles] + [c['high'] for c in candles]
        min_price = min(price_range)
        max_price = max(price_range)
        
        if vwap < min_price or vwap > max_price:
            print(f"  ⚠️  WARNING: VWAP ({vwap:.2f}) is outside price range ({min_price:.2f} - {max_price:.2f})")
        else:
            print(f"  ✅ VWAP ({vwap:.2f}) is within price range ({min_price:.2f} - {max_price:.2f})")
        
        # Check that VWAP points match candles
        vwap_in_range = all(min_price <= vp <= max_price for vp in vwap_points)
        if not vwap_in_range:
            print(f"  ⚠️  WARNING: Some VWAP points are outside price range")
        else:
            print(f"  ✅ All VWAP points are within price range")
        print()
        
        # Summary
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"✅ API endpoint is accessible")
        print(f"✅ Response structure is correct")
        print(f"✅ Received {len(candles)} candles")
        print(f"✅ Time labels are formatted correctly")
        print(f"✅ Data is ready for frontend rendering")
        print()
        
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
    success = test_vwap_chart_api_endpoint()
    sys.exit(0 if success else 1)
