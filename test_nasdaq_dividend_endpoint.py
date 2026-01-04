#!/usr/bin/env python3
"""
Test NASDAQ dividend calendar endpoint to check if it exists and estimate latency
"""

import requests
import time
from datetime import datetime, timedelta

def test_nasdaq_dividend_endpoint():
    """Test if NASDAQ has a dividend calendar endpoint"""
    print("=" * 80)
    print("NASDAQ DIVIDEND ENDPOINT TEST")
    print("=" * 80)
    print()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://www.nasdaq.com/'
    }
    
    # Test different possible endpoints
    endpoints_to_test = [
        'https://api.nasdaq.com/api/calendar/dividends',
        'https://api.nasdaq.com/api/calendar/dividends?date=2024-12-11',
        'https://api.nasdaq.com/api/calendar/dividend',
        'https://api.nasdaq.com/api/calendar/dividend?date=2024-12-11',
        'https://api.nasdaq.com/api/dividends',
        'https://api.nasdaq.com/api/dividends?date=2024-12-11',
    ]
    
    print("Testing NASDAQ dividend endpoints...")
    print()
    
    for endpoint in endpoints_to_test:
        print(f"Testing: {endpoint}")
        try:
            start_time = time.time()
            response = requests.get(endpoint, headers=headers, timeout=5, verify=False)
            elapsed = time.time() - start_time
            
            print(f"  Status: {response.status_code}")
            print(f"  Latency: {elapsed:.3f}s")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"  ✅ SUCCESS - Endpoint exists!")
                    print(f"  Response structure: {list(data.keys())[:5] if isinstance(data, dict) else 'List/Array'}")
                    
                    # Check if it has dividend data
                    if isinstance(data, dict):
                        if 'data' in data:
                            data_section = data['data']
                            if isinstance(data_section, dict) and 'rows' in data_section:
                                rows = data_section['rows']
                                print(f"  Found {len(rows)} dividend entries")
                                if rows:
                                    print(f"  Sample entry: {list(rows[0].keys()) if isinstance(rows[0], dict) else rows[0]}")
                    print()
                    return endpoint, elapsed
                except:
                    print(f"  ⚠️  Response is not JSON")
            elif response.status_code == 404:
                print(f"  ❌ Endpoint not found (404)")
            else:
                print(f"  ⚠️  Status {response.status_code}")
            print()
        except Exception as e:
            print(f"  ❌ Error: {str(e)[:100]}")
            print()
    
    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print()
    print("If no dividend endpoint found, we need to:")
    print("1. Check if dividends are in the earnings calendar response")
    print("2. Use alternative sources (Yahoo Finance, Alpha Vantage, etc.)")
    print("3. Parse dividend data from company websites or press releases")
    
    return None, None

if __name__ == "__main__":
    endpoint, latency = test_nasdaq_dividend_endpoint()
    if endpoint:
        print(f"\n✅ Found working endpoint: {endpoint}")
        print(f"   Average latency: {latency:.3f}s per request")
        print(f"\nEstimated total latency for date range:")
        print(f"   - Dec 3 to Dec 30 = 28 days")
        print(f"   - 28 API calls × {latency:.3f}s = {28 * latency:.2f}s total")
    else:
        print("\n❌ No dividend endpoint found")

