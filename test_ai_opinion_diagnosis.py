#!/usr/bin/env python3
"""Test AI opinion to diagnose why it's not working"""

import sys
from datetime import datetime, timedelta, timezone
from main import LayoffTracker

def test_ai_opinion():
    """Test AI opinion with a simple example"""
    print("=" * 80)
    print("AI OPINION DIAGNOSIS TEST")
    print("=" * 80)
    print()
    
    # Initialize tracker
    print("Step 1: Initializing LayoffTracker...")
    tracker = LayoffTracker()
    
    # Check API key
    print(f"Step 2: Checking API key...")
    if not tracker.claude_api_key:
        print("❌ ERROR: No API key found!")
        return False
    
    if not tracker.claude_api_key:
        print("❌ ERROR: API key is still using placeholder value!")
        return False
    
    print(f"✅ API key found: {tracker.claude_api_key[:20]}...{tracker.claude_api_key[-10:]}")
    print()
    
    # Test with a simple stock
    ticker = "AAPL"
    company_name = "Apple Inc."
    
    print(f"Step 3: Testing with {ticker}...")
    print()
    
    # Create minimal stock_data
    bearish_date = datetime.now(timezone.utc) - timedelta(days=10)
    target_date = datetime.now(timezone.utc)
    
    # Fetch price history
    print("  Fetching price history...")
    try:
        price_history = tracker.get_stock_price_history(ticker, bearish_date - timedelta(days=90), target_date)
        if not price_history:
            print("  ❌ Could not fetch price history")
            return False
        print(f"  ✅ Fetched {len(price_history)} price points")
    except Exception as e:
        print(f"  ❌ Error fetching price history: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Extract prices
    print("  Extracting prices...")
    try:
        bearish_price, actual_bearish_date = tracker.extract_price_from_history(price_history, bearish_date)
        target_price, actual_target_date = tracker.extract_price_from_history(price_history, target_date)
        
        if bearish_price is None or target_price is None:
            print("  ❌ Could not extract prices")
            return False
        
        print(f"  ✅ Bearish price: ${bearish_price:.2f}")
        print(f"  ✅ Target price: ${target_price:.2f}")
    except Exception as e:
        print(f"  ❌ Error extracting prices: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Build stock_data
    stock_data = {
        'company_name': company_name,
        'industry': 'Technology',
        'market_cap': 3000000,  # $3T
        'bearish_date': actual_bearish_date or bearish_date.strftime('%Y-%m-%d'),
        'bearish_price': bearish_price,
        'prev_price': bearish_price * 1.05,  # Assume 5% drop
        'pct_drop': -5.0,
        'target_date': actual_target_date or target_date.strftime('%Y-%m-%d'),
        'target_price': target_price,
        'recovery_pct': ((target_price - bearish_price) / bearish_price) * 100,
        'price_history': price_history,
        'earnings_dividends': {'events_during': [], 'next_events': []}
    }
    
    print()
    print("Step 4: Calling get_ai_recovery_opinion...")
    print("  (This may take 30-90 seconds)")
    print()
    
    try:
        result = tracker.get_ai_recovery_opinion(ticker, company_name, stock_data)
        
        if result:
            print("✅ SUCCESS! AI opinion returned:")
            print(f"   Score: {result.get('score')}/10")
            print(f"   Explanation length: {len(result.get('explanation', ''))} characters")
            if result.get('explanation'):
                print(f"   First 200 chars: {result.get('explanation', '')[:200]}...")
            return True
        else:
            print("❌ FAILED: get_ai_recovery_opinion returned None")
            print("   This usually means:")
            print("   - API request failed (check network)")
            print("   - API key is invalid")
            print("   - Response parsing failed")
            print()
            print("   Check the server logs for [AI OPINION] error messages")
            return False
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ai_opinion()
    print()
    if success:
        print("=" * 80)
        print("✅ DIAGNOSIS COMPLETE: AI opinion is working!")
        print("=" * 80)
    else:
        print("=" * 80)
        print("❌ DIAGNOSIS COMPLETE: AI opinion is NOT working")
        print("   Check the error messages above for details")
        print("=" * 80)
    sys.exit(0 if success else 1)

