#!/usr/bin/env python3
"""
Test NASDAQ earnings calendar API to verify it works and check response structure
"""

import sys
import requests
import json
from datetime import datetime, timedelta

def test_nasdaq_api(ticker='AAPL'):
    """Test NASDAQ API endpoints"""
    print("=" * 80)
    print("NASDAQ EARNINGS CALENDAR API TEST")
    print("=" * 80)
    print()
    
    # Test different NASDAQ endpoints
    endpoints = [
        f"https://api.nasdaq.com/api/company/{ticker}/calendar",
        f"https://api.nasdaq.com/api/calendar/earnings?date=2025-12-30",
        f"https://www.nasdaq.com/api/v1/calendar/earnings?symbol={ticker}",
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://www.nasdaq.com/'
    }
    
    for i, url in enumerate(endpoints, 1):
        print(f"Test {i}: {url}")
        print("-" * 80)
        try:
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   ✅ Success! Response type: {type(data)}")
                    print(f"   Response keys/structure:")
                    if isinstance(data, dict):
                        print(f"      Top-level keys: {list(data.keys())[:10]}")
                        # Try to find earnings data
                        if 'data' in data:
                            print(f"      'data' type: {type(data['data'])}")
                            if isinstance(data['data'], dict):
                                print(f"      'data' keys: {list(data['data'].keys())[:10]}")
                            elif isinstance(data['data'], list):
                                print(f"      'data' length: {len(data['data'])}")
                                if len(data['data']) > 0:
                                    print(f"      Sample entry: {data['data'][0]}")
                        elif 'rows' in data:
                            print(f"      'rows' length: {len(data['rows'])}")
                            if len(data['rows']) > 0:
                                print(f"      Sample entry: {data['rows'][0]}")
                    elif isinstance(data, list):
                        print(f"      List length: {len(data)}")
                        if len(data) > 0:
                            print(f"      Sample entry: {data[0]}")
                    
                    # Show first 500 chars of response for debugging
                    response_str = json.dumps(data, indent=2)[:500]
                    print(f"   Response preview:\n{response_str}...")
                    print()
                    return True, data, url
                except json.JSONDecodeError:
                    print(f"   ⚠️  Response is not JSON")
                    print(f"   Response text (first 200 chars): {response.text[:200]}")
            else:
                print(f"   ❌ Failed with status {response.status_code}")
                print(f"   Response: {response.text[:200]}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
        print()
    
    return False, None, None

if __name__ == "__main__":
    success, data, url = test_nasdaq_api('AAPL')
    if success:
        print("=" * 80)
        print("✅ NASDAQ API is accessible!")
        print(f"   Working endpoint: {url}")
        print("=" * 80)
    else:
        print("=" * 80)
        print("❌ Could not access NASDAQ API")
        print("=" * 80)
    sys.exit(0 if success else 1)

