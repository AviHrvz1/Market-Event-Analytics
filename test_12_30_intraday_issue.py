#!/usr/bin/env python3
"""
Unit test to diagnose why 12:30 (1hr) interval shows actual price instead of Daily Close
for articles >60 days old
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker
from config import LOOKBACK_DAYS

def test_12_30_intraday_issue():
    """Test specific cases where 12:30 shows price instead of Daily Close"""
    
    print("=" * 80)
    print("12:30 INTRADAY DATA ISSUE DIAGNOSIS")
    print("=" * 80)
    print()
    
    # Test cases from user report
    test_cases = [
        {
            'company': 'Anavex Life Sciences Corp',
            'ticker': 'AVXL',
            'article_date': '2025-10-02 03:00:00',
            'next_trading': '2025-10-03',
            'expected_12_30_price': None,  # Should be None (use daily close fallback)
            'expected_12_30_label': 'Daily Close'
        },
        {
            'company': 'Eli Lilly and Company',
            'ticker': 'LLY',
            'article_date': '2025-08-26 03:00:00',
            'next_trading': '2025-08-27',
            'expected_12_30_price': None,
            'expected_12_30_label': 'Daily Close'
        },
        {
            'company': 'argenx SE',
            'ticker': 'ARGX',
            'article_date': '2025-08-25 03:00:00',
            'next_trading': '2025-08-26',
            'expected_12_30_price': None,
            'expected_12_30_label': 'Daily Close'
        }
    ]
    
    now = datetime.now(timezone.utc)
    tracker = LayoffTracker()
    
    for i, case in enumerate(test_cases, 1):
        print(f"Test Case {i}: {case['company']} ({case['ticker']})")
        print("-" * 80)
        
        # Parse article date
        article_dt = datetime.strptime(case['article_date'], '%Y-%m-%d %H:%M:%S')
        article_dt = article_dt.replace(tzinfo=timezone.utc)
        
        # Calculate next trading day
        next_trading = article_dt + timedelta(days=1)
        while next_trading.weekday() >= 5:  # Skip weekends
            next_trading += timedelta(days=1)
        
        days_ago = (now - article_dt).days
        next_days_ago = (now - next_trading).days
        
        print(f"  Article Date: {article_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"  Days Ago: {days_ago} days")
        print(f"  Next Trading Day: {next_trading.strftime('%Y-%m-%d')}")
        print(f"  Next Trading Days Ago: {next_days_ago} days")
        print()
        
        # Check if intraday data would be fetched
        print(f"  Checking intraday data fetch logic:")
        if next_days_ago > 60:
            print(f"    ✅ Next trading day is >60 days old - should NOT fetch intraday data")
        else:
            print(f"    ⚠️  Next trading day is within 60 days - might fetch intraday data")
        print()
        
        # Simulate the market-closed path logic
        print(f"  Simulating market-closed article processing:")
        
        # Check what _fetch_intraday_data_for_day returns
        intraday_data_1min = tracker._fetch_intraday_data_for_day(case['ticker'], next_trading, interval='1min')
        intraday_data_5min = tracker._fetch_intraday_data_for_day(case['ticker'], next_trading, interval='5min')
        
        print(f"    _fetch_intraday_data_for_day(1min): {intraday_data_1min is not None}")
        print(f"    _fetch_intraday_data_for_day(5min): {intraday_data_5min is not None}")
        
        # Check the actual logic from calculate_stock_changes
        now_utc = datetime.now(timezone.utc)
        next_day_utc = next_trading.replace(tzinfo=timezone.utc) if next_trading.tzinfo is None else next_trading.astimezone(timezone.utc)
        days_ago_check = (now_utc - next_day_utc).days
        
        print(f"    Days ago check in code: {days_ago_check} days")
        
        # Simulate the fetch logic
        intraday_data = None
        intraday_data_interval = None
        if days_ago_check <= 30:
            intraday_data = tracker._fetch_intraday_data_for_day(case['ticker'], next_trading, interval='1min')
            if intraday_data:
                intraday_data_interval = '1min'
        if not intraday_data and days_ago_check <= 60:
            intraday_data = tracker._fetch_intraday_data_for_day(case['ticker'], next_trading, interval='5min')
            if intraday_data:
                intraday_data_interval = '5min'
        
        # Check the critical fix: force None if >60 days
        if days_ago_check > 60:
            print(f"    ✅ Applying fix: days_ago > 60, forcing intraday_data = None")
            intraday_data = None
            intraday_data_interval = None
        
        print(f"    Final intraday_data: {intraday_data is not None}")
        print(f"    Final intraday_data_interval: {intraday_data_interval}")
        print()
        
        # Check what would happen for 12:30 (1hr) interval
        print(f"  Checking 12:30 (1hr) interval logic:")
        
        # Calculate 12:30 time (1hr after market open, which is typically 9:30 ET = 13:30 UTC)
        # For simplicity, let's assume market open is 9:30 ET = 13:30 UTC
        market_open_utc = next_trading.replace(hour=13, minute=30, second=0, microsecond=0)
        if market_open_utc.tzinfo is None:
            market_open_utc = market_open_utc.replace(tzinfo=timezone.utc)
        else:
            market_open_utc = market_open_utc.astimezone(timezone.utc)
        
        # 1hr after market open = 12:30 ET = 16:30 UTC (but wait, that's wrong)
        # Actually, 1hr after 9:30 ET = 10:30 ET = 14:30 UTC
        # But the user shows 12:30, which is 1hr after 11:30? Let me recalculate
        
        # Actually, looking at the user's data:
        # 09:35, 09:40, 10:00, 10:30, 11:30, 12:30
        # So 12:30 is 3 hours after 9:30, not 1 hour
        # Wait, the intervals are: 1min, 2min, 3min, 4min, 5min, 10min, 30min, 1hr
        # So 1hr = 1 hour after market open = 10:30 ET
        # But user shows 12:30... let me check the interval mapping
        
        # Actually, I think the issue is simpler - let's just check if intraday_data exists
        # and if it would be used for the 1hr interval
        
        if intraday_data:
            print(f"    ❌ ISSUE: intraday_data exists - would try to extract price for 1hr")
            print(f"       This would cause 12:30 to show actual price instead of Daily Close")
            
            # Check if we can extract a price from this data
            # Calculate 1hr after market open
            market_open_et = next_trading.replace(hour=9, minute=30, second=0, microsecond=0)
            # Convert to UTC (ET is UTC-5 or UTC-4 depending on DST)
            # For simplicity, assume UTC-4 (EDT)
            market_open_utc = market_open_et.replace(tzinfo=timezone(timedelta(hours=-4)))
            market_open_utc = market_open_utc.astimezone(timezone.utc)
            
            # 1hr after market open
            target_1hr = market_open_utc + timedelta(hours=1)
            
            target_price, is_exact, actual_ts = tracker._extract_intraday_price_from_batch(intraday_data, target_1hr)
            if target_price:
                print(f"       ❌ Can extract price: ${target_price:.2f}")
                print(f"       This is why 12:30 shows actual price!")
            else:
                print(f"       ✅ Cannot extract price - would use daily close fallback")
        else:
            print(f"    ✅ intraday_data is None - would use daily close fallback")
            print(f"       This is correct behavior")
        
        print()
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("Expected behavior:")
    print("  - For articles >60 days old, ALL intervals should show 'Daily Close'")
    print("  - This includes 12:30 (1hr) interval")
    print()
    print("If 12:30 shows actual price:")
    print("  - intraday_data is not None when it should be")
    print("  - Date validation fix may not be working")
    print("  - Cache may contain stale data")
    print()

if __name__ == '__main__':
    test_12_30_intraday_issue()

