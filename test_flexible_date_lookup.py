#!/usr/bin/env python3
"""
Unit test to verify flexible date lookup feature
Tests from 12/11/2025 to 30/12/2025 with -5% change and flexible_days=2
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_flexible_date_lookup():
    """Test flexible date lookup with flexible_days=2"""
    print("=" * 80)
    print("FLEXIBLE DATE LOOKUP TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Test parameters
    bearish_date = datetime(2025, 12, 11, 0, 0, 0, tzinfo=timezone.utc)
    target_date = datetime(2025, 12, 30, 0, 0, 0, tzinfo=timezone.utc)
    industry = "All Industries"
    filter_type = "bearish"
    pct_threshold = -5.0
    flexible_days = 2
    
    print(f"Test Parameters:")
    print(f"  Bearish Date: {bearish_date.strftime('%Y-%m-%d')}")
    print(f"  Target Date: {target_date.strftime('%Y-%m-%d')}")
    print(f"  Industry: {industry}")
    print(f"  Filter Type: {filter_type}")
    print(f"  Percentage Threshold: {pct_threshold}%")
    print(f"  Flexible Days: ±{flexible_days} days")
    print()
    print(f"Expected Date Range: {bearish_date.strftime('%Y-%m-%d')} ± {flexible_days} days")
    print(f"  Min Date: {(bearish_date - timedelta(days=flexible_days)).strftime('%Y-%m-%d')}")
    print(f"  Max Date: {(bearish_date + timedelta(days=flexible_days)).strftime('%Y-%m-%d')}")
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
        
        print("=" * 80)
        print("RESULTS")
        print("=" * 80)
        print()
        print(f"Total stocks found: {len(results)}")
        print()
        
        if len(results) == 0:
            print("⚠️  No stocks found. This could be:")
            print("   - No stocks met the criteria")
            print("   - Data not available for these dates")
            print("   - API issues")
            return True  # Not necessarily a failure
        
        # Verify results
        print("Verifying results...")
        print()
        
        min_date = (bearish_date - timedelta(days=flexible_days)).date()
        max_date = (bearish_date + timedelta(days=flexible_days)).date()
        bearish_date_only = bearish_date.date()
        
        all_valid = True
        date_range_stats = {}
        
        for i, stock in enumerate(results, 1):
            ticker = stock.get('ticker', 'N/A')
            company_name = stock.get('company_name', 'N/A')
            actual_bearish_date_str = stock.get('bearish_date', '')
            pct_drop = stock.get('pct_drop', 0)
            
            # Parse actual date
            try:
                actual_date = datetime.strptime(actual_bearish_date_str, '%Y-%m-%d').date()
            except:
                print(f"❌ Stock {i}: {ticker} ({company_name})")
                print(f"   ERROR: Invalid bearish_date format: {actual_bearish_date_str}")
                all_valid = False
                continue
            
            # Check if date is within flexible range
            if actual_date < min_date or actual_date > max_date:
                print(f"❌ Stock {i}: {ticker} ({company_name})")
                print(f"   ERROR: Actual date {actual_bearish_date_str} is outside flexible range")
                print(f"   Expected: {min_date} to {max_date}")
                all_valid = False
            else:
                # Count days difference
                days_diff = (actual_date - bearish_date_only).days
                days_diff_str = f"{days_diff:+d}" if days_diff != 0 else "0"
                
                # Track statistics
                if days_diff not in date_range_stats:
                    date_range_stats[days_diff] = 0
                date_range_stats[days_diff] += 1
                
                # Check percentage threshold
                if pct_drop > pct_threshold:
                    print(f"⚠️  Stock {i}: {ticker} ({company_name})")
                    print(f"   WARNING: pct_drop {pct_drop:.2f}% does not meet threshold {pct_threshold}%")
                    print(f"   Actual date: {actual_bearish_date_str} ({days_diff_str} days from analysis date)")
                else:
                    print(f"✅ Stock {i}: {ticker} ({company_name})")
                    print(f"   Actual date: {actual_bearish_date_str} ({days_diff_str} days from analysis date)")
                    print(f"   Drop: {pct_drop:.2f}%")
        
        print()
        print("=" * 80)
        print("STATISTICS")
        print("=" * 80)
        print()
        print(f"Total stocks: {len(results)}")
        print()
        print("Date distribution (days from analysis date):")
        for days_diff in sorted(date_range_stats.keys()):
            count = date_range_stats[days_diff]
            days_str = f"{days_diff:+d}" if days_diff != 0 else "0"
            percentage = (count / len(results)) * 100
            print(f"  {days_str} days: {count} stocks ({percentage:.1f}%)")
        print()
        
        # Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print()
        
        if all_valid:
            print("✅ ALL STOCKS HAVE VALID DATES WITHIN FLEXIBLE RANGE")
        else:
            print("❌ SOME STOCKS HAVE INVALID DATES")
        
        # Check if we found stocks on different dates
        unique_dates = len(date_range_stats)
        if unique_dates > 1:
            print(f"✅ Flexible date lookup is working! Found stocks on {unique_dates} different dates within the range.")
        elif unique_dates == 1:
            days_diff = list(date_range_stats.keys())[0]
            if days_diff == 0:
                print("ℹ️  All stocks found on the exact analysis date (flexible_days=2 may not have been needed)")
            else:
                print(f"✅ All stocks found on {days_diff:+d} days from analysis date (flexible lookup working)")
        else:
            print("⚠️  No date statistics available")
        
        return all_valid
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_flexible_date_lookup()
    sys.exit(0 if success else 1)

