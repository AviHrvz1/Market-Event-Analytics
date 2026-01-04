#!/usr/bin/env python3
"""
Unit test to verify volume percentages for FOLD (Amicus Therapeutics) on Dec 22, 2025
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_fold_volume_verification():
    """Verify volume percentages match displayed values"""
    print("=" * 80)
    print("FOLD VOLUME VERIFICATION TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Article data from user
    ticker = 'FOLD'
    company = 'AMICUS THERAPEUTICS'
    article_datetime_str = 'Mon, Dec 22, 2025 11:46'
    
    # Parse article datetime (assuming ET timezone, market open)
    # Dec 22, 2025 11:46 ET = 16:46 UTC (ET is UTC-5 in December)
    # NOTE: Dec 22, 2025 is in the future - we may not have real data for this date
    # But we can still test the calculation logic
    article_datetime = datetime(2025, 12, 22, 16, 46, 0, tzinfo=timezone.utc)  # 11:46 ET = 16:46 UTC
    
    print("⚠️  NOTE: Dec 22, 2025 is in the future. Test will attempt to fetch data,")
    print("   but may not have real historical data. This test verifies calculation logic.")
    print()
    
    print(f"Ticker: {ticker}")
    print(f"Company: {company}")
    print(f"Article Date: {article_datetime_str}")
    print(f"Article DateTime (UTC): {article_datetime.isoformat()}")
    print()
    
    # Expected volume changes from UI
    expected_volumes = {
        '11:46': 161.64,  # +161.64%
        '11:51': 99.42,   # +99.42%
        '11:56': -37.36,  # -37.36%
        '12:16': 142.90,  # +142.90%
        '12:46': 64.72,   # +64.72%
        '13:46': -42.51,  # -42.51%
        '14:46': None,    # No percentage shown (likely ±0.00%)
    }
    
    # Create mock layoff for testing
    mock_layoff = {
        'company_name': company,
        'stock_ticker': ticker,
        'datetime': article_datetime,
        'date': article_datetime.strftime('%Y-%m-%d'),
        'time': article_datetime.strftime('%H:%M:%S'),
        'url': 'https://test.com/fold',
        'title': f'{company} test article'
    }
    
    print("Fetching stock data and calculating volume changes...")
    print()
    
    try:
        # Calculate stock changes (this will fetch data and calculate volumes)
        stock_changes = tracker.calculate_stock_changes(mock_layoff)
        
        # Get base volume (volume at announcement time)
        base_price = stock_changes.get('base_price')
        print(f"Base Price: ${base_price:.2f}" if base_price else "Base Price: N/A")
        print()
        
        # First, let's see ALL available intervals and their volumes
        print("=" * 80)
        print("ALL AVAILABLE INTERVALS")
        print("=" * 80)
        print()
        
        all_intervals = ['1min', '2min', '3min', '4min', '5min', '10min', '30min', '1hr', '1.5hr', '2hr', '2.5hr', '3hr']
        for interval_name in all_intervals:
            volume_change_key = f'volume_change_{interval_name}'
            price_key = f'price_{interval_name}'
            change_key = f'change_{interval_name}'
            datetime_key = f'datetime_{interval_name}'
            
            vol_change = stock_changes.get(volume_change_key)
            price = stock_changes.get(price_key)
            change = stock_changes.get(change_key)
            dt_str = stock_changes.get(datetime_key)
            
            if vol_change is not None or price is not None:
                print(f"{interval_name:8s}: Vol={vol_change:+.2f}%" if vol_change is not None else f"{interval_name:8s}: Vol=N/A", end="")
                print(f"  Price=${price:.2f}" if price else "  Price=N/A", end="")
                print(f"  Change={change:+.2f}%" if change is not None else "  Change=N/A", end="")
                if dt_str:
                    try:
                        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                        et = dt.astimezone(timezone(timedelta(hours=-5)))  # ET timezone
                        print(f"  Time={et.strftime('%H:%M')} ET")
                    except:
                        print(f"  Time={dt_str}")
                else:
                    print()
        print()
        
        # Map UI times to system intervals
        # The article was at 11:46 ET, which is 2h 16min after market open (9:30 AM ET)
        # System calculates intervals from market open, not from article time
        # So we need to find which system intervals correspond to the UI times
        
        # UI times relative to article (11:46 ET):
        # 11:46 = article time (might be 2hr interval from market open)
        # 11:51 = 5 min after article (might be 2.5hr from market open)
        # 11:56 = 10 min after article (might be 2.5hr or 3hr from market open)
        # 12:16 = 30 min after article (might be 3hr from market open)
        # 12:46 = 1 hr after article (might be 3hr+ from market open)
        # 13:46 = 2 hr after article
        # 14:46 = 3 hr after article
        
        # Since article is at 11:46 ET (2h 16min after 9:30), the intervals would be:
        # 2hr interval = 11:30 ET (closest to 11:46)
        # 2.5hr interval = 12:00 ET
        # 3hr interval = 12:30 ET
        
        # This doesn't match the UI times exactly. Let's try a different approach:
        # Maybe the UI is showing intervals calculated from article time, not market open?
        
        # For now, let's try to match based on approximate times
        interval_times = {
            '11:46': '2hr',     # ~2h 16min after market open, closest to 2hr
            '11:51': '2.5hr',   # ~2h 21min after market open, closest to 2.5hr
            '11:56': '2.5hr',   # ~2h 26min after market open, still closest to 2.5hr
            '12:16': '3hr',     # ~2h 46min after market open, closest to 3hr
            '12:46': '3hr',    # ~3h 16min after market open, still 3hr
            '13:46': '3hr',    # ~4h 16min after market open, still 3hr (max)
            '14:46': '3hr',    # ~5h 16min after market open, still 3hr (max)
        }
        
        # Check each interval
        print("=" * 80)
        print("VOLUME VERIFICATION RESULTS")
        print("=" * 80)
        print()
        
        all_match = True
        results = []
        
        for time_str, interval_name in interval_times.items():
            volume_change_key = f'volume_change_{interval_name}'
            actual_vol_change = stock_changes.get(volume_change_key)
            expected_vol_change = expected_volumes.get(time_str)
            
            # Get price and change for this interval
            price_key = f'price_{interval_name}'
            change_key = f'change_{interval_name}'
            price = stock_changes.get(price_key)
            change = stock_changes.get(change_key)
            
            # Format comparison
            if expected_vol_change is None:
                # No expected value (like 14:46)
                match_status = "N/A (no expected value)"
                if actual_vol_change is not None and abs(actual_vol_change) < 0.01:
                    match_status = "✅ MATCH (≈0.00%)"
                elif actual_vol_change is None:
                    match_status = "✅ MATCH (None)"
                else:
                    match_status = f"⚠️  UNEXPECTED: {actual_vol_change:+.2f}%"
            elif actual_vol_change is None:
                match_status = "❌ MISMATCH: Expected {expected_vol_change:+.2f}%, got None"
                all_match = False
            else:
                # Allow small tolerance for rounding differences
                diff = abs(actual_vol_change - expected_vol_change)
                if diff < 0.1:  # Within 0.1% tolerance
                    match_status = "✅ MATCH"
                else:
                    match_status = f"❌ MISMATCH: Expected {expected_vol_change:+.2f}%, got {actual_vol_change:+.2f}% (diff: {diff:.2f}%)"
                    all_match = False
            
            results.append({
                'time': time_str,
                'interval': interval_name,
                'expected': expected_vol_change,
                'actual': actual_vol_change,
                'match': match_status,
                'price': price,
                'change': change
            })
            
            print(f"{time_str} ({interval_name}):")
            print(f"  Expected Vol Change: {expected_vol_change:+.2f}%" if expected_vol_change is not None else "  Expected Vol Change: N/A")
            print(f"  Actual Vol Change:   {actual_vol_change:+.2f}%" if actual_vol_change is not None else "  Actual Vol Change:   N/A")
            print(f"  Price: ${price:.2f}" if price else "  Price: N/A")
            print(f"  Change: {change:+.2f}%" if change is not None else "  Change: N/A")
            print(f"  Status: {match_status}")
            print()
        
        # Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print()
        
        if all_match:
            print("✅ ALL VOLUME PERCENTAGES MATCH!")
        else:
            print("❌ SOME VOLUME PERCENTAGES DO NOT MATCH")
            print()
            print("Mismatches:")
            for r in results:
                if "❌" in r['match']:
                    print(f"  {r['time']} ({r['interval']}): {r['match']}")
        
        return all_match
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_fold_volume_verification()
    sys.exit(0 if success else 1)

