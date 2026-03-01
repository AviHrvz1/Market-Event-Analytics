#!/usr/bin/env python3
"""
Comprehensive unit test to verify events filtering in backend
This test actually queries the backend and verifies the filtering logic works correctly.
It will FAIL if filtering is broken.
"""

import sys
import os
import warnings
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

# Suppress warnings
warnings.filterwarnings('ignore')
os.environ['PYTHONWARNINGS'] = 'ignore'

def test_events_filtering_comprehensive():
    """Test events filtering for KRMN - this test will FAIL if filtering is broken"""
    
    # Query parameters (matching the user's query)
    bearish_date_str = "2025-11-11"  # Parameter date
    target_date_str = "2025-12-31"
    filter_type = "bearish"
    pct_threshold = -4.0
    flexible_days = 2
    ticker_filter = "KRMN"
    industry = ""
    
    print("=" * 80)
    print("TEST: Events Filtering Verification")
    print("=" * 80)
    print(f"Query: bearish_date={bearish_date_str}, target_date={target_date_str}, flexible_days={flexible_days}, ticker={ticker_filter}")
    print()
    
    try:
        # Parse dates
        bearish_date = datetime.strptime(bearish_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        
        # Initialize tracker
        tracker = LayoffTracker()
        
        # Run bearish analytics (ACTUAL BACKEND CALL)
        # Suppress stdout to reduce noise
        import io
        from contextlib import redirect_stdout, redirect_stderr
        
        # Capture output but only show [EVENTS FILTER] messages
        captured_output = io.StringIO()
        with redirect_stdout(captured_output), redirect_stderr(captured_output):
            results, logs = tracker.get_bearish_analytics(
                bearish_date=bearish_date,
                target_date=target_date,
                industry=industry if industry else None,
                filter_type=filter_type,
                pct_threshold=pct_threshold,
                flexible_days=flexible_days,
                ticker_filter=ticker_filter
            )
        
        # Extract only [EVENTS FILTER] messages from captured output
        output_lines = captured_output.getvalue().split('\n')
        events_filter_lines = [line for line in output_lines if '[EVENTS FILTER]' in line]
        
        if events_filter_lines:
            print("Backend Filtering Logs:")
            for line in events_filter_lines:
                print(f"  {line}")
            print()
        
        print("=" * 80)
        print("VERIFICATION")
        print("=" * 80)
        print()
        
        # Find KRMN in results
        krmn_result = None
        for stock in results:
            if stock.get('ticker') == ticker_filter:
                krmn_result = stock
                break
        
        if not krmn_result:
            print(f"❌ FAIL: {ticker_filter} not found in results")
            print(f"   Found {len(results)} stocks total")
            if results:
                print(f"   Tickers found: {[s.get('ticker') for s in results]}")
            return False
        
        print(f"✅ Found {ticker_filter} in results")
        print()
        
        # Get the ACTUAL bearish_date from stock_result (this is what matters!)
        actual_bearish_date_str = krmn_result.get('bearish_date')
        parameter_bearish_date_str = bearish_date_str
        
        print(f"📅 Date Information:")
        print(f"   Parameter bearish_date: {parameter_bearish_date_str}")
        print(f"   Actual bearish_date from stock_result: {actual_bearish_date_str}")
        if actual_bearish_date_str != parameter_bearish_date_str:
            print(f"   ⚠️  Note: Actual date differs from parameter (flexible_days={flexible_days} was used)")
        print()
        
        if not actual_bearish_date_str:
            print(f"❌ FAIL: stock_result.bearish_date is None or missing!")
            return False
        
        # Get events data
        earnings_dividends = krmn_result.get('earnings_dividends', {})
        events_during = earnings_dividends.get('events_during', [])
        all_events_for_recovery = earnings_dividends.get('all_events_for_recovery', [])
        
        print(f"📊 Events Data:")
        print(f"   events_during count: {len(events_during)}")
        print(f"   all_events_for_recovery count: {len(all_events_for_recovery)}")
        print()
        
        # CRITICAL TEST 1: Verify events_during only contains events between ACTUAL bearish_date and target_date
        print("TEST 1: events_during filtering")
        print(f"  Range: {actual_bearish_date_str} to {target_date_str}")
        print(f"  events_during count: {len(events_during)}")
        
        actual_bearish_date_obj = datetime.strptime(actual_bearish_date_str, '%Y-%m-%d').date()
        target_date_obj = target_date.date()
        
        events_outside_range = []
        events_inside_range = []
        
        for event in events_during:
            event_date_str = event.get('date', '')
            if not event_date_str:
                continue
            
            try:
                event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
                
                if actual_bearish_date_obj <= event_date <= target_date_obj:
                    events_inside_range.append((event_date_str, event.get('type'), event.get('name')))
                else:
                    events_outside_range.append((event_date_str, event.get('type'), event.get('name')))
            except ValueError:
                continue
        
        if events_inside_range:
            print(f"  ✓ Events inside range: {[d[0] for d in events_inside_range]}")
        
        # THIS IS THE CRITICAL TEST - events_during MUST NOT contain events outside the range
        if events_outside_range:
            print(f"  ❌ FAIL: Found {len(events_outside_range)} events OUTSIDE the range:")
            for date_str, event_type, event_name in events_outside_range:
                print(f"     ✗ {date_str}: {event_type} - {event_name}")
            print(f"  Expected: Only events between {actual_bearish_date_str} and {target_date_str}")
            return False
        else:
            print(f"  ✅ PASS: All {len(events_inside_range)} events are within the range")
        print()
        
        # TEST 2: Verify all_events_for_recovery contains full list
        print("TEST 2: all_events_for_recovery")
        print(f"  all_events_for_recovery count: {len(all_events_for_recovery)}")
        
        if len(all_events_for_recovery) == 0:
            print(f"  ⚠️  WARNING: all_events_for_recovery is empty (might not be serialized correctly)")
        elif len(all_events_for_recovery) < len(events_during):
            print(f"  ⚠️  WARNING: all_events_for_recovery has fewer events than events_during")
        else:
            print(f"  ✅ PASS: all_events_for_recovery has {len(all_events_for_recovery)} events")
            if all_events_for_recovery:
                event_dates = [e.get('date') for e in all_events_for_recovery if e.get('date')]
                print(f"  Event dates: {event_dates}")
        print()
        
        # TEST 3: Verify all_events_for_recovery contains all events from events_during
        print("TEST 3: all_events_for_recovery contains all events_during events")
        events_during_dates = set(event.get('date') for event in events_during if event.get('date'))
        all_events_dates = set(event.get('date') for event in all_events_for_recovery if event.get('date'))
        missing_events = events_during_dates - all_events_dates
        
        if missing_events:
            print(f"  ❌ FAIL: {len(missing_events)} events from events_during are missing")
            return False
        else:
            print(f"  ✅ PASS: All events_during events are in all_events_for_recovery")
        print()
        
        # Final verification: No events before actual_bearish_date in events_during
        print("FINAL VERIFICATION")
        events_before_in_during = [e for e in events_during 
                                   if e.get('date') and e.get('date') < actual_bearish_date_str]
        
        if events_before_in_during:
            print(f"  ❌ CRITICAL FAIL: Found {len(events_before_in_during)} events in events_during BEFORE {actual_bearish_date_str}:")
            for event in events_before_in_during:
                print(f"     ✗ {event.get('date')}: {event.get('type')} - {event.get('name')}")
            return False
        else:
            print(f"  ✅ PASS: No events before {actual_bearish_date_str} in events_during")
        
        print()
        print("=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        print(f"Summary: events_during={len(events_during)} (filtered), all_events_for_recovery={len(all_events_for_recovery)} (full list)")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_events_filtering_comprehensive()
    sys.exit(0 if success else 1)
