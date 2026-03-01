#!/usr/bin/env python3
"""
Diagnostic test to check why filtering is removing stocks
"""

import sys
from datetime import datetime, timezone
from main import LayoffTracker

def test_filtering_diagnostic():
    """Check what pct_change values are in results before/after filtering"""
    print("=" * 80)
    print("FILTERING DIAGNOSTIC TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    bearish_date = datetime(2025, 12, 11, 0, 0, 0, tzinfo=timezone.utc)
    target_date = datetime(2025, 12, 31, 0, 0, 0, tzinfo=timezone.utc)
    industry = "All Industries"
    filter_type = "bearish"
    pct_threshold = -5.0
    flexible_days = 2  # Use 2 to match what user might have used
    
    print(f"Test Parameters:")
    print(f"  Analysis Date: {bearish_date.strftime('%Y-%m-%d')}")
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
        print("RESULTS ANALYSIS")
        print("=" * 80)
        print()
        print(f"Total results: {len(results)}")
        print()
        
        if len(results) > 0:
            print("Stocks that passed the filter:")
            for i, stock in enumerate(results, 1):
                ticker = stock.get('ticker', 'N/A')
                company = stock.get('company_name', 'N/A')
                pct_change = stock.get('pct_change', 'N/A')
                pct_drop = stock.get('pct_drop', 'N/A')
                actual_date = stock.get('bearish_date', 'N/A')
                
                print(f"  {i}. {ticker} ({company}):")
                print(f"     pct_change: {pct_change}")
                print(f"     pct_drop: {pct_drop}")
                print(f"     bearish_date: {actual_date}")
                print(f"     Passes filter? {pct_change <= pct_threshold if isinstance(pct_change, (int, float)) else 'N/A'}")
                print()
        else:
            print("⚠️  No stocks passed the filter!")
            print()
            print("This means all stocks had pct_change > -5.0%")
            print("(i.e., drops less than 5%)")
        
        # Check logs for filtering message
        print("=" * 80)
        print("FILTERING LOG MESSAGES")
        print("=" * 80)
        print()
        filter_logs = [log for log in logs if 'Filtered by bearish drop' in log or 'After filtering' in log]
        for log in filter_logs:
            print(f"  {log}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_filtering_diagnostic()
    sys.exit(0 if success else 1)

