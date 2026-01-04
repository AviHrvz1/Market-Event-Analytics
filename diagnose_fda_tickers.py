#!/usr/bin/env python3
"""
Diagnose why FDA approval tickers show N/A:
- NOVN (Novan)
- AVZO (Avertex Biotherapeutics)
- BAYRY (Bayer AG) - has some data
- MRTX (Mirati) - already known issue
- HGEN (Humanigen)
"""

from datetime import datetime, timezone, timedelta
from main import LayoffTracker

tracker = LayoffTracker()

tickers_to_test = [
    ('NOVN', 'Novan', datetime(2025, 11, 14, 3, 0, tzinfo=timezone.utc)),
    ('AVZO', 'Avertex Biotherapeutics Inc', datetime(2025, 11, 14, 3, 0, tzinfo=timezone.utc)),
    ('BAYRY', 'Bayer AG', datetime(2025, 11, 13, 3, 0, tzinfo=timezone.utc)),
    ('MRTX', 'Mirati Therapeutics', datetime(2025, 10, 28, 3, 0, tzinfo=timezone.utc)),
    ('HGEN', 'Humanigen', datetime(2025, 10, 23, 3, 0, tzinfo=timezone.utc)),
]

print(f"\n{'='*80}")
print("FDA Approval Tickers Diagnosis")
print(f"{'='*80}\n")

for ticker, company_name, article_dt in tickers_to_test:
    print(f"\n{'='*80}")
    print(f"{company_name} ({ticker})")
    print(f"Article Date: {article_dt.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*80}")
    
    # Test 1: Check if ticker is in SEC EDGAR (valid US ticker)
    print(f"\n[1] SEC EDGAR Validation:")
    try:
        is_valid = tracker._is_valid_ticker(ticker)
        print(f"    {'✅ Valid' if is_valid else '❌ Invalid/Not Found'}")
        if not is_valid:
            print(f"    → Ticker not found in SEC EDGAR database")
            print(f"    → Possible reasons: Foreign ticker, OTC, delisted, or invalid")
    except Exception as e:
        print(f"    ❌ Error: {e}")
    
    # Test 2: Check Prixe.io API response
    print(f"\n[2] Prixe.io API Check:")
    test_start = article_dt - timedelta(days=5)
    test_end = article_dt + timedelta(days=3)
    
    try:
        price_data = tracker._fetch_price_data_batch(ticker, test_start, test_end, '1d')
        
        if price_data:
            if price_data.get('success'):
                data = price_data.get('data', {})
                timestamps = data.get('timestamp', [])
                closes = data.get('close', [])
                print(f"    ✅ API returned data")
                print(f"    → Data points: {len(timestamps)}")
                if timestamps and closes:
                    first_date = datetime.fromtimestamp(timestamps[0]).date()
                    last_date = datetime.fromtimestamp(timestamps[-1]).date()
                    print(f"    → Date range: {first_date} to {last_date}")
                    print(f"    → Latest close: ${closes[0]:.2f}" if closes else "    → No close prices")
            else:
                print(f"    ❌ API returned success=False")
                print(f"    → Response: {price_data}")
        else:
            print(f"    ❌ API returned None")
            print(f"    → Possible reasons:")
            print(f"       - API endpoint 404 error")
            print(f"       - Ticker not in Prixe.io database")
            print(f"       - Ticker in failed_tickers cache")
            
            # Check if in failed_tickers
            if ticker.upper() in tracker.failed_tickers:
                print(f"    → Ticker is in failed_tickers cache (marked as failed)")
            if ticker.upper() in tracker.invalid_tickers:
                print(f"    → Ticker is in invalid_tickers list")
    except Exception as e:
        print(f"    ❌ Exception: {e}")
    
    # Test 3: Check if ticker format might be wrong
    print(f"\n[3] Ticker Format Check:")
    print(f"    Ticker: '{ticker}'")
    print(f"    Length: {len(ticker)}")
    print(f"    Contains dot: {'.' in ticker}")
    print(f"    Contains colon: {':' in ticker}")
    
    # Test 4: Simulate stock changes calculation
    print(f"\n[4] Stock Changes Calculation:")
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
        
        print(f"    Base price: {base_price if base_price else 'N/A'}")
        print(f"    Market was open: {market_was_open}")
        
        # Check intervals
        test_intervals = ['5min', '10min', '30min', '1hr', '2hr', '3hr', 'next_close']
        intervals_with_data = [i for i in test_intervals if stock_changes.get(f'price_{i}') is not None]
        intervals_na = [i for i in test_intervals if stock_changes.get(f'price_{i}') is None]
        
        print(f"    Intervals with data: {len(intervals_with_data)}")
        if intervals_with_data:
            print(f"    → {', '.join(intervals_with_data)}")
        print(f"    Intervals N/A: {len(intervals_na)}")
        
        if len(intervals_with_data) == 0:
            print(f"    ❌ All intervals N/A")
            if not base_price:
                print(f"    → Root cause: No base price (API failed or no data)")
        else:
            print(f"    ✅ Some intervals have data")
            
    except Exception as e:
        print(f"    ❌ Error: {e}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*80}")
print("Summary & Diagnosis")
print(f"{'='*80}\n")

print("Possible Root Causes:")
print("1. Prixe.io API endpoint /api/price returning 404")
print("   → Affects ALL tickers")
print("   → Solution: Check if endpoint changed to /api/historical or other")
print()
print("2. Ticker not in Prixe.io database")
print("   → Foreign tickers (BAYRY is German)")
print("   → OTC/pink sheet stocks")
print("   → Delisted/acquired companies (MRTX, HGEN)")
print()
print("3. Ticker extraction issue (Claude)")
print("   → Claude might extract wrong ticker")
print("   → Ticker format issue (e.g., BAYRY vs BAYN.DE)")
print()
print("4. Date range outside Prixe.io availability")
print("   → Prixe.io might not have data for these dates")
print("   → Historical data limitations")

