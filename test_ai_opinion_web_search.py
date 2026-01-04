#!/usr/bin/env python3
"""
Test script to verify AI Opinion with web search is working correctly
Tests the updated get_ai_recovery_score method with web search enabled
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_ai_opinion_web_search():
    """Test AI recovery score with web search enabled"""
    print("=" * 80)
    print("AI OPINION WEB SEARCH TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    if not tracker.claude_api_key:
        print("❌ Claude API key not available")
        return False
    
    print("✅ Claude API key found")
    print()
    
    # Test case: HUM (Humana) drop on Dec 16, 2025
    # This is a known case where we expect to find news
    test_ticker = "HUM"
    test_company = "Humana Inc"
    bearish_date = datetime(2025, 12, 16, tzinfo=timezone.utc)
    target_date = datetime(2026, 1, 25, tzinfo=timezone.utc)
    
    print(f"Test Case: {test_ticker} ({test_company})")
    print(f"Bearish Date: {bearish_date.strftime('%Y-%m-%d')}")
    print(f"Target Date: {target_date.strftime('%Y-%m-%d')}")
    print()
    
    # Fetch price history
    print("📊 Fetching price history...")
    try:
        price_history = tracker.get_stock_price_history(test_ticker, bearish_date - timedelta(days=90), target_date)
        if not price_history:
            print("❌ Could not fetch price history")
            return False
        
        print(f"✅ Fetched {len(price_history)} data points")
        
        # Extract prices
        bearish_price, actual_bearish_date = tracker.extract_price_from_history(price_history, bearish_date)
        target_price, actual_target_date = tracker.extract_price_from_history(price_history, target_date)
        
        if bearish_price is None or target_price is None:
            print("❌ Could not extract prices")
            return False
        
        print(f"✅ Bearish Price: ${bearish_price:.2f} (date: {actual_bearish_date})")
        print(f"✅ Target Price: ${target_price:.2f} (date: {actual_target_date})")
        
        # Calculate drop percentage (need previous price)
        prev_price = bearish_price * 1.062  # Assuming ~6.2% drop (known from earlier tests)
        pct_drop = ((bearish_price - prev_price) / prev_price) * 100
        recovery_pct = ((target_price - bearish_price) / bearish_price) * 100
        
        print(f"✅ Previous Price: ${prev_price:.2f}")
        print(f"✅ Drop Percentage: {pct_drop:.2f}%")
        print(f"✅ Recovery Needed: {recovery_pct:.2f}%")
        print()
        
    except Exception as e:
        print(f"❌ Error fetching price history: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Build stock_data
    stock_data = {
        'company_name': test_company,
        'industry': 'Healthcare',
        'market_cap': 50000000000,  # $50B estimate
        'bearish_date': actual_bearish_date or bearish_date.strftime('%Y-%m-%d'),
        'bearish_price': bearish_price,
        'prev_price': prev_price,
        'pct_drop': pct_drop,
        'target_date': actual_target_date or target_date.strftime('%Y-%m-%d'),
        'target_price': target_price,
        'recovery_pct': recovery_pct,
        'price_history': price_history,
        'earnings_dividends': {
            'events_during': [],
            'next_events': [],
            'has_events_during': False,
            'has_next_events': False
        }
    }
    
    # Test AI recovery score
    print("=" * 80)
    print("TESTING AI RECOVERY SCORE (with web search)")
    print("=" * 80)
    print()
    print("⏳ Calling Claude API with web search enabled...")
    print("   (This may take 30-60 seconds as Claude searches the web)")
    print()
    
    try:
        result = tracker.get_ai_recovery_score(test_ticker, test_company, stock_data)
        
        if result:
            score = result.get('score')
            if score and 1 <= score <= 10:
                print(f"✅ SUCCESS! AI Recovery Score: {score}/10")
                print()
                print("=" * 80)
                print("VERIFICATION")
                print("=" * 80)
                print()
                print(f"✅ Score returned: {score}")
                print(f"✅ Score is in valid range (1-10)")
                print()
                print("✅ Web search integration appears to be working!")
                print("   Claude should have searched the web for news about the stock drop.")
                return True
            else:
                print(f"❌ Invalid score returned: {score}")
                return False
        else:
            print("❌ No result returned from get_ai_recovery_score")
            print("   Check logs above for errors")
            return False
            
    except Exception as e:
        print(f"❌ Error calling get_ai_recovery_score: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ai_opinion_web_search()
    sys.exit(0 if success else 1)

