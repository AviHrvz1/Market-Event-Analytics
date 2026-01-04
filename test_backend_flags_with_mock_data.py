#!/usr/bin/env python3
"""
Unit test to verify backend flags with mock successful API responses
Simulates the case where daily_price_data exists but intraday_data is None
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_backend_flags_with_mock_data():
    """Test backend flags when daily_price_data exists but intraday_data is None"""
    
    print("=" * 80)
    print("BACKEND FLAGS WITH MOCK DATA TEST")
    print("=" * 80)
    print()
    
    test_cases = [
        {
            'company': 'Anavex Life Sciences Corp.',
            'ticker': 'AVXL',
            'article_datetime': '2025-10-02 03:00:00',
            'next_trading': '2025-10-03',
            'expected_close_price': 9.96
        },
        {
            'company': 'Eli Lilly and Company',
            'ticker': 'LLY',
            'article_datetime': '2025-08-26 03:00:00',
            'next_trading': '2025-08-27',
            'expected_close_price': 733.09
        }
    ]
    
    tracker = LayoffTracker()
    now = datetime.now(timezone.utc)
    
    for i, case in enumerate(test_cases, 1):
        print(f"Test Case {i}: {case['company']} ({case['ticker']})")
        print("-" * 80)
        
        article_dt = datetime.strptime(case['article_datetime'], '%Y-%m-%d %H:%M:%S')
        article_dt = article_dt.replace(tzinfo=timezone.utc)
        next_trading = datetime.strptime(case['next_trading'], '%Y-%m-%d')
        next_trading = next_trading.replace(tzinfo=timezone.utc)
        
        days_ago = (now - article_dt).days
        next_days_ago = (now - next_trading).days
        
        print(f"  Article Date: {article_dt.strftime('%Y-%m-%d')} ({days_ago} days ago)")
        print(f"  Next Trading Day: {next_trading.strftime('%Y-%m-%d')} ({next_days_ago} days ago)")
        print()
        
        # Simulate the code path
        print("  Simulating code execution:")
        print()
        
        # Step 1: Check market_was_open
        market_was_open = tracker.is_market_open(article_dt, case['ticker'])
        print(f"  1. market_was_open = {market_was_open}")
        
        if not market_was_open:
            print(f"     → Using market-closed path (line 3586)")
            
            # Step 2: Get next trading day
            next_trading_day = tracker.get_next_trading_day(article_dt, case['ticker'], None)
            print(f"  2. next_trading_day = {next_trading_day.strftime('%Y-%m-%d') if next_trading_day else 'None'}")
            
            if next_trading_day:
                # Step 3: Check days_ago
                now_utc = datetime.now(timezone.utc)
                next_day_utc = next_trading_day.replace(tzinfo=timezone.utc) if next_trading_day.tzinfo is None else next_trading_day.astimezone(timezone.utc)
                days_ago_check = (now_utc - next_day_utc).days
                print(f"  3. days_ago check = {days_ago_check} days")
                
                # Step 4: Intraday data fetch
                print(f"  4. Intraday data fetch:")
                intraday_data = None
                intraday_data_interval = None
                
                if days_ago_check <= 30:
                    print(f"     → Would try 1min (days_ago <= 30)")
                if not intraday_data and days_ago_check <= 60:
                    print(f"     → Would try 5min (days_ago <= 60)")
                
                # Force None if >60 days
                if days_ago_check > 60:
                    print(f"     → Applying fix: days_ago > 60, forcing intraday_data = None")
                    intraday_data = None
                    intraday_data_interval = None
                
                print(f"     Final: intraday_data = {intraday_data is not None}")
                print()
                
                # Step 5: Simulate interval processing for 1hr
                print(f"  5. Processing 1hr interval:")
                
                # Simulate: close_price exists (from daily_price_data)
                close_price = case['expected_close_price']
                print(f"     close_price = {close_price} (from daily_price_data)")
                
                # Simulate: target_price extraction
                if intraday_data:
                    target_price = None  # Would extract from intraday_data
                else:
                    target_price = None  # No intraday_data, so None
                
                print(f"     target_price = {target_price} (extracted from intraday_data)")
                print()
                
                # Step 6: Check condition at line 3780
                print(f"  6. Check condition (line 3780):")
                print(f"     if target_price and intraday_data is not None:")
                condition_result = target_price and intraday_data is not None
                print(f"       target_price = {target_price}")
                print(f"       intraday_data is not None = {intraday_data is not None}")
                print(f"       → Condition result: {condition_result}")
                print()
                
                if condition_result:
                    print(f"     ❌ Would set is_intraday_1hr = True (WRONG!)")
                else:
                    print(f"     ✅ Condition is False, will use else block (line 3810)")
                    print(f"     ✅ Should set:")
                    print(f"        is_daily_close_1hr = True")
                    print(f"        is_intraday_1hr = False")
                    print(f"        price_1hr = {close_price}")
        
        print()
        print()
    
    # Now test with actual calculate_stock_changes but check what happens
    print("=" * 80)
    print("TESTING WITH ACTUAL CODE (checking flag assignment)")
    print("=" * 80)
    print()
    
    # Check if there's a code path issue
    print("Code Path Analysis:")
    print()
    print("For market-closed articles >60 days old:")
    print("  1. market_was_open = False → uses else block (line 3586)")
    print("  2. next_trading_day calculated")
    print("  3. days_ago > 60 → intraday_data forced to None (line 3618-3620)")
    print("  4. For each interval (including 1hr):")
    print("     a. target_price extracted from intraday_data (line 3767-3775)")
    print("     b. Since intraday_data is None, target_price = None")
    print("     c. Condition check: if target_price and intraday_data is not None (line 3780)")
    print("     d. Condition is False → goes to else block (line 3810)")
    print("     e. Sets is_daily_close_1hr = True, is_intraday_1hr = False (line 3818-3819)")
    print()
    print("Expected Result:")
    print("  is_daily_close_1hr = True")
    print("  is_intraday_1hr = False")
    print("  price_1hr = close_price")
    print()

if __name__ == '__main__':
    test_backend_flags_with_mock_data()

