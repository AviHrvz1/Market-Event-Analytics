#!/usr/bin/env python3
"""
Unit test to verify stock prices at specific date/time using yfinance
Usage: python test_yfinance_price.py
Or modify the test cases below with your ticker, date, time, and expected price
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timezone, timedelta
import sys

def get_price_at_time(ticker: str, date_str: str, time_str: str, timezone_str: str = "America/New_York"):
    """
    Get stock price at a specific date and time using yfinance
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'SAFT')
        date_str: Date in format 'YYYY-MM-DD' (e.g., '2025-11-25')
        time_str: Time in format 'HH:MM' (e.g., '10:30')
        timezone_str: Timezone (default: 'America/New_York' for ET)
    
    Returns:
        tuple: (price, timestamp, success_message) or (None, None, error_message)
    """
    try:
        # Parse date and time
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        time_obj = datetime.strptime(time_str, '%H:%M').time()
        target_datetime = datetime.combine(date_obj.date(), time_obj)
        
        # Create timezone-aware datetime
        tz = pd.Timestamp.now(tz=timezone_str).tz
        target_ts = pd.Timestamp(target_datetime, tz=tz)
        
        print(f"\n{'='*70}")
        print(f"Fetching price for {ticker} at {target_ts}")
        print(f"{'='*70}")
        
        # Download intraday data for the day (use 1-minute interval for precision)
        # yfinance requires start and end to be different, so add 1 day
        start_date = date_str
        end_date = (date_obj + timedelta(days=1)).strftime('%Y-%m-%d')
        
        print(f"Downloading intraday data from yfinance...")
        data = yf.download(
            ticker,
            start=start_date,
            end=end_date,
            interval='1m',
            progress=False,
            auto_adjust=False
        )
        
        if data.empty:
            # Try 5-minute interval if 1-minute not available
            print("1-minute data not available, trying 5-minute interval...")
            data = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                interval='5m',
                progress=False,
                auto_adjust=False
            )
        
        if data.empty:
            return None, None, f"❌ No intraday data available for {ticker} on {date_str}"
        
        # Ensure timezone-aware index
        if data.index.tz is None:
            data.index = data.index.tz_localize(timezone_str)
        else:
            data.index = data.index.tz_convert(timezone_str)
        
        # Find the closest timestamp to target
        closest_idx = data.index.get_indexer([target_ts], method='nearest')[0]
        
        if closest_idx == -1:
            return None, None, f"❌ Could not find data near {target_ts}"
        
        closest_ts = data.index[closest_idx]
        close_value = data.iloc[closest_idx]['Close']
        price = float(close_value.iloc[0]) if isinstance(close_value, pd.Series) else float(close_value)
        
        # Calculate time difference
        time_diff = abs((closest_ts - target_ts).total_seconds() / 60)  # minutes
        
        return price, closest_ts, f"✓ Price: ${price:.2f} at {closest_ts} (diff: {time_diff:.1f} min)"
        
    except Exception as e:
        return None, None, f"❌ Error: {str(e)}"


def verify_price(ticker: str, date_str: str, time_str: str, expected_price: float, tolerance: float = 0.01):
    """
    Verify that the actual price matches the expected price
    
    Args:
        ticker: Stock ticker symbol
        date_str: Date in format 'YYYY-MM-DD'
        time_str: Time in format 'HH:MM'
        expected_price: Expected price to verify against (None to just fetch and display)
        tolerance: Allowed difference (default: $0.01)
    
    Returns:
        bool: True if price matches within tolerance (or if expected_price is None, just returns True if price found)
    """
    price, timestamp, message = get_price_at_time(ticker, date_str, time_str)
    
    print(message)
    
    if price is None:
        print(f"❌ Could not fetch price - cannot verify")
        return False
    
    # If no expected price provided, just display the actual price
    if expected_price is None:
        print(f"Actual price: ${price:.2f} (no expected price to compare)")
        return True
    
    print(f"Expected: ${expected_price:.2f}")
    print(f"Actual:   ${price:.2f}")
    
    difference = abs(price - expected_price)
    
    if difference <= tolerance:
        print(f"✓ PASS: Price matches within tolerance (${tolerance:.2f})")
        print(f"  Difference: ${difference:.2f}")
        return True
    else:
        print(f"✗ FAIL: Price difference exceeds tolerance")
        print(f"  Difference: ${difference:.2f} (tolerance: ${tolerance:.2f})")
        return False


def test_case(ticker: str, date_str: str, time_str: str, expected_price, test_name: str = ""):
    """Run a single test case"""
    print(f"\n{'#'*70}")
    if test_name:
        print(f"TEST: {test_name}")
    if expected_price is not None:
        print(f"Ticker: {ticker}, Date: {date_str}, Time: {time_str}, Expected: ${expected_price:.2f}")
    else:
        print(f"Ticker: {ticker}, Date: {date_str}, Time: {time_str}, Expected: (display only)")
    print(f"{'#'*70}")
    
    result = verify_price(ticker, date_str, time_str, expected_price)
    return result


if __name__ == '__main__':
    print("="*70)
    print("yfinance Price Verification Test")
    print("="*70)
    print("\nAdd your test cases below in the test_cases list")
    print("Format: (ticker, date, time, expected_price, test_name)")
    print()
    
    # ============================================================
    # ADD YOUR TEST CASES HERE
    # ============================================================
    test_cases = [
        # Consumers (CMS-PB) test cases - Nov 3, 2025
        ('CMS-PB', '2025-11-03', '09:35', 79.75, 'CMS-PB Mon Nov 3 09:35'),
        ('CMS-PB', '2025-11-03', '09:40', 79.75, 'CMS-PB Mon Nov 3 09:40'),
        ('CMS-PB', '2025-11-03', '10:00', 79.75, 'CMS-PB Mon Nov 3 10:00'),
        ('CMS-PB', '2025-11-03', '10:30', 79.75, 'CMS-PB Mon Nov 3 10:30'),
        ('CMS-PB', '2025-11-03', '11:00', 79.75, 'CMS-PB Mon Nov 3 11:00'),
        ('CMS-PB', '2025-11-03', '11:30', 79.75, 'CMS-PB Mon Nov 3 11:30'),
        ('CMS-PB', '2025-11-03', '12:00', 79.75, 'CMS-PB Mon Nov 3 12:00'),
        ('CMS-PB', '2025-11-03', '12:30', 79.75, 'CMS-PB Mon Nov 3 12:30'),
    ]
    
    if not test_cases:
        print("⚠ No test cases defined!")
        print("\nTo add a test case, edit this file and add to test_cases list:")
        print("  ('TICKER', 'YYYY-MM-DD', 'HH:MM', expected_price, 'Test Name')")
        print("\nExample:")
        print("  ('SAFT', '2025-11-25', '10:30', 76.50, 'SAFT morning price')")
        sys.exit(0)
    
    # Run all test cases
    results = []
    for ticker, date_str, time_str, expected_price, test_name in test_cases:
        result = test_case(ticker, date_str, time_str, expected_price, test_name)
        results.append(result)
    
    # Summary
    print(f"\n{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)

