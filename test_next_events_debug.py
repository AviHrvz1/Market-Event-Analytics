#!/usr/bin/env python3
"""
Debug test to check why "Next Events" is always empty
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_next_events():
    """Test next events detection"""
    print("=" * 80)
    print("NEXT EVENTS DEBUG TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Use a test case with known dates
    ticker = 'AAPL'
    bearish_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
    target_date = datetime(2024, 6, 30, tzinfo=timezone.utc)  # Mid-year, should have future events
    
    print(f"Ticker: {ticker}")
    print(f"Bearish Date: {bearish_date.date()}")
    print(f"Target Date: {target_date.date()}")
    print(f"Looking for events after {target_date.date()} up to {(target_date.date() + timedelta(days=60))}")
    print()
    
    result = tracker._check_earnings_dividends_sec(ticker, bearish_date, target_date, future_days=60)
    
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()
    print(f"Events During Period: {len(result['events_during'])}")
    for event in result['events_during']:
        print(f"  - {event['name']} on {event['date']}")
    print()
    print(f"Next Events: {len(result['next_events'])}")
    for event in result['next_events']:
        print(f"  - {event['name']} on {event['date']}")
    print()
    
    # Debug: Check what dates we're comparing
    print("=" * 80)
    print("DEBUG: Date Range Check")
    print("=" * 80)
    print(f"Target Date: {target_date.date()}")
    print(f"Future End Date: {target_date.date() + timedelta(days=60)}")
    print()
    
    # Get CIK and check filings manually
    cik = tracker.get_cik_from_ticker(ticker)
    if cik:
        print(f"CIK: {cik}")
        print("Fetching filings to check date ranges...")
        
        import requests
        from config import SEC_EDGAR_COMPANY_API, SEC_USER_AGENT
        
        url = f"{SEC_EDGAR_COMPANY_API}/CIK{cik}.json"
        headers = {
            'User-Agent': SEC_USER_AGENT,
            'Accept': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                filings = data.get('filings', {}).get('recent', {})
                form_types = filings.get('form', [])
                filing_dates = filings.get('filingDate', [])
                
                print(f"\nFound {len(form_types)} total filings")
                print("\nChecking for earnings/dividend filings after target date:")
                print(f"  Target Date: {target_date.date()}")
                print(f"  Future End: {target_date.date() + timedelta(days=60)}")
                print()
                
                earnings_forms = ['10-Q', '10-K', '8-K']
                count_after_target = 0
                count_in_range = 0
                
                for i, form_type in enumerate(form_types[:50]):  # Check first 50
                    if i >= len(filing_dates):
                        continue
                    
                    if form_type in earnings_forms:
                        filing_date_str = filing_dates[i]
                        filing_date = datetime.strptime(filing_date_str, '%Y-%m-%d').date()
                        
                        if filing_date > target_date.date():
                            count_after_target += 1
                            print(f"  Found {form_type} on {filing_date} (after target date)")
                            
                            if filing_date <= (target_date.date() + timedelta(days=60)):
                                count_in_range += 1
                                print(f"    ✅ In range (within 60 days)")
                            else:
                                print(f"    ❌ Out of range (beyond 60 days)")
                
                print()
                print(f"Total earnings/dividend filings after target date: {count_after_target}")
                print(f"Filings within 60-day range: {count_in_range}")
        except Exception as e:
            print(f"Error fetching filings: {e}")
    
    return len(result['next_events']) > 0

if __name__ == "__main__":
    success = test_next_events()
    sys.exit(0 if success else 1)

