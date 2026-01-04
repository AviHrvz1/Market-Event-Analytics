#!/usr/bin/env python3
"""
Test to see what Claude batch API is actually returning
"""

import sys
from main import LayoffTracker

def test_batch_api_response():
    """Test what Claude batch API actually returns"""
    
    print("=" * 80)
    print("BATCH API RESPONSE TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Test with a small batch
    test_articles = [
        {
            'index': 0,
            'title': 'Pfizer announces new drug approval',
            'description': 'Pfizer Inc has received FDA approval for its new treatment',
            'url': 'https://example.com/pfizer'
        },
        {
            'index': 1,
            'title': 'Moderna reports positive trial results',
            'description': 'Moderna Inc announced positive Phase 3 trial results',
            'url': 'https://example.com/moderna'
        },
        {
            'index': 2,
            'title': 'Kura Oncology gets FDA breakthrough designation',
            'description': 'Kura Oncology received breakthrough therapy designation from FDA',
            'url': 'https://example.com/kura'
        }
    ]
    
    print("🔍 Testing batch API with 3 sample articles...")
    print()
    
    results = tracker.get_ai_prediction_score_batch(test_articles)
    
    print("📊 Results:")
    print()
    for i, article in enumerate(test_articles):
        result = results.get(i)
        print(f"Article {i + 1}: {article['title'][:50]}...")
        if result:
            print(f"   ✅ Claude returned:")
            print(f"      Company: {result.get('company_name', 'N/A')}")
            print(f"      Ticker: {result.get('ticker', 'N/A')}")
            print(f"      Score: {result.get('score', 'N/A')}")
            print(f"      Direction: {result.get('direction', 'N/A')}")
        else:
            print(f"   ❌ Claude returned None")
        print()
    
    # Check what the actual API response looks like
    print("=" * 80)
    print("🔍 DEBUGGING: Checking API response format...")
    print()
    print("If Claude is returning results but we're not parsing them correctly,")
    print("we need to see the raw response format.")
    print()
    print("To debug, we should add logging in get_ai_prediction_score_batch()")
    print("to see what Claude actually returns.")
    
    return results

if __name__ == '__main__':
    try:
        results = test_batch_api_response()
        print("\n✅ Test completed")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

