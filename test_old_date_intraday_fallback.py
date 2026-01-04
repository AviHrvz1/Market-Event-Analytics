#!/usr/bin/env python3
"""
Unit test to diagnose why old articles (>60 days) show mixed daily close and intraday prices
Tests specific cases: AVXL (Oct 2, 2025), LLY (Aug 26, 2025), ARGX (Aug 25, 2025)
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker
from config import LOOKBACK_DAYS

def test_old_date_intraday_fallback():
    """Test that articles >60 days old use daily close fallback for ALL intervals"""
    
    print("=" * 80)
    print("OLD DATE INTRADAY FALLBACK DIAGNOSIS")
    print("=" * 80)
    print()
    
    # Test cases from user report
    test_cases = [
        {
            'company': 'Anavex Life Sciences Corp',
            'ticker': 'AVXL',
            'article_date': '2025-10-02 03:00:00',
            'expected_next_trading': '2025-10-03',
            'days_ago': None  # Will calculate
        },
        {
            'company': 'Eli Lilly and Company',
            'ticker': 'LLY',
            'article_date': '2025-08-26 03:00:00',
            'expected_next_trading': '2025-08-27',
            'days_ago': None
        },
        {
            'company': 'argenx SE',
            'ticker': 'ARGX',
            'article_date': '2025-08-25 03:00:00',
            'expected_next_trading': '2025-08-26',
            'days_ago': None
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
        
        # Calculate days ago
        days_ago = (now - article_dt).days
        case['days_ago'] = days_ago
        
        print(f"  Article Date: {article_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"  Days Ago: {days_ago} days")
        print(f"  Expected Next Trading Day: {case['expected_next_trading']}")
        print()
        
        # Check if date is >60 days (Prixe.io intraday limit)
        if days_ago > 60:
            print(f"  ✅ Date is >60 days old - intraday data should NOT be fetched")
        else:
            print(f"  ⚠️  Date is within 60 days - intraday data MAY be fetched")
        print()
        
        # Check cache for intraday data
        next_trading_day = article_dt + timedelta(days=1)
        # Skip weekends
        while next_trading_day.weekday() >= 5:  # Saturday = 5, Sunday = 6
            next_trading_day += timedelta(days=1)
        
        date_str = next_trading_day.strftime('%Y-%m-%d')
        cache_keys_to_check = [
            f"prixe_intraday_day_{case['ticker']}_{date_str}_1min",
            f"prixe_intraday_day_{case['ticker']}_{date_str}_5min",
        ]
        
        print(f"  Checking cache for next trading day ({date_str}):")
        cached_intraday_found = False
        for cache_key in cache_keys_to_check:
            if cache_key in tracker.stock_price_cache:
                cached_data = tracker.stock_price_cache[cache_key]
                print(f"    ❌ FOUND cached intraday data: {cache_key}")
                print(f"       This should NOT be used for dates >60 days old!")
                cached_intraday_found = True
            else:
                print(f"    ✅ No cached intraday data: {cache_key}")
        
        if cached_intraday_found:
            print(f"  ⚠️  ISSUE: Cached intraday data exists - may be used incorrectly!")
        print()
        
        # Simulate what calculate_stock_changes would do
        print(f"  Simulating calculate_stock_changes() for this article:")
        
        # Create a mock layoff dict
        layoff = {
            'company_name': case['company'],
            'stock_ticker': case['ticker'],
            'datetime': article_dt,
            'publishedAt': article_dt.isoformat()
        }
        
        # Check if intraday data would be fetched
        article_day = article_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        if article_day.tzinfo is None:
            article_day_utc = article_day.replace(tzinfo=timezone.utc)
        else:
            article_day_utc = article_day.astimezone(timezone.utc)
        
        days_ago_check = (now - article_day_utc).days
        print(f"    Days ago check: {days_ago_check} days")
        
        if days_ago_check <= 60:
            print(f"    ⚠️  Code would TRY to fetch intraday data (within 60 days)")
            print(f"    ⚠️  But article is {days_ago} days old - mismatch!")
        else:
            print(f"    ✅ Code would NOT fetch intraday data (>60 days)")
        
        # Check what _fetch_intraday_data_for_day would return
        print(f"    Testing _fetch_intraday_data_for_day():")
        intraday_data_1min = tracker._fetch_intraday_data_for_day(case['ticker'], next_trading_day, interval='1min')
        intraday_data_5min = tracker._fetch_intraday_data_for_day(case['ticker'], next_trading_day, interval='5min')
        
        if intraday_data_1min:
            print(f"      ❌ 1min intraday data returned (should be None for >60 days)")
            print(f"         This means cached data exists or date check failed!")
        else:
            print(f"      ✅ 1min intraday data correctly returned None")
        
        if intraday_data_5min:
            print(f"      ❌ 5min intraday data returned (should be None for >60 days)")
            print(f"         This means cached data exists or date check failed!")
        else:
            print(f"      ✅ 5min intraday data correctly returned None")
        
        # Simulate the actual calculate_stock_changes logic for market closed articles
        print(f"    Simulating market-closed article logic:")
        print(f"      Code checks: days_ago <= 60 for next_trading_day")
        next_day_utc = next_trading_day.replace(tzinfo=timezone.utc) if next_trading_day.tzinfo is None else next_trading_day.astimezone(timezone.utc)
        next_days_ago = (now - next_day_utc).days
        print(f"      Next trading day days ago: {next_days_ago} days")
        
        if next_days_ago <= 60:
            print(f"      ⚠️  Code WOULD try to fetch intraday data (next day within 60 days)")
        else:
            print(f"      ✅ Code would NOT fetch intraday data (next day >60 days)")
        
        # Check if there's any batch cache that might contain this data
        print(f"    Checking batch cache for overlapping dates:")
        batch_cache_found = False
        for batch_key in tracker.stock_price_cache.keys():
            if f"prixe_intraday_batch_{case['ticker']}_" in batch_key:
                print(f"      Found batch cache: {batch_key}")
                batch_cache_found = True
                # Try to extract date range
                try:
                    parts = batch_key.replace(f"prixe_intraday_batch_{case['ticker']}_", "").split("_")
                    if len(parts) >= 3:
                        batch_start_str = parts[0]
                        batch_end_str = parts[1]
                        batch_start = datetime.strptime(batch_start_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                        batch_end = datetime.strptime(batch_end_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                        if batch_start <= next_day_utc <= batch_end:
                            batch_days_ago = (now - next_day_utc).days
                            print(f"        ⚠️  Batch cache contains next trading day ({next_day_utc.date()})")
                            print(f"        ⚠️  Days ago: {batch_days_ago} days")
                            if batch_days_ago > 60:
                                print(f"        ❌ ISSUE: Batch cache contains data >60 days old - should be ignored!")
                            else:
                                print(f"        ✅ Batch cache data is within 60 days")
                except:
                    pass
        
        if not batch_cache_found:
            print(f"      ✅ No batch cache found")
        
        print()
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("Expected behavior for articles >60 days old:")
    print("  - ALL intervals (1min, 2min, 3min, 4min, 5min, 10min, 30min, 1hr) should show 'Daily Close'")
    print("  - Daily close (16:00) should show actual price")
    print("  - NO intraday data should be fetched or used")
    print()
    print("If 12:30 (1hr) shows actual price instead of 'Daily Close':")
    print("  - Cached intraday data may be used incorrectly")
    print("  - Date validation may not be checking cache before use")
    print("  - Batch cache may contain old data")
    print()

if __name__ == '__main__':
    test_old_date_intraday_fallback()

