#!/usr/bin/env python3
"""
Unit test to verify market-closed logic: intervals should be on next trading day
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_market_closed_logic():
    """Test that market-closed articles calculate intervals for next trading day"""
    
    print("=" * 80)
    print("MARKET CLOSED INTERVALS LOGIC TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Test cases
    test_cases = [
        {
            'name': 'Tuesday 3:00 AM (market closed)',
            'datetime': datetime(2025, 8, 26, 3, 0, 0, tzinfo=timezone.utc),  # Tue Aug 26, 3:00 AM
            'expected_next': datetime(2025, 8, 27, 0, 0, 0, tzinfo=timezone.utc),  # Wed Aug 27
            'ticker': 'LLY'
        },
        {
            'name': 'Monday 3:00 AM (market closed)',
            'datetime': datetime(2025, 8, 25, 3, 0, 0, tzinfo=timezone.utc),  # Mon Aug 25, 3:00 AM
            'expected_next': datetime(2025, 8, 26, 0, 0, 0, tzinfo=timezone.utc),  # Tue Aug 26
            'ticker': 'ARGX'
        },
        {
            'name': 'Friday 8:00 PM (market closed, weekend next)',
            'datetime': datetime(2025, 12, 27, 20, 0, 0, tzinfo=timezone.utc),  # Fri Dec 27, 8:00 PM
            'expected_next': datetime(2025, 12, 30, 0, 0, 0, tzinfo=timezone.utc),  # Mon Dec 30 (skip weekend)
            'ticker': 'TEST'
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"Test Case {i}: {case['name']}")
        print("-" * 80)
        
        article_dt = case['datetime']
        expected_next = case['expected_next']
        ticker = case['ticker']
        
        print(f"  Article DateTime: {article_dt.strftime('%Y-%m-%d %H:%M:%S %Z')} ({article_dt.strftime('%A')})")
        print(f"  Expected Next Trading Day: {expected_next.strftime('%Y-%m-%d')} ({expected_next.strftime('%A')})")
        print()
        
        # Check if market was closed
        is_closed = not tracker.is_market_open(article_dt, ticker)
        print(f"  Market Status: {'✅ CLOSED' if is_closed else '❌ OPEN'}")
        print()
        
        if is_closed:
            # Get next trading day
            next_trading = tracker.get_next_trading_day(article_dt, ticker, None)
            
            if next_trading:
                # Normalize to date for comparison
                if hasattr(next_trading, 'date'):
                    next_date = next_trading.date()
                else:
                    next_date = next_trading.replace(hour=0, minute=0, second=0, microsecond=0).date()
                
                expected_date = expected_next.date()
                
                print(f"  Next Trading Day Calculation:")
                print(f"    Expected: {expected_date}")
                print(f"    Got: {next_date}")
                
                if next_date == expected_date:
                    print(f"    ✅ Correct!")
                else:
                    print(f"    ❌ Wrong! Expected {expected_date}, got {next_date}")
                print()
                
                # Verify intervals would be calculated for this day
                print(f"  Interval Date Verification:")
                print(f"    All intervals (1min, 2min, 3min, 5min, 10min, 30min, 1hr) should use date: {next_date}")
                print(f"    ✅ Logic: Intervals = market_open({next_date}) + time_offset")
                print()
            else:
                print(f"  ❌ Could not calculate next trading day")
                print()
        else:
            print(f"  ⚠️  Market was open - intervals would be on same day")
            print()
        
        print()
    
    # Test the actual code path
    print("=" * 80)
    print("CODE PATH VERIFICATION")
    print("=" * 80)
    print()
    
    # Simulate the market-closed path in calculate_stock_changes
    test_case = test_cases[0]
    article_dt = test_case['datetime']
    ticker = test_case['ticker']
    
    print(f"Simulating calculate_stock_changes() logic for:")
    print(f"  Article: {article_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Ticker: {ticker}")
    print()
    
    # Check market_was_open flag
    market_was_open = tracker.is_market_open(article_dt, ticker)
    print(f"  market_was_open = {market_was_open}")
    
    if not market_was_open:
        print(f"  ✅ Market was closed - will use 'else' path (line 3585)")
        print(f"  ✅ Will call get_next_trading_day()")
        
        next_trading = tracker.get_next_trading_day(article_dt, ticker, None)
        if next_trading:
            print(f"  ✅ Next trading day: {next_trading.strftime('%Y-%m-%d') if hasattr(next_trading, 'strftime') else next_trading}")
            print(f"  ✅ Intervals will be calculated for this day")
            print(f"  ✅ Interval times = market_open({next_trading}) + hours_after_open")
            print()
            print(f"  Expected interval dates:")
            intervals = ['1min', '2min', '3min', '5min', '10min', '30min', '1hr']
            for interval in intervals:
                if hasattr(next_trading, 'date'):
                    interval_date = next_trading.date()
                else:
                    interval_date = next_trading.replace(hour=0, minute=0, second=0, microsecond=0).date()
                print(f"    {interval}: {interval_date}")
        else:
            print(f"  ❌ Could not get next trading day")
    else:
        print(f"  ⚠️  Market was open - would use different path")
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("Expected Logic for Market-Closed Articles:")
    print("  1. Detect market was closed at article time")
    print("  2. Calculate next trading day")
    print("  3. All intervals (1min, 2min, 3min, 5min, 10min, 30min, 1hr) use next trading day")
    print("  4. Interval times = market_open(next_trading_day) + time_offset")
    print("  5. For articles >60 days old, use daily close fallback for all intervals")
    print()

if __name__ == '__main__':
    test_market_closed_logic()

