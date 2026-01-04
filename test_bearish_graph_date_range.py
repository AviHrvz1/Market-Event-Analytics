#!/usr/bin/env python3
"""
Unit test to verify if the previous trading day is visible in the graph
when the graph only shows 3 days before the bearish date.

This test uses date logic to simulate scenarios without requiring API calls.
"""

import sys
from datetime import datetime, timezone, timedelta

def is_weekend(date):
    """Check if a date is a weekend"""
    return date.weekday() >= 5  # Saturday = 5, Sunday = 6

def get_previous_trading_day(date):
    """Get the previous trading day (skip weekends)"""
    prev_day = date - timedelta(days=1)
    while is_weekend(prev_day):
        prev_day = prev_day - timedelta(days=1)
    return prev_day

def test_previous_trading_day_visibility():
    """Test if previous trading day is within 3 calendar days of bearish date"""
    print("=" * 80)
    print("TEST: Previous Trading Day Visibility in Graph (Date Logic Only)")
    print("=" * 80)
    print()
    
    # Test cases: bearish dates that might have issues
    # Format: (bearish_date, description)
    test_cases = [
        (datetime(2025, 12, 18, 0, 0, 0, tzinfo=timezone.utc), "Thursday (Dec 18) - prev day is Wednesday"),
        (datetime(2025, 12, 16, 0, 0, 0, tzinfo=timezone.utc), "Monday (Dec 16) - prev day is Friday (3 days back)"),
        (datetime(2025, 12, 19, 0, 0, 0, tzinfo=timezone.utc), "Friday (Dec 19) - prev day is Thursday"),
        (datetime(2025, 12, 22, 0, 0, 0, tzinfo=timezone.utc), "Monday (Dec 22) - prev day is Friday (3 days back)"),
        (datetime(2025, 12, 23, 0, 0, 0, tzinfo=timezone.utc), "Tuesday (Dec 23) - prev day is Monday"),
        (datetime(2025, 12, 15, 0, 0, 0, tzinfo=timezone.utc), "Sunday (Dec 15) - should use Friday as prev day"),
    ]
    
    issues_found = []
    all_ok = True
    
    for bearish_date, description in test_cases:
        print(f"Testing: {bearish_date.strftime('%Y-%m-%d (%A)')} - {description}")
        print("-" * 80)
        
        # Calculate 3 days before (current graph range)
        three_days_before = bearish_date - timedelta(days=3)
        
        # Get previous trading day
        prev_trading_day = get_previous_trading_day(bearish_date)
        
        # Calculate calendar days difference
        days_diff = (bearish_date - prev_trading_day).days
        
        # Check if previous trading day is within 3 calendar days
        is_visible = prev_trading_day >= three_days_before
        
        print(f"   Bearish date: {bearish_date.strftime('%Y-%m-%d (%A)')}")
        print(f"   Previous trading day: {prev_trading_day.strftime('%Y-%m-%d (%A)')}")
        print(f"   Calendar days difference: {days_diff} days")
        print(f"   Graph start date (3 days before): {three_days_before.strftime('%Y-%m-%d (%A)')}")
        print(f"   Previous day visible in graph (3-day range): {'✅ YES' if is_visible else '❌ NO'}")
        
        if not is_visible:
            all_ok = False
            issues_found.append({
                'bearish_date': bearish_date.strftime('%Y-%m-%d'),
                'bearish_day': bearish_date.strftime('%A'),
                'prev_trading_day': prev_trading_day.strftime('%Y-%m-%d'),
                'prev_day': prev_trading_day.strftime('%A'),
                'days_diff': days_diff,
                'graph_start': three_days_before.strftime('%Y-%m-%d')
            })
            print(f"   ⚠️  ISSUE: Previous trading day is {days_diff} calendar days back!")
            print(f"      Graph only shows 3 days before ({three_days_before.strftime('%Y-%m-%d')})")
            print(f"      But previous trading day is {prev_trading_day.strftime('%Y-%m-%d')}")
            print(f"      The drop percentage will NOT be visible on the graph.")
        else:
            print(f"   ✅ OK: Previous trading day is visible in the graph.")
        
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    if all_ok:
        print("✅ All test cases passed: Previous trading day is visible in 3-day graph range")
        print()
        print("However, this test only checks calendar days. In reality:")
        print("  - Market holidays can add extra days")
        print("  - Some stocks may have different trading schedules")
        print("  - It's safer to extend the range to 7 days to ensure visibility")
    else:
        print(f"❌ Found {len(issues_found)} case(s) where previous trading day is NOT visible:")
        print()
        for issue in issues_found:
            print(f"   • Bearish Date: {issue['bearish_date']} ({issue['bearish_day']})")
            print(f"     Previous Trading Day: {issue['prev_trading_day']} ({issue['prev_day']})")
            print(f"     Days Difference: {issue['days_diff']} calendar days")
            print(f"     Graph Start (3 days before): {issue['graph_start']}")
            print()
        
        print("=" * 80)
        print("RECOMMENDATION")
        print("=" * 80)
        print()
        print("Extend the graph range from 3 days to 7 days before the bearish date")
        print("to ensure the previous trading day is always visible, even when:")
        print("  - The bearish date is on a Monday (previous day is Friday, 3 days back)")
        print("  - There are market holidays")
        print("  - Weekends create gaps")
        print()
        print("Changes needed:")
        print("  1. In main.py line ~3547:")
        print("     Change: graph_start_date = bearish_date - timedelta(days=3)")
        print("     To:     graph_start_date = bearish_date - timedelta(days=7)")
        print()
        print("  2. In templates/index.html line ~3506:")
        print("     Change: threeDaysBefore.setDate(threeDaysBefore.getDate() - 3)")
        print("     To:     threeDaysBefore.setDate(threeDaysBefore.getDate() - 7)")
        print()
        print("This will ensure the previous trading day is always visible on the graph,")
        print("making the percentage drop clearly visible to users.")
    
    return all_ok

if __name__ == "__main__":
    success = test_previous_trading_day_visibility()
    sys.exit(0 if success else 1)

