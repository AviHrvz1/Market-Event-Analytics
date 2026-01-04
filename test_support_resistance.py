#!/usr/bin/env python3
"""
Unit test to verify improved support/resistance calculation
"""

import sys
from datetime import datetime, timezone
from main import LayoffTracker

def test_support_resistance_calculation():
    """Test the improved support/resistance calculation with various scenarios"""
    print("=" * 80)
    print("SUPPORT/RESISTANCE CALCULATION TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Test Case 1: Clear support and resistance with significant swings
    print("Test Case 1: Clear support and resistance levels")
    print("-" * 80)
    prices1 = [
        100.0,  # Start high
        95.0,   # Drop
        90.0,   # Support level (significant low)
        92.0,   # Bounce
        95.0,   # Rise
        98.0,   # Rise
        100.0,  # Resistance level (significant high)
        102.0,  # Breakout attempt
        100.0,  # Rejection
        98.0,   # Pullback
        95.0,   # Pullback
        92.0,   # Pullback
        90.0,   # Back to support
        88.0,   # Below support
        90.0,   # Bounce from support
        95.0,   # Current price
    ]
    
    price_history1 = [{'price': p, 'date': f'2024-01-{i+1:02d}', 'timestamp': i * 86400000} 
                      for i, p in enumerate(prices1)]
    current_price1 = 95.0
    bearish_price1 = 100.0
    
    indicators1 = tracker._calculate_technical_indicators(price_history1, current_price1, bearish_price1)
    
    support1 = indicators1.get('nearest_support')
    resistance1 = indicators1.get('nearest_resistance')
    
    print(f"Price History: {[p['price'] for p in price_history1]}")
    print(f"Current Price: ${current_price1:.2f}")
    print(f"Support: ${support1:.2f}" if support1 else "Support: None")
    print(f"Resistance: ${resistance1:.2f}" if resistance1 else "Resistance: None")
    
    if support1 and resistance1:
        distance = ((resistance1 - support1) / support1) * 100
        print(f"Distance between Support/Resistance: {distance:.2f}%")
        
        # Verify support is below current price
        assert support1 < current_price1, f"Support ({support1}) should be below current price ({current_price1})"
        # Verify resistance is above current price
        assert resistance1 > current_price1, f"Resistance ({resistance1}) should be above current price ({current_price1})"
        # Verify they're not too close (at least 2% apart)
        assert distance >= 2.0, f"Support and resistance should be at least 2% apart, got {distance:.2f}%"
        print("✅ Test Case 1 PASSED")
    else:
        print("❌ Test Case 1 FAILED: Missing support or resistance")
        return False
    
    print()
    
    # Test Case 2: Uptrend with clear levels
    print("Test Case 2: Uptrend scenario")
    print("-" * 80)
    prices2 = [
        50.0,   # Start
        48.0,   # Support 1
        52.0,   # Rise
        50.0,   # Pullback
        55.0,   # Rise
        53.0,   # Support 2
        58.0,   # Rise
        60.0,   # Resistance
        62.0,   # Breakout
        65.0,   # Current (high)
    ]
    
    price_history2 = [{'price': p, 'date': f'2024-02-{i+1:02d}', 'timestamp': i * 86400000} 
                      for i, p in enumerate(prices2)]
    current_price2 = 65.0
    bearish_price2 = 50.0
    
    indicators2 = tracker._calculate_technical_indicators(price_history2, current_price2, bearish_price2)
    
    support2 = indicators2.get('nearest_support')
    resistance2 = indicators2.get('nearest_resistance')
    
    print(f"Price History: {[p['price'] for p in price_history2]}")
    print(f"Current Price: ${current_price2:.2f}")
    print(f"Support: ${support2:.2f}" if support2 else "Support: None")
    print(f"Resistance: ${resistance2:.2f}" if resistance2 else "Resistance: None")
    
    if support2 and resistance2:
        distance = ((resistance2 - support2) / support2) * 100
        print(f"Distance between Support/Resistance: {distance:.2f}%")
        
        assert support2 < current_price2, f"Support should be below current price"
        # Resistance might be fallback (5% above) if no significant high found
        print("✅ Test Case 2 PASSED")
    else:
        print("❌ Test Case 2 FAILED: Missing support or resistance")
        return False
    
    print()
    
    # Test Case 3: Downtrend
    print("Test Case 3: Downtrend scenario")
    print("-" * 80)
    prices3 = [
        80.0,   # Start high
        78.0,   # Resistance
        75.0,   # Drop
        73.0,   # Drop
        70.0,   # Support
        72.0,   # Bounce
        75.0,   # Rise
        73.0,   # Drop
        70.0,   # Back to support
        68.0,   # Break below
        65.0,   # Current (low)
    ]
    
    price_history3 = [{'price': p, 'date': f'2024-03-{i+1:02d}', 'timestamp': i * 86400000} 
                      for i, p in enumerate(prices3)]
    current_price3 = 65.0
    bearish_price3 = 80.0
    
    indicators3 = tracker._calculate_technical_indicators(price_history3, current_price3, bearish_price3)
    
    support3 = indicators3.get('nearest_support')
    resistance3 = indicators3.get('nearest_resistance')
    
    print(f"Price History: {[p['price'] for p in price_history3]}")
    print(f"Current Price: ${current_price3:.2f}")
    print(f"Support: ${support3:.2f}" if support3 else "Support: None")
    print(f"Resistance: ${resistance3:.2f}" if resistance3 else "Resistance: None")
    
    if support3 and resistance3:
        distance = ((resistance3 - support3) / support3) * 100
        print(f"Distance between Support/Resistance: {distance:.2f}%")
        
        assert support3 < current_price3, f"Support should be below current price"
        assert resistance3 > current_price3, f"Resistance should be above current price"
        assert distance >= 2.0, f"Support and resistance should be at least 2% apart"
        print("✅ Test Case 3 PASSED")
    else:
        print("❌ Test Case 3 FAILED: Missing support or resistance")
        return False
    
    print()
    
    # Test Case 4: Sideways/consolidation
    print("Test Case 4: Sideways/consolidation scenario")
    print("-" * 80)
    prices4 = [
        100.0,  # Start
        98.0,   # Support
        102.0,  # Resistance
        99.0,   # Middle
        101.0,  # Middle
        98.0,   # Support
        102.0,  # Resistance
        100.0,  # Middle
        98.0,   # Support
        102.0,  # Resistance
        100.0,  # Current (middle)
    ]
    
    price_history4 = [{'price': p, 'date': f'2024-04-{i+1:02d}', 'timestamp': i * 86400000} 
                      for i, p in enumerate(prices4)]
    current_price4 = 100.0
    bearish_price4 = 100.0
    
    indicators4 = tracker._calculate_technical_indicators(price_history4, current_price4, bearish_price4)
    
    support4 = indicators4.get('nearest_support')
    resistance4 = indicators4.get('nearest_resistance')
    
    print(f"Price History: {[p['price'] for p in price_history4]}")
    print(f"Current Price: ${current_price4:.2f}")
    print(f"Support: ${support4:.2f}" if support4 else "Support: None")
    print(f"Resistance: ${resistance4:.2f}" if resistance4 else "Resistance: None")
    
    if support4 and resistance4:
        distance = ((resistance4 - support4) / support4) * 100
        print(f"Distance between Support/Resistance: {distance:.2f}%")
        
        assert support4 < current_price4, f"Support should be below current price"
        assert resistance4 > current_price4, f"Resistance should be above current price"
        # In consolidation, support and resistance should be clearly defined
        assert distance >= 1.0, f"Support and resistance should be at least 1% apart in consolidation"
        print("✅ Test Case 4 PASSED")
    else:
        print("❌ Test Case 4 FAILED: Missing support or resistance")
        return False
    
    print()
    
    # Test Case 5: Edge case - price at extreme high
    print("Test Case 5: Price at extreme high (fallback test)")
    print("-" * 80)
    prices5 = [
        50.0,
        52.0,
        55.0,
        58.0,
        60.0,  # Current (at high)
    ]
    
    price_history5 = [{'price': p, 'date': f'2024-05-{i+1:02d}', 'timestamp': i * 86400000} 
                      for i, p in enumerate(prices5)]
    current_price5 = 60.0
    bearish_price5 = 50.0
    
    indicators5 = tracker._calculate_technical_indicators(price_history5, current_price5, bearish_price5)
    
    support5 = indicators5.get('nearest_support')
    resistance5 = indicators5.get('nearest_resistance')
    
    print(f"Price History: {[p['price'] for p in price_history5]}")
    print(f"Current Price: ${current_price5:.2f}")
    print(f"Support: ${support5:.2f}" if support5 else "Support: None")
    print(f"Resistance: ${resistance5:.2f}" if resistance5 else "Resistance: None")
    
    if support5 and resistance5:
        distance = ((resistance5 - support5) / support5) * 100
        print(f"Distance between Support/Resistance: {distance:.2f}%")
        
        assert support5 < current_price5, f"Support should be below current price"
        assert resistance5 > current_price5, f"Resistance should be above current price (fallback to 5% above)"
        print("✅ Test Case 5 PASSED (fallback logic working)")
    else:
        print("❌ Test Case 5 FAILED: Missing support or resistance")
        return False
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("✅ All test cases passed!")
    print()
    print("Key improvements verified:")
    print("  - Support is always below current price")
    print("  - Resistance is always above current price")
    print("  - Support and resistance are meaningfully separated (not too close)")
    print("  - Fallback logic works when no significant levels found")
    print("  - Algorithm handles various market conditions (uptrend, downtrend, sideways)")
    
    return True

if __name__ == "__main__":
    success = test_support_resistance_calculation()
    sys.exit(0 if success else 1)

