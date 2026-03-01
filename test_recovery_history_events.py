#!/usr/bin/env python3
"""Test recovery history events for KRMN to diagnose why events aren't showing"""

import sys
from datetime import datetime, timedelta, timezone
from main import LayoffTracker
import json

def test_recovery_history_events():
    """Test recovery history events for KRMN with Nov 13, 2025 bearish date"""
    print("=" * 80)
    print("RECOVERY HISTORY EVENTS DIAGNOSIS TEST")
    print("=" * 80)
    print()
    
    ticker = "KRMN"
    bearish_date = datetime(2025, 11, 13, tzinfo=timezone.utc)
    target_date = datetime(2025, 12, 31, tzinfo=timezone.utc)
    pct_threshold = -5.0
    flexible_days = 2
    industry = "Technology"
    
    print(f"Testing: {ticker}")
    print(f"Bearish Date: {bearish_date.strftime('%Y-%m-%d')}")
    print(f"Target Date: {target_date.strftime('%Y-%m-%d')}")
    print(f"Pct Threshold: {pct_threshold}%")
    print(f"Flexible Days: {flexible_days}")
    print(f"Industry: {industry}")
    print()
    
    # Initialize tracker
    print("Step 1: Initializing LayoffTracker...")
    tracker = LayoffTracker()
    print("✅ Tracker initialized")
    print()
    
    # Step 2: Call get_bearish_analytics (simulating the API call)
    print("Step 2: Calling get_bearish_analytics...")
    print("  (This simulates: /api/bearish-analytics/stream?bearish_date=2025-11-13&target_date=2025-12-31&filter_type=bearish&pct_threshold=-5&flexible_days=2&industry=Technology)")
    print()
    
    try:
        results, logs = tracker.get_bearish_analytics(
            bearish_date=bearish_date,
            target_date=target_date,
            industry=industry,
            filter_type='bearish',
            pct_threshold=pct_threshold,
            flexible_days=flexible_days,
            ticker_filter=None
        )
        
        print(f"✅ get_bearish_analytics returned {len(results)} results")
        print()
        
        # Find KRMN in results
        krmn_result = None
        for result in results:
            if result.get('ticker') == ticker:
                krmn_result = result
                break
        
        if not krmn_result:
            print(f"❌ KRMN not found in results")
            print(f"   Available tickers: {[r.get('ticker') for r in results]}")
            return False
        
        print(f"✅ Found KRMN in results")
        print()
        
        # Check recovery history
        print("Step 3: Checking recovery history...")
        recovery_history = krmn_result.get('recovery_history', [])
        recovery_history_summary = krmn_result.get('recovery_history_summary')
        
        if not recovery_history:
            print("❌ No recovery history found")
            return False
        
        print(f"✅ Found {len(recovery_history)} recovery history items")
        print()
        
        # Check each recovery history item for events
        print("Step 4: Checking for events in recovery history items...")
        print()
        
        events_found_count = 0
        events_missing_count = 0
        
        for idx, item in enumerate(recovery_history):
            drop_date = item.get('drop_date', '')
            drop_pct = item.get('drop_pct', 0)
            recovery_trading_days = item.get('recovery_trading_days')
            event_info = item.get('event_info')
            
            print(f"  Item {idx + 1}: {drop_date} ({drop_pct}% drop)")
            print(f"    - Recovery trading days: {recovery_trading_days}")
            print(f"    - Event info: {event_info}")
            
            if event_info:
                events_found_count += 1
                print(f"    ✅ EVENT FOUND: {event_info.get('type')} on {event_info.get('date')} ({event_info.get('days_after_drop')} days later)")
            else:
                events_missing_count += 1
                print(f"    ❌ NO EVENT")
                
                # Check why no event
                if recovery_trading_days is not None and recovery_trading_days <= 7:
                    print(f"      Reason: Recovered within 7 trading days (events only shown for drops that didn't recover within 7 days)")
                else:
                    print(f"      Reason: Unknown (should have event if one exists within 21 days)")
            
            print()
        
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total recovery history items: {len(recovery_history)}")
        print(f"Items with events: {events_found_count}")
        print(f"Items without events: {events_missing_count}")
        print()
        
        # Step 5: Manually test event fetching
        print("Step 5: Manually testing event fetching...")
        print()
        
        try:
            # Fetch events for 120 days before bearish_date
            events_start_date = bearish_date - timedelta(days=120)
            events_end_date = bearish_date
            
            print(f"  Fetching events from {events_start_date.strftime('%Y-%m-%d')} to {events_end_date.strftime('%Y-%m-%d')}")
            
            sec_events = tracker._check_earnings_dividends_sec(ticker, events_start_date, events_end_date, future_days=0)
            yfinance_events = tracker._check_earnings_dividends_yfinance(ticker, events_start_date, events_end_date, future_days=0)
            
            events_during = sec_events.get('events_during', [])
            if yfinance_events:
                yfinance_events_during = yfinance_events.get('events_during', [])
                if yfinance_events_during:
                    events_during.extend(yfinance_events_during)
            
            print(f"  ✅ Fetched {len(events_during)} events")
            
            if events_during:
                print(f"  Events found:")
                for event in events_during:
                    print(f"    - {event.get('date')}: {event.get('type')} - {event.get('name')}")
                
                # Check if any events match the drop dates
                print()
                print("  Checking event matches for recovery history drops:")
                for item in recovery_history:
                    drop_date = item.get('drop_date', '')
                    recovery_trading_days = item.get('recovery_trading_days')
                    
                    if recovery_trading_days is None or recovery_trading_days > 7:
                        # Should have event if one exists
                        drop_dt = datetime.strptime(drop_date, '%Y-%m-%d')
                        event_window_end = drop_dt + timedelta(days=21)
                        
                        matching_events = []
                        for event in events_during:
                            event_date_str = event.get('date', '')
                            if event_date_str:
                                try:
                                    event_dt = datetime.strptime(event_date_str, '%Y-%m-%d')
                                    if event_dt >= drop_dt and event_dt <= event_window_end:
                                        days_diff = (event_dt - drop_dt).days
                                        matching_events.append((event, days_diff))
                                except ValueError:
                                    pass
                        
                        if matching_events:
                            print(f"    ✅ {drop_date}: Found {len(matching_events)} matching event(s):")
                            for event, days_diff in matching_events:
                                print(f"       - {event.get('date')}: {event.get('type')} ({days_diff} days later)")
                        else:
                            print(f"    ❌ {drop_date}: No matching events found (checked up to {event_window_end.strftime('%Y-%m-%d')})")
            else:
                print(f"  ⚠️  No events found - this might be why events aren't showing")
                
        except Exception as e:
            print(f"  ❌ Error fetching events: {e}")
            import traceback
            traceback.print_exc()
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_recovery_history_events()
    print()
    if success:
        print("=" * 80)
        print("✅ TEST COMPLETE")
        print("=" * 80)
    else:
        print("=" * 80)
        print("❌ TEST FAILED")
        print("=" * 80)
    sys.exit(0 if success else 1)

