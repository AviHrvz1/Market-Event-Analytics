#!/usr/bin/env python3
"""
Unit test to trace why 12:30 (1hr) shows actual price instead of Daily Close
for articles >60 days old
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_12_30_daily_close_fallback():
    """Trace the exact code path for 12:30 interval"""
    
    print("=" * 80)
    print("12:30 DAILY CLOSE FALLBACK TRACE")
    print("=" * 80)
    print()
    
    test_cases = [
        {
            'company': 'Anavex Life Sciences Corp.',
            'ticker': 'AVXL',
            'article_datetime': '2025-10-02 03:00:00',
            'next_trading': '2025-10-03'
        },
        {
            'company': 'Eli Lilly and Company',
            'ticker': 'LLY',
            'article_datetime': '2025-08-26 03:00:00',
            'next_trading': '2025-08-27'
        },
        {
            'company': 'argenx SE',
            'ticker': 'ARGX',
            'article_datetime': '2025-08-25 03:00:00',
            'next_trading': '2025-08-26'
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
        
        # Simulate the market-closed path logic step by step
        print("  Step-by-step code execution:")
        print()
        
        # Step 1: Check market_was_open
        market_was_open = tracker.is_market_open(article_dt, case['ticker'])
        print(f"  1. market_was_open = {market_was_open}")
        print(f"     → Will use {'market-open path' if market_was_open else 'market-closed path (line 3586)'}")
        print()
        
        if not market_was_open:
            # Step 2: Get next trading day
            next_trading_day = tracker.get_next_trading_day(article_dt, case['ticker'], None)
            print(f"  2. next_trading_day = {next_trading_day.strftime('%Y-%m-%d') if next_trading_day else 'None'}")
            print()
            
            if next_trading_day:
                # Step 3: Check days_ago for next trading day
                now_utc = datetime.now(timezone.utc)
                next_day_utc = next_trading_day.replace(tzinfo=timezone.utc) if next_trading_day.tzinfo is None else next_trading_day.astimezone(timezone.utc)
                days_ago_check = (now_utc - next_day_utc).days
                
                print(f"  3. days_ago check for next_trading_day:")
                print(f"     days_ago = {days_ago_check} days")
                print(f"     days_ago <= 60? {days_ago_check <= 60}")
                print()
                
                # Step 4: Intraday data fetch logic (lines 3600-3620)
                print(f"  4. Intraday data fetch logic (lines 3600-3620):")
                intraday_data = None
                intraday_data_interval = None
                
                if days_ago_check <= 30:
                    print(f"     → Would try 1min data (days_ago <= 30)")
                    # Don't actually fetch, just simulate
                    intraday_data = None  # Simulate: would return None for >60 days
                if not intraday_data and days_ago_check <= 60:
                    print(f"     → Would try 5min data (days_ago <= 60)")
                    # Don't actually fetch, just simulate
                    intraday_data = None  # Simulate: would return None for >60 days
                
                # Step 5: Force None if >60 days (line 3618-3620)
                if days_ago_check > 60:
                    print(f"     → Applying fix: days_ago > 60, forcing intraday_data = None")
                    intraday_data = None
                    intraday_data_interval = None
                
                print(f"     Final: intraday_data = {intraday_data is not None}")
                print(f"     Final: intraday_data_interval = {intraday_data_interval}")
                print()
                
                # Step 6: Interval processing for 1hr (line 3714-3827)
                print(f"  5. Processing 1hr interval (line 3714-3827):")
                print(f"     interval_name = '1hr'")
                print(f"     hours_after_open = 1.0")
                print()
                
                # Calculate target datetime
                market_open_utc = tracker._get_market_open_time(next_trading_day, case['ticker'])
                if market_open_utc:
                    target_datetime_utc = market_open_utc + timedelta(hours=1.0)
                    print(f"     market_open_utc = {market_open_utc.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"     target_datetime_utc = {target_datetime_utc.strftime('%Y-%m-%d %H:%M:%S')}")
                    print()
                    
                    # Step 7: Extract intraday price (line 3766-3774)
                    print(f"  6. Extract intraday price (line 3766-3774):")
                    if intraday_data:
                        print(f"     → intraday_data exists, would call _extract_intraday_price_from_batch()")
                        target_price = None  # Simulate: would return None if no data
                    else:
                        print(f"     → intraday_data is None, setting target_price = None")
                        target_price = None
                        is_exact = False
                        actual_ts = None
                    print(f"     target_price = {target_price}")
                    print()
                    
                    # Step 8: Check if target_price and intraday_data (line 3777)
                    print(f"  7. Check condition (line 3777):")
                    print(f"     if target_price and intraday_data is not None:")
                    print(f"       target_price = {target_price}")
                    print(f"       intraday_data is not None = {intraday_data is not None}")
                    condition_result = target_price and intraday_data is not None
                    print(f"     → Condition result: {condition_result}")
                    print()
                    
                    if condition_result:
                        print(f"     ❌ ISSUE: Would set is_intraday_1hr = True (line 3806)")
                        print(f"        This would cause UI to show actual price instead of Daily Close")
                    else:
                        print(f"     ✅ Condition is False, will use daily close fallback (line 3808)")
                        print(f"        Should set:")
                        print(f"          is_daily_close_1hr = True")
                        print(f"          is_intraday_1hr = False")
                        print(f"          price_1hr = close_price")
        
        print()
        print()
    
    print("=" * 80)
    print("DIAGNOSIS")
    print("=" * 80)
    print()
    print("If 12:30 shows actual price instead of Daily Close:")
    print("  1. Check if intraday_data is somehow not None")
    print("  2. Check if target_price is being set from somewhere else")
    print("  3. Check if is_intraday_1hr is being set to True incorrectly")
    print("  4. Check if is_daily_close_1hr is not being set to True")
    print("  5. Check UI condition: isDailyClose && !isIntraday")
    print()

if __name__ == '__main__':
    test_12_30_daily_close_fallback()

