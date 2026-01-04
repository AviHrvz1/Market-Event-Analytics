#!/usr/bin/env python3
"""
Test the exact UI scenario to debug why Next Events is empty
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_ui_scenario():
    """Test exact scenario from UI"""
    print("=" * 80)
    print("UI SCENARIO TEST - Next Events Debug")
    print("=" * 80)
    print()
    
    # Exact parameters from image
    bearish_date = datetime(2025, 11, 17, tzinfo=timezone.utc)  # 17/11/2025
    target_date = datetime(2025, 12, 29, tzinfo=timezone.utc)   # 29/12/2025
    industry = "Technology"
    filter_type = "bearish"
    pct_threshold = -5.0
    
    print(f"📅 Bullish/Bearish Date: {bearish_date.date()}")
    print(f"📅 Target Date: {target_date.date()}")
    print(f"🏭 Industry: {industry}")
    print(f"🔍 Filter Type: {filter_type}")
    print(f"📊 Min % Change: {pct_threshold}%")
    print()
    print(f"Looking for Next Events from {target_date.date()} to {(target_date.date() + timedelta(days=60))}")
    print()
    
    tracker = LayoffTracker()
    
    # Run the full analysis
    print("🚀 Running full analysis...")
    results, logs = tracker.get_bearish_analytics(
        bearish_date=bearish_date,
        target_date=target_date,
        industry=industry,
        filter_type=filter_type,
        pct_threshold=pct_threshold
    )
    
    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Found {len(results)} stocks")
    print()
    
    # Check earnings/dividends data for each result
    stocks_with_next_events = 0
    stocks_with_events_during = 0
    
    for i, stock in enumerate(results[:5], 1):  # Check first 5
        ticker = stock.get('ticker', 'N/A')
        earnings_data = stock.get('earnings_dividends', {})
        
        events_during = earnings_data.get('events_during', [])
        next_events = earnings_data.get('next_events', [])
        
        print(f"{i}. {ticker} ({stock.get('company_name', 'N/A')})")
        print(f"   Events During Period: {len(events_during)}")
        if events_during:
            stocks_with_events_during += 1
            for event in events_during[:2]:
                print(f"     - {event.get('name', 'N/A')} on {event.get('date', 'N/A')}")
        
        print(f"   Next Events: {len(next_events)}")
        if next_events:
            stocks_with_next_events += 1
            for event in next_events:
                print(f"     - {event.get('name', 'N/A')} on {event.get('date', 'N/A')} ({event.get('form', 'N/A')})")
        else:
            print(f"     ⚠️  No next events found")
            # Debug: Test NASDAQ API directly for this ticker
            print(f"     🔍 Testing NASDAQ API directly for {ticker}...")
            nasdaq_result = tracker._check_earnings_dividends_nasdaq(
                ticker, bearish_date, target_date, future_days=60
            )
            print(f"        NASDAQ returned {len(nasdaq_result.get('next_events', []))} next events")
            if nasdaq_result.get('next_events'):
                for event in nasdaq_result['next_events']:
                    print(f"          - {event.get('name', 'N/A')} on {event.get('date', 'N/A')}")
        print()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total stocks: {len(results)}")
    print(f"Stocks with events during period: {stocks_with_events_during}")
    print(f"Stocks with next events: {stocks_with_next_events}")
    print()
    
    if stocks_with_next_events == 0:
        print("⚠️  ISSUE: No stocks have next events")
        print("   Possible reasons:")
        print("   1. NASDAQ API not being called")
        print("   2. No scheduled earnings in the 60-day window")
        print("   3. NASDAQ API failing silently")
        print("   4. Date range issue")
    else:
        print("✅ Next events are being found!")
    
    return stocks_with_next_events > 0

if __name__ == "__main__":
    success = test_ui_scenario()
    sys.exit(0 if success else 1)

