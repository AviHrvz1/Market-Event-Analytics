#!/usr/bin/env python3
"""
Test if Prixe.io returns data for Dec 9, 2025 for ABG ticker
This script checks if Prixe.io actually has data for that date
"""

import requests
import json
from datetime import datetime, timezone
from config import PRIXE_API_KEY, PRIXE_BASE_URL

def test_prixe_data_for_date(ticker: str, date_str: str):
    """Test if Prixe.io returns data for a specific date"""
    
    print(f"\n{'='*80}")
    print(f"Testing Prixe.io API for {ticker} on {date_str}")
    print(f"{'='*80}\n")
    
    # Test 1: Daily data (1d interval)
    print("Test 1: Daily data (1d interval)")
    print("-" * 80)
    url = f"{PRIXE_BASE_URL}/api/price"
    headers = {
        "Authorization": f"Bearer {PRIXE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        'ticker': ticker,
        'start_date': date_str,
        'end_date': date_str,
        'interval': '1d'
    }
    
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success', False)}")
            if data.get('success'):
                data_obj = data.get('data', {})
                timestamps = data_obj.get('timestamp', [])
                closes = data_obj.get('close', [])
                opens = data_obj.get('open', [])
                volumes = data_obj.get('volume', [])
                
                print(f"Timestamps returned: {len(timestamps)}")
                if timestamps:
                    for i, ts in enumerate(timestamps):
                        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                        print(f"  [{i}] {dt} - Close: {closes[i] if i < len(closes) else 'N/A'}, Open: {opens[i] if i < len(opens) else 'N/A'}, Volume: {volumes[i] if i < len(volumes) else 'N/A'}")
                else:
                    print("⚠️  No timestamps in response (empty data)")
            else:
                print(f"❌ API returned success=False")
                print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"❌ HTTP Error {response.status_code}")
            try:
                error_data = response.json()
                print(f"Response: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Response text: {response.text[:500]}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Intraday data (5min interval)
    print("\n\nTest 2: Intraday data (5min interval)")
    print("-" * 80)
    payload_intraday = {
        'ticker': ticker,
        'start_date': date_str,
        'end_date': date_str,
        'interval': '5m'
    }
    
    print(f"Payload: {json.dumps(payload_intraday, indent=2)}")
    
    try:
        response = requests.post(url, headers=headers, json=payload_intraday, timeout=10)
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success', False)}")
            if data.get('success'):
                data_obj = data.get('data', {})
                timestamps = data_obj.get('timestamp', [])
                closes = data_obj.get('close', [])
                volumes = data_obj.get('volume', [])
                
                print(f"Timestamps returned: {len(timestamps)}")
                if timestamps:
                    print(f"First timestamp: {datetime.fromtimestamp(timestamps[0], tz=timezone.utc)}")
                    print(f"Last timestamp: {datetime.fromtimestamp(timestamps[-1], tz=timezone.utc)}")
                    print(f"\nFirst 5 data points:")
                    for i in range(min(5, len(timestamps))):
                        dt = datetime.fromtimestamp(timestamps[i], tz=timezone.utc)
                        print(f"  [{i}] {dt} - Close: {closes[i] if i < len(closes) else 'N/A'}, Volume: {volumes[i] if i < len(volumes) else 'N/A'}")
                    if len(timestamps) > 5:
                        print(f"\n... and {len(timestamps) - 5} more data points")
                else:
                    print("⚠️  No timestamps in response (empty data)")
            else:
                print(f"❌ API returned success=False")
                print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"❌ HTTP Error {response.status_code}")
            try:
                error_data = response.json()
                print(f"Response: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Response text: {response.text[:500]}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Check current date and date comparison
    print("\n\nTest 3: Current date check")
    print("-" * 80)
    now = datetime.now(timezone.utc)
    print(f"Current UTC time: {now}")
    print(f"Current date: {now.date()}")
    
    test_date = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    print(f"Test date: {test_date}")
    print(f"Test date (date only): {test_date.date()}")
    print(f"Is test date in future? {test_date > now}")
    print(f"Days difference: {(test_date.date() - now.date()).days}")
    
    # Test 4: Check date range (Dec 8-10 to see if Dec 9 is in the range)
    print("\n\nTest 4: Date range check (Dec 8-10, 2025)")
    print("-" * 80)
    payload_range = {
        'ticker': ticker,
        'start_date': '2025-12-08',
        'end_date': '2025-12-10',
        'interval': '1d'
    }
    
    print(f"Payload: {json.dumps(payload_range, indent=2)}")
    
    try:
        response = requests.post(url, headers=headers, json=payload_range, timeout=10)
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success', False)}")
            if data.get('success'):
                data_obj = data.get('data', {})
                timestamps = data_obj.get('timestamp', [])
                closes = data_obj.get('close', [])
                
                print(f"Timestamps returned: {len(timestamps)}")
                if timestamps:
                    print("Dates in range:")
                    for i, ts in enumerate(timestamps):
                        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                        print(f"  {dt.date()} - Close: {closes[i] if i < len(closes) else 'N/A'}")
                        if dt.date() == datetime.strptime(date_str, '%Y-%m-%d').date():
                            print(f"    ✓ Found Dec 9, 2025 in range!")
                else:
                    print("⚠️  No timestamps in response (empty data)")
            else:
                print(f"❌ API returned success=False")
                print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"❌ HTTP Error {response.status_code}")
            try:
                error_data = response.json()
                print(f"Response: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Response text: {response.text[:500]}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # Test for ABG on Dec 9, 2025
    test_prixe_data_for_date('ABG', '2025-12-09')

