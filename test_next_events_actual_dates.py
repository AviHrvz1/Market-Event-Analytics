#!/usr/bin/env python3
"""
Test next events with actual dates from the user's scenario
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_next_events_actual():
    """Test with actual dates: target_date = 2025-12-29"""
    print("=" * 80)
    print("NEXT EVENTS TEST - Actual Dates")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Actual dates from user's scenario
    ticker = 'AAPL'
    bearish_date = datetime(2025, 3, 11, tzinfo=timezone.utc)
    target_date = datetime(2025, 12, 29, tzinfo=timezone.utc)
    
    print(f"Ticker: {ticker}")
    print(f"Bearish Date: {bearish_date.date()}")
    print(f"Target Date: {target_date.date()}")
    print(f"Looking for events after {target_date.date()} up to {(target_date.date() + timedelta(days=60))}")
    print()
    print("⚠️  NOTE: SEC EDGAR only has historical filings, not future scheduled events.")
    print("   If target_date is in the future, there may be no filings after it yet.")
    print()
    
    result = tracker._check_earnings_dividends_sec(ticker, bearish_date, target_date, future_days=60)
    
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()
    print(f"Events During Period ({bearish_date.date()} to {target_date.date}): {len(result['events_during'])}")
    for event in result['events_during']:
        print(f"  - {event['name']} on {event['date']}")
    print()
    print(f"Next Events (after {target_date.date()} up to {(target_date.date() + timedelta(days=60))}): {len(result['next_events'])}")
    if result['next_events']:
        for event in result['next_events']:
            print(f"  - {event['name']} on {event['date']}")
    else:
        print("  ⚠️  No next events found")
        print("     This is expected if target_date is in the future (2025-12-29)")
        print("     SEC EDGAR only has historical filings, not future scheduled events")
    print()
    
    # Check what the current date is
    from datetime import date
    today = date.today()
    print(f"Today's date: {today}")
    print(f"Target date: {target_date.date()}")
    if target_date.date() > today:
        print(f"  ⚠️  Target date is in the future - SEC EDGAR won't have filings after it yet")
    else:
        print(f"  ✅ Target date is in the past - should find filings if they exist")
    print()
    
    return len(result['next_events']) > 0

if __name__ == "__main__":
    success = test_next_events_actual()
    sys.exit(0 if success else 1)

