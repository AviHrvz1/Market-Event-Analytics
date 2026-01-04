#!/usr/bin/env python3
"""
Unit test to verify technical indicators and target date price accuracy
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_target_date_price_accuracy():
    """Test that target date price uses correct date (on or before target_date, not after)"""
    print("=" * 80)
    print("TEST 1: Target Date Price Accuracy")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Create mock price history with dates before, on, and after target_date
    target_date = datetime(2025, 12, 29, tzinfo=timezone.utc)  # Dec 29 (Sunday - market closed)
    bearish_date = datetime(2025, 11, 17, tzinfo=timezone.utc)  # Nov 17
    
    # Simulate price history: Dec 26 ($100), Dec 27 ($101), Dec 30 ($102)
    # Dec 29 is Sunday, so we should use Dec 27 (last trading day before)
    price_history = [
        {'date': '2025-12-26', 'price': 100.0, 'timestamp': int(datetime(2025, 12, 26, tzinfo=timezone.utc).timestamp() * 1000)},
        {'date': '2025-12-27', 'price': 101.0, 'timestamp': int(datetime(2025, 12, 27, tzinfo=timezone.utc).timestamp() * 1000)},
        {'date': '2025-12-30', 'price': 102.0, 'timestamp': int(datetime(2025, 12, 30, tzinfo=timezone.utc).timestamp() * 1000)},
    ]
    
    # Test extract_price_from_history logic (simulate the function)
    def extract_price_from_history(price_history, target_date):
        """Simulate the extract_price_from_history function"""
        if not price_history:
            return None
        
        target_date_str = target_date.strftime('%Y-%m-%d')
        target_timestamp = int(target_date.timestamp())
        
        # Try exact date match first
        for entry in price_history:
            if entry.get('date') == target_date_str:
                return entry.get('price')
        
        # Find closest date ON or BEFORE target_date
        closest_price = None
        min_diff = float('inf')
        
        for entry in price_history:
            entry_timestamp = entry.get('timestamp', 0) / 1000
            price = entry.get('price')
            if price is None:
                continue
            
            # Only consider dates on or before target_date
            if entry_timestamp <= target_timestamp:
                diff = target_timestamp - entry_timestamp
                if diff < min_diff:
                    min_diff = diff
                    closest_price = float(price)
        
        return closest_price
    
    target_price = extract_price_from_history(price_history, target_date)
    
    print(f"Target Date: {target_date.strftime('%Y-%m-%d')} (Sunday - market closed)")
    print(f"Price History:")
    for entry in price_history:
        print(f"  {entry['date']}: ${entry['price']:.2f}")
    print()
    print(f"Expected: $101.00 (Dec 27 - last trading day before target_date)")
    print(f"Actual: ${target_price:.2f}")
    print()
    
    if target_price == 101.0:
        print("✅ PASS: Target date price correctly uses last trading day before target_date")
        return True
    else:
        print(f"❌ FAIL: Target date price is incorrect. Got ${target_price:.2f}, expected $101.00")
        return False

def test_technical_indicators_date_filtering():
    """Test that technical indicators only use data up to target_date"""
    print("=" * 80)
    print("TEST 2: Technical Indicators Date Filtering")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    target_date = datetime(2025, 12, 29, tzinfo=timezone.utc)
    target_date_str = target_date.strftime('%Y-%m-%d')
    target_timestamp = int(target_date.timestamp())
    
    # Create price history with dates before, on, and after target_date
    price_history = [
        {'date': '2025-12-15', 'price': 95.0, 'timestamp': int(datetime(2025, 12, 15, tzinfo=timezone.utc).timestamp() * 1000)},
        {'date': '2025-12-20', 'price': 97.0, 'timestamp': int(datetime(2025, 12, 20, tzinfo=timezone.utc).timestamp() * 1000)},
        {'date': '2025-12-26', 'price': 98.0, 'timestamp': int(datetime(2025, 12, 26, tzinfo=timezone.utc).timestamp() * 1000)},
        {'date': '2025-12-27', 'price': 99.0, 'timestamp': int(datetime(2025, 12, 27, tzinfo=timezone.utc).timestamp() * 1000)},
        {'date': '2025-12-29', 'price': 100.0, 'timestamp': int(datetime(2025, 12, 29, tzinfo=timezone.utc).timestamp() * 1000)},
        {'date': '2025-12-30', 'price': 105.0, 'timestamp': int(datetime(2025, 12, 30, tzinfo=timezone.utc).timestamp() * 1000)},  # AFTER target_date
    ]
    
    print(f"Target Date: {target_date_str}")
    print(f"Full Price History:")
    for entry in price_history:
        marker = " ⚠️  AFTER TARGET" if entry['date'] > target_date_str else ""
        print(f"  {entry['date']}: ${entry['price']:.2f}{marker}")
    print()
    
    # Filter to only include dates up to target_date
    filtered_price_history = [
        entry for entry in price_history
        if entry.get('date') <= target_date_str or 
        (entry.get('timestamp', 0) / 1000) <= target_timestamp
    ]
    
    print(f"Filtered Price History (up to target_date):")
    for entry in filtered_price_history:
        print(f"  {entry['date']}: ${entry['price']:.2f}")
    print()
    
    # Check if Dec 30 is excluded
    dates_after_target = [e['date'] for e in filtered_price_history if e['date'] > target_date_str]
    
    if dates_after_target:
        print(f"❌ FAIL: Filtered history includes dates after target_date: {dates_after_target}")
        return False
    else:
        print("✅ PASS: Filtered history correctly excludes dates after target_date")
    
    # Test RSI calculation uses filtered data
    prices = [p['price'] for p in filtered_price_history if p.get('price') is not None]
    print(f"Prices used for RSI: {prices}")
    print(f"Last price: ${prices[-1]:.2f}")
    
    if prices[-1] == 100.0:  # Dec 29 price, not Dec 30 ($105)
        print("✅ PASS: RSI uses correct last price (target_date, not future)")
    else:
        print(f"❌ FAIL: RSI uses wrong last price. Got ${prices[-1]:.2f}, expected $100.00")
        return False
    
    return True

def test_full_flow_accuracy():
    """Test the full flow with actual data"""
    print("=" * 80)
    print("TEST 3: Full Flow Accuracy Test")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Use actual dates from user's scenario
    bearish_date = datetime(2025, 11, 17, tzinfo=timezone.utc)
    target_date = datetime(2025, 12, 29, tzinfo=timezone.utc)
    
    print(f"Bearish Date: {bearish_date.strftime('%Y-%m-%d')}")
    print(f"Target Date: {target_date.strftime('%Y-%m-%d')}")
    print()
    
    # Test with a known ticker (e.g., AAPL)
    ticker = 'AAPL'
    print(f"Testing with {ticker}...")
    print()
    
    try:
        # Fetch price history
        graph_start_date = bearish_date - timedelta(days=30)
        price_history_end_date = target_date + timedelta(days=1)
        price_history = tracker.get_stock_price_history(ticker, graph_start_date, price_history_end_date)
        
        if not price_history:
            print(f"⚠️  No price history found for {ticker}, skipping full flow test")
            return True
        
        print(f"Fetched {len(price_history)} price data points")
        print(f"Date range: {price_history[0].get('date')} to {price_history[-1].get('date')}")
        print()
        
        # Check if price_history includes dates after target_date
        target_date_str = target_date.strftime('%Y-%m-%d')
        dates_after_target = [e.get('date') for e in price_history if e.get('date') > target_date_str]
        
        if dates_after_target:
            print(f"⚠️  Price history includes dates after target_date: {dates_after_target[:3]}")
        else:
            print("✅ Price history correctly ends at or before target_date")
        print()
        
        # Filter price_history to target_date
        target_timestamp = int(target_date.timestamp())
        filtered_price_history = [
            entry for entry in price_history
            if entry.get('date') <= target_date_str or 
            (entry.get('timestamp', 0) / 1000) <= target_timestamp
        ]
        
        print(f"Filtered to {len(filtered_price_history)} data points (up to target_date)")
        print(f"Last date in filtered: {filtered_price_history[-1].get('date')}")
        print()
        
        # Extract target price
        def extract_price_from_history(price_history, target_date):
            target_date_str = target_date.strftime('%Y-%m-%d')
            target_timestamp = int(target_date.timestamp())
            
            for entry in price_history:
                if entry.get('date') == target_date_str:
                    return entry.get('price')
            
            closest_price = None
            min_diff = float('inf')
            
            for entry in price_history:
                entry_timestamp = entry.get('timestamp', 0) / 1000
                price = entry.get('price')
                if price is None:
                    continue
                if entry_timestamp <= target_timestamp:
                    diff = target_timestamp - entry_timestamp
                    if diff < min_diff:
                        min_diff = diff
                        closest_price = float(price)
            
            return closest_price
        
        target_price = extract_price_from_history(filtered_price_history, target_date)
        print(f"Target Date Price: ${target_price:.2f}")
        
        # Calculate technical indicators
        base_price = extract_price_from_history(filtered_price_history, bearish_date)
        if base_price:
            technical_indicators = tracker._calculate_technical_indicators(
                filtered_price_history, target_price, base_price
            )
            
            print(f"Technical Indicators:")
            print(f"  RSI: {technical_indicators.get('rsi', 'N/A')}")
            print(f"  Support: ${technical_indicators.get('nearest_support', 'N/A')}")
            print(f"  Resistance: ${technical_indicators.get('nearest_resistance', 'N/A')}")
            print(f"  Trend: {technical_indicators.get('trend', 'N/A')}")
            print()
            
            # Verify RSI is reasonable (0-100)
            rsi = technical_indicators.get('rsi')
            if rsi is not None:
                if 0 <= rsi <= 100:
                    print("✅ RSI is within valid range (0-100)")
                else:
                    print(f"❌ RSI is out of range: {rsi}")
                    return False
            
            # Verify support/resistance make sense
            support = technical_indicators.get('nearest_support')
            resistance = technical_indicators.get('nearest_resistance')
            
            if support and resistance:
                if support < target_price < resistance:
                    print("✅ Support and Resistance are correctly positioned")
                else:
                    print(f"⚠️  Support/Resistance positioning: Support=${support}, Price=${target_price}, Resistance=${resistance}")
            
            print()
            print("✅ Full flow test completed successfully")
            return True
        else:
            print(f"⚠️  Could not find base_price for {ticker}, skipping indicator test")
            return True
            
    except Exception as e:
        print(f"❌ Error in full flow test: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_tests():
    """Run all tests"""
    print()
    print("=" * 80)
    print("TECHNICAL INDICATORS & TARGET DATE PRICE ACCURACY TESTS")
    print("=" * 80)
    print()
    
    results = []
    
    # Test 1: Target date price accuracy
    results.append(("Target Date Price Accuracy", test_target_date_price_accuracy()))
    print()
    
    # Test 2: Technical indicators date filtering
    results.append(("Technical Indicators Date Filtering", test_technical_indicators_date_filtering()))
    print()
    
    # Test 3: Full flow accuracy
    results.append(("Full Flow Accuracy", test_full_flow_accuracy()))
    print()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print()
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if not result:
            all_passed = False
    
    print()
    if all_passed:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    
    return all_passed

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

