#!/usr/bin/env python3
"""
Test to verify events are fetched and can be matched to recovery history drops
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_recovery_events_fetching():
    """Test that events are fetched for the extended period and can be matched"""
    print("=" * 80)
    print("RECOVERY HISTORY EVENTS TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Test case: KRMN on Nov 13, 2025 (bearish_date)
    ticker = 'KRMN'
    bearish_date = datetime(2025, 11, 13, tzinfo=timezone.utc)
    target_date = datetime(2025, 12, 31, tzinfo=timezone.utc)
    
    print(f"Ticker: {ticker}")
    print(f"Bearish Date: {bearish_date.date()}")
    print(f"Target Date: {target_date.date()}")
    print()
    
    # Calculate the extended date range (120 days before bearish_date to target_date)
    events_start_date = bearish_date - timedelta(days=120)
    print(f"Events fetch range: {events_start_date.date()} to {target_date.date()}")
    print()
    
    # Fetch events using the same method as the backend
    print("Fetching events...")
    try:
        sec_events = tracker._check_earnings_dividends_sec(ticker, events_start_date, target_date, future_days=0)
        yfinance_events = tracker._check_earnings_dividends_yfinance(ticker, events_start_date, target_date, future_days=0)
        
        # Combine events
        all_events = sec_events.get('events_during', [])
        if yfinance_events:
            yfinance_events_during = yfinance_events.get('events_during', [])
            if yfinance_events_during:
                all_events.extend(yfinance_events_during)
        
        # Remove duplicates
        seen_events = set()
        unique_events = []
        for event in sorted(all_events, key=lambda x: (x.get('date', ''), x.get('type', ''))):
            event_key = (event.get('date', ''), event.get('type', ''), event.get('name', ''))
            if event_key not in seen_events:
                seen_events.add(event_key)
                unique_events.append(event)
        all_events = unique_events
        
        print(f"✅ Fetched {len(all_events)} unique events")
        print()
        
        if len(all_events) > 0:
            print("Event dates:")
            for i, event in enumerate(all_events[:10]):  # Show first 10
                print(f"  {i+1}. {event.get('date')} - {event.get('type')} - {event.get('name')}")
            if len(all_events) > 10:
                print(f"  ... and {len(all_events) - 10} more")
            print()
        else:
            print("⚠️ No events found!")
            print()
        
        # Now test recovery history analysis
        print("Analyzing recovery history...")
        pct_threshold = -2.0  # -2% threshold
        bearish_date_str = bearish_date.strftime('%Y-%m-%d')
        
        # Get price history using the tracker's method
        price_history = tracker.get_stock_price_history(ticker, events_start_date, bearish_date)
        if not price_history:
            print("❌ Could not fetch price history")
            return
        
        print(f"✅ Fetched {len(price_history)} price history entries")
        print()
        
        # Analyze recovery history (without events - events will be matched in frontend)
        rh_result = tracker.analyze_recovery_history(price_history, pct_threshold, bearish_date_str, None)
        
        if isinstance(rh_result, dict):
            recovery_history = rh_result.get('items', [])
        else:
            recovery_history = rh_result
        
        print(f"✅ Found {len(recovery_history)} recovery history drops")
        print()
        
        if len(recovery_history) > 0:
            print("Recovery history drops:")
            for i, item in enumerate(recovery_history[:5]):  # Show first 5
                drop_date = item.get('drop_date')
                drop_pct = item.get('drop_pct')
                recovery_trading_days = item.get('recovery_trading_days')
                print(f"  {i+1}. {drop_date}: {drop_pct}% drop, recovery: {recovery_trading_days} trading days")
            if len(recovery_history) > 5:
                print(f"  ... and {len(recovery_history) - 5} more")
            print()
            
            # Now simulate frontend event matching
            print("=" * 80)
            print("FRONTEND EVENT MATCHING SIMULATION")
            print("=" * 80)
            print()
            
            for item in recovery_history[:5]:  # Test first 5 drops
                drop_date = item.get('drop_date')
                drop_pct = item.get('drop_pct')
                recovery_trading_days = item.get('recovery_trading_days')
                
                print(f"Drop: {drop_date} ({drop_pct}%), Recovery: {recovery_trading_days} trading days")
                
                # Only show events for drops that didn't recover within 7 trading days
                should_show_event = recovery_trading_days is None or recovery_trading_days > 7
                
                if should_show_event:
                    # Find events within 21 days of drop date
                    try:
                        drop_dt = datetime.strptime(drop_date, '%Y-%m-%d')
                        event_window_end = drop_dt + timedelta(days=21)
                        
                        closest_event = None
                        min_days_diff = None
                        
                        for event in all_events:
                            event_date_str = event.get('date', '')
                            if not event_date_str:
                                continue
                            
                            try:
                                event_dt = datetime.strptime(event_date_str, '%Y-%m-%d')
                                # Event must be on or after drop date and within 21 calendar days
                                if event_dt >= drop_dt and event_dt <= event_window_end:
                                    days_diff = (event_dt - drop_dt).days
                                    if min_days_diff is None or days_diff < min_days_diff:
                                        min_days_diff = days_diff
                                        closest_event = event
                            except ValueError:
                                continue
                        
                        if closest_event:
                            print(f"  ✅ Found event: {closest_event.get('name')} on {closest_event.get('date')} ({min_days_diff} days later)")
                        else:
                            print(f"  ❌ No event found within 21 days (checked {len(all_events)} events)")
                            print(f"     Window: {drop_date} to {event_window_end.strftime('%Y-%m-%d')}")
                    except Exception as e:
                        print(f"  ❌ Error matching events: {e}")
                else:
                    print(f"  ⏭️  Skipped (recovered within 7 trading days)")
                print()
        else:
            print("❌ No recovery history drops found")
            print()
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_recovery_events_fetching()

