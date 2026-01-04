#!/usr/bin/env python3
"""
Debug NASDAQ API to see why Next Events is empty
"""

import requests
from datetime import datetime, timedelta

def test_nasdaq_for_tickers():
    """Test NASDAQ API for specific tickers from UI results"""
    
    # Tickers from UI results
    test_tickers = ['DOMO', 'DOCN', 'LRCX', 'NET', 'ZS', 'TSLA', 'AAPL']
    
    # Date range from UI scenario
    target_date = datetime(2025, 12, 29).date()
    future_end = target_date + timedelta(days=60)
    
    print(f"Target Date: {target_date}")
    print(f"Looking for earnings from {target_date + timedelta(days=1)} to {future_end}")
    print()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://www.nasdaq.com/'
    }
    
    # Query strategy: daily for first 30 days, then every 2 days
    current_date = target_date + timedelta(days=1)
    mid_point = target_date + timedelta(days=30)
    dates_to_query = []
    
    while current_date <= min(mid_point, future_end):
        dates_to_query.append(current_date)
        current_date += timedelta(days=1)
    
    while current_date <= future_end:
        dates_to_query.append(current_date)
        current_date += timedelta(days=2)
        if len(dates_to_query) >= 50:
            break
    
    print(f"Querying {len(dates_to_query)} dates...")
    print()
    
    found_earnings = {ticker: [] for ticker in test_tickers}
    total_queries = 0
    successful_queries = 0
    
    for query_date in dates_to_query:
        url = f"https://api.nasdaq.com/api/calendar/earnings?date={query_date.strftime('%Y-%m-%d')}"
        total_queries += 1
        
        try:
            response = requests.get(url, headers=headers, timeout=5, verify=False)
            if response.status_code == 200:
                successful_queries += 1
                data = response.json()
                earnings_data = data.get('data', {}).get('rows', []) if isinstance(data, dict) else []
                
                # Check if any of our test tickers are in the results
                for event in earnings_data:
                    event_ticker = event.get('symbol', '').upper()
                    if event_ticker in test_tickers:
                        found_earnings[event_ticker].append({
                            'date': query_date.strftime('%Y-%m-%d'),
                            'fiscal_quarter': event.get('fiscalQuarterEnding', ''),
                            'name': event.get('name', '')
                        })
        except Exception as e:
            pass
    
    print(f"Queries: {successful_queries}/{total_queries} successful")
    print()
    print("Found earnings:")
    for ticker, events in found_earnings.items():
        if events:
            print(f"  {ticker}: {len(events)} event(s)")
            for event in events:
                print(f"    - {event['date']} ({event['fiscal_quarter']})")
        else:
            print(f"  {ticker}: None")
    
    print()
    print(f"Total tickers with earnings: {sum(1 for events in found_earnings.values() if events)}/{len(test_tickers)}")

if __name__ == "__main__":
    test_nasdaq_for_tickers()

