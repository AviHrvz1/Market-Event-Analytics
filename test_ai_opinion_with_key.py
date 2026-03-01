#!/usr/bin/env python3
"""
Test AI opinion functionality with manually set API key
This verifies the code logic works when the API key is available
"""

import sys
import os
from datetime import datetime, timezone

# Set API key manually before importing (simulates .env file working)
# NOTE: Replace with your actual API key for testing
TEST_API_KEY = os.getenv('TEST_CLAUDE_API_KEY', '')
if not TEST_API_KEY:
    print("=" * 80)
    print("WARNING: TEST_CLAUDE_API_KEY not set")
    print("=" * 80)
    print()
    print("To test with a real API key, set the environment variable:")
    print("  export TEST_CLAUDE_API_KEY='your-actual-claude-api-key'")
    print("  python3 test_ai_opinion_with_key.py")
    print()
    print("Or the test will run in mock mode (will show what would happen)")
    print()
    sys.exit(0)

# Set the API key in environment before importing LayoffTracker
os.environ['CLAUDE_API_KEY'] = TEST_API_KEY

def test_ai_opinion_with_key():
    """Test AI opinion with manually set API key"""
    print("=" * 80)
    print("AI OPINION TEST WITH MANUAL API KEY")
    print("=" * 80)
    print()
    
    from main import LayoffTracker
    
    tracker = LayoffTracker()
    
    # Verify API key is loaded
    print("CHECK 1: Verifying API key is loaded")
    print("-" * 80)
    if tracker.claude_api_key:
        print(f"✅ API Key loaded: {tracker.claude_api_key[:10]}...{tracker.claude_api_key[-5:]}")
    else:
        print("❌ API Key NOT loaded - this shouldn't happen if we set it manually")
        return False
    print()
    
    # Create test stock_data
    print("CHECK 2: Preparing test stock data")
    print("-" * 80)
    
    stock_data = {
        'company_name': 'Apple Inc.',
        'industry': 'Technology',
        'market_cap': 3000000000000,  # $3T
        'bearish_date': '2025-12-11',
        'bearish_price': 150.0,
        'prev_price': 160.0,
        'pct_drop': -6.25,
        'target_date': '2025-12-31',
        'target_price': 155.0,
        'recovery_pct': 3.33,
        'price_history': [
            {'date': '2025-11-01', 'price': 165.0},
            {'date': '2025-11-15', 'price': 162.0},
            {'date': '2025-12-01', 'price': 160.0},
            {'date': '2025-12-11', 'price': 150.0},
            {'date': '2025-12-15', 'price': 152.0},
            {'date': '2025-12-20', 'price': 154.0},
            {'date': '2025-12-25', 'price': 155.0},
            {'date': '2025-12-31', 'price': 155.0}
        ],
        'earnings_dividends': {
            'events_during': [],
            'has_events_during': False,
            'next_events': []
        }
    }
    
    print("Stock data prepared:")
    print(f"  Ticker: AAPL")
    print(f"  Company: {stock_data['company_name']}")
    print(f"  Bearish Date: {stock_data['bearish_date']}")
    print(f"  Bearish Price: ${stock_data['bearish_price']:.2f}")
    print(f"  Drop: {stock_data['pct_drop']:.2f}%")
    print(f"  Target Date: {stock_data['target_date']}")
    print(f"  Target Price: ${stock_data['target_price']:.2f}")
    print(f"  Recovery: {stock_data['recovery_pct']:.2f}%")
    print()
    
    # Test AI opinion function
    print("CHECK 3: Calling get_ai_recovery_opinion")
    print("-" * 80)
    print("Making API call to Claude... (this may take 30-90 seconds)")
    print()
    
    try:
        result = tracker.get_ai_recovery_opinion('AAPL', 'Apple Inc.', stock_data)
        
        if result:
            print("✅ AI opinion returned successfully!")
            print()
            print("=" * 80)
            print("RESULT")
            print("=" * 80)
            print()
            print(f"Score: {result.get('score')}/10")
            print()
            print("Explanation:")
            print("-" * 80)
            explanation = result.get('explanation', '')
            # Show first 500 chars
            if len(explanation) > 500:
                print(explanation[:500])
                print("...")
                print(f"[Explanation continues - total length: {len(explanation)} characters]")
            else:
                print(explanation)
            print()
            return True
        else:
            print("❌ AI opinion returned None")
            print("   This could mean:")
            print("   - API key is invalid")
            print("   - API request failed")
            print("   - Response parsing failed")
            return False
            
    except Exception as e:
        print(f"❌ Error calling get_ai_recovery_opinion: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ai_opinion_with_key()
    print()
    print("=" * 80)
    if success:
        print("✅ TEST PASSED: AI opinion works when API key is available")
    else:
        print("❌ TEST FAILED: Check the error messages above")
    print("=" * 80)
    sys.exit(0 if success else 1)

