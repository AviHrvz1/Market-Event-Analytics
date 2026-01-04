#!/usr/bin/env python3
"""Unit tests for exchange detection and market hours functionality"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_exchange_detection():
    """Test exchange detection from ticker symbols"""
    tracker = LayoffTracker()
    
    test_cases = [
        ('AAPL', 'US'),
        ('TSLA', 'US'),
        ('MSFT', 'US'),
        ('1211.HK', 'HK'),
        ('AIR.PA', 'PA'),
        ('BP.L', 'L'),
        ('7203.T', 'T'),
        ('', 'US'),  # Empty ticker defaults to US
        (None, 'US'),  # None defaults to US
    ]
    
    print("Testing exchange detection...")
    all_passed = True
    
    for ticker, expected in test_cases:
        try:
            result = tracker._detect_exchange_from_ticker(ticker)
            if result == expected:
                print(f"  ✅ {ticker or 'None':10s} -> {result}")
            else:
                print(f"  ❌ {ticker or 'None':10s} -> {result} (expected {expected})")
                all_passed = False
        except AttributeError:
            print(f"  ⚠️  _detect_exchange_from_ticker() not implemented yet")
            return False
    
    return all_passed

def test_market_hours_config():
    """Test market hours configuration exists"""
    tracker = LayoffTracker()
    
    print("\nTesting market hours configuration...")
    
    try:
        config = tracker._get_market_hours('US')
        if config and 'open' in config and 'close' in config:
            print(f"  ✅ US market hours configured")
            print(f"     Open: {config['open']}, Close: {config['close']}")
        else:
            print(f"  ❌ US market hours missing required fields")
            return False
    except AttributeError:
        print(f"  ⚠️  _get_market_hours() not implemented yet")
        return False
    
    # Test HK market hours
    try:
        config = tracker._get_market_hours('HK')
        if config:
            print(f"  ✅ HK market hours configured")
            print(f"     Open: {config['open']}, Close: {config['close']}")
        else:
            print(f"  ❌ HK market hours not configured")
            return False
    except AttributeError:
        print(f"  ⚠️  HK market hours not configured")
        return False
    
    return True

def test_is_market_open_with_ticker():
    """Test is_market_open() with ticker parameter"""
    tracker = LayoffTracker()
    
    print("\nTesting is_market_open() with ticker...")
    
    # Test US market (9:30 AM - 4:00 PM ET)
    # Dec 1, 2025, 2:00 PM ET = 7:00 PM UTC (EST) or 6:00 PM UTC (EDT)
    # Using Dec 1, 2025 (winter, so EST = UTC-5)
    # 2:00 PM ET = 19:00 UTC
    us_open_time = datetime(2025, 12, 1, 19, 0, tzinfo=timezone.utc)  # 2:00 PM ET
    
    try:
        result = tracker.is_market_open(us_open_time, 'AAPL')
        if result:
            print(f"  ✅ US market open check works (AAPL at 2:00 PM ET)")
        else:
            print(f"  ❌ US market should be open at 2:00 PM ET")
            return False
    except TypeError:
        # Function doesn't accept ticker parameter yet
        print(f"  ⚠️  is_market_open() doesn't accept ticker parameter yet")
        return False
    
    # Test HK market (9:30 AM - 4:00 PM HKT = 1:30 AM - 8:00 AM UTC)
    # Dec 1, 2025, 10:00 AM HKT = 2:00 AM UTC
    hk_open_time = datetime(2025, 12, 1, 2, 0, tzinfo=timezone.utc)  # 10:00 AM HKT
    
    try:
        result = tracker.is_market_open(hk_open_time, '1211.HK')
        if result:
            print(f"  ✅ HK market open check works (1211.HK at 10:00 AM HKT)")
        else:
            print(f"  ❌ HK market should be open at 10:00 AM HKT")
            return False
    except Exception as e:
        print(f"  ❌ Error checking HK market: {e}")
        return False
    
    # Test HK market closed (outside hours)
    hk_closed_time = datetime(2025, 12, 1, 14, 0, tzinfo=timezone.utc)  # 2:00 PM UTC = 10:00 PM HKT (closed)
    
    try:
        result = tracker.is_market_open(hk_closed_time, '1211.HK')
        if not result:
            print(f"  ✅ HK market closed check works (1211.HK at 10:00 PM HKT)")
        else:
            print(f"  ❌ HK market should be closed at 10:00 PM HKT")
            return False
    except Exception as e:
        print(f"  ❌ Error checking HK market closed: {e}")
        return False
    
    return True

def test_byd_calculation():
    """Test BYD stock change calculation with exchange detection"""
    tracker = LayoffTracker()
    
    print("\nTesting BYD (1211.HK) stock change calculation...")
    
    # Article published on Sunday (market closed)
    article_date = datetime(2025, 11, 30, 4, 48, tzinfo=timezone.utc)
    
    mock_layoff = {
        'company_name': 'BYD Company Limited',
        'stock_ticker': '1211.HK',
        'datetime': article_date,
        'date': article_date.strftime('%Y-%m-%d'),
        'time': article_date.strftime('%H:%M:%S'),
        'url': 'https://test.com/byd',
        'title': 'BYD test article'
    }
    
    try:
        stock_changes = tracker.calculate_stock_changes(mock_layoff)
        
        # Check that we have a base price
        base_price = stock_changes.get('base_price')
        if base_price:
            print(f"  ✅ Base price calculated: ${base_price:.2f}")
        else:
            print(f"  ❌ Base price not calculated")
            return False
        
        # Check that intervals are calculated (should have prices, not all None)
        intervals = ['5min', '10min', '30min', '1hr']
        prices_found = 0
        
        for interval in intervals:
            price = stock_changes.get(f'price_{interval}')
            if price is not None:
                prices_found += 1
                change = stock_changes.get(f'change_{interval}')
                print(f"  ✅ {interval}: ${price:.2f} ({change:+.2f}%)" if change else f"  ✅ {interval}: ${price:.2f}")
        
        if prices_found > 0:
            print(f"  ✅ Found prices for {prices_found}/{len(intervals)} intervals")
            return True
        else:
            print(f"  ⚠️  No prices found for intervals (may be expected if data unavailable)")
            # This might be OK if Prixe.io doesn't have data, but let's check if it's because of wrong hours
            print(f"     This could indicate exchange hours not being used correctly")
            return False
        
    except Exception as e:
        print(f"  ❌ Error calculating stock changes: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_tests():
    """Run all tests"""
    print("=" * 80)
    print("Exchange Detection and Market Hours - Unit Tests")
    print("=" * 80)
    
    results = []
    
    results.append(("Exchange Detection", test_exchange_detection()))
    results.append(("Market Hours Config", test_market_hours_config()))
    results.append(("Market Open Check", test_is_market_open_with_ticker()))
    results.append(("BYD Calculation", test_byd_calculation()))
    
    print("\n" + "=" * 80)
    print("Test Results Summary")
    print("=" * 80)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    print("=" * 80)
    
    if all_passed:
        print("✅ All tests passed! Implementation is ready.")
        return True
    else:
        print("❌ Some tests failed. Fix implementation before applying.")
        return False

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

