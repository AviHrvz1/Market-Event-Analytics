#!/usr/bin/env python3
"""
Unit test to verify recovery history calculation for KRMN
Tests what occurrences we get and what averages should be calculated
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker
import json

def match_events_to_recovery_items(recovery_history, all_events):
    """Match events to recovery history items (same logic as frontend)"""
    items_with_event_info = []
    
    for item in recovery_history:
        drop_date = item.get('drop_date', '')
        if not drop_date or not all_events or len(all_events) == 0:
            items_with_event_info.append({**item, 'hasEvent': False})
            continue
        
        try:
            drop_date_obj = datetime.strptime(drop_date, '%Y-%m-%d')
            event_window_end = drop_date_obj + timedelta(days=21)
            
            has_event = False
            # Find if any event occurred within 21 calendar days after drop date (including same day)
            for event in all_events:
                event_date_str = event.get('date', '')
                if not event_date_str:
                    continue
                
                try:
                    event_date_obj = datetime.strptime(event_date_str, '%Y-%m-%d')
                    # Event must be on or after drop date and within 21 calendar days
                    if event_date_obj >= drop_date_obj and event_date_obj <= event_window_end:
                        has_event = True
                        break
                except ValueError:
                    continue
        except ValueError:
            has_event = False
        
        items_with_event_info.append({**item, 'hasEvent': has_event})
    
    return items_with_event_info

def calculate_averages(drops_without_events):
    """Calculate averages from drops without events (same logic as frontend)"""
    if not drops_without_events or len(drops_without_events) == 0:
        return {
            'total_drops': 0,
            'recovered_count_7': 0,
            'recovered_count_40': 0,
            'recovery_percent_7': 0.0,
            'recovery_percent_40': 0.0,
            'avg_recovery_pct': 'N/A',
            'avg_days_to_recover': 'N/A'
        }
    
    # Calculate 7 trading days metric
    recovered_within_7_trading = [
        item for item in drops_without_events
        if item.get('recovery_pct') is not None 
        and item.get('recovery_trading_days') is not None
        and item.get('recovery_trading_days') <= 7
    ]
    
    # Calculate 40 calendar days metric
    recovered_within_40_days = [
        item for item in drops_without_events
        if item.get('recovery_pct') is not None 
        and item.get('recovery_days') is not None
        and item.get('recovery_days') <= 40
    ]
    
    # Calculate average recovery from ALL recovered drops
    all_recovered = [
        item for item in drops_without_events
        if item.get('recovery_pct') is not None 
        and item.get('recovery_days') is not None
    ]
    
    total_drops = len(drops_without_events)
    recovered_count_7 = len(recovered_within_7_trading)
    recovered_count_40 = len(recovered_within_40_days)
    
    recovery_percent_7 = (recovered_count_7 / total_drops * 100.0) if total_drops > 0 else 0.0
    recovery_percent_40 = (recovered_count_40 / total_drops * 100.0) if total_drops > 0 else 0.0
    
    if len(all_recovered) > 0:
        avg_recovery_pct = sum(item['recovery_pct'] for item in all_recovered) / len(all_recovered)
        avg_days_to_recover = sum(item['recovery_days'] for item in all_recovered) / len(all_recovered)
    else:
        avg_recovery_pct = 'N/A'
        avg_days_to_recover = 'N/A'
    
    return {
        'total_drops': total_drops,
        'recovered_count_7': recovered_count_7,
        'recovered_count_40': recovered_count_40,
        'recovery_percent_7': round(recovery_percent_7, 1),
        'recovery_percent_40': round(recovery_percent_40, 1),
        'avg_recovery_pct': round(avg_recovery_pct, 1) if avg_recovery_pct != 'N/A' else 'N/A',
        'avg_days_to_recover': round(avg_days_to_recover, 1) if avg_days_to_recover != 'N/A' else 'N/A'
    }

def test_krmn_recovery_calculation():
    """Test recovery history calculation for KRMN"""
    print("=" * 80)
    print("KRMN RECOVERY HISTORY CALCULATION TEST")
    print("=" * 80)
    print()
    
    ticker = "KRMN"
    bearish_date = datetime(2025, 11, 11, tzinfo=timezone.utc)  # Actual API call uses 2025-11-11
    target_date = datetime(2025, 12, 31, tzinfo=timezone.utc)
    pct_threshold = -5.0  # From API call
    flexible_days = 2  # From API call
    
    print(f"Ticker: {ticker}")
    print(f"Bearish Date: {bearish_date.strftime('%Y-%m-%d')}")
    print(f"Target Date: {target_date.strftime('%Y-%m-%d')}")
    print(f"Pct Threshold: {pct_threshold}%")
    print()
    
    tracker = LayoffTracker()
    
    # Step 1: Get price history
    print("Step 1: Fetching price history...")
    graph_start_date = bearish_date - timedelta(days=120)
    price_history = tracker.get_stock_price_history(ticker, graph_start_date, target_date)
    
    if not price_history:
        print("❌ No price history found")
        return False
    
    print(f"✅ Found {len(price_history)} price history entries")
    print()
    
    # Step 2: Analyze recovery history
    print("Step 2: Analyzing recovery history...")
    bearish_date_str = bearish_date.strftime('%Y-%m-%d')
    rh_result = tracker.analyze_recovery_history(price_history, pct_threshold, bearish_date_str, None)
    
    if isinstance(rh_result, dict):
        recovery_history = rh_result.get('items', [])
    else:
        recovery_history = rh_result
    
    print(f"✅ Found {len(recovery_history)} recovery history items")
    print()
    
    # Step 3: Get events
    print("Step 3: Fetching events...")
    events_start_date = bearish_date - timedelta(days=120)
    earnings_dividends = tracker._check_earnings_dividends_sec(ticker, events_start_date, target_date, future_days=0)
    yfinance_result = tracker._check_earnings_dividends_yfinance(ticker, events_start_date, target_date, future_days=0)
    
    all_events = earnings_dividends.get('events_during', [])
    if yfinance_result:
        yfinance_events = yfinance_result.get('events_during', [])
        all_events.extend(yfinance_events)
    
    print(f"✅ Found {len(all_events)} events")
    if all_events:
        print("   Events:")
        for event in all_events:
            print(f"     - {event.get('date')}: {event.get('type')} - {event.get('name')}")
    print()
    
    # Step 4: Match events to recovery history items
    print("Step 4: Matching events to recovery history items...")
    items_with_event_info = match_events_to_recovery_items(recovery_history, all_events)
    
    print(f"✅ Matched events to {len(items_with_event_info)} items")
    print()
    
    # Step 5: Show all occurrences
    print("=" * 80)
    print("ALL OCCURRENCES (Before Filtering):")
    print("=" * 80)
    for idx, item in enumerate(items_with_event_info, 1):
        drop_date = item.get('drop_date', '')
        drop_pct = item.get('drop_pct', 0)
        recovery_trading_days = item.get('recovery_trading_days')
        recovery_days = item.get('recovery_days')
        recovery_date = item.get('recovery_date')
        recovery_pct = item.get('recovery_pct')
        has_event = item.get('hasEvent', False)
        
        event_str = " 📅 Has Event" if has_event else ""
        
        if recovery_pct is not None and recovery_date:
            print(f"{idx}. {drop_date}: {drop_pct:.1f}% → {recovery_trading_days} trading days → {recovery_date} +{recovery_pct:.1f}%{event_str}")
        else:
            print(f"{idx}. {drop_date}: {drop_pct:.1f}% → No recovery{event_str}")
    print()
    
    # Step 6: Filter out items with events
    print("=" * 80)
    print("OCCURRENCES WITHOUT EVENTS (Used for Calculations):")
    print("=" * 80)
    drops_without_events = [item for item in items_with_event_info if not item.get('hasEvent', False)]
    
    for idx, item in enumerate(drops_without_events, 1):
        drop_date = item.get('drop_date', '')
        drop_pct = item.get('drop_pct', 0)
        recovery_trading_days = item.get('recovery_trading_days')
        recovery_date = item.get('recovery_date')
        recovery_pct = item.get('recovery_pct')
        
        if recovery_pct is not None and recovery_date:
            print(f"{idx}. {drop_date}: {drop_pct:.1f}% → {recovery_trading_days} trading days → {recovery_date} +{recovery_pct:.1f}%")
        else:
            print(f"{idx}. {drop_date}: {drop_pct:.1f}% → No recovery")
    print()
    
    # Step 7: Calculate averages
    print("=" * 80)
    print("CALCULATED AVERAGES:")
    print("=" * 80)
    averages = calculate_averages(drops_without_events)
    
    print(f"Total Drops (without events): {averages['total_drops']}")
    print(f"Recovered within 7 trading days: {averages['recovered_count_7']}/{averages['total_drops']} = {averages['recovery_percent_7']}%")
    print(f"Recovered within 40 days: {averages['recovered_count_40']}/{averages['total_drops']} = {averages['recovery_percent_40']}%")
    print(f"Avg Recovery: {averages['avg_recovery_pct']}")
    print(f"Avg Days: {averages['avg_days_to_recover']}")
    print()
    
    # Step 8: Expected display format
    print("=" * 80)
    print("EXPECTED DISPLAY IN UI:")
    print("=" * 80)
    print(f"{averages['recovery_percent_7']}%")
    print(f"({averages['recovered_count_7']}/{averages['total_drops']})")
    print("✓ within 7 trading days")
    print()
    print(f"{averages['recovery_percent_40']}%")
    print(f"({averages['recovered_count_40']}/{averages['total_drops']})")
    print("✓ within 40 days")
    print()
    print(f"Avg Recovery: {averages['avg_recovery_pct']}")
    print(f"Avg Days: {averages['avg_days_to_recover']}")
    print()
    
    return True

if __name__ == '__main__':
    try:
        test_krmn_recovery_calculation()
    except Exception as e:
        import traceback
        print(f"❌ Error: {e}")
        traceback.print_exc()
        sys.exit(1)
