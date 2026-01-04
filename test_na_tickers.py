#!/usr/bin/env python3
"""
Test why certain tickers show N/A for all intervals
"""

from datetime import datetime, timezone, timedelta
from main import LayoffTracker

tracker = LayoffTracker()

tickers_to_test = [
    ('ATI', 'NYSE: ATI'),
    ('BRK.A', 'Berkshire Hathaway'),
    ('SKAB.ST', 'Skanska'),
]

print(f"\n{'='*80}")
print("Testing Tickers Showing N/A")
print(f"{'='*80}\n")

for ticker, company_name in tickers_to_test:
    print(f"\n{'='*80}")
    print(f"Testing: {company_name} ({ticker})")
    print(f"{'='*80}")
    
    # Test 1: Check if ticker is valid in Prixe.io
    print(f"\n1. Checking if ticker exists in Prixe.io...")
    test_date = datetime(2025, 12, 8, 0, 0, 0, tzinfo=timezone.utc)
    test_data = tracker._fetch_price_data_batch(ticker, test_date, test_date, '1d')
    
    if test_data and test_data.get('success'):
        print(f"   ✓ Ticker exists in Prixe.io")
        data = test_data.get('data', {})
        timestamps = data.get('timestamp', [])
        closes = data.get('close', [])
        print(f"   Data points: {len(timestamps)}")
        if timestamps:
            print(f"   Latest close: {closes[0] if closes else 'N/A'}")
    else:
        print(f"   ✗ Ticker NOT found in Prixe.io or no data")
        if test_data:
            print(f"   Response: {test_data}")
    
    # Test 2: Check if ticker is in SEC EDGAR
    print(f"\n2. Checking if ticker is in SEC EDGAR...")
    is_valid = tracker._is_valid_ticker(ticker)
    print(f"   Valid in SEC EDGAR: {is_valid}")
    
    # Test 3: Simulate calculate_stock_changes
    print(f"\n3. Simulating calculate_stock_changes...")
    article_dt = datetime(2025, 12, 8, 8, 56, tzinfo=timezone.utc) if ticker == 'ATI' else datetime(2025, 12, 8, 8, 22, tzinfo=timezone.utc)
    
    mock_layoff = {
        'company_name': company_name,
        'stock_ticker': ticker,
        'datetime': article_dt,
        'date': article_dt.strftime('%Y-%m-%d'),
        'time': article_dt.strftime('%H:%M:%S'),
        'url': f'https://test.com/{ticker}',
        'title': f'{company_name} test article'
    }
    
    print(f"   Article datetime: {article_dt}")
    print(f"   Market was open: {tracker.is_market_open(article_dt, ticker)}")
    
    stock_changes = tracker.calculate_stock_changes(mock_layoff)
    
    # Check results
    print(f"\n   Results:")
    print(f"   Base price: {stock_changes.get('base_price')}")
    print(f"   Market was open: {stock_changes.get('market_was_open')}")
    
    # Check a few intervals
    for interval in ['5min', '10min', '30min', '1hr']:
        price = stock_changes.get(f'price_{interval}')
        change = stock_changes.get(f'change_{interval}')
        market_closed = stock_changes.get(f'market_closed_{interval}')
        no_data = stock_changes.get(f'no_intraday_data_{interval}')
        
        print(f"   {interval}:")
        print(f"     Price: {price}")
        print(f"     Change: {change}")
        print(f"     Market closed: {market_closed}")
        print(f"     No intraday data: {no_data}")

