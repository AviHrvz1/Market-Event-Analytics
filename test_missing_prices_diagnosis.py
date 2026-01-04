#!/usr/bin/env python3
"""
Diagnostic test for missing stock prices - check Prixe.io and Yahoo Finance
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_specific_tickers_and_dates():
    """Test the specific tickers and dates that are showing N/A"""
    print("=" * 80)
    print("MISSING PRICES DIAGNOSIS")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Test cases from user's examples
    test_cases = [
        ('NBEV', 'NovaBay Pharmaceuticals', '2024-01-11 03:00:00'),
        ('PYXS', 'Pyxis Oncology', '2023-08-23 03:00:00'),
        ('CRSP', 'CRISPR Therapeutics', '2023-02-06 03:00:00'),
        ('ATHA', 'Athira Pharma', '2023-01-28 03:00:00'),
        ('GILD', 'Gilead Sciences', '2022-03-08 03:00:00'),
        ('IMMU', 'Immunomedics', '2020-09-14 03:00:00'),
        ('GOVX', 'GeoVax Labs', '2020-10-04 13:47:00'),
        ('ESPR', 'Esperion Therapeutics', '2021-10-22 23:50:00'),
    ]
    
    print("Testing Prixe.io and Yahoo Finance for these tickers and dates:")
    print()
    
    for ticker, company, date_str in test_cases:
        print(f"📊 {company} ({ticker}) - {date_str}")
        print("-" * 80)
        
        try:
            # Parse date
            from dateutil import parser
            article_date = parser.parse(date_str).replace(tzinfo=timezone.utc)
            article_day = article_date.date()
            
            # Test Prixe.io daily data using the actual method
            print("   Testing Prixe.io daily data...")
            start_date = article_date - timedelta(days=5)
            end_date = article_date + timedelta(days=3)
            daily_data = tracker._fetch_price_data_batch(ticker, start_date, end_date, '1d')
            if daily_data and daily_data.get('success') and 'data' in daily_data:
                # Extract price for the article date
                price_data = daily_data['data']
                timestamps = price_data.get('timestamp', [])
                closes = price_data.get('close', [])
                if timestamps and closes:
                    # Find closest match
                    target_ts = int(article_date.timestamp())
                    closest_idx = 0
                    min_diff = abs(timestamps[0] - target_ts)
                    for i, ts in enumerate(timestamps):
                        if abs(ts - target_ts) < min_diff:
                            min_diff = abs(ts - target_ts)
                            closest_idx = i
                    if closest_idx < len(closes):
                        print(f"   ✅ Prixe.io daily: ${closes[closest_idx]:.2f}")
                    else:
                        print(f"   ❌ Prixe.io daily: No close price found")
                else:
                    print(f"   ❌ Prixe.io daily: No data in response")
            else:
                print(f"   ❌ Prixe.io daily: API call failed or no data")
            
            # Test Yahoo Finance as fallback
            print("   Testing Yahoo Finance fallback...")
            try:
                import yfinance as yf
                stock = yf.Ticker(ticker)
                hist = stock.history(start=article_day, end=(article_day + timedelta(days=5)))
                if not hist.empty:
                    close_price = float(hist['Close'].iloc[0])
                    print(f"   ✅ Yahoo Finance: ${close_price:.2f}")
                else:
                    print(f"   ❌ Yahoo Finance: No data")
            except Exception as e:
                print(f"   ❌ Yahoo Finance error: {str(e)[:100]}")
            
            # Check days ago
            now_utc = datetime.now(timezone.utc)
            days_ago = (now_utc - article_date).days
            print(f"   Days ago: {days_ago} (intraday only works if ≤60 days)")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        print()
    
    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print()
    print("Common issues:")
    print("1. Prixe.io may not have intraday data for old dates (>30-60 days)")
    print("2. Some tickers may have changed (IMMU was acquired, NBEV may have changed)")
    print("3. Prixe.io may not have daily data for very old dates (2020, 2016)")
    print("4. Yahoo Finance should be used as fallback for old dates")
    print()

def test_prixe_limits():
    """Test Prixe.io data availability limits"""
    print("=" * 80)
    print("PRIXE.IO DATA LIMITS TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    test_ticker = 'AAPL'  # Apple - should have data
    
    # Test different date ranges
    test_dates = [
        ('Recent (5 days ago)', datetime.now(timezone.utc) - timedelta(days=5)),
        ('30 days ago', datetime.now(timezone.utc) - timedelta(days=30)),
        ('60 days ago', datetime.now(timezone.utc) - timedelta(days=60)),
        ('90 days ago', datetime.now(timezone.utc) - timedelta(days=90)),
        ('1 year ago', datetime.now(timezone.utc) - timedelta(days=365)),
    ]
    
    print(f"Testing Prixe.io data availability for {test_ticker}:")
    print()
    
    for label, test_date in test_dates:
        print(f"{label}: {test_date.date()}")
        
        # Test daily using _fetch_price_data_batch
        start_date = test_date - timedelta(days=1)
        end_date = test_date + timedelta(days=1)
        daily_data = tracker._fetch_price_data_batch(test_ticker, start_date, end_date, '1d')
        if daily_data and daily_data.get('success'):
            print(f"   ✅ Daily: Prixe.io has data")
        else:
            print(f"   ❌ Daily: Prixe.io no data")
        
        # Test intraday (should only work for ≤60 days)
        days_ago = (datetime.now(timezone.utc) - test_date).days
        if days_ago <= 60:
            intraday_data = tracker._fetch_intraday_data_for_day(test_ticker, test_date, '5min')
            if intraday_data:
                print(f"   ✅ Intraday: Prixe.io has data")
            else:
                print(f"   ❌ Intraday: Prixe.io no data")
        else:
            print(f"   ⚠️  Intraday: Skipped (>60 days limit)")
        print()

if __name__ == '__main__':
    try:
        test_specific_tickers_and_dates()
        test_prixe_limits()
        print("✅ Diagnosis completed")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

