#!/usr/bin/env python3
"""
Test Prixe.io API limits for 1-minute and 5-minute interval data
Tests different date ranges to determine actual API limitations
"""

import requests
import json
from datetime import datetime, timedelta, timezone
from config import PRIXE_API_KEY, PRIXE_BASE_URL

def test_prixe_api_limit(ticker: str, days_ago: int, interval: str):
    """Test Prixe.io API with a specific date range and interval"""
    
    # Calculate test date
    now = datetime.now(timezone.utc)
    test_date = now - timedelta(days=days_ago)
    date_str = test_date.strftime('%Y-%m-%d')
    
    # Map interval
    interval_map = {
        '1min': '1m',
        '5min': '5m',
    }
    prixe_interval = interval_map.get(interval, interval)
    
    url = f"{PRIXE_BASE_URL}/api/price"
    headers = {
        "Authorization": f"Bearer {PRIXE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        'ticker': ticker,
        'start_date': date_str,
        'end_date': date_str,
        'interval': prixe_interval
    }
    
    print(f"\n{'='*80}")
    print(f"Testing: {ticker} | {interval} interval | {days_ago} days ago ({date_str})")
    print(f"{'='*80}")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                price_data = data.get('data', {})
                timestamps = price_data.get('timestamp', [])
                closes = price_data.get('close', [])
                
                print(f"✅ SUCCESS")
                print(f"   Data points returned: {len(timestamps)}")
                if timestamps:
                    first_ts = datetime.fromtimestamp(timestamps[0], tz=timezone.utc)
                    last_ts = datetime.fromtimestamp(timestamps[-1], tz=timezone.utc)
                    print(f"   Time range: {first_ts.strftime('%Y-%m-%d %H:%M:%S UTC')} to {last_ts.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    if closes:
                        print(f"   First price: ${closes[0]:.2f}, Last price: ${closes[-1]:.2f}")
                return True
            else:
                print(f"❌ API returned success=false")
                print(f"   Response: {json.dumps(data, indent=2)}")
                return False
        elif response.status_code == 400:
            try:
                error_data = response.json()
                print(f"❌ 400 BAD REQUEST")
                print(f"   Error: {json.dumps(error_data, indent=2)}")
                # Check if it mentions date/interval limits
                error_str = str(error_data).lower()
                if '30' in error_str or 'days' in error_str:
                    print(f"   ⚠️  Likely date range limit issue")
                if 'interval' in error_str or '1m' in error_str or '1min' in error_str:
                    print(f"   ⚠️  Likely interval limit issue")
            except:
                print(f"❌ 400 BAD REQUEST (could not parse error)")
                print(f"   Response: {response.text[:500]}")
            return False
        elif response.status_code == 404:
            print(f"❌ 404 NOT FOUND")
            print(f"   Ticker or endpoint not found")
            return False
        else:
            print(f"❌ Status Code: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Response: {json.dumps(error_data, indent=2)}")
            except:
                print(f"   Response: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"❌ EXCEPTION: {type(e).__name__}: {e}")
        return False

def main():
    """Run comprehensive tests"""
    
    ticker = 'AAPL'  # Use a common, liquid stock
    test_ranges = [25, 30, 31, 35, 60, 61, 90]  # Test various date ranges
    intervals = ['1min', '5min']
    
    print(f"\n{'#'*80}")
    print(f"# Prixe.io API Limit Test")
    print(f"# Ticker: {ticker}")
    print(f"# Testing intervals: {', '.join(intervals)}")
    print(f"# Testing date ranges: {', '.join(map(str, test_ranges))} days ago")
    print(f"{'#'*80}")
    
    results = {}
    
    for interval in intervals:
        print(f"\n\n{'='*80}")
        print(f"INTERVAL: {interval}")
        print(f"{'='*80}")
        results[interval] = {}
        
        for days_ago in test_ranges:
            success = test_prixe_api_limit(ticker, days_ago, interval)
            results[interval][days_ago] = success
    
    # Summary
    print(f"\n\n{'#'*80}")
    print(f"# SUMMARY")
    print(f"{'#'*80}")
    
    for interval in intervals:
        print(f"\n{interval.upper()} INTERVAL:")
        print(f"  Days Ago | Status")
        print(f"  {'-'*40}")
        
        last_success = None
        limit_found = False
        
        for days_ago in sorted(test_ranges):
            success = results[interval][days_ago]
            status = "✅ WORKS" if success else "❌ FAILS"
            print(f"  {days_ago:8d} | {status}")
            
            # Detect the limit (first failure after a success)
            if last_success is True and not success and not limit_found:
                print(f"  {' '*10} ⚠️  LIMIT DETECTED: {interval} data fails after {days_ago-1} days")
                limit_found = True
            
            last_success = success
        
        if not limit_found:
            if all(results[interval].values()):
                print(f"  {' '*10} ✅ All tests passed - no limit detected up to {max(test_ranges)} days")
            elif not any(results[interval].values()):
                print(f"  {' '*10} ❌ All tests failed - check API key or ticker")

if __name__ == '__main__':
    main()

