#!/usr/bin/env python3
"""
Unit test to simulate the exact JavaScript logic for auto-loading events
and identify why the button is still showing.
"""

import sys
from datetime import datetime, timezone

def test_javascript_auto_load_logic():
    """Simulate the exact JavaScript logic from templates/index.html"""
    print("=" * 80)
    print("JAVASCRIPT AUTO-LOAD LOGIC SIMULATION")
    print("=" * 80)
    print()
    
    # Simulate a stock object as it would appear in JavaScript
    # Based on backend structure from main.py line 4096-4101
    mock_stock = {
        'ticker': 'AAPL',
        'target_date': '2026-01-01',  # Today
        'bearish_date': '2025-12-31',
        'earnings_dividends': {
            'events_during': [],
            'next_events': [],
            'has_events_during': False,
            'has_next_events': False
            # NOTE: 'next_events_loaded' is NOT in the initial structure!
        }
    }
    
    print("Mock Stock Object:")
    print(f"  ticker: {mock_stock['ticker']}")
    print(f"  target_date: {mock_stock['target_date']}")
    print(f"  bearish_date: {mock_stock['bearish_date']}")
    print(f"  earnings_dividends: {mock_stock['earnings_dividends']}")
    print(f"  earnings_dividends.next_events_loaded: {mock_stock['earnings_dividends'].get('next_events_loaded', 'UNDEFINED')}")
    print()
    
    # Simulate JavaScript condition from line 3716
    # if (!stock.earnings_dividends || !stock.earnings_dividends.next_events_loaded) {
    print("=" * 80)
    print("TESTING CONDITION: if (!stock.earnings_dividends || !stock.earnings_dividends.next_events_loaded)")
    print("=" * 80)
    print()
    
    earnings_dividends = mock_stock['earnings_dividends']
    next_events_loaded = earnings_dividends.get('next_events_loaded')
    
    print(f"stock.earnings_dividends: {earnings_dividends}")
    print(f"!stock.earnings_dividends: {not earnings_dividends}")
    print(f"stock.earnings_dividends.next_events_loaded: {next_events_loaded}")
    print(f"!stock.earnings_dividends.next_events_loaded: {not next_events_loaded}")
    print()
    
    condition_result = (not earnings_dividends) or (not next_events_loaded)
    print(f"Condition Result: {condition_result}")
    print()
    
    if condition_result:
        print("✅ Condition PASSES - should enter auto-load block")
        print()
        
        # Simulate date comparison from lines 3718-3725
        print("=" * 80)
        print("TESTING DATE COMPARISON: if (targetDateStr >= todayStr)")
        print("=" * 80)
        print()
        
        target_date_str = mock_stock['target_date']  # "2026-01-01"
        
        # Simulate JavaScript: const today = new Date();
        # In JavaScript, new Date() uses LOCAL timezone
        today = datetime.now()  # Local time (simulating JavaScript behavior)
        today_str = f"{today.year}-{str(today.month).zfill(2)}-{str(today.day).zfill(2)}"
        
        print(f"targetDateStr: {target_date_str}")
        print(f"today (local): {today.isoformat()}")
        print(f"todayStr: {today_str}")
        print()
        
        date_comparison = target_date_str >= today_str
        print(f"targetDateStr >= todayStr: {target_date_str} >= {today_str} = {date_comparison}")
        print()
        
        if date_comparison:
            print("✅ Date comparison PASSES - should call loadStockNextEvents()")
            print()
            print("=" * 80)
            print("CONCLUSION")
            print("=" * 80)
            print("The logic SHOULD work correctly!")
            print("If the button is still showing, possible issues:")
            print("  1. JavaScript error preventing execution (check browser console)")
            print("  2. The condition is evaluated before stock data is loaded")
            print("  3. The setTimeout delay (200ms) might not be enough")
            print("  4. There might be a race condition")
            return True
        else:
            print("❌ Date comparison FAILS - will NOT call loadStockNextEvents()")
            print()
            print("=" * 80)
            print("PROBLEM IDENTIFIED")
            print("=" * 80)
            print(f"Target date: {target_date_str}")
            print(f"Today (local): {today_str}")
            print(f"Comparison: {target_date_str} >= {today_str} = {date_comparison}")
            print()
            print("This suggests a timezone issue!")
            print("JavaScript's new Date() uses local timezone.")
            print("If the user is in a timezone where it's still yesterday,")
            print("the comparison might fail.")
            return False
    else:
        print("❌ Condition FAILS - will NOT enter auto-load block")
        print()
        print("=" * 80)
        print("PROBLEM IDENTIFIED")
        print("=" * 80)
        print("The condition (!stock.earnings_dividends || !stock.earnings_dividends.next_events_loaded)")
        print("is evaluating to FALSE, which means:")
        print(f"  - stock.earnings_dividends exists: {earnings_dividends is not None}")
        print(f"  - stock.earnings_dividends.next_events_loaded: {next_events_loaded}")
        print()
        if next_events_loaded:
            print("⚠️  next_events_loaded is already TRUE!")
            print("   This means the backend might be setting it to True initially,")
            print("   or it's being set somewhere else before this check.")
        return False
    
    print()
    return False

def test_edge_cases():
    """Test edge cases that might cause issues"""
    print("=" * 80)
    print("EDGE CASE TESTS")
    print("=" * 80)
    print()
    
    # Test Case 1: earnings_dividends is null
    print("Test 1: earnings_dividends is null")
    stock1 = {'earnings_dividends': None, 'target_date': '2026-01-01'}
    condition1 = (not stock1['earnings_dividends']) or (not stock1['earnings_dividends'].get('next_events_loaded') if stock1['earnings_dividends'] else True)
    print(f"  Condition: {condition1}")
    print(f"  Should enter block: {condition1}")
    print()
    
    # Test Case 2: earnings_dividends is undefined (doesn't exist)
    print("Test 2: earnings_dividends is undefined")
    stock2 = {'target_date': '2026-01-01'}  # No earnings_dividends key
    condition2 = ('earnings_dividends' not in stock2) or (not stock2.get('earnings_dividends', {}).get('next_events_loaded'))
    print(f"  Condition: {condition2}")
    print(f"  Should enter block: {condition2}")
    print()
    
    # Test Case 3: earnings_dividends exists but next_events_loaded is explicitly False
    print("Test 3: earnings_dividends exists, next_events_loaded = False")
    stock3 = {
        'earnings_dividends': {'next_events_loaded': False},
        'target_date': '2026-01-01'
    }
    condition3 = (not stock3['earnings_dividends']) or (not stock3['earnings_dividends'].get('next_events_loaded'))
    print(f"  Condition: {condition3}")
    print(f"  Should enter block: {condition3}")
    print()
    
    # Test Case 4: earnings_dividends exists and next_events_loaded is True
    print("Test 4: earnings_dividends exists, next_events_loaded = True")
    stock4 = {
        'earnings_dividends': {'next_events_loaded': True},
        'target_date': '2026-01-01'
    }
    condition4 = (not stock4['earnings_dividends']) or (not stock4['earnings_dividends'].get('next_events_loaded'))
    print(f"  Condition: {condition4}")
    print(f"  Should enter block: {condition4}")
    print(f"  ⚠️  This should NOT enter block (events already loaded)")
    print()

if __name__ == "__main__":
    success1 = test_javascript_auto_load_logic()
    print()
    test_edge_cases()
    sys.exit(0 if success1 else 1)

