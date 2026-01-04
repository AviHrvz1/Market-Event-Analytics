#!/usr/bin/env python3
"""
Test NASDAQ API endpoints: dividends, splits, company calendar
"""

import requests
import json
from datetime import datetime, timedelta

def test_nasdaq_endpoints():
    """Test various NASDAQ API endpoints"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://www.nasdaq.com/'
    }
    
    test_ticker = 'AAPL'
    test_date = datetime.now().date()
    
    print("=" * 80)
    print("TESTING NASDAQ API ENDPOINTS")
    print("=" * 80)
    print()
    
    # Test 1: Dividends Calendar
    print("Test 1: Dividends Calendar")
    print("-" * 80)
    dividends_url = f"https://api.nasdaq.com/api/calendar/dividends?date={test_date.strftime('%Y-%m-%d')}"
    print(f"URL: {dividends_url}")
    
    try:
        response = requests.get(dividends_url, headers=headers, timeout=5, verify=False)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response structure: {json.dumps(data, indent=2)[:500]}")
            rows = data.get('data', {}).get('rows', [])
            print(f"✅ Dividends calendar works: Found {len(rows)} dividend events")
            if rows:
                print(f"Sample dividend event:")
                print(json.dumps(rows[0], indent=2)[:300])
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()
    
    # Test 2: Stock Splits Calendar
    print("Test 2: Stock Splits Calendar")
    print("-" * 80)
    splits_url = f"https://api.nasdaq.com/api/calendar/splits?date={test_date.strftime('%Y-%m-%d')}"
    print(f"URL: {splits_url}")
    
    try:
        response = requests.get(splits_url, headers=headers, timeout=5, verify=False)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            rows = data.get('data', {}).get('rows', [])
            print(f"✅ Splits calendar works: Found {len(rows)} split events")
            if rows:
                print(f"Sample split event:")
                print(json.dumps(rows[0], indent=2)[:300])
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()
    
    # Test 3: Company Calendar (per ticker - might reduce API calls!)
    print("Test 3: Company Calendar (per ticker)")
    print("-" * 80)
    company_url = f"https://api.nasdaq.com/api/company/{test_ticker}/calendar"
    print(f"URL: {company_url}")
    
    try:
        response = requests.get(company_url, headers=headers, timeout=5, verify=False)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response structure: {json.dumps(data, indent=2)[:800]}")
            # Check different possible response structures
            if 'data' in data:
                if isinstance(data['data'], dict):
                    earnings = data['data'].get('earnings', [])
                    dividends = data['data'].get('dividends', [])
                    splits = data['data'].get('splits', [])
                    print(f"✅ Company calendar works!")
                    print(f"   Earnings events: {len(earnings) if isinstance(earnings, list) else 'N/A'}")
                    print(f"   Dividends events: {len(dividends) if isinstance(dividends, list) else 'N/A'}")
                    print(f"   Splits events: {len(splits) if isinstance(splits, list) else 'N/A'}")
                elif isinstance(data['data'], list):
                    print(f"✅ Company calendar works: Found {len(data['data'])} events")
            else:
                print(f"✅ Company calendar works (different structure)")
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()
    
    # Test 4: Check if company calendar has date range or future events
    if response.status_code == 200:
        print("Test 4: Company Calendar Date Range")
        print("-" * 80)
        # Try with date parameters
        company_url_with_date = f"https://api.nasdaq.com/api/company/{test_ticker}/calendar?start_date={test_date.strftime('%Y-%m-%d')}&end_date={(test_date + timedelta(days=30)).strftime('%Y-%m-%d')}"
        print(f"URL: {company_url_with_date}")
        
        try:
            response2 = requests.get(company_url_with_date, headers=headers, timeout=5, verify=False)
            print(f"Status: {response2.status_code}")
            if response2.status_code == 200:
                print(f"✅ Company calendar with date range works!")
            else:
                print(f"❌ Date range not supported: {response2.status_code}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("If company calendar works, we can use 1 API call per ticker instead of 40+ calls!")

if __name__ == "__main__":
    test_nasdaq_endpoints()

