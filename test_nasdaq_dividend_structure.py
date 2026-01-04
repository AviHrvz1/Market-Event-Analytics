#!/usr/bin/env python3
"""
Test NASDAQ dividend calendar endpoint structure and check for SRE dividend on Dec 11
"""

import requests
import json
import time
from datetime import datetime

def test_nasdaq_dividend_structure():
    """Test NASDAQ dividend endpoint structure and latency"""
    print("=" * 80)
    print("NASDAQ DIVIDEND ENDPOINT STRUCTURE TEST")
    print("=" * 80)
    print()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://www.nasdaq.com/'
    }
    
    # Test the dividend endpoint for Dec 11, 2024
    test_date = '2024-12-11'
    endpoint = f'https://api.nasdaq.com/api/calendar/dividends?date={test_date}'
    
    print(f"Testing endpoint: {endpoint}")
    print(f"Date: {test_date}")
    print()
    
    try:
        start_time = time.time()
        response = requests.get(endpoint, headers=headers, timeout=5, verify=False)
        elapsed = time.time() - start_time
        
        print(f"Status Code: {response.status_code}")
        print(f"Latency: {elapsed:.3f}s")
        print()
        
        if response.status_code == 200:
            data = response.json()
            
            print("Response Structure:")
            print(f"  Top-level keys: {list(data.keys())}")
            print()
            
            if 'data' in data:
                data_section = data['data']
                print(f"Data section type: {type(data_section)}")
                
                if isinstance(data_section, dict):
                    print(f"Data section keys: {list(data_section.keys())}")
                    
                    if 'rows' in data_section:
                        rows = data_section['rows']
                        print(f"Number of dividend entries: {len(rows)}")
                        print()
                        
                        if rows:
                            print("Sample entry structure:")
                            sample = rows[0]
                            print(f"  Keys: {list(sample.keys())}")
                            print(f"  Sample: {json.dumps(sample, indent=2)[:500]}")
                            print()
                            
                            # Check for SRE
                            print("Searching for SRE (Sempra Energy)...")
                            sre_found = False
                            for entry in rows:
                                symbol = entry.get('symbol', '').upper()
                                if symbol == 'SRE':
                                    sre_found = True
                                    print(f"  ✅ FOUND SRE!")
                                    print(f"     Entry: {json.dumps(entry, indent=2)}")
                                    break
                            
                            if not sre_found:
                                print(f"  ❌ SRE not found in {len(rows)} entries")
                                print(f"     Available symbols: {[e.get('symbol', 'N/A') for e in rows[:10]]}")
                        else:
                            print("  ⚠️  No dividend entries for this date")
                    else:
                        print("  ⚠️  No 'rows' key in data section")
                        print(f"     Data section: {json.dumps(data_section, indent=2)[:500]}")
                else:
                    print(f"  Data section is not a dict: {type(data_section)}")
            else:
                print("  ⚠️  No 'data' key in response")
                print(f"     Response: {json.dumps(data, indent=2)[:500]}")
        else:
            print(f"  ❌ Error: Status {response.status_code}")
            print(f"     Response: {response.text[:200]}")
    
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 80)
    print("LATENCY ESTIMATION")
    print("=" * 80)
    print()
    print(f"Single API call latency: ~{elapsed:.3f}s")
    print()
    print("For date range Dec 3 to Dec 30 (28 days):")
    print(f"  - Sequential: 28 calls × {elapsed:.3f}s = {28 * elapsed:.2f}s")
    print(f"  - Parallel (10 workers): ~{28 * elapsed / 10:.2f}s")
    print()
    print("Current implementation queries earnings calendar for same dates:")
    print("  - Already making 28 API calls for earnings")
    print("  - Adding dividends would DOUBLE the API calls (28 more)")
    print("  - Total: 56 API calls per stock")
    print(f"  - Sequential: 56 × {elapsed:.3f}s = {56 * elapsed:.2f}s per stock")
    print(f"  - Parallel (10 workers): ~{56 * elapsed / 10:.2f}s per stock")

if __name__ == "__main__":
    test_nasdaq_dividend_structure()

