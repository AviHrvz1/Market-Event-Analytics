#!/usr/bin/env python3
"""
Test NASDAQ integration with actual dates
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_nasdaq_integration():
    """Test NASDAQ earnings calendar integration"""
    print("=" * 80)
    print("NASDAQ INTEGRATION TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Test with actual dates
    ticker = 'AAPL'
    bearish_date = datetime(2025, 3, 11, tzinfo=timezone.utc)
    target_date = datetime(2025, 12, 29, tzinfo=timezone.utc)
    
    print(f"Ticker: {ticker}")
    print(f"Bearish Date: {bearish_date.date()}")
    print(f"Target Date: {target_date.date()}")
    print(f"Looking for next events up to: {(target_date.date() + timedelta(days=60))}")
    print()
    
    # Test NASDAQ function
    print("Testing NASDAQ API...")
    nasdaq_result = tracker._check_earnings_dividends_nasdaq(ticker, bearish_date, target_date, future_days=60)
    
    print()
    print("=" * 80)
    print("NASDAQ RESULTS")
    print("=" * 80)
    print(f"Next Events: {len(nasdaq_result['next_events'])}")
    for event in nasdaq_result['next_events']:
        print(f"  - {event['name']} on {event['date']}")
    print()
    
    # Test combined (SEC + NASDAQ)
    print("Testing Combined (SEC + NASDAQ)...")
    sec_result = tracker._check_earnings_dividends_sec(ticker, bearish_date, target_date, future_days=60)
    
    # Merge results
    combined_result = sec_result.copy()
    if nasdaq_result.get('next_events'):
        combined_result['next_events'].extend(nasdaq_result['next_events'])
        combined_result['has_next_events'] = len(combined_result['next_events']) > 0
        # Remove duplicates
        seen_dates = set()
        unique_events = []
        for event in sorted(combined_result['next_events'], key=lambda x: x['date']):
            if event['date'] not in seen_dates:
                seen_dates.add(event['date'])
                unique_events.append(event)
        combined_result['next_events'] = unique_events
    
    print()
    print("=" * 80)
    print("COMBINED RESULTS (SEC + NASDAQ)")
    print("=" * 80)
    print(f"Events During Period: {len(combined_result['events_during'])}")
    for event in combined_result['events_during'][:3]:
        print(f"  - {event['name']} on {event['date']}")
    print()
    print(f"Next Events: {len(combined_result['next_events'])}")
    for event in combined_result['next_events']:
        print(f"  - {event['name']} on {event['date']} ({event.get('form', 'N/A')})")
    print()
    
    if len(combined_result['next_events']) > 0:
        print("✅ SUCCESS: Found next events!")
        return True
    else:
        print("⚠️  No next events found (may be expected if no scheduled earnings)")
        return False

if __name__ == "__main__":
    success = test_nasdaq_integration()
    sys.exit(0 if success else 1)

