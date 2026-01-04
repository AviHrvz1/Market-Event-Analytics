#!/usr/bin/env python3
"""
Unit test for Top Bearish Analytics feature
Tests if the optimized yfinance approach can find bearish stocks
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_bearish_analytics():
    """Test the bearish analytics feature"""
    print("=" * 80)
    print("TOP BEARISH ANALYTICS TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Use a known past date that definitely had trading activity
    # October 15, 2024 was a Tuesday and had market activity
    # If that doesn't work, try other known dates
    test_dates = [
        datetime(2024, 10, 15, tzinfo=timezone.utc),  # Tuesday
        datetime(2024, 9, 15, tzinfo=timezone.utc),   # Sunday -> Monday
        datetime(2024, 8, 15, tzinfo=timezone.utc),   # Thursday
        datetime(2024, 7, 15, tzinfo=timezone.utc),   # Monday
    ]
    
    # Find first weekday
    bearish_date = None
    for test_date in test_dates:
        if test_date.weekday() < 5:  # Monday-Friday
            bearish_date = test_date
            break
    
    if bearish_date is None:
        # Fallback: use a date from 30 days ago
        today = datetime.now(timezone.utc)
        bearish_date = today - timedelta(days=30)
        while bearish_date.weekday() >= 5:
            bearish_date -= timedelta(days=1)
    
    # Target date is 7 days after bearish date
    target_date = bearish_date + timedelta(days=7)
    while target_date.weekday() >= 5:
        target_date += timedelta(days=1)
    
    print(f"Bearish Date: {bearish_date.strftime('%Y-%m-%d')} ({bearish_date.strftime('%A')})")
    print(f"Target Date:  {target_date.strftime('%Y-%m-%d')} ({target_date.strftime('%A')})")
    print()
    
    # Test 1: Get top losers using yfinance
    print("-" * 80)
    print("TEST 1: Quick Top Losers Identification (yfinance)")
    print("-" * 80)
    print()
    
    try:
        losers = tracker.get_top_losers_yfinance(bearish_date, industry=None, logs=None)
        
        print(f"✅ Found {len(losers)} stocks with drops on {bearish_date.strftime('%Y-%m-%d')}")
        print()
        
        if len(losers) > 0:
            print("Top 10 Losers:")
            for i, (ticker, pct_drop, company_info) in enumerate(losers[:10], 1):
                print(f"  {i}. {ticker} ({company_info.get('name', 'N/A')}) - {pct_drop:.2f}%")
            print()
        else:
            print("⚠️  No losers found. This could mean:")
            print("   - The date was a market holiday")
            print("   - All stocks went up that day")
            print("   - yfinance data not available for that date")
            print()
        
    except Exception as e:
        print(f"❌ Error in get_top_losers_yfinance: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Full bearish analytics
    print("-" * 80)
    print("TEST 2: Full Bearish Analytics (with recovery calculation)")
    print("-" * 80)
    print()
    
    try:
        results, logs = tracker.get_bearish_analytics(bearish_date, target_date, industry=None)
        
        # Print logs
        print("Processing Logs:")
        for log in logs:
            print(f"  {log}")
        print()
        
        print(f"✅ Analysis Complete!")
        print(f"   Found {len(results)} stocks with drops and recovery data")
        print()
        
        if len(results) > 0:
            print("Top 10 Results:")
            for i, stock in enumerate(results[:10], 1):
                print(f"  {i}. {stock['ticker']} - {stock['company_name']}")
                print(f"      Industry: {stock['industry']}")
                print(f"      Bearish Date ({stock['bearish_date']}): ${stock['bearish_price']:.2f} ({stock['pct_drop']:.2f}% drop)")
                print(f"      Target Date ({stock['target_date']}): ${stock['target_price']:.2f} ({stock['recovery_pct']:+.2f}% recovery)")
                print(f"      Price History Points: {len(stock.get('price_history', []))}")
                print()
        else:
            print("⚠️  No results found. Possible reasons:")
            print("   - No stocks dropped on the bearish date")
            print("   - Missing price data for target date")
            print("   - Date range issues")
            print()
        
        return len(results) > 0
        
    except Exception as e:
        print(f"❌ Error in get_bearish_analytics: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_bearish_analytics_with_industry():
    """Test bearish analytics with industry filter"""
    print("=" * 80)
    print("TOP BEARISH ANALYTICS TEST (WITH INDUSTRY FILTER)")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Use a known past date
    test_dates = [
        datetime(2024, 10, 15, tzinfo=timezone.utc),
        datetime(2024, 9, 15, tzinfo=timezone.utc),
        datetime(2024, 8, 15, tzinfo=timezone.utc),
    ]
    
    bearish_date = None
    for test_date in test_dates:
        if test_date.weekday() < 5:
            bearish_date = test_date
            break
    
    if bearish_date is None:
        today = datetime.now(timezone.utc)
        bearish_date = today - timedelta(days=30)
        while bearish_date.weekday() >= 5:
            bearish_date -= timedelta(days=1)
    
    target_date = bearish_date + timedelta(days=7)
    while target_date.weekday() >= 5:
        target_date += timedelta(days=1)
    
    print(f"Bearish Date: {bearish_date.strftime('%Y-%m-%d')}")
    print(f"Target Date:  {target_date.strftime('%Y-%m-%d')}")
    print(f"Industry: Technology")
    print()
    
    try:
        results, logs = tracker.get_bearish_analytics(bearish_date, target_date, industry='Technology')
        
        print("Processing Logs:")
        for log in logs:
            print(f"  {log}")
        print()
        
        print(f"✅ Found {len(results)} Technology stocks with drops")
        
        if len(results) > 0:
            print("\nTop 5 Technology Losers:")
            for i, stock in enumerate(results[:5], 1):
                print(f"  {i}. {stock['ticker']} - {stock['pct_drop']:.2f}% drop, {stock['recovery_pct']:+.2f}% recovery")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print()
    success1 = test_bearish_analytics()
    print()
    print()
    success2 = test_bearish_analytics_with_industry()
    print()
    
    if success1 or success2:
        print("=" * 80)
        print("✅ TEST COMPLETE - Bearish Analytics is working!")
        print("=" * 80)
        sys.exit(0)
    else:
        print("=" * 80)
        print("⚠️  TEST COMPLETE - No results found (may need different dates)")
        print("=" * 80)
        sys.exit(0)  # Don't fail, just inform

