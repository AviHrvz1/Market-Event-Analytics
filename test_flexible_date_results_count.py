#!/usr/bin/env python3
"""
Unit test to verify expected results count for flexible date lookup
Tests from 12/11/2025 to 31/12/2025 with -5% change and different flexible_days values
"""

import sys
from datetime import datetime, timezone
from main import LayoffTracker

def test_flexible_date_results_count():
    """Test expected results count with different flexible_days values"""
    print("=" * 80)
    print("FLEXIBLE DATE RESULTS COUNT TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Test parameters
    bearish_date = datetime(2025, 12, 11, 0, 0, 0, tzinfo=timezone.utc)
    target_date = datetime(2025, 12, 31, 0, 0, 0, tzinfo=timezone.utc)
    industry = "All Industries"
    filter_type = "bearish"
    pct_threshold = -5.0
    
    print(f"Test Parameters:")
    print(f"  Analysis Date: {bearish_date.strftime('%Y-%m-%d')}")
    print(f"  Target Date: {target_date.strftime('%Y-%m-%d')}")
    print(f"  Industry: {industry}")
    print(f"  Filter Type: {filter_type}")
    print(f"  Percentage Threshold: {pct_threshold}%")
    print()
    
    # Test with different flexible_days values
    flexible_days_values = [0, 1, 2]
    
    results_summary = []
    
    for flexible_days in flexible_days_values:
        print("=" * 80)
        print(f"Testing with flexible_days = {flexible_days}")
        print("=" * 80)
        print()
        
        if flexible_days > 0:
            min_date = (bearish_date - timedelta(days=flexible_days)).strftime('%Y-%m-%d')
            max_date = (bearish_date + timedelta(days=flexible_days)).strftime('%Y-%m-%d')
            print(f"Date Range: {min_date} to {max_date} (±{flexible_days} days)")
        else:
            print(f"Date Range: {bearish_date.strftime('%Y-%m-%d')} (exact date only)")
        print()
        
        print("Running analysis...")
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
            
            result_count = len(results)
            results_summary.append({
                'flexible_days': flexible_days,
                'count': result_count,
                'results': results
            })
            
            print(f"Results: {result_count} stocks found")
            print()
            
            if result_count > 0:
                print("Sample results (first 5):")
                for i, stock in enumerate(results[:5], 1):
                    ticker = stock.get('ticker', 'N/A')
                    company_name = stock.get('company_name', 'N/A')
                    actual_date = stock.get('bearish_date', 'N/A')
                    pct_drop = stock.get('pct_drop', 0)
                    print(f"  {i}. {ticker} ({company_name}): {pct_drop:.2f}% on {actual_date}")
                if result_count > 5:
                    print(f"  ... and {result_count - 5} more")
            print()
            
        except Exception as e:
            print(f"❌ Error during test: {e}")
            import traceback
            traceback.print_exc()
            results_summary.append({
                'flexible_days': flexible_days,
                'count': 0,
                'error': str(e)
            })
            print()
    
    # Summary comparison
    print("=" * 80)
    print("SUMMARY COMPARISON")
    print("=" * 80)
    print()
    print(f"{'Flexible Days':<15} {'Results Count':<15} {'Difference':<15}")
    print("-" * 45)
    
    prev_count = None
    for summary in results_summary:
        flexible_days = summary['flexible_days']
        count = summary['count']
        
        if 'error' in summary:
            diff_str = "ERROR"
        elif prev_count is not None:
            diff = count - prev_count
            diff_str = f"{diff:+d}" if diff != 0 else "0"
        else:
            diff_str = "-"
        
        print(f"{flexible_days:<15} {count:<15} {diff_str:<15}")
        prev_count = count
    
    print()
    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print()
    
    if len(results_summary) >= 2:
        count_0 = results_summary[0]['count']
        count_2 = results_summary[2]['count'] if len(results_summary) > 2 else None
        
        print(f"With flexible_days=0 (exact date): {count_0} stocks")
        if count_2 is not None:
            print(f"With flexible_days=2 (±2 days): {count_2} stocks")
            if count_2 > count_0:
                print(f"✅ Flexible date lookup found {count_2 - count_0} additional stocks")
            elif count_2 == count_0:
                print("ℹ️  Flexible date lookup found the same number of stocks")
            else:
                print(f"⚠️  Flexible date lookup found fewer stocks (unexpected)")
        
        if count_0 == 1:
            print()
            print("⚠️  Only 1 stock found with flexible_days=0")
            print("   This suggests either:")
            print("   - Very few stocks met the criteria on that exact date")
            print("   - Data availability issues for Dec 2025 (future date)")
            print("   - Network/API issues")
        
        if count_2 and count_2 > count_0:
            print()
            print(f"✅ Expected: With flexible_days=2, you should get at least {count_2} stocks")
            print(f"   If you only got 1 result in the UI, there may be a filtering issue")
    
    return True

if __name__ == "__main__":
    from datetime import timedelta  # Import here to avoid issues
    success = test_flexible_date_results_count()
    sys.exit(0 if success else 1)

