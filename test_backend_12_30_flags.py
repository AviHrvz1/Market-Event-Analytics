#!/usr/bin/env python3
"""
Unit test to verify backend is sending correct flags for 12:30 interval
Tests is_daily_close_1hr and is_intraday_1hr flags
"""

import sys
from datetime import datetime, timezone
from main import LayoffTracker

def test_backend_12_30_flags():
    """Test that backend sets correct flags for 12:30 interval"""
    
    print("=" * 80)
    print("BACKEND 12:30 FLAGS VERIFICATION")
    print("=" * 80)
    print()
    
    test_cases = [
        {
            'company': 'Anavex Life Sciences Corp.',
            'ticker': 'AVXL',
            'article_datetime': '2025-10-02 03:00:00',
            'next_trading': '2025-10-03'
        },
        {
            'company': 'Eli Lilly and Company',
            'ticker': 'LLY',
            'article_datetime': '2025-08-26 03:00:00',
            'next_trading': '2025-08-27'
        },
        {
            'company': 'argenx SE',
            'ticker': 'ARGX',
            'article_datetime': '2025-08-25 03:00:00',
            'next_trading': '2025-08-26'
        }
    ]
    
    tracker = LayoffTracker()
    now = datetime.now(timezone.utc)
    
    for i, case in enumerate(test_cases, 1):
        print(f"Test Case {i}: {case['company']} ({case['ticker']})")
        print("-" * 80)
        
        article_dt = datetime.strptime(case['article_datetime'], '%Y-%m-%d %H:%M:%S')
        article_dt = article_dt.replace(tzinfo=timezone.utc)
        
        days_ago = (now - article_dt).days
        print(f"  Article Date: {article_dt.strftime('%Y-%m-%d %H:%M:%S')} ({days_ago} days ago)")
        print()
        
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
        try:
            results = tracker.calculate_stock_changes(layoff)
            
            if results:
                print("  ✅ calculate_stock_changes() returned results")
                print()
                
                # Check 1hr interval flags
                print("  Checking 1hr interval flags:")
                print()
                
                price_1hr = results.get('price_1hr')
                change_1hr = results.get('change_1hr')
                is_daily_close_1hr = results.get('is_daily_close_1hr', False)
                is_intraday_1hr = results.get('is_intraday_1hr', False)
                date_1hr = results.get('date_1hr')
                
                print(f"    price_1hr: {price_1hr}")
                print(f"    change_1hr: {change_1hr}")
                print(f"    is_daily_close_1hr: {is_daily_close_1hr}")
                print(f"    is_intraday_1hr: {is_intraday_1hr}")
                print(f"    date_1hr: {date_1hr}")
                print()
                
                # Verify flags
                print("  Flag Verification:")
                if is_daily_close_1hr:
                    print(f"    ✅ is_daily_close_1hr = True (correct)")
                else:
                    print(f"    ❌ is_daily_close_1hr = False (SHOULD BE True!)")
                
                if not is_intraday_1hr:
                    print(f"    ✅ is_intraday_1hr = False (correct)")
                else:
                    print(f"    ❌ is_intraday_1hr = True (SHOULD BE False!)")
                
                print()
                
                # Check what UI would receive
                print("  What API would send to browser:")
                api_data = {
                    'price_1hr': price_1hr,
                    'change_1hr': change_1hr,
                    'is_daily_close_1hr': is_daily_close_1hr,
                    'is_intraday_1hr': is_intraday_1hr,
                    'date_1hr': date_1hr
                }
                print(f"    {api_data}")
                print()
                
                # Check UI condition
                print("  UI Condition Check:")
                print(f"    if (isDailyClose && intervalName === '1hr'):")
                print(f"      isDailyClose = {is_daily_close_1hr}")
                print(f"      intervalName = '1hr'")
                condition_result = is_daily_close_1hr and True  # intervalName would be '1hr'
                print(f"      → Condition result: {condition_result}")
                
                if condition_result:
                    print(f"      ✅ UI should show 'Daily Close' label")
                else:
                    print(f"      ❌ UI will NOT show 'Daily Close' label")
                    print(f"      This is the problem!")
                
                print()
                
                # Check other intervals for comparison
                print("  Other intervals for comparison:")
                for interval in ['5min', '10min', '30min']:
                    is_daily_close = results.get(f'is_daily_close_{interval}', False)
                    is_intraday = results.get(f'is_intraday_{interval}', False)
                    price = results.get(f'price_{interval}')
                    print(f"    {interval}: is_daily_close={is_daily_close}, is_intraday={is_intraday}, price={price}")
                
            else:
                print("  ❌ calculate_stock_changes() returned None or empty")
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        print()
        print()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("Expected Backend Data:")
    print("  For articles >60 days old:")
    print("    is_daily_close_1hr = True")
    print("    is_intraday_1hr = False")
    print("    price_1hr = close_price (daily close)")
    print()
    print("Expected UI Behavior:")
    print("  if (isDailyClose && intervalName === '1hr'):")
    print("    → Show 'Daily Close' label")
    print()

if __name__ == '__main__':
    test_backend_12_30_flags()

