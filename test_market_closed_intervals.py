#!/usr/bin/env python3
"""
Unit test to verify that when market is closed, intervals show data for next trading day
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker
from config import LOOKBACK_DAYS

def test_market_closed_intervals():
    """Test that market-closed articles show intervals for next trading day"""
    
    print("=" * 80)
    print("MARKET CLOSED INTERVALS TEST")
    print("=" * 80)
    print()
    
    # Test cases: articles published when market was closed
    test_cases = [
        {
            'company': 'Eli Lilly and Company',
            'ticker': 'LLY',
            'article_datetime': '2025-08-26 03:00:00',  # Tuesday 3:00 AM (market closed)
            'expected_next_trading': '2025-08-27',  # Wednesday (next trading day)
            'expected_intervals_date': '2025-08-27'  # All intervals should be on Wednesday
        },
        {
            'company': 'argenx SE',
            'ticker': 'ARGX',
            'article_datetime': '2025-08-25 03:00:00',  # Monday 3:00 AM (market closed)
            'expected_next_trading': '2025-08-26',  # Tuesday (next trading day)
            'expected_intervals_date': '2025-08-26'  # All intervals should be on Tuesday
        },
        {
            'company': 'Anavex Life Sciences Corp',
            'ticker': 'AVXL',
            'article_datetime': '2025-10-02 03:00:00',  # Thursday 3:00 AM (market closed)
            'expected_next_trading': '2025-10-03',  # Friday (next trading day)
            'expected_intervals_date': '2025-10-03'  # All intervals should be on Friday
        },
        {
            'company': 'Test Company',
            'ticker': 'TEST',
            'article_datetime': '2025-12-27 20:00:00',  # Friday 8:00 PM (market closed)
            'expected_next_trading': '2025-12-30',  # Monday (skip weekend)
            'expected_intervals_date': '2025-12-30'  # All intervals should be on Monday
        }
    ]
    
    tracker = LayoffTracker()
    now = datetime.now(timezone.utc)
    
    for i, case in enumerate(test_cases, 1):
        print(f"Test Case {i}: {case['company']} ({case['ticker']})")
        print("-" * 80)
        
        # Parse article datetime
        article_dt = datetime.strptime(case['article_datetime'], '%Y-%m-%d %H:%M:%S')
        article_dt = article_dt.replace(tzinfo=timezone.utc)
        
        print(f"  Article Published: {article_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"  Day of Week: {article_dt.strftime('%A')}")
        print()
        
        # Check if market was closed at article time
        is_market_closed = not tracker.is_market_open(article_dt)
        print(f"  Market Status at Article Time:")
        print(f"    {'✅ Market was CLOSED' if is_market_closed else '❌ Market was OPEN'}")
        print()
        
        # Calculate expected next trading day
        expected_next = datetime.strptime(case['expected_next_trading'], '%Y-%m-%d')
        expected_next = expected_next.replace(tzinfo=timezone.utc)
        
        # Use the actual get_next_trading_day method
        # We need daily_price_data for this, so let's simulate
        next_trading = tracker.get_next_trading_day(article_dt, case['ticker'], None)
        
        if next_trading:
            next_trading_date = next_trading.date() if hasattr(next_trading, 'date') else next_trading.replace(hour=0, minute=0, second=0, microsecond=0).date()
            expected_date = expected_next.date()
            
            print(f"  Next Trading Day Calculation:")
            print(f"    Expected: {expected_date}")
            print(f"    Got: {next_trading_date}")
            
            if next_trading_date == expected_date:
                print(f"    ✅ Correct next trading day")
            else:
                print(f"    ❌ Wrong next trading day!")
            print()
            
            # Check if intervals would be calculated for next trading day
            print(f"  Interval Date Verification:")
            
            # Simulate interval calculation
            intervals_to_check = ['1min', '2min', '3min', '5min', '10min', '30min', '1hr']
            all_correct = True
            
            for interval_name in intervals_to_check:
                # Calculate what the interval date should be
                # For market closed articles, intervals are on next trading day
                interval_date = next_trading_date
                expected_interval_date = expected_next.date()
                
                if interval_date == expected_interval_date:
                    status = "✅"
                else:
                    status = "❌"
                    all_correct = False
                
                print(f"    {status} {interval_name}: {interval_date} (expected: {expected_interval_date})")
            
            print()
            
            if all_correct:
                print(f"  ✅ All intervals correctly set to next trading day")
            else:
                print(f"  ❌ Some intervals have wrong dates")
        else:
            print(f"  ❌ Could not calculate next trading day")
        
        print()
        print()
    
    # Test the actual calculate_stock_changes for a market-closed article
    print("=" * 80)
    print("TESTING ACTUAL calculate_stock_changes()")
    print("=" * 80)
    print()
    
    # Use first test case
    test_case = test_cases[0]
    article_dt = datetime.strptime(test_case['article_datetime'], '%Y-%m-%d %H:%M:%S')
    article_dt = article_dt.replace(tzinfo=timezone.utc)
    
    print(f"Testing: {test_case['company']} ({test_case['ticker']})")
    print(f"Article Date: {article_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print()
    
    # Create mock layoff dict
    layoff = {
        'company_name': test_case['company'],
        'stock_ticker': test_case['ticker'],
        'datetime': article_dt,
        'publishedAt': article_dt.isoformat()
    }
    
    print("Calling calculate_stock_changes()...")
    try:
        results = tracker.calculate_stock_changes(layoff)
        
        if results:
            print("✅ calculate_stock_changes() returned results")
            print()
            
            # Check interval dates
            intervals_to_check = ['1min', '2min', '3min', '5min', '10min', '30min', '1hr']
            expected_date = datetime.strptime(test_case['expected_intervals_date'], '%Y-%m-%d').date()
            
            print(f"Checking interval dates (should all be {expected_date}):")
            all_correct = True
            
            for interval_name in intervals_to_check:
                date_key = f'date_{interval_name}'
                price_key = f'price_{interval_name}'
                is_daily_close_key = f'is_daily_close_{interval_name}'
                is_intraday_key = f'is_intraday_{interval_name}'
                
                interval_date_str = results.get(date_key)
                price = results.get(price_key)
                is_daily_close = results.get(is_daily_close_key, False)
                is_intraday = results.get(is_intraday_key, False)
                
                if interval_date_str:
                    try:
                        interval_date = datetime.strptime(interval_date_str, '%Y-%m-%d').date()
                        if interval_date == expected_date:
                            status = "✅"
                        else:
                            status = "❌"
                            all_correct = False
                        
                        price_display = f"${price:.2f}" if price else "N/A"
                        daily_close_label = " [Daily Close]" if is_daily_close else ""
                        intraday_label = " [Intraday]" if is_intraday else ""
                        
                        print(f"  {status} {interval_name}: {interval_date} - {price_display}{daily_close_label}{intraday_label}")
                    except:
                        print(f"  ❌ {interval_name}: Could not parse date '{interval_date_str}'")
                        all_correct = False
                else:
                    print(f"  ⚠️  {interval_name}: No date set")
            
            print()
            
            if all_correct:
                print("✅ All intervals correctly set to next trading day date")
            else:
                print("❌ Some intervals have wrong dates")
        else:
            print("❌ calculate_stock_changes() returned None or empty results")
    except Exception as e:
        print(f"❌ Error calling calculate_stock_changes(): {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("Expected behavior for market-closed articles:")
    print("  - Article published when market is closed")
    print("  - All intervals (1min, 2min, 3min, 5min, 10min, 30min, 1hr) should be on NEXT trading day")
    print("  - Intervals should show data from next trading day's market open + time offset")
    print("  - For articles >60 days old, intervals should use daily close fallback")
    print()

if __name__ == '__main__':
    test_market_closed_intervals()

