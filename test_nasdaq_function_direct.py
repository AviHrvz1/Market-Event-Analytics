#!/usr/bin/env python3
"""
Test NASDAQ function directly with debug output
"""

import sys
from datetime import datetime, timezone
from main import LayoffTracker
import requests

def test_nasdaq_function():
    """Test the NASDAQ function directly"""
    
    tracker = LayoffTracker()
    ticker = 'LRCX'
    bearish_date = datetime(2025, 11, 17, tzinfo=timezone.utc)
    target_date = datetime(2025, 12, 29, tzinfo=timezone.utc)
    
    print(f"Testing NASDAQ function for {ticker}")
    print(f"Target date: {target_date.date()}")
    print(f"Looking for earnings from {target_date.date() + timedelta(days=1)} to {target_date.date() + timedelta(days=60)}")
    print()
    
    # Test the function
    result = tracker._check_earnings_dividends_nasdaq(ticker, bearish_date, target_date, future_days=60)
    
    print(f"Result: {result}")
    print(f"Next events: {len(result.get('next_events', []))}")
    if result.get('next_events'):
        for event in result['next_events']:
            print(f"  - {event.get('date')}: {event.get('name')}")
    print()
    
    # Now test the API directly for the specific date we know has earnings
    test_date = datetime(2026, 2, 4).date()
    print(f"Testing API directly for {ticker} on {test_date}...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://www.nasdaq.com/'
    }
    
    url = f"https://api.nasdaq.com/api/calendar/earnings?date={test_date.strftime('%Y-%m-%d')}"
    try:
        response = requests.get(url, headers=headers, timeout=5, verify=False)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            earnings_data = data.get('data', {}).get('rows', []) if isinstance(data, dict) else []
            print(f"Total earnings on this date: {len(earnings_data)}")
            
            # Check if LRCX is in the results
            for event in earnings_data:
                event_ticker = event.get('symbol', '').upper()
                if event_ticker == ticker.upper():
                    print(f"✅ Found {ticker} in results!")
                    print(f"   Company: {event.get('name', 'N/A')}")
                    print(f"   Fiscal Quarter: {event.get('fiscalQuarterEnding', 'N/A')}")
                    break
            else:
                print(f"❌ {ticker} not found in results")
                print(f"   Sample tickers: {[e.get('symbol', 'N/A') for e in earnings_data[:5]]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    from datetime import timedelta
    test_nasdaq_function()

