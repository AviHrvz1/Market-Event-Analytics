#!/usr/bin/env python3
"""
Comprehensive unittest to verify why SRE dividend on Dec 11, 2024 might not appear in NASDAQ calendar
"""

import requests
import json
from datetime import datetime, timedelta

def test_sre_dividend_comprehensive():
    """Comprehensive test to find SRE dividend in NASDAQ calendar"""
    print("=" * 80)
    print("COMPREHENSIVE SRE DIVIDEND TEST")
    print("=" * 80)
    print()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://www.nasdaq.com/'
    }
    
    # Test 1: Check Dec 11, 2024 specifically
    print("TEST 1: Checking Dec 11, 2024 (the date user mentioned)")
    print("-" * 80)
    test_date = '2024-12-11'
    endpoint = f'https://api.nasdaq.com/api/calendar/dividends?date={test_date}'
    
    try:
        response = requests.get(endpoint, headers=headers, timeout=5, verify=False)
        if response.status_code == 200:
            data = response.json()
            calendar = data.get('data', {}).get('calendar', {})
            rows = calendar.get('rows', [])
            
            print(f"Total entries for {test_date}: {len(rows)}")
            
            # Check for SRE by symbol
            sre_by_symbol = None
            for entry in rows:
                if entry.get('symbol', '').upper() == 'SRE':
                    sre_by_symbol = entry
                    break
            
            # Check for SRE by company name
            sre_by_name = None
            for entry in rows:
                company_name = entry.get('companyName', '').upper()
                if 'SEMPR' in company_name or 'SRE' in company_name:
                    sre_by_name = entry
                    break
            
            if sre_by_symbol:
                print(f"✅ FOUND SRE by symbol on {test_date}")
                print(json.dumps(sre_by_symbol, indent=2))
            elif sre_by_name:
                print(f"✅ FOUND SRE by company name on {test_date}")
                print(json.dumps(sre_by_name, indent=2))
            else:
                print(f"❌ SRE not found on {test_date}")
                print(f"   Available symbols: {[e.get('symbol', 'N/A') for e in rows]}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    print()
    
    # Test 2: Check wider date range (Nov 1 to Dec 31, 2024)
    print("TEST 2: Checking wider date range (Nov 1 - Dec 31, 2024)")
    print("-" * 80)
    print("This will check all dates to find where SRE dividend appears...")
    print()
    
    start_date = datetime(2024, 11, 1)
    end_date = datetime(2024, 12, 31)
    
    sre_entries = []
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
                    company_name = entry.get('companyName', '').upper()
                    
                    if symbol == 'SRE' or 'SEMPR' in company_name:
                        entry_copy = entry.copy()
                        entry_copy['calendar_date'] = date_str
                        sre_entries.append(entry_copy)
                
                dates_checked += 1
                if dates_checked % 10 == 0:
                    print(f"  Checked {dates_checked} dates, found {len(sre_entries)} SRE entries...", end='\r')
        
        except Exception:
            pass
        
        current_date += timedelta(days=1)
    
    print()
    print()
    
    if sre_entries:
        print(f"✅ FOUND {len(sre_entries)} SRE dividend entry/entries:")
        print()
        for entry in sre_entries:
            print(f"Calendar Date: {entry.get('calendar_date', 'N/A')}")
            print(f"  Symbol: {entry.get('symbol', 'N/A')}")
            print(f"  Company: {entry.get('companyName', 'N/A')}")
            print(f"  Ex-Dividend Date: {entry.get('dividend_Ex_Date', 'N/A')}")
            print(f"  Payment Date: {entry.get('payment_Date', 'N/A')}")
            print(f"  Record Date: {entry.get('record_Date', 'N/A')}")
            print(f"  Announcement Date: {entry.get('announcement_Date', 'N/A')}")
            print(f"  Dividend Rate: {entry.get('dividend_Rate', 'N/A')}")
            print()
            
            # Check if Dec 11 appears in any date field
            dec_11_found = False
            for field in ['dividend_Ex_Date', 'payment_Date', 'record_Date', 'announcement_Date']:
                field_value = entry.get(field, '')
                if 'Dec 11' in field_value or '12/11' in field_value or '2024-12-11' in field_value:
                    dec_11_found = True
                    print(f"  ✅ Dec 11 found in {field}: {field_value}")
            
            if not dec_11_found:
                print(f"  ⚠️  Dec 11 NOT found in any date field")
            print()
    else:
        print("❌ SRE dividend NOT found in NASDAQ calendar for Nov 1 - Dec 31, 2024")
        print()
        print("Possible reasons:")
        print("1. SRE dividend might not be in NASDAQ calendar at all")
        print("2. SRE might use a different symbol or company name format")
        print("3. NASDAQ calendar might not include all NYSE-listed stocks")
        print("4. Dividend might be listed under a different date format")
    
    print()
    
    # Test 3: Check if NASDAQ calendar includes NYSE stocks
    print("TEST 3: Verifying NASDAQ calendar includes NYSE-listed stocks")
    print("-" * 80)
    
    # Check a known date with many dividends
    test_date = '2024-12-15'  # A Monday, likely to have dividends
    endpoint = f'https://api.nasdaq.com/api/calendar/dividends?date={test_date}'
    
    try:
        response = requests.get(endpoint, headers=headers, timeout=5, verify=False)
        if response.status_code == 200:
            data = response.json()
            calendar = data.get('data', {}).get('calendar', {})
            rows = calendar.get('rows', [])
            
            print(f"Total entries for {test_date}: {len(rows)}")
            
            # Check for NYSE-listed stocks (they might have different format)
            nyse_symbols = []
            nasdaq_symbols = []
            other_symbols = []
            
            for entry in rows[:20]:  # Check first 20
                symbol = entry.get('symbol', '')
                company = entry.get('companyName', '')
                # Try to identify exchange (this is approximate)
                if len(symbol) <= 4 and symbol.isalpha():
                    # Most NASDAQ symbols are 4 letters or less
                    nasdaq_symbols.append(symbol)
                else:
                    other_symbols.append(symbol)
            
            print(f"Sample symbols: {[e.get('symbol', 'N/A') for e in rows[:10]]}")
            print()
            print("Note: NASDAQ calendar should include all exchanges, but verification needed")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    print()
    
    # Test 4: Check alternative endpoints or methods
    print("TEST 4: Checking if there's an alternative way to get SRE dividend")
    print("-" * 80)
    print("Checking if we can search by ticker directly...")
    
    # Try searching without date (if supported)
    alternative_endpoints = [
        'https://api.nasdaq.com/api/dividends/SRE',
        'https://api.nasdaq.com/api/calendar/dividends?symbol=SRE',
        'https://api.nasdaq.com/api/quote/SRE/dividends',
    ]
    
    for alt_endpoint in alternative_endpoints:
        try:
            response = requests.get(alt_endpoint, headers=headers, timeout=5, verify=False)
            if response.status_code == 200:
                print(f"✅ Alternative endpoint works: {alt_endpoint}")
                data = response.json()
                print(f"   Response keys: {list(data.keys())[:5]}")
            else:
                print(f"❌ {alt_endpoint}: Status {response.status_code}")
        except Exception as e:
            print(f"❌ {alt_endpoint}: Error - {str(e)[:50]}")
    
    print()
    print("=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print()
    
    if sre_entries:
        print("✅ SRE dividend WAS found in NASDAQ calendar")
        print("   However, it might not be on Dec 11, 2024")
        print("   Check the date fields above to see which date it appears on")
    else:
        print("❌ SRE dividend NOT found in NASDAQ calendar")
        print()
        print("REASONS WHY IT MAY NOT APPEAR:")
        print("1. NASDAQ calendar might only show ex-dividend dates, not payment/record dates")
        print("2. Dec 11 might be payment/record date, not ex-dividend date")
        print("3. NASDAQ calendar might not include all NYSE-listed stocks")
        print("4. SRE might use a different symbol format in NASDAQ system")
        print("5. Dividend might be listed under announcement date (earlier)")
        print()
        print("RECOMMENDATION:")
        print("- NASDAQ dividend calendar is date-based (shows dividends for that specific date)")
        print("- If Dec 11 is payment/record date, it won't appear on that date")
        print("- Need to check ex-dividend date or announcement date instead")
        print("- May need to query multiple dates or use alternative data source")

if __name__ == "__main__":
    test_sre_dividend_comprehensive()

