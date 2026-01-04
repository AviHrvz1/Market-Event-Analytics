#!/usr/bin/env python3
"""
Check if SRE dividend appears in NASDAQ dividend calendar for Dec 11, 2024
"""

import requests
import json

def test_sre_in_nasdaq_dividend():
    """Check if SRE dividend is in NASDAQ dividend calendar"""
    print("=" * 80)
    print("SRE DIVIDEND IN NASDAQ CALENDAR TEST")
    print("=" * 80)
    print()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://www.nasdaq.com/'
    }
    
    # Test Dec 11, 2024
    test_date = '2024-12-11'
    endpoint = f'https://api.nasdaq.com/api/calendar/dividends?date={test_date}'
    
    print(f"Date: {test_date}")
    print(f"Endpoint: {endpoint}")
    print()
    
    try:
        response = requests.get(endpoint, headers=headers, timeout=5, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            
            # Navigate to calendar.rows
            calendar = data.get('data', {}).get('calendar', {})
            rows = calendar.get('rows', [])
            
            print(f"Total dividend entries for {test_date}: {len(rows)}")
            print()
            
            # Search for SRE
            sre_found = False
            for entry in rows:
                symbol = entry.get('symbol', '').upper()
                if symbol == 'SRE':
                    sre_found = True
                    print("✅ FOUND SRE DIVIDEND!")
                    print()
                    print("SRE Dividend Details:")
                    print(f"  Symbol: {entry.get('symbol', 'N/A')}")
                    print(f"  Company: {entry.get('companyName', 'N/A')}")
                    print(f"  Ex-Dividend Date: {entry.get('dividend_Ex_Date', 'N/A')}")
                    print(f"  Payment Date: {entry.get('payment_Date', 'N/A')}")
                    print(f"  Record Date: {entry.get('record_Date', 'N/A')}")
                    print(f"  Dividend Rate: {entry.get('dividend_Rate', 'N/A')}")
                    print(f"  Announcement Date: {entry.get('announcement_Date', 'N/A')}")
                    print()
                    break
            
            if not sre_found:
                print("❌ SRE not found in dividend calendar for Dec 11, 2024")
                print()
                print("Possible reasons:")
                print("1. Dec 11 might be ex-dividend date, but dividend was announced earlier")
                print("2. SRE might use a different date format or symbol")
                print("3. Dividend might be listed under a different date")
                print()
                print("Sample symbols found:")
                symbols = [e.get('symbol', 'N/A') for e in rows[:20]]
                print(f"  {', '.join(symbols)}")
        else:
            print(f"❌ Error: Status {response.status_code}")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 80)
    print("LATENCY SUMMARY")
    print("=" * 80)
    print()
    print("NASDAQ Dividend Calendar Endpoint:")
    print("  - Endpoint: https://api.nasdaq.com/api/calendar/dividends?date=YYYY-MM-DD")
    print("  - Latency per call: ~0.5-0.6s")
    print()
    print("For date range Dec 3 to Dec 30 (28 days):")
    print("  - API calls needed: 28 (one per day)")
    print("  - Sequential latency: 28 × 0.5s = ~14s")
    print("  - Parallel (10 workers): ~1.4s")
    print()
    print("Current implementation:")
    print("  - Already queries earnings calendar: 28 calls")
    print("  - Adding dividends: +28 calls")
    print("  - Total: 56 API calls per stock")
    print("  - Sequential: ~28s per stock")
    print("  - Parallel (10 workers): ~2.8s per stock")
    print()
    print("Impact on overall analysis:")
    print("  - For 50 stocks: 50 × 56 = 2,800 API calls")
    print("  - Parallel (10 workers): ~280s = ~4.7 minutes")
    print("  - Current (earnings only): ~2.3 minutes")
    print("  - Additional time: ~2.4 minutes")

if __name__ == "__main__":
    test_sre_in_nasdaq_dividend()

