#!/usr/bin/env python3
"""
Simple test to diagnose AI opinion issues - checks configuration and basic function call
"""

import sys
import os
from datetime import datetime, timezone
from main import LayoffTracker

def test_ai_opinion_config():
    """Test AI opinion configuration and basic functionality"""
    print("=" * 80)
    print("AI OPINION CONFIGURATION TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Check 1: API Key
    print("CHECK 1: Claude API Key")
    print("-" * 80)
    if tracker.claude_api_key:
        print(f"✅ API Key found: {tracker.claude_api_key[:10]}...{tracker.claude_api_key[-5:]}")
    else:
        print("❌ NO API KEY FOUND!")
        print("   Check if CLAUDE_API_KEY is set in .env file")
        return False
    print()
    
    # Check 2: API URL
    print("CHECK 2: Claude API URL")
    print("-" * 80)
    print(f"API URL: {tracker.claude_api_url}")
    print()
    
    # Check 3: Test with minimal stock_data
    print("CHECK 3: Testing get_ai_recovery_opinion with minimal data")
    print("-" * 80)
    
    # Create minimal valid stock_data
    stock_data = {
        'company_name': 'Test Company',
        'industry': 'Technology',
        'market_cap': 1000000000,
        'bearish_date': '2025-12-11',
        'bearish_price': 100.0,
        'prev_price': 105.0,
        'pct_drop': -5.0,
        'target_date': '2025-12-31',
        'target_price': 102.0,
        'recovery_pct': 2.0,
        'price_history': [
            {'date': '2025-12-11', 'price': 100.0},
            {'date': '2025-12-12', 'price': 101.0},
            {'date': '2025-12-13', 'price': 102.0}
        ],
        'earnings_dividends': {
            'events_during': [],
            'has_events_during': False
        }
    }
    
    print("Calling get_ai_recovery_opinion with test data...")
    print()
    
    try:
        result = tracker.get_ai_recovery_opinion('TEST', 'Test Company', stock_data)
        
        if result:
            print("✅ AI opinion returned successfully!")
            print(f"   Score: {result.get('score')}")
            print(f"   Explanation length: {len(result.get('explanation', ''))}")
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
    success = test_ai_opinion_config()
    sys.exit(0 if success else 1)

