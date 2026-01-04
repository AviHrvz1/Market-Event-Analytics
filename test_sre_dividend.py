#!/usr/bin/env python3
"""
Unit test to verify SRE (Sempra Energy) dividend detection on Dec 11, 2024
"""

import sys
from datetime import datetime, timezone
from main import LayoffTracker

def test_sre_dividend_detection():
    """Test if SRE dividend on Dec 11, 2024 is detected"""
    print("=" * 80)
    print("SRE DIVIDEND DETECTION TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Test dates
    bearish_date = datetime(2024, 12, 3, tzinfo=timezone.utc)  # Dec 3, 2024
    target_date = datetime(2024, 12, 30, tzinfo=timezone.utc)  # Dec 30, 2024
    dividend_date = datetime(2024, 12, 11, tzinfo=timezone.utc)  # Dec 11, 2024 (expected dividend)
    
    ticker = 'SRE'
    
    print(f"Ticker: {ticker}")
    print(f"Bearish Date: {bearish_date.strftime('%Y-%m-%d')}")
    print(f"Target Date: {target_date.strftime('%Y-%m-%d')}")
    print(f"Expected Dividend Date: {dividend_date.strftime('%Y-%m-%d')}")
    print()
    
    print("Testing events during period detection...")
    print()
    
    try:
        # Test the methods that fetch events during period (same as used in get_bearish_analytics)
        print("Fetching events from SEC EDGAR and NASDAQ...")
        print()
        
        # Combine results from both sources (same logic as in add_events_during_to_stock)
        earnings_dividends = tracker._check_earnings_dividends_sec(ticker, bearish_date, target_date, future_days=0)
        
        # Also check NASDAQ for dividends during period
        try:
            nasdaq_result = tracker._check_earnings_dividends_nasdaq(ticker, bearish_date, target_date, future_days=0)
            if nasdaq_result:
                nasdaq_events_during = nasdaq_result.get('events_during', [])
                if nasdaq_events_during:
                    earnings_dividends['events_during'].extend(nasdaq_events_during)
                    earnings_dividends['has_events_during'] = len(earnings_dividends['events_during']) > 0
                    
                    # Remove duplicates
                    seen_events = set()
                    unique_events = []
                    for event in sorted(earnings_dividends['events_during'], key=lambda x: (x['date'], x.get('type', ''))):
                        event_key = (event['date'], event.get('type', ''), event.get('name', ''))
                        if event_key not in seen_events:
                            seen_events.add(event_key)
                            unique_events.append(event)
                    earnings_dividends['events_during'] = unique_events
                    earnings_dividends['has_events_during'] = len(earnings_dividends['events_during']) > 0
        except Exception as e:
            print(f"  ⚠️  NASDAQ check error: {str(e)}")
        
        print("=" * 80)
        print("EVENTS DURING PERIOD RESULTS")
        print("=" * 80)
        print()
        
        events_during = earnings_dividends.get('events_during', [])
        has_events = earnings_dividends.get('has_events_during', False)
        
        print(f"Has Events: {has_events}")
        print(f"Number of Events Found: {len(events_during)}")
        print()
        
        if events_during:
            print("Events Found:")
            for i, event in enumerate(events_during, 1):
                print(f"  {i}. Date: {event.get('date', 'N/A')}")
                print(f"     Type: {event.get('type', 'N/A')}")
                print(f"     Name: {event.get('name', 'N/A')}")
                print(f"     Form: {event.get('form', 'N/A')}")
                print(f"     Description: {event.get('description', 'N/A')}")
                print()
        else:
            print("❌ No events found!")
            print()
        
        # Check if Dec 11 dividend is in the results
        dec_11_found = False
        dividend_found = False
        
        for event in events_during:
            event_date = event.get('date', '')
            event_type = event.get('type', '').lower()
            
            if event_date == '2024-12-11':
                dec_11_found = True
                print(f"✅ Found event on Dec 11: {event.get('name', 'N/A')} ({event.get('type', 'N/A')})")
            
            if event_type == 'dividend':
                dividend_found = True
                print(f"✅ Found dividend event: {event.get('name', 'N/A')} on {event.get('date', 'N/A')}")
        
        print()
        print("=" * 80)
        print("VERIFICATION")
        print("=" * 80)
        print()
        
        if dec_11_found:
            print("✅ PASS: Event on Dec 11, 2024 was found")
        else:
            print("❌ FAIL: Event on Dec 11, 2024 was NOT found")
            print("   This suggests the dividend detection is missing this date")
        
        if dividend_found:
            print("✅ PASS: At least one dividend event was found")
        else:
            print("❌ FAIL: No dividend events were found at all")
        
        print()
        print("=" * 80)
        print("DEBUGGING: Checking SEC EDGAR and NASDAQ sources separately")
        print("=" * 80)
        print()
        
        # Test SEC EDGAR directly
        print("Testing SEC EDGAR detection...")
        try:
            sec_events = tracker._check_earnings_dividends_sec(ticker, bearish_date, target_date, future_days=0)
            sec_events_during = sec_events.get('events_during', [])
            print(f"SEC EDGAR found {len(sec_events_during)} events during period")
            if sec_events_during:
                for event in sec_events_during:
                    print(f"  - {event.get('date', 'N/A')}: {event.get('name', 'N/A')} ({event.get('type', 'N/A')})")
            else:
                print("  No events found in SEC EDGAR")
        except Exception as e:
            print(f"  ⚠️  SEC EDGAR error: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print()
        
        # Test NASDAQ directly
        print("Testing NASDAQ detection...")
        try:
            nasdaq_events = tracker._check_earnings_dividends_nasdaq(ticker, bearish_date, target_date, future_days=0)
            nasdaq_events_during = nasdaq_events.get('events_during', [])
            print(f"NASDAQ found {len(nasdaq_events_during)} events during period")
            if nasdaq_events_during:
                for event in nasdaq_events_during:
                    print(f"  - {event.get('date', 'N/A')}: {event.get('name', 'N/A')} ({event.get('type', 'N/A')})")
            else:
                print("  No events found in NASDAQ")
                print()
                print("  ⚠️  NOTE: NASDAQ code only queries earnings calendar, not dividends!")
                print("     NASDAQ likely has a separate dividend calendar endpoint that we're not using.")
        except Exception as e:
            print(f"  ⚠️  NASDAQ error: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print()
        print("=" * 80)
        print("ANALYSIS")
        print("=" * 80)
        print()
        print("Potential reasons why Dec 11 dividend was missed:")
        print("1. SEC EDGAR only checks 8-K filings with Item 8.01 mentioning 'dividend'")
        print("   - Regular quarterly dividends may not require 8-K filings")
        print("   - Dividend might have been declared earlier (before Dec 3)")
        print("2. NASDAQ code only queries earnings calendar (/api/calendar/earnings)")
        print("   - Does NOT query dividend calendar (likely /api/calendar/dividends)")
        print("3. Dec 11 might be ex-dividend date or payment date, not declaration date")
        print("   - SEC filings would show declaration date, not ex-dividend/payment date")
        
        return dec_11_found and dividend_found
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_sre_dividend_detection()
    sys.exit(0 if success else 1)

