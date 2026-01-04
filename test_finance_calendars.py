#!/usr/bin/env python3
"""
Test finance-calendars package to verify it works for earnings/dividend data
"""

import sys
from datetime import datetime, timedelta

try:
    from finance_calendars import get_earnings_calendar, get_dividend_calendar
    FINANCE_CALENDARS_AVAILABLE = True
except ImportError:
    FINANCE_CALENDARS_AVAILABLE = False
    print("❌ finance-calendars not installed. Install with: pip install finance-calendars")

def test_finance_calendars():
    """Test finance-calendars package"""
    print("=" * 80)
    print("FINANCE-CALENDARS PACKAGE TEST")
    print("=" * 80)
    print()
    
    if not FINANCE_CALENDARS_AVAILABLE:
        return False
    
    # Test with AAPL
    ticker = 'AAPL'
    start_date = '2025-12-29'
    end_date = '2026-02-27'  # 60 days after
    
    print(f"Testing ticker: {ticker}")
    print(f"Date range: {start_date} to {end_date}")
    print()
    
    # Test earnings calendar
    print("📊 Testing Earnings Calendar...")
    try:
        earnings = get_earnings_calendar(ticker=ticker, start_date=start_date, end_date=end_date)
        print(f"   ✅ Earnings calendar retrieved")
        print(f"   Type: {type(earnings)}")
        if isinstance(earnings, (list, dict)):
            print(f"   Length/Keys: {len(earnings) if isinstance(earnings, list) else list(earnings.keys())}")
            if isinstance(earnings, list) and len(earnings) > 0:
                print(f"   Sample entry: {earnings[0]}")
            elif isinstance(earnings, dict) and len(earnings) > 0:
                first_key = list(earnings.keys())[0]
                print(f"   Sample entry: {earnings[first_key]}")
        else:
            print(f"   Data: {earnings}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # Test dividend calendar
    print("💰 Testing Dividend Calendar...")
    try:
        dividends = get_dividend_calendar(ticker=ticker, start_date=start_date, end_date=end_date)
        print(f"   ✅ Dividend calendar retrieved")
        print(f"   Type: {type(dividends)}")
        if isinstance(dividends, (list, dict)):
            print(f"   Length/Keys: {len(dividends) if isinstance(dividends, list) else list(dividends.keys())}")
            if isinstance(dividends, list) and len(dividends) > 0:
                print(f"   Sample entry: {dividends[0]}")
            elif isinstance(dividends, dict) and len(dividends) > 0:
                first_key = list(dividends.keys())[0]
                print(f"   Sample entry: {dividends[first_key]}")
        else:
            print(f"   Data: {dividends}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 80)
    if FINANCE_CALENDARS_AVAILABLE:
        print("✅ finance-calendars package is available and working")
    else:
        print("❌ finance-calendars package is not available")
    print("=" * 80)
    
    return FINANCE_CALENDARS_AVAILABLE

if __name__ == "__main__":
    success = test_finance_calendars()
    sys.exit(0 if success else 1)

