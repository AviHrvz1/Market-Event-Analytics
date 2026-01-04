#!/usr/bin/env python3
"""
Unit test to verify if the previous trading day is visible in the graph
when the graph only shows 3 days before the bearish date.
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_previous_trading_day_visibility():
    """Test if previous trading day is within 3 calendar days of bearish date"""
    print("=" * 80)
    print("TEST: Previous Trading Day Visibility in Graph")
    print("=" * 80)
    print()
    
    # Test cases: bearish dates that might have issues
    test_cases = [
        datetime(2025, 12, 18, 0, 0, 0, tzinfo=timezone.utc),  # Dec 18, 2025 (Wednesday)
        datetime(2025, 12, 16, 0, 0, 0, tzinfo=timezone.utc),  # Dec 16, 2025 (Monday - previous day is Friday, 3 days back)
        datetime(2025, 12, 19, 0, 0, 0, tzinfo=timezone.utc),  # Dec 19, 2025 (Thursday)
        datetime(2025, 12, 20, 0, 0, 0, tzinfo=timezone.utc),  # Dec 20, 2025 (Friday)
    ]
    
    tracker = LayoffTracker()
    
    issues_found = []
    all_ok = True
    
    for bearish_date in test_cases:
        print(f"Testing bearish date: {bearish_date.strftime('%Y-%m-%d (%A)')}")
        print("-" * 80)
        
        # Calculate 3 days before (current graph range)
        three_days_before = bearish_date - timedelta(days=3)
        
        # Get a sample ticker to test with
        companies = tracker._get_large_cap_companies_with_options()
        if not companies:
            print("   ⚠️  No companies found, skipping...")
            continue
            
        test_ticker = list(companies.keys())[0]
        print(f"   Using ticker: {test_ticker}")
        
        # Fetch price history starting 7 days before to find previous trading day
        graph_start_date = bearish_date - timedelta(days=7)
        target_date = bearish_date + timedelta(days=5)  # Just need some range
        
        try:
            price_history = tracker.get_stock_price_history(test_ticker, graph_start_date, target_date)
            
            if not price_history:
                print(f"   ⚠️  No price history found for {test_ticker}, skipping...")
                continue
            
            # Find previous trading day
            bearish_date_str = bearish_date.strftime('%Y-%m-%d')
            prev_trading_day = None
            prev_trading_day_date = None
            bearish_price = None
            
            # Sort by date
            sorted_history = sorted(price_history, key=lambda x: x.get('date', ''))
            
            for entry in sorted_history:
                entry_date = entry.get('date', '')
                price = entry.get('price')
                
                if entry_date == bearish_date_str:
                    bearish_price = price
                elif entry_date < bearish_date_str:
                    # This is a previous trading day (use the most recent one)
                    if prev_trading_day is None:
                        prev_trading_day = price
                        prev_trading_day_date = entry_date
            
            if prev_trading_day is None or bearish_price is None:
                print(f"   ⚠️  Could not find previous trading day or bearish date price")
                continue
            
            # Parse previous trading day date
            prev_date = datetime.strptime(prev_trading_day_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            
            # Calculate calendar days difference
            days_diff = (bearish_date - prev_date).days
            
            # Check if previous trading day is within 3 calendar days
            is_visible = prev_date >= three_days_before
            
            # Calculate percentage change
            pct_change = ((bearish_price - prev_trading_day) / prev_trading_day) * 100
            
            print(f"   Previous trading day: {prev_trading_day_date} ({days_diff} calendar days before)")
            print(f"   Graph start date (3 days before): {three_days_before.strftime('%Y-%m-%d')}")
            print(f"   Previous day price: ${prev_trading_day:.2f}")
            print(f"   Bearish date price: ${bearish_price:.2f}")
            print(f"   Percentage change: {pct_change:+.2f}%")
            print(f"   Previous day visible in graph (3-day range): {'✅ YES' if is_visible else '❌ NO'}")
            
            if not is_visible:
                all_ok = False
                issues_found.append({
                    'bearish_date': bearish_date.strftime('%Y-%m-%d'),
                    'prev_trading_day': prev_trading_day_date,
                    'days_diff': days_diff,
                    'pct_change': pct_change,
                    'ticker': test_ticker
                })
                print(f"   ⚠️  ISSUE: Previous trading day is {days_diff} calendar days back, but graph only shows 3 days!")
                print(f"      The {pct_change:+.2f}% drop will NOT be visible on the graph.")
            else:
                print(f"   ✅ OK: Previous trading day is visible in the graph.")
            
            print()
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            print()
            continue
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    if all_ok:
        print("✅ All test cases passed: Previous trading day is visible in 3-day graph range")
    else:
        print(f"❌ Found {len(issues_found)} case(s) where previous trading day is NOT visible:")
        print()
        for issue in issues_found:
            print(f"   • Bearish Date: {issue['bearish_date']}")
            print(f"     Previous Trading Day: {issue['prev_trading_day']} ({issue['days_diff']} days back)")
            print(f"     Percentage Change: {issue['pct_change']:+.2f}%")
            print(f"     Ticker: {issue['ticker']}")
            print()
        
        print("RECOMMENDATION:")
        print("   Extend the graph range from 3 days to 7 days before the bearish date")
        print("   to ensure the previous trading day is always visible.")
        print()
        print("   Changes needed:")
        print("   1. In main.py line ~3547: Change timedelta(days=3) to timedelta(days=7)")
        print("   2. In templates/index.html line ~3506: Change setDate(-3) to setDate(-7)")
    
    return all_ok

if __name__ == "__main__":
    success = test_previous_trading_day_visibility()
    sys.exit(0 if success else 1)

