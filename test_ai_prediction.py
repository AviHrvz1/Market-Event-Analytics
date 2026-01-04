#!/usr/bin/env python3
"""
Unit test to verify AI prediction (score and direction) from Claude API
"""

import sys
from datetime import datetime, timezone
from main import LayoffTracker

def test_ai_prediction():
    """Test AI prediction score and direction from Claude API"""
    print("=" * 80)
    print("Testing AI Prediction Flow")
    print("=" * 80)
    
    tracker = LayoffTracker()
    
    # Test article data
    test_article = {
        'title': 'Tesla announces major layoffs affecting 10% of workforce',
        'description': 'Tesla Inc. announced today that it will be cutting 10% of its global workforce, affecting approximately 14,000 employees. The company cited cost reduction efforts and restructuring needs. Analysts are concerned about the impact on production capacity.',
        'url': 'https://example.com/tesla-layoffs',
        'publishedAt': datetime.now(timezone.utc).isoformat()
    }
    
    print(f"\n📰 Test Article:")
    print(f"Title: {test_article['title']}")
    print(f"Description: {test_article['description'][:100]}...")
    print(f"URL: {test_article['url']}")
    
    print(f"\n🤖 Calling Claude API...")
    print(f"API Key: {tracker.claude_api_key[:20]}...")
    print(f"API URL: {tracker.claude_api_url}")
    
    # Test AI prediction
    company_name = "Tesla"
    ticker = "TSLA"
    
    try:
        result = tracker.get_ai_prediction_score(
            company_name=company_name,
            ticker=ticker,
            title=test_article['title'],
            description=test_article['description'],
            url=test_article['url']
        )
        
        print(f"\n✅ API Call Successful!")
        print(f"Result type: {type(result)}")
        print(f"Result: {result}")
        
        if result is None:
            print("\n❌ ERROR: API returned None")
            print("Possible reasons:")
            print("  - API key invalid")
            print("  - Network error")
            print("  - API rate limit")
            print("  - Response format not recognized")
            return False
        
        if isinstance(result, dict):
            score = result.get('score')
            direction = result.get('direction')
            
            print(f"\n📊 AI Prediction Results:")
            print(f"  Score: {score}")
            print(f"  Direction: {direction}")
            
            # Validate score
            if score is None:
                print("\n❌ ERROR: Score is None")
                return False
            
            if not isinstance(score, int):
                print(f"\n❌ ERROR: Score is not an integer (got {type(score)})")
                return False
            
            if score < 1 or score > 10:
                print(f"\n❌ ERROR: Score out of range (got {score}, expected 1-10)")
                return False
            
            # Validate direction
            if direction is None:
                print("\n❌ ERROR: Direction is None")
                return False
            
            if direction.lower() not in ['bullish', 'bearish']:
                print(f"\n❌ ERROR: Invalid direction (got '{direction}', expected 'bullish' or 'bearish')")
                return False
            
            print(f"\n✅ Validation Passed!")
            print(f"  ✓ Score is valid: {score}/10")
            print(f"  ✓ Direction is valid: {direction}")
            
            # Test caching
            print(f"\n🔄 Testing cache...")
            cached_result = tracker.get_ai_prediction_score(
                company_name=company_name,
                ticker=ticker,
                title=test_article['title'],
                description=test_article['description'],
                url=test_article['url']
            )
            
            if cached_result == result:
                print("✅ Cache working correctly (same result returned)")
            else:
                print("⚠️  Cache may not be working (different result)")
            
            return True
            
        else:
            print(f"\n❌ ERROR: Unexpected result type (got {type(result)}, expected dict)")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: Exception occurred")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_full_layoff_extraction():
    """Test full layoff extraction with AI prediction"""
    print("\n" + "=" * 80)
    print("Testing Full Layoff Extraction with AI Prediction")
    print("=" * 80)
    
    tracker = LayoffTracker()
    
    test_article = {
        'title': 'Microsoft announces 10,000 job cuts amid economic uncertainty',
        'description': 'Microsoft Corp. said it will eliminate 10,000 jobs, or about 5% of its workforce, as the software giant joins other tech companies in cutting costs. The layoffs will affect multiple divisions.',
        'url': 'https://example.com/microsoft-layoffs',
        'publishedAt': datetime.now(timezone.utc).isoformat()
    }
    
    print(f"\n📰 Testing with article:")
    print(f"Title: {test_article['title']}")
    
    try:
        result = tracker.extract_layoff_info(test_article, fetch_content=False)
        
        if result is None:
            print("\n❌ ERROR: extract_layoff_info returned None")
            print("This might be because:")
            print("  - Company name not found")
            print("  - Event type not matched")
            return False
        
        print(f"\n✅ Layoff info extracted!")
        print(f"Company: {result.get('company_name')}")
        print(f"Ticker: {result.get('stock_ticker')}")
        print(f"Event Type: {result.get('event_type')}")
        
        ai_score = result.get('ai_prediction_score')
        ai_direction = result.get('ai_prediction_direction')
        
        print(f"\n🤖 AI Prediction:")
        print(f"  Score: {ai_score}")
        print(f"  Direction: {ai_direction}")
        
        if ai_score is None and ai_direction is None:
            print("\n⚠️  WARNING: AI prediction is None")
            print("This could mean:")
            print("  - API call failed")
            print("  - Company name or ticker not found")
            print("  - API error occurred")
        elif ai_score is not None and ai_direction is not None:
            print(f"\n✅ AI Prediction present in result!")
            print(f"  ✓ Score: {ai_score}/10")
            print(f"  ✓ Direction: {ai_direction}")
            return True
        else:
            print(f"\n⚠️  Partial data: score={ai_score}, direction={ai_direction}")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: Exception occurred")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("\n🧪 Starting AI Prediction Tests...\n")
    
    # Test 1: Direct API call
    test1_passed = test_ai_prediction()
    
    # Test 2: Full extraction flow
    test2_passed = test_full_layoff_extraction()
    
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    print(f"Test 1 (Direct API Call): {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Test 2 (Full Extraction): {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Check output above for details.")
        sys.exit(1)

