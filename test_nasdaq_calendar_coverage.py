#!/usr/bin/env python3
"""
Test NASDAQ calendar coverage - does it include NYSE stocks and what dates does it show?
"""

import requests
import json
from datetime import datetime, timedelta

def test_nasdaq_calendar_coverage():
    """Test what NASDAQ dividend calendar actually covers"""
    print("=" * 80)
    print("NASDAQ DIVIDEND CALENDAR COVERAGE TEST")
    print("=" * 80)
    print()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://www.nasdaq.com/'
    }
    
    # Test 1: Check what dates the calendar shows (ex-dividend vs payment vs record)
    print("TEST 1: What dates does NASDAQ calendar show?")
    print("-" * 80)
    
    # Check a date with dividends
    test_date = '2024-12-11'
    endpoint = f'https://api.nasdaq.com/api/calendar/dividends?date={test_date}'
    
    try:
        response = requests.get(endpoint, headers=headers, timeout=5, verify=False)
        if response.status_code == 200:
            data = response.json()
            calendar = data.get('data', {}).get('calendar', {})
            rows = calendar.get('rows', [])
            
            print(f"Total entries for {test_date}: {len(rows)}")
            print()
            
            if rows:
                # Analyze first few entries to see what dates they show
                print("Sample entries (checking what dates are shown):")
                for i, entry in enumerate(rows[:3], 1):
                    print(f"\nEntry {i}:")
                    print(f"  Symbol: {entry.get('symbol', 'N/A')}")
                    print(f"  Company: {entry.get('companyName', 'N/A')}")
                    print(f"  Calendar Date (query): {test_date}")
                    print(f"  Ex-Dividend Date: {entry.get('dividend_Ex_Date', 'N/A')}")
                    print(f"  Payment Date: {entry.get('payment_Date', 'N/A')}")
                    print(f"  Record Date: {entry.get('record_Date', 'N/A')}")
                    print(f"  Announcement Date: {entry.get('announcement_Date', 'N/A')}")
                    
                    # Check which date matches the calendar date
                    ex_date = entry.get('dividend_Ex_Date', '')
                    pay_date = entry.get('payment_Date', '')
                    rec_date = entry.get('record_Date', '')
                    
                    print(f"  Analysis:")
                    if test_date in ex_date or ex_date.replace('/', '-') == test_date:
                        print(f"    ✅ Calendar shows EX-DIVIDEND date")
                    elif test_date in pay_date or pay_date.replace('/', '-') == test_date:
                        print(f"    ✅ Calendar shows PAYMENT date")
                    elif test_date in rec_date or rec_date.replace('/', '-') == test_date:
                        print(f"    ✅ Calendar shows RECORD date")
                    else:
                        print(f"    ⚠️  Calendar date doesn't match any date field")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    print()
    
    # Test 2: Check if NYSE-listed stocks appear in calendar
    print("TEST 2: Does NASDAQ calendar include NYSE-listed stocks?")
    print("-" * 80)
    
    # Known NYSE stocks that pay dividends
    nyse_stocks = ['JPM', 'BAC', 'WMT', 'XOM', 'CVX']  # Large NYSE stocks
    
    # Check multiple dates to find these stocks
    found_nyse = {}
    
    for test_date in ['2024-12-01', '2024-12-15', '2024-12-20']:
        endpoint = f'https://api.nasdaq.com/api/calendar/dividends?date={test_date}'
        try:
            response = requests.get(endpoint, headers=headers, timeout=5, verify=False)
            if response.status_code == 200:
                data = response.json()
                calendar = data.get('data', {}).get('calendar', {})
                rows = calendar.get('rows', [])
                
                for entry in rows:
                    symbol = entry.get('symbol', '').upper()
                    if symbol in nyse_stocks and symbol not in found_nyse:
                        found_nyse[symbol] = {
                            'date': test_date,
                            'entry': entry
                        }
        except Exception:
            pass
    
    if found_nyse:
        print(f"✅ Found {len(found_nyse)} NYSE-listed stocks in NASDAQ calendar:")
        for symbol, info in found_nyse.items():
            print(f"  {symbol} on {info['date']}")
        print()
        print("✅ NASDAQ calendar DOES include NYSE-listed stocks")
    else:
        print("❌ No NYSE-listed stocks found in sample dates")
        print("   This suggests NASDAQ calendar might NOT include NYSE stocks")
        print("   OR these stocks don't have dividends on those dates")
    
    print()
    
    # Test 3: Check SRE specifically - what dates should we check?
    print("TEST 3: What dates should we check for SRE dividend?")
    print("-" * 80)
    print("If Dec 11 is payment/record date, ex-dividend date would be earlier")
    print("Checking dates BEFORE Dec 11 for SRE...")
    print()
    
    # Check dates from Nov 1 to Dec 10 (before Dec 11)
    start_date = datetime(2024, 11, 1)
    end_date = datetime(2024, 12, 10)
    
    sre_found_before = []
    dates_checked = 0
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        endpoint = f'https://api.nasdaq.com/api/calendar/dividends?date={date_str}'
        
        try:
            response = requests.get(endpoint, headers=headers, timeout=5, verify=False)
            if response.status_code == 200:
                data = response.json()
                calendar = data.get('data', {}).get('calendar', {})
                rows = calendar.get('rows', [])
                
                for entry in rows:
                    symbol = entry.get('symbol', '').upper()
                    if symbol == 'SRE':
                        entry_copy = entry.copy()
                        entry_copy['calendar_date'] = date_str
                        sre_found_before.append(entry_copy)
                
                dates_checked += 1
                if dates_checked % 10 == 0:
                    print(f"  Checked {dates_checked} dates...", end='\r')
        except Exception:
            pass
        
        current_date += timedelta(days=1)
    
    print()
    print()
    
    if sre_found_before:
        print(f"✅ Found SRE dividend BEFORE Dec 11:")
        for entry in sre_found_before:
            print(f"  Calendar Date: {entry.get('calendar_date')}")
            print(f"  Ex-Dividend: {entry.get('dividend_Ex_Date')}")
            print(f"  Payment: {entry.get('payment_Date')}")
            print(f"  Record: {entry.get('record_Date')}")
    else:
        print("❌ SRE not found in dates before Dec 11 either")
    
    print()
    print("=" * 80)
    print("FINAL ANALYSIS")
    print("=" * 80)
    print()
    print("WHY SRE DIVIDEND ON DEC 11 MAY NOT APPEAR:")
    print()
    print("1. NASDAQ calendar shows dividends by EX-DIVIDEND DATE")
    print("   - If Dec 11 is payment/record date, it won't appear on Dec 11")
    print("   - Need to check ex-dividend date (usually 1-2 days before)")
    print()
    print("2. NASDAQ calendar might not include all NYSE stocks")
    print("   - SRE is NYSE-listed (not NASDAQ)")
    print("   - Calendar might prioritize NASDAQ-listed stocks")
    print()
    print("3. Date format or symbol mismatch")
    print("   - SRE might use different symbol in NASDAQ system")
    print("   - Date formats might not match exactly")
    print()
    print("RECOMMENDATION:")
    print("- NASDAQ dividend calendar is useful but has limitations")
    print("- Should be used as supplementary source, not primary")
    print("- SEC EDGAR is more reliable for dividend announcements")
    print("- For payment/record dates, need to check ex-dividend dates instead")

if __name__ == "__main__":
    test_nasdaq_calendar_coverage()

