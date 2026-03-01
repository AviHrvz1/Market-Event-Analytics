#!/usr/bin/env python3
"""
Test to check results for November 12, 2025 (the date actually being used)
"""

import sys
from datetime import datetime, timezone
from main import LayoffTracker

def test_nov_12_results():
    """Test with November 12, 2025 (the date actually being used)"""
    print("=" * 80)
    print("TESTING NOVEMBER 12, 2025 (ACTUAL DATE BEING USED)")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Use the date that's actually being sent to the API
    bearish_date = datetime(2025, 11, 12, 0, 0, 0, tzinfo=timezone.utc)  # November 12, not December 11!
    target_date = datetime(2025, 12, 31, 0, 0, 0, tzinfo=timezone.utc)
    industry = "All Industries"
    filter_type = "bearish"
    pct_threshold = -5.0
    flexible_days = 2
    
    print(f"Test Parameters:")
    print(f"  Analysis Date: {bearish_date.strftime('%Y-%m-%d')} (November 12, 2025)")
    print(f"  Target Date: {target_date.strftime('%Y-%m-%d')}")
    print(f"  Flexible Days: {flexible_days}")
    print(f"  Threshold: {pct_threshold}%")
    print()
    
    try:
        results, logs = tracker.get_bearish_analytics(
            bearish_date=bearish_date,
            target_date=target_date,
            industry=industry,
            filter_type=filter_type,
            pct_threshold=pct_threshold,
            flexible_days=flexible_days
        )
        
        print("=" * 80)
        print("RESULTS")
        print("=" * 80)
        print()
        print(f"Total results: {len(results)}")
        print()
        
        if len(results) > 0:
            print("Stocks found:")
            for i, stock in enumerate(results, 1):
                ticker = stock.get('ticker', 'N/A')
                company = stock.get('company_name', 'N/A')
                pct_change = stock.get('pct_change', 'N/A')
                actual_date = stock.get('bearish_date', 'N/A')
                print(f"  {i}. {ticker} ({company}): {pct_change}% on {actual_date}")
        else:
            print("⚠️  No stocks found!")
        
        # Check filtering logs
        filter_logs = [log for log in logs if 'Filtered by bearish drop' in log or 'After filtering' in log]
        if filter_logs:
            print()
            print("Filtering information:")
            for log in filter_logs:
                print(f"  {log}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_nov_12_results()
    sys.exit(0 if success else 1)

