#!/usr/bin/env python3
"""
Diagnose why certain tickers show N/A for all stock price intervals.
Tests: SGEN (Seagen), AVLT (Avalo), MRTX (Mirati)
"""

from datetime import datetime, timezone, timedelta
from main import LayoffTracker

tracker = LayoffTracker()

# Test tickers from user's issue
tickers_to_test = [
    ('SGEN', 'Seagen Inc', datetime(2025, 11, 14, 3, 0, tzinfo=timezone.utc)),
    ('AVLT', 'Avalo Therapeutics', datetime(2025, 11, 12, 3, 0, tzinfo=timezone.utc)),
    ('MRTX', 'Mirati Therapeutics', datetime(2025, 10, 28, 3, 0, tzinfo=timezone.utc)),
]

print(f"\n{'='*80}")
print("Diagnosing N/A Tickers Issue")
print(f"{'='*80}\n")

for ticker, company_name, article_dt in tickers_to_test:
    print(f"\n{'='*80}")
    print(f"Testing: {company_name} ({ticker})")
    print(f"Article Date: {article_dt}")
    print(f"{'='*80}")
    
    # Test 1: Check if Prixe.io has data for this ticker
    print(f"\n[Test 1] Checking Prixe.io API for ticker '{ticker}'...")
    test_start = article_dt - timedelta(days=5)
    test_end = article_dt + timedelta(days=3)
    
    try:
        price_data = tracker._fetch_price_data_batch(ticker, test_start, test_end, '1d')
        
        if price_data:
            if price_data.get('success'):
                data = price_data.get('data', {})
                timestamps = data.get('timestamp', [])
                closes = data.get('close', [])
                print(f"   ✅ API returned data")
                print(f"   Data points: {len(timestamps)}")
                if timestamps and closes:
                    print(f"   Date range: {datetime.fromtimestamp(timestamps[0]).date()} to {datetime.fromtimestamp(timestamps[-1]).date()}")
                    print(f"   Sample prices: {closes[:3] if len(closes) >= 3 else closes}")
                else:
                    print(f"   ⚠️  No timestamp/close data in response")
            else:
                print(f"   ❌ API returned success=False")
                print(f"   Response: {price_data}")
        else:
            print(f"   ❌ API returned None (no response or error)")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Check if ticker is in SEC EDGAR (valid ticker)
    print(f"\n[Test 2] Checking if ticker is valid in SEC EDGAR...")
    try:
        is_valid = tracker._is_valid_ticker(ticker)
        print(f"   {'✅' if is_valid else '❌'} Ticker valid: {is_valid}")
    except Exception as e:
        print(f"   ❌ Error checking ticker: {e}")
    
    # Test 3: Test calculate_stock_changes
    print(f"\n[Test 3] Testing calculate_stock_changes...")
    mock_layoff = {
        'company_name': company_name,
        'stock_ticker': ticker,
        'datetime': article_dt,
        'date': article_dt.date().isoformat(),
        'time': article_dt.strftime('%H:%M'),
    }
    
    try:
        stock_changes = tracker.calculate_stock_changes(mock_layoff)
        
        base_price = stock_changes.get('base_price')
        market_was_open = stock_changes.get('market_was_open')
        
        print(f"   Base price: {base_price if base_price else 'N/A'}")
        print(f"   Market was open: {market_was_open}")
        
        # Check a few intervals
        test_intervals = ['5min', '10min', '30min', '1hr', '2hr', '3hr', 'next_close']
        intervals_with_data = []
        intervals_na = []
        
        for interval in test_intervals:
            price = stock_changes.get(f'price_{interval}')
            if price is not None:
                intervals_with_data.append(interval)
            else:
                intervals_na.append(interval)
        
        print(f"   Intervals with data: {len(intervals_with_data)} ({intervals_with_data})")
        print(f"   Intervals N/A: {len(intervals_na)} ({intervals_na})")
        
        if len(intervals_with_data) == 0:
            print(f"   ❌ All intervals are N/A - this matches the user's issue")
            print(f"   Possible causes:")
            print(f"     1. Prixe.io doesn't have data for this ticker/date range")
            print(f"     2. Ticker was delisted/acquired before the article date")
            print(f"     3. API call failed silently")
            print(f"     4. Date range is outside Prixe.io's available data")
        else:
            print(f"   ✅ Some intervals have data")
            
    except Exception as e:
        print(f"   ❌ Error in calculate_stock_changes: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Check if ticker is in failed_tickers cache
    print(f"\n[Test 4] Checking failed_tickers cache...")
    if ticker in tracker.failed_tickers:
        print(f"   ⚠️  Ticker is in failed_tickers cache (marked as failed)")
    else:
        print(f"   ✅ Ticker not in failed_tickers cache")
    
    # Test 5: Check if ticker is in invalid_tickers list
    print(f"\n[Test 5] Checking invalid_tickers list...")
    if ticker in tracker.invalid_tickers:
        print(f"   ⚠️  Ticker is in invalid_tickers list")
    else:
        print(f"   ✅ Ticker not in invalid_tickers list")

print(f"\n{'='*80}")
print("Diagnosis Complete")
print(f"{'='*80}\n")

print("Summary:")
print("If all tests show N/A, likely causes:")
print("1. Ticker was delisted/acquired (SGEN acquired by Pfizer, MRTX acquired by BMS)")
print("2. Prixe.io doesn't have historical data for these tickers")
print("3. Date range is outside Prixe.io's available data window")
print("4. API endpoint issue (404 errors)")

