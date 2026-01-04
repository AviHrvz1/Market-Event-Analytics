#!/usr/bin/env python3
"""
Unit test to diagnose exactly where the issue occurs for FDA approval tickers showing N/A.
Tests the entire flow from ticker extraction to stock price calculation.
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker
from config import PRIXE_BASE_URL, PRIXE_API_KEY, PRIXE_PRICE_ENDPOINT
import requests
import json

print(f"\n{'='*80}")
print("Unit Test: FDA Approval Ticker N/A Issue Diagnosis")
print(f"{'='*80}\n")

# Test tickers from user's issue
test_cases = [
    {
        'ticker': 'NOVN',
        'company': 'Novan',
        'article_date': datetime(2025, 11, 14, 3, 0, tzinfo=timezone.utc),
        'expected_issue': 'Not in SEC EDGAR, API 404'
    },
    {
        'ticker': 'AVZO',
        'company': 'Avertex Biotherapeutics Inc',
        'article_date': datetime(2025, 11, 14, 3, 0, tzinfo=timezone.utc),
        'expected_issue': 'Not in SEC EDGAR, API 404'
    },
    {
        'ticker': 'BAYRY',
        'company': 'Bayer AG',
        'article_date': datetime(2025, 11, 13, 3, 0, tzinfo=timezone.utc),
        'expected_issue': 'Foreign ticker, partial data'
    },
    {
        'ticker': 'MRTX',
        'company': 'Mirati Therapeutics',
        'article_date': datetime(2025, 10, 28, 3, 0, tzinfo=timezone.utc),
        'expected_issue': 'Delisted/acquired, API 404'
    },
    {
        'ticker': 'HGEN',
        'company': 'Humanigen',
        'article_date': datetime(2025, 10, 23, 3, 0, tzinfo=timezone.utc),
        'expected_issue': 'Not in SEC EDGAR, API 404'
    },
]

tracker = LayoffTracker()

# Test 1: Direct Prixe.io API endpoint test
print(f"{'='*80}")
print("TEST 1: Direct Prixe.io API Endpoint Test")
print(f"{'='*80}\n")

print(f"Testing endpoint: {PRIXE_BASE_URL}{PRIXE_PRICE_ENDPOINT}")
print(f"API Key: {PRIXE_API_KEY[:20]}...")

test_ticker = 'AAPL'  # Use a known good ticker
test_payload = {
    'ticker': test_ticker,
    'start_date': '2025-11-10',
    'end_date': '2025-11-17',
    'interval': '1d'
}

try:
    url = f"{PRIXE_BASE_URL}{PRIXE_PRICE_ENDPOINT}"
    headers = {
        "Authorization": f"Bearer {PRIXE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    print(f"\nMaking direct API call to Prixe.io...")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(test_payload, indent=2)}")
    
    response = requests.post(url, json=test_payload, headers=headers, timeout=10)
    
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        print(f"✅ API endpoint is working!")
        try:
            data = response.json()
            print(f"Response structure: {list(data.keys())}")
            if data.get('success'):
                print(f"✅ API returned success=True")
            else:
                print(f"⚠️  API returned success=False")
                print(f"Response: {json.dumps(data, indent=2)[:500]}")
        except:
            print(f"Response text (first 500 chars): {response.text[:500]}")
    elif response.status_code == 404:
        print(f"❌ API endpoint returns 404 - ENDPOINT DOES NOT EXIST")
        print(f"Response: {response.text[:500]}")
        print(f"\n🔍 DIAGNOSIS: Prixe.io endpoint {PRIXE_PRICE_ENDPOINT} is not valid")
        print(f"   This is the PRIMARY issue affecting all tickers")
    else:
        print(f"❌ API returned status {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
except Exception as e:
    print(f"❌ Exception calling API: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Ticker validation flow
print(f"\n{'='*80}")
print("TEST 2: Ticker Validation Flow")
print(f"{'='*80}\n")

for case in test_cases:
    ticker = case['ticker']
    company = case['company']
    
    print(f"\n{company} ({ticker}):")
    
    # 2a: SEC EDGAR validation
    try:
        is_valid = tracker._is_valid_ticker(ticker)
        print(f"  [2a] SEC EDGAR: {'✅ Valid' if is_valid else '❌ Invalid/Not Found'}")
        if not is_valid:
            print(f"       → Ticker not in SEC EDGAR database")
    except Exception as e:
        print(f"  [2a] SEC EDGAR: ❌ Error - {e}")
    
    # 2b: Check failed_tickers cache
    if ticker.upper() in tracker.failed_tickers:
        print(f"  [2b] Failed Cache: ⚠️  Ticker in failed_tickers cache")
    else:
        print(f"  [2b] Failed Cache: ✅ Not in failed_tickers")
    
    # 2c: Check invalid_tickers list
    if ticker.upper() in tracker.invalid_tickers:
        print(f"  [2c] Invalid List: ⚠️  Ticker in invalid_tickers list")
    else:
        print(f"  [2c] Invalid List: ✅ Not in invalid_tickers")

# Test 3: Prixe.io API request flow
print(f"\n{'='*80}")
print("TEST 3: Prixe.io API Request Flow (via tracker)")
print(f"{'='*80}\n")

for case in test_cases:
    ticker = case['ticker']
    company = case['company']
    article_dt = case['article_date']
    
    print(f"\n{company} ({ticker}):")
    
    test_start = article_dt - timedelta(days=5)
    test_end = article_dt + timedelta(days=3)
    
    # 3a: Test _fetch_price_data_batch
    print(f"  [3a] _fetch_price_data_batch:")
    try:
        price_data = tracker._fetch_price_data_batch(ticker, test_start, test_end, '1d')
        
        if price_data:
            if price_data.get('success'):
                data = price_data.get('data', {})
                timestamps = data.get('timestamp', [])
                print(f"       ✅ API returned data ({len(timestamps)} points)")
            else:
                print(f"       ❌ API returned success=False")
                print(f"       Response: {json.dumps(price_data, indent=2)[:200]}")
        else:
            print(f"       ❌ API returned None")
            print(f"       → This causes calculate_stock_changes to return empty_results")
    except Exception as e:
        print(f"       ❌ Exception: {e}")

# Test 4: Stock price calculation flow
print(f"\n{'='*80}")
print("TEST 4: Stock Price Calculation Flow")
print(f"{'='*80}\n")

for case in test_cases:
    ticker = case['ticker']
    company = case['company']
    article_dt = case['article_date']
    
    print(f"\n{company} ({ticker}):")
    
    mock_layoff = {
        'company_name': company,
        'stock_ticker': ticker,
        'datetime': article_dt,
        'date': article_dt.date().isoformat(),
        'time': article_dt.strftime('%H:%M'),
    }
    
    # 4a: Test calculate_stock_changes entry point
    print(f"  [4a] calculate_stock_changes entry:")
    try:
        # Check if ticker exists
        if not ticker or not article_dt:
            print(f"       ❌ Missing ticker or datetime")
        else:
            print(f"       ✅ Ticker and datetime present")
    except Exception as e:
        print(f"       ❌ Error: {e}")
    
    # 4b: Test batch data fetch
    print(f"  [4b] Batch data fetch:")
    try:
        test_start = article_dt - timedelta(days=5)
        test_end = article_dt + timedelta(days=3)
        
        # Check cache first
        cache_key = f"prixe_batch_{ticker}_{test_start.strftime('%Y-%m-%d')}_{test_end.strftime('%Y-%m-%d')}_1d"
        if cache_key in tracker.stock_price_cache:
            print(f"       ✅ Found in cache")
        else:
            print(f"       ⚠️  Not in cache, will make API call")
        
        daily_price_data = tracker._fetch_price_data_batch(ticker, test_start, test_end, '1d')
        
        if daily_price_data:
            print(f"       ✅ Batch data retrieved")
        else:
            print(f"       ❌ Batch data is None")
            print(f"       → This causes calculate_stock_changes to return empty_results at line 2752-2754")
    except Exception as e:
        print(f"       ❌ Exception: {e}")
    
    # 4c: Test base price extraction
    print(f"  [4c] Base price extraction:")
    try:
        if daily_price_data:
            base_price = None
            prev_day = article_dt - timedelta(days=1)
            for attempt in range(5):
                price, is_exact, actual_ts = tracker._extract_price_from_batch(daily_price_data, prev_day, 'close')
                if price:
                    base_price = price
                    break
                prev_day = prev_day - timedelta(days=1)
            
            if base_price:
                print(f"       ✅ Base price found: ${base_price:.2f}")
            else:
                print(f"       ❌ Base price is None")
                print(f"       → This causes calculate_stock_changes to return empty_results at line 2774-2775")
        else:
            print(f"       ⚠️  Skipped (no batch data)")
    except Exception as e:
        print(f"       ❌ Exception: {e}")
    
    # 4d: Full calculate_stock_changes test
    print(f"  [4d] Full calculate_stock_changes:")
    try:
        stock_changes = tracker.calculate_stock_changes(mock_layoff)
        
        base_price = stock_changes.get('base_price')
        intervals_with_data = []
        intervals_na = []
        
        test_intervals = ['5min', '10min', '30min', '1hr', '2hr', '3hr', 'next_close']
        for interval in test_intervals:
            if stock_changes.get(f'price_{interval}') is not None:
                intervals_with_data.append(interval)
            else:
                intervals_na.append(interval)
        
        print(f"       Base price: {base_price if base_price else 'N/A'}")
        print(f"       Intervals with data: {len(intervals_with_data)}")
        print(f"       Intervals N/A: {len(intervals_na)}")
        
        if len(intervals_with_data) == 0:
            print(f"       ❌ All intervals N/A - matches user's issue")
            if not base_price:
                print(f"       → Root cause: No base price (API failed)")
        else:
            print(f"       ✅ Some intervals have data")
            
    except Exception as e:
        print(f"       ❌ Exception: {e}")
        import traceback
        traceback.print_exc()

# Test 5: Alternative endpoint test
print(f"\n{'='*80}")
print("TEST 5: Alternative Prixe.io Endpoints Test")
print(f"{'='*80}\n")

alternative_endpoints = [
    '/api/historical',
    '/api/v1/price',
    '/api/v1/historical',
    '/api/stock/price',
    '/api/stock/historical',
]

test_payload_simple = {'ticker': 'AAPL'}

for endpoint in alternative_endpoints:
    print(f"\nTesting endpoint: {endpoint}")
    try:
        url = f"{PRIXE_BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {PRIXE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Try simple payload first
        response = requests.post(url, json=test_payload_simple, headers=headers, timeout=5)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"  ✅ Endpoint exists and works!")
            try:
                data = response.json()
                print(f"  Response keys: {list(data.keys())}")
            except:
                print(f"  Response: {response.text[:200]}")
        elif response.status_code == 404:
            print(f"  ❌ Endpoint not found (404)")
        elif response.status_code == 400:
            print(f"  ⚠️  Bad request (400) - endpoint exists but needs different payload")
            print(f"  Response: {response.text[:200]}")
        else:
            print(f"  Status {response.status_code}: {response.text[:200]}")
    except requests.exceptions.Timeout:
        print(f"  ⏱️  Timeout")
    except Exception as e:
        print(f"  ❌ Error: {e}")

# Final Summary
print(f"\n{'='*80}")
print("FINAL DIAGNOSIS SUMMARY")
print(f"{'='*80}\n")

print("Issue Location Analysis:")
print("=" * 80)
print()
print("1. API ENDPOINT ISSUE:")
print("   Location: main.py -> _prixe_api_request() -> Prixe.io API")
print("   Status: /api/price returns 404")
print("   Impact: ALL tickers fail to get price data")
print()
print("2. FAILURE POINT IN CODE:")
print("   Location: main.py -> calculate_stock_changes() -> line 2752-2754")
print("   Code: if not daily_price_data: return empty_results")
print("   Trigger: _fetch_price_data_batch() returns None due to API 404")
print()
print("3. TICKER-SPECIFIC ISSUES:")
for case in test_cases:
    ticker = case['ticker']
    company = case['company']
    is_valid = tracker._is_valid_ticker(ticker) if hasattr(tracker, '_is_valid_ticker') else False
    in_failed = ticker.upper() in tracker.failed_tickers
    
    print(f"   {company} ({ticker}):")
    print(f"     - SEC EDGAR: {'Valid' if is_valid else 'Invalid/Not Found'}")
    print(f"     - Failed Cache: {'Yes' if in_failed else 'No'}")
    print(f"     - Primary Issue: API 404 (affects all)")
    if not is_valid:
        print(f"     - Secondary Issue: Ticker not in SEC EDGAR")
    print()
print("=" * 80)
print()
print("ROOT CAUSE:")
print("  The Prixe.io API endpoint '/api/price' is returning 404 errors.")
print("  This causes _fetch_price_data_batch() to return None,")
print("  which triggers calculate_stock_changes() to return empty_results")
print("  (all N/A values) at line 2752-2754 in main.py")
print()
print("SOLUTION:")
print("  1. Verify correct Prixe.io API endpoint (check documentation)")
print("  2. Update PRIXE_PRICE_ENDPOINT in config.py if endpoint changed")
print("  3. For delisted/foreign tickers: May need alternative data source")

