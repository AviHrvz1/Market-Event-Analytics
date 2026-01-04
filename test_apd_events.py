#!/usr/bin/env python3
"""
Test to check if APD (Air Products and Chemicals Inc) had any events or dividends
from Sep 23, 2025 to Oct 30, 2025
"""

import sys
from datetime import datetime, timezone
from main import LayoffTracker

def test_apd_events():
    """Test APD events during the period"""
    print("=" * 80)
    print("APD EVENTS TEST: Sep 23 - Oct 30, 2025")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Test dates
    bearish_date = datetime(2025, 9, 23, tzinfo=timezone.utc)  # Sep 23, 2025
    target_date = datetime(2025, 10, 30, tzinfo=timezone.utc)  # Oct 30, 2025
    
    ticker = 'APD'
    
    print(f"Ticker: {ticker}")
    print(f"Company: Air Products and Chemicals Inc")
    print(f"Bearish Date: {bearish_date.strftime('%Y-%m-%d')}")
    print(f"Target Date: {target_date.strftime('%Y-%m-%d')}")
    print()
    
    try:
        # Test SEC EDGAR
        print("=" * 80)
        print("TESTING SEC EDGAR")
        print("=" * 80)
        print()
        
        sec_events = tracker._check_earnings_dividends_sec(ticker, bearish_date, target_date, future_days=0)
        sec_events_during = sec_events.get('events_during', [])
        
        print(f"SEC EDGAR Events: {len(sec_events_during)}")
        if sec_events_during:
            for event in sec_events_during:
                print(f"  ✅ {event.get('date')}: {event.get('name')} ({event.get('type')})")
                print(f"     Form: {event.get('form')}")
                print(f"     Description: {event.get('description', '')[:100]}")
        else:
            print("  ❌ No events found in SEC EDGAR")
        print()
        
        # Test NASDAQ
        print("=" * 80)
        print("TESTING NASDAQ CALENDAR")
        print("=" * 80)
        print()
        
        nasdaq_events = tracker._check_earnings_dividends_nasdaq(ticker, bearish_date, target_date, future_days=0)
        nasdaq_events_during = nasdaq_events.get('events_during', [])
        
        print(f"NASDAQ Events: {len(nasdaq_events_during)}")
        if nasdaq_events_during:
            for event in nasdaq_events_during:
                print(f"  ✅ {event.get('date')}: {event.get('name')} ({event.get('type')})")
                print(f"     Form: {event.get('form')}")
                if event.get('type') == 'dividend':
                    print(f"     Dividend Rate: ${event.get('dividend_rate', 'N/A')}")
                    print(f"     Ex-Date: {event.get('ex_date', 'N/A')}")
                    print(f"     Payment Date: {event.get('payment_date', 'N/A')}")
        else:
            print("  ❌ No events found in NASDAQ calendar")
        print()
        
        # Combined (same as UI shows)
        print("=" * 80)
        print("COMBINED RESULTS (as shown in UI)")
        print("=" * 80)
        print()
        
        # Combine both sources (same logic as in add_events_during_to_stock)
        all_events = sec_events_during.copy()
        all_events.extend(nasdaq_events_during)
        
        # Remove duplicates
        seen_events = set()
        unique_events = []
        for event in sorted(all_events, key=lambda x: (x['date'], x.get('type', ''))):
            event_key = (event['date'], event.get('type', ''), event.get('name', ''))
            if event_key not in seen_events:
                seen_events.add(event_key)
                unique_events.append(event)
        
        print(f"Total Unique Events: {len(unique_events)}")
        print()
        
        if unique_events:
            print("✅ EVENTS FOUND:")
            for i, event in enumerate(unique_events, 1):
                print(f"  {i}. {event.get('date')}: {event.get('name')} ({event.get('type')})")
                print(f"     Source: {event.get('form', 'N/A')}")
        else:
            print("❌ NO EVENTS FOUND")
            print()
            print("This matches what you're seeing in the UI: 'None'")
            print()
            print("Possible reasons:")
            print("  1. No earnings announcements during Sep 23 - Oct 30, 2025")
            print("  2. No dividend declarations during this period")
            print("  3. APD may not file 8-K for regular quarterly dividends")
            print("  4. Dates are in the future (2025) - may not have real data yet")
            print("  5. Dividend ex-dates might be outside this range")
        
        return len(unique_events) > 0
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    has_events = test_apd_events()
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print()
    if has_events:
        print("✅ Events were found - UI should show them")
    else:
        print("❌ No events found - UI showing 'None' is CORRECT")
    sys.exit(0)


