#!/usr/bin/env python3
"""
Test what the API endpoint would return for these articles
Simulates the /api/layoffs endpoint response
"""

import sys
import json
from datetime import datetime, timezone
from main import LayoffTracker

def test_api_response_flags():
    """Test what flags the API endpoint returns"""
    
    print("=" * 80)
    print("API RESPONSE FLAGS TEST")
    print("=" * 80)
    print()
    
    test_cases = [
        {
            'company': 'Anavex Life Sciences Corp.',
            'ticker': 'AVXL',
            'article_datetime': '2025-10-02 03:00:00'
        },
        {
            'company': 'Eli Lilly and Company',
            'ticker': 'LLY',
            'article_datetime': '2025-08-26 03:00:00'
        },
        {
            'company': 'argenx SE',
            'ticker': 'ARGX',
            'article_datetime': '2025-08-25 03:00:00'
        }
    ]
    
    tracker = LayoffTracker()
    
    for i, case in enumerate(test_cases, 1):
        print(f"Test Case {i}: {case['company']} ({case['ticker']})")
        print("-" * 80)
        
        article_dt = datetime.strptime(case['article_datetime'], '%Y-%m-%d %H:%M:%S')
        article_dt = article_dt.replace(tzinfo=timezone.utc)
        
        # Create layoff dict
        layoff = {
            'company_name': case['company'],
            'stock_ticker': case['ticker'],
            'datetime': article_dt,
            'publishedAt': article_dt.isoformat(),
            'url': 'https://test.com',
            'title': f"Test article for {case['company']}"
        }
        
        print("  Calling calculate_stock_changes()...")
        results = tracker.calculate_stock_changes(layoff)
        
        if results:
            # Simulate what app.py /api/layoffs endpoint would return
            api_layoff_data = {
                'price_1hr': results.get('price_1hr'),
                'change_1hr': results.get('change_1hr'),
                'is_daily_close_1hr': results.get('is_daily_close_1hr'),
                'is_intraday_1hr': results.get('is_intraday_1hr'),
                'date_1hr': results.get('date_1hr'),
                'datetime_1hr': results.get('datetime_1hr'),
            }
            
            print("  API Response Data (what browser receives):")
            print(f"    {json.dumps(api_layoff_data, indent=2, default=str)}")
            print()
            
            print("  Flag Analysis:")
            is_daily_close = api_layoff_data.get('is_daily_close_1hr', False)
            is_intraday = api_layoff_data.get('is_intraday_1hr', False)
            price = api_layoff_data.get('price_1hr')
            
            print(f"    is_daily_close_1hr: {is_daily_close}")
            print(f"    is_intraday_1hr: {is_intraday}")
            print(f"    price_1hr: {price}")
            print()
            
            if is_daily_close and not is_intraday:
                print("    ✅ Flags are CORRECT - UI should show 'Daily Close'")
            elif is_daily_close and is_intraday:
                print("    ❌ ISSUE: Both flags are True (conflicting)")
            elif not is_daily_close and is_intraday:
                print("    ❌ ISSUE: is_intraday is True when it should be False")
            elif not is_daily_close and not is_intraday and price:
                print("    ❌ ISSUE: Price exists but flags are not set!")
                print("    This means the daily close fallback path was not reached")
            else:
                print("    ⚠️  No price data available")
            
            print()
            
            # Check UI condition
            print("  UI Condition Check:")
            print(f"    if (isDailyClose && intervalName === '1hr'):")
            print(f"      isDailyClose = {is_daily_close}")
            if is_daily_close:
                print(f"      → Condition is TRUE - UI should show 'Daily Close' label")
            else:
                print(f"      → Condition is FALSE - UI will show price instead")
                print(f"      → This is why you see actual price instead of 'Daily Close'")
        else:
            print("  ❌ No results returned")
        
        print()
        print()

if __name__ == '__main__':
    test_api_response_flags()

