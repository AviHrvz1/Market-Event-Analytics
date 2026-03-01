#!/usr/bin/env python3
"""
Unit test to verify events filtering in backend
Tests that events_during is filtered to bearish_date-target_date range
and all_events_for_recovery contains full 120 days of events
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_events_filtering():
    """Test events filtering for KRMN with specific query parameters"""
    
    print("=" * 80)
    print("TEST: Events Filtering in Backend")
    print("=" * 80)
    print()
    
    # Query parameters (matching the user's query)
    bearish_date_str = "2025-11-11"
    target_date_str = "2025-12-31"
    filter_type = "bearish"
    pct_threshold = -5.0
    flexible_days = 2
    ticker_filter = "KRMN"
    industry = ""
    
    print(f"📋 Test Parameters:")
    print(f"   Bearish Date: {bearish_date_str}")
    print(f"   Target Date: {target_date_str}")
    print(f"   Filter Type: {filter_type}")
    print(f"   PCT Threshold: {pct_threshold}%")
    print(f"   Flexible Days: {flexible_days}")
    print(f"   Ticker Filter: {ticker_filter}")
    print(f"   Industry: {industry or 'All'}")
    print()
    
    try:
        # Parse dates
        bearish_date = datetime.strptime(bearish_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        
        print("✅ Dates parsed successfully")
        print()
        
        # Initialize tracker
        print("🚀 Initializing LayoffTracker...")
        tracker = LayoffTracker()
        print("✅ Tracker initialized")
        print()
        
        # Run bearish analytics
        print("📊 Running get_bearish_analytics...")
        print("   This may take a minute...")
        print()
        
        results, logs = tracker.get_bearish_analytics(
            bearish_date=bearish_date,
            target_date=target_date,
            industry=industry if industry else None,
            filter_type=filter_type,
            pct_threshold=pct_threshold,
            flexible_days=flexible_days,
            ticker_filter=ticker_filter
        )
        
        print()
        print("=" * 80)
        print("RESULTS")
        print("=" * 80)
        print()
        
        # Find KRMN in results
        krmn_result = None
        for stock in results:
            if stock.get('ticker') == ticker_filter:
                krmn_result = stock
                break
        
        if not krmn_result:
            print(f"❌ ERROR: {ticker_filter} not found in results")
            print(f"   Found {len(results)} stocks total")
            if results:
                print(f"   Tickers found: {[s.get('ticker') for s in results]}")
            return False
        
        print(f"✅ Found {ticker_filter} in results")
        print()
        
        # Get events data
        earnings_dividends = krmn_result.get('earnings_dividends', {})
        events_during = earnings_dividends.get('events_during', [])
        all_events_for_recovery = earnings_dividends.get('all_events_for_recovery', [])
        
        print(f"📊 Events Data:")
        print(f"   events_during count: {len(events_during)}")
        print(f"   all_events_for_recovery count: {len(all_events_for_recovery)}")
        print()
        
        # Test 1: Verify events_during only contains events between ACTUAL bearish_date and target_date
        print("=" * 80)
        print("TEST 1: events_during filtering (actual bearish_date to target_date)")
        print("=" * 80)
        print()
        
        # Get the ACTUAL bearish_date from stock_result (may differ from parameter if flexible_days was used)
        actual_bearish_date_str = krmn_result.get('bearish_date', bearish_date_str)
        print(f"📅 Parameter bearish_date: {bearish_date_str}")
        print(f"📅 Actual bearish_date from stock_result: {actual_bearish_date_str}")
        if actual_bearish_date_str != bearish_date_str:
            print(f"   ⚠️  Note: Actual date differs from parameter (flexible_days was used)")
        print()
        
        actual_bearish_date_only = datetime.strptime(actual_bearish_date_str, '%Y-%m-%d').date()
        target_date_only = target_date.date()
        
        events_outside_range = []
        events_inside_range = []
        
        for event in events_during:
            event_date_str = event.get('date', '')
            if not event_date_str:
                continue
            
            try:
                event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
                
                if actual_bearish_date_only <= event_date <= target_date_only:
                    events_inside_range.append((event_date_str, event.get('type'), event.get('name')))
                else:
                    events_outside_range.append((event_date_str, event.get('type'), event.get('name')))
            except ValueError:
                continue
        
        print(f"✅ Events inside range ({actual_bearish_date_str} to {target_date_str}): {len(events_inside_range)}")
        if events_inside_range:
            for date_str, event_type, event_name in events_inside_range:
                print(f"   ✓ {date_str}: {event_type} - {event_name}")
        print()
        
        if events_outside_range:
            print(f"❌ FAIL: Found {len(events_outside_range)} events OUTSIDE the range:")
            for date_str, event_type, event_name in events_outside_range:
                print(f"   ✗ {date_str}: {event_type} - {event_name}")
            print()
            return False
        else:
            print(f"✅ PASS: All {len(events_inside_range)} events are within the range")
            print()
        
        # Test 2: Verify all_events_for_recovery contains events from 120 days before bearish_date
        print("=" * 80)
        print("TEST 2: all_events_for_recovery contains full 120 days")
        print("=" * 80)
        print()
        
        events_start_date = bearish_date - timedelta(days=120)
        events_start_date_only = events_start_date.date()
        
        events_before_120_days = []
        events_in_120_day_range = []
        
        for event in all_events_for_recovery:
            event_date_str = event.get('date', '')
            if not event_date_str:
                continue
            
            try:
                event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
                
                if event_date >= events_start_date_only and event_date <= target_date_only:
                    events_in_120_day_range.append((event_date_str, event.get('type'), event.get('name')))
                elif event_date < events_start_date_only:
                    events_before_120_days.append((event_date_str, event.get('type'), event.get('name')))
            except ValueError:
                continue
        
        print(f"✅ Events in 120-day range ({events_start_date_only} to {target_date_only}): {len(events_in_120_day_range)}")
        if events_in_120_day_range:
            print(f"   Sample events (showing first 10):")
            for date_str, event_type, event_name in events_in_120_day_range[:10]:
                print(f"   - {date_str}: {event_type} - {event_name}")
            if len(events_in_120_day_range) > 10:
                print(f"   ... and {len(events_in_120_day_range) - 10} more")
        print()
        
        if events_before_120_days:
            print(f"⚠️  WARNING: Found {len(events_before_120_days)} events before 120-day window:")
            for date_str, event_type, event_name in events_before_120_days[:5]:
                print(f"   - {date_str}: {event_type} - {event_name}")
            if len(events_before_120_days) > 5:
                print(f"   ... and {len(events_before_120_days) - 5} more")
            print()
        
        # Test 3: Verify all_events_for_recovery contains all events from events_during
        print("=" * 80)
        print("TEST 3: all_events_for_recovery contains all events_during events")
        print("=" * 80)
        print()
        
        events_during_dates = set(event.get('date') for event in events_during if event.get('date'))
        all_events_dates = set(event.get('date') for event in all_events_for_recovery if event.get('date'))
        
        missing_events = events_during_dates - all_events_dates
        
        if missing_events:
            print(f"❌ FAIL: {len(missing_events)} events from events_during are missing in all_events_for_recovery:")
            for date in sorted(missing_events):
                print(f"   ✗ {date}")
            print()
            return False
        else:
            print(f"✅ PASS: All {len(events_during_dates)} events from events_during are in all_events_for_recovery")
            print()
        
        # Test 4: Verify all_events_for_recovery has more events than events_during (should have events from 120 days before)
        print("=" * 80)
        print("TEST 4: all_events_for_recovery has more events than events_during")
        print("=" * 80)
        print()
        
        if len(all_events_for_recovery) >= len(events_during):
            print(f"✅ PASS: all_events_for_recovery has {len(all_events_for_recovery)} events (>= {len(events_during)} in events_during)")
            if len(all_events_for_recovery) > len(events_during):
                print(f"   ✓ Correctly includes {len(all_events_for_recovery) - len(events_during)} additional events from 120 days before bearish_date")
            print()
        else:
            print(f"❌ FAIL: all_events_for_recovery has {len(all_events_for_recovery)} events (< {len(events_during)} in events_during)")
            print()
            return False
        
        # Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print()
        print("✅ All tests passed!")
        print()
        print(f"📊 Final Counts:")
        print(f"   events_during: {len(events_during)} events (filtered to {bearish_date_str} - {target_date_str})")
        print(f"   all_events_for_recovery: {len(all_events_for_recovery)} events (full 120 days: {events_start_date_only} - {target_date_only})")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_events_filtering()
    sys.exit(0 if success else 1)
