#!/usr/bin/env python3
"""
Test if NASDAQ API supports date range parameters
"""

import requests
import json
from datetime import datetime, timedelta

def test_nasdaq_date_range():
    """Test if NASDAQ API supports start_date and end_date parameters"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://www.nasdaq.com/'
    }
    
    # Test date range: next 7 days
    start_date = datetime.now().date()
    end_date = start_date + timedelta(days=7)
    
    print("=" * 80)
    print("TESTING NASDAQ API DATE RANGE SUPPORT")
    print("=" * 80)
    print()
    
    # Test 1: Single date (current implementation - should work)
    print("Test 1: Single date query (baseline - should work)")
    single_date_url = f"https://api.nasdaq.com/api/calendar/earnings?date={start_date.strftime('%Y-%m-%d')}"
    print(f"URL: {single_date_url}")
    
    try:
        response = requests.get(single_date_url, headers=headers, timeout=5, verify=False)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            rows = data.get('data', {}).get('rows', [])
            print(f"✅ Single date works: Found {len(rows)} earnings events")
        else:
            print(f"❌ Single date failed: {response.status_code}")
            print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()
    
    # Test 2: Date range with start_date and end_date
    print("Test 2: Date range query (start_date + end_date)")
    range_url = f"https://api.nasdaq.com/api/calendar/earnings?start_date={start_date.strftime('%Y-%m-%d')}&end_date={end_date.strftime('%Y-%m-%d')}"
    print(f"URL: {range_url}")
    
    try:
        response = requests.get(range_url, headers=headers, timeout=5, verify=False)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            rows = data.get('data', {}).get('rows', [])
            print(f"✅ Date range works: Found {len(rows)} earnings events")
            print(f"   This would replace ~7 API calls with 1 call!")
        else:
            print(f"❌ Date range failed: {response.status_code}")
            print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()
    
    # Test 3: Alternative parameter names
    print("Test 3: Alternative parameter names (from/to)")
    alt_url = f"https://api.nasdaq.com/api/calendar/earnings?from={start_date.strftime('%Y-%m-%d')}&to={end_date.strftime('%Y-%m-%d')}"
    print(f"URL: {alt_url}")
    
    try:
        response = requests.get(alt_url, headers=headers, timeout=5, verify=False)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            rows = data.get('data', {}).get('rows', [])
            print(f"✅ Alternative params work: Found {len(rows)} earnings events")
        else:
            print(f"❌ Alternative params failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()
    
    # Test 4: Check response structure if range works
    print("Test 4: If range works, check if we can filter by ticker")
    if response.status_code == 200:
        try:
            data = response.json()
            rows = data.get('data', {}).get('rows', [])
            if rows:
                print(f"Sample event structure:")
                print(json.dumps(rows[0], indent=2)[:300])
                print()
                # Check if ticker is in the response
                if isinstance(rows[0], dict):
                    ticker_fields = [k for k in rows[0].keys() if 'ticker' in k.lower() or 'symbol' in k.lower()]
                    print(f"Ticker fields found: {ticker_fields}")
        except Exception as e:
            print(f"Error parsing response: {e}")
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("If Test 2 or Test 3 returns 200, we can use date ranges!")
    print("This would reduce API calls from ~35 per stock to 1 per stock!")

if __name__ == "__main__":
    test_nasdaq_date_range()

