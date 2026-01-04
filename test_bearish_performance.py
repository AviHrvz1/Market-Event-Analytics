#!/usr/bin/env python3
"""
Performance test for Top Bearish Analytics feature
Measures time taken and identifies bottlenecks for date range 8/12/25 to 22/12/25
"""

import sys
import time
from datetime import datetime, timezone
from main import LayoffTracker

def test_bearish_performance():
    """Test performance and identify bottlenecks"""
    print("=" * 80)
    print("BEARISH ANALYTICS PERFORMANCE TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Test dates: 8/12/25 to 22/12/25
    bearish_date = datetime(2025, 12, 8, tzinfo=timezone.utc)
    target_date = datetime(2025, 12, 22, tzinfo=timezone.utc)
    
    print(f"Bearish Date: {bearish_date.strftime('%Y-%m-%d')} ({bearish_date.strftime('%A')})")
    print(f"Target Date:  {target_date.strftime('%Y-%m-%d')} ({target_date.strftime('%A')})")
    print(f"Date Range:   {(target_date - bearish_date).days} days")
    print()
    
    # Track timing for each step
    timings = {}
    errors = []
    
    print("-" * 80)
    print("STEP 1: Loading Companies List")
    print("-" * 80)
    start_time = time.time()
    try:
        companies = tracker._get_large_cap_companies_with_options()
        timings['load_companies'] = time.time() - start_time
        print(f"✅ Loaded {len(companies)} companies in {timings['load_companies']:.2f}s")
    except Exception as e:
        timings['load_companies'] = time.time() - start_time
        errors.append(f"Load companies error: {e}")
        print(f"❌ Error loading companies: {e}")
    print()
    
    print("-" * 80)
    print("STEP 2: Quick Top Losers Identification (Prixe.io)")
    print("-" * 80)
    start_time = time.time()
    try:
        losers = tracker.get_top_losers_prixe(bearish_date, industry=None, logs=None)
        timings['top_losers'] = time.time() - start_time
        print(f"✅ Found {len(losers)} losers in {timings['top_losers']:.2f}s")
        if len(losers) > 0:
            print(f"   Top 5 losers:")
            for i, (ticker, pct_drop, info) in enumerate(losers[:5], 1):
                print(f"     {i}. {ticker}: {pct_drop:.2f}%")
    except Exception as e:
        timings['top_losers'] = time.time() - start_time
        errors.append(f"Top losers error: {e}")
        print(f"❌ Error finding top losers: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    print("-" * 80)
    print("STEP 3: Full Bearish Analytics (with recovery)")
    print("-" * 80)
    start_time = time.time()
    try:
        results, logs = tracker.get_bearish_analytics(bearish_date, target_date, industry=None)
        timings['full_analytics'] = time.time() - start_time
        print(f"✅ Completed full analytics in {timings['full_analytics']:.2f}s")
        print(f"   Found {len(results)} stocks with complete data")
        
        # Show logs with timing context
        print()
        print("Processing Logs:")
        for log in logs:
            print(f"  {log}")
    except Exception as e:
        timings['full_analytics'] = time.time() - start_time
        errors.append(f"Full analytics error: {e}")
        print(f"❌ Error in full analytics: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # Break down full analytics timing if we have detailed logs
    print("-" * 80)
    print("STEP 4: Detailed Timing Breakdown")
    print("-" * 80)
    
    price_fetch_times = []
    # Test individual price fetches to see where time is spent
    if len(losers) > 0:
        print(f"Testing individual price fetches for top 5 losers...")
        price_fetch_times = []
        for i, (ticker, pct_drop, info) in enumerate(losers[:5], 1):
            start_time = time.time()
            try:
                bearish_price = tracker.get_stock_price_on_date(ticker, bearish_date)
                target_price = tracker.get_stock_price_on_date(ticker, target_date)
                fetch_time = time.time() - start_time
                price_fetch_times.append((ticker, fetch_time))
                print(f"  {i}. {ticker}: {fetch_time:.2f}s (bearish=${bearish_price:.2f}, target=${target_price:.2f if target_price else 0:.2f})")
            except Exception as e:
                fetch_time = time.time() - start_time
                price_fetch_times.append((ticker, fetch_time))
                errors.append(f"Price fetch error for {ticker}: {e}")
                print(f"  {i}. {ticker}: {fetch_time:.2f}s (ERROR: {e})")
        
        if price_fetch_times:
            avg_fetch_time = sum(t for _, t in price_fetch_times) / len(price_fetch_times)
            print(f"  Average price fetch time: {avg_fetch_time:.2f}s per ticker")
    else:
        print("⚠️  No losers found, skipping individual price fetch test")
    print()
    
    # Summary
    print("=" * 80)
    print("PERFORMANCE SUMMARY")
    print("=" * 80)
    print()
    
    total_time = sum(timings.values())
    print(f"Total Time: {total_time:.2f}s")
    print()
    print("Time Breakdown:")
    for step, duration in sorted(timings.items(), key=lambda x: x[1], reverse=True):
        percentage = (duration / total_time * 100) if total_time > 0 else 0
        print(f"  {step:20s}: {duration:6.2f}s ({percentage:5.1f}%)")
    print()
    
    if errors:
        print("=" * 80)
        print("ERRORS ENCOUNTERED")
        print("=" * 80)
        for i, error in enumerate(errors, 1):
            print(f"{i}. {error}")
        print()
    else:
        print("✅ No errors encountered")
        print()
    
    # Performance analysis
    print("=" * 80)
    print("PERFORMANCE ANALYSIS")
    print("=" * 80)
    print()
    
    if timings.get('top_losers', 0) > 10:
        print("⚠️  Top losers identification took >10s - consider optimizing batch size")
    
    if timings.get('full_analytics', 0) > 30:
        print("⚠️  Full analytics took >30s - may need optimization")
    
    if timings.get('load_companies', 0) > 1:
        print("⚠️  Loading companies took >1s - consider caching")
    
    if price_fetch_times:
        avg_fetch = sum(t for _, t in price_fetch_times) / len(price_fetch_times)
        if avg_fetch > 2:
            print(f"⚠️  Average price fetch took {avg_fetch:.2f}s - consider batching or caching")
    
    if not errors and total_time < 10:
        print("✅ Performance is good - all steps completed quickly")
    elif not errors:
        print("⚠️  Performance is acceptable but could be improved")
    else:
        print("❌ Performance issues detected - see errors above")
    
    print()
    
    return {
        'timings': timings,
        'errors': errors,
        'total_time': total_time,
        'results_count': len(results) if 'results' in locals() else 0
    }

if __name__ == "__main__":
    result = test_bearish_performance()
    sys.exit(0 if len(result['errors']) == 0 else 1)

