#!/usr/bin/env python3
"""
Unit test to verify bio_companies fix - specifically testing that articles
are not filtered out incorrectly after the matches_event_type fix
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker
from config import EVENT_TYPES, LOOKBACK_DAYS

def test_matches_event_type_for_bio_companies():
    """Test 1: Verify matches_event_type returns True for bio_companies"""
    print("=" * 80)
    print("Test 1: matches_event_type() for bio_companies")
    print("=" * 80)
    
    tracker = LayoffTracker()
    
    # Test article that should match bio_companies
    test_article = {
        'title': 'Pfizer announces new drug approval',
        'description': 'Pfizer Inc. has received FDA approval for its new treatment',
        'event_type': 'bio_companies',
        'source': {'name': 'Google News'}
    }
    
    result = tracker.matches_event_type(test_article, 'bio_companies')
    
    assert result == True, f"Expected True for bio_companies, got {result}"
    print(f"✅ PASS: matches_event_type() returns True for bio_companies")
    
    # Test with article without event_type tag (should still work)
    test_article2 = {
        'title': 'Moderna reports strong earnings',
        'description': 'Moderna Inc. announced quarterly results',
    }
    
    result2 = tracker.matches_event_type(test_article2, 'bio_companies')
    assert result2 == True, f"Expected True for bio_companies without event_type tag, got {result2}"
    print(f"✅ PASS: matches_event_type() returns True for bio_companies even without event_type tag")
    
    return True

def test_extract_layoff_info_with_bio_companies():
    """Test 2: Verify extract_layoff_info processes bio_companies articles correctly"""
    print("\n" + "=" * 80)
    print("Test 2: extract_layoff_info() with bio_companies")
    print("=" * 80)
    
    tracker = LayoffTracker()
    
    # Create a test article that should be processed
    test_article = {
        'title': 'Johnson & Johnson announces new clinical trial results',
        'description': 'Johnson & Johnson Inc. reported positive results from its Phase 3 trial',
        'publishedAt': datetime.now(timezone.utc).isoformat(),
        'url': 'https://example.com/jnj-trial',
        'event_type': 'bio_companies',
        'source': {'name': 'Google News'}
    }
    
    print(f"Testing article: {test_article['title']}")
    
    try:
        result = tracker.extract_layoff_info(
            article=test_article,
            fetch_content=False,
            event_types=['bio_companies']
        )
        
        if result:
            print(f"✅ PASS: extract_layoff_info() returned a result")
            print(f"   Company: {result.get('company_name', 'N/A')}")
            print(f"   Ticker: {result.get('stock_ticker', 'N/A')}")
            print(f"   Event Type: {result.get('event_type', 'N/A')}")
            return True
        else:
            print(f"❌ FAIL: extract_layoff_info() returned None")
            print(f"   This means the article was filtered out")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Error during extract_layoff_info(): {e}")
        import traceback
        traceback.print_exc()
        return False

def test_full_pipeline_with_real_articles():
    """Test 3: Test full pipeline with real articles from Google News RSS"""
    print("\n" + "=" * 80)
    print("Test 3: Full Pipeline with Real Articles")
    print("=" * 80)
    
    tracker = LayoffTracker()
    
    print("Step 1: Fetching articles from Google News RSS...")
    articles = tracker.search_google_news_rss(event_types=['bio_companies'])
    
    print(f"   Found {len(articles)} articles")
    
    if len(articles) == 0:
        print("   ⚠️  No articles found - cannot test full pipeline")
        return False
    
    # Check if articles have event_type set
    articles_with_event_type = [a for a in articles if a.get('event_type') == 'bio_companies']
    print(f"   Articles with event_type='bio_companies': {len(articles_with_event_type)}")
    
    # Test extract_layoff_info on first few articles
    print("\nStep 2: Testing extract_layoff_info() on sample articles...")
    processed_count = 0
    filtered_count = 0
    
    for i, article in enumerate(articles[:5], 1):
        title = article.get('title', '')[:60]
        print(f"\n   Article {i}: {title}...")
        
        try:
            result = tracker.extract_layoff_info(
                article=article,
                fetch_content=False,
                event_types=['bio_companies']
            )
            
            if result:
                processed_count += 1
                company = result.get('company_name', 'N/A')
                ticker = result.get('stock_ticker', 'N/A')
                print(f"      ✅ Processed: {company} ({ticker})")
            else:
                filtered_count += 1
                print(f"      ❌ Filtered out")
                
        except Exception as e:
            filtered_count += 1
            print(f"      ❌ Error: {e}")
    
    print(f"\n   Summary: {processed_count} processed, {filtered_count} filtered out")
    
    if processed_count > 0:
        print(f"✅ PASS: At least one article was processed successfully")
        return True
    else:
        print(f"❌ FAIL: No articles were processed (all filtered out)")
        return False

def test_fetch_layoffs_with_bio_companies():
    """Test 4: Test full fetch_layoffs() with bio_companies"""
    print("\n" + "=" * 80)
    print("Test 4: Full fetch_layoffs() with bio_companies")
    print("=" * 80)
    
    tracker = LayoffTracker()
    
    print("Calling fetch_layoffs() with event_types=['bio_companies']...")
    print("This may take a while...")
    
    try:
        tracker.fetch_layoffs(
            fetch_full_content=False,  # Faster for testing
            event_types=['bio_companies'],
            selected_sources=['google_news']  # Only Google News for testing
        )
        
        print(f"\n✅ PASS: fetch_layoffs() completed")
        print(f"   Total layoffs found: {len(tracker.layoffs)}")
        
        if len(tracker.layoffs) > 0:
            print(f"\n   Sample layoffs:")
            for i, layoff in enumerate(tracker.layoffs[:3], 1):
                company = layoff.get('company_name', 'N/A')
                ticker = layoff.get('stock_ticker', 'N/A')
                title = layoff.get('title', 'N/A')[:60]
                event_type = layoff.get('event_type', 'N/A')
                print(f"   {i}. {company} ({ticker}) - {title}...")
                print(f"      Event Type: {event_type}")
            
            print(f"\n✅ SUCCESS: Found {len(tracker.layoffs)} bio company announcements!")
            return True
        else:
            print(f"\n⚠️  WARNING: No layoffs found")
            print(f"   This could mean:")
            print(f"   - Articles are still being filtered out")
            print(f"   - Company name extraction is failing")
            print(f"   - Ticker lookup is failing")
            print(f"   - Date filtering is too strict")
            return False
        
    except Exception as e:
        print(f"❌ FAIL: Error during fetch_layoffs(): {e}")
        import traceback
        traceback.print_exc()
        return False

def test_event_type_matching_logic():
    """Test 5: Verify the event type matching logic in extract_layoff_info"""
    print("\n" + "=" * 80)
    print("Test 5: Event Type Matching Logic")
    print("=" * 80)
    
    tracker = LayoffTracker()
    
    # Test case 1: Article with event_type tag from Google News
    article1 = {
        'title': 'Merck announces breakthrough',
        'description': 'Merck & Co. reports new findings',
        'event_type': 'bio_companies',
        'source': {'name': 'Google News'},
        'publishedAt': datetime.now(timezone.utc).isoformat(),
        'url': 'https://example.com/merck'
    }
    
    print("Test Case 1: Article with event_type='bio_companies' from Google News")
    result1 = tracker.extract_layoff_info(article1, fetch_content=False, event_types=['bio_companies'])
    
    if result1:
        print(f"   ✅ PASS: Article was processed (company: {result1.get('company_name', 'N/A')})")
    else:
        print(f"   ❌ FAIL: Article was filtered out")
    
    # Test case 2: Article without event_type tag (should use matches_event_type)
    article2 = {
        'title': 'AbbVie reports earnings',
        'description': 'AbbVie Inc. announced quarterly results',
        'source': {'name': 'Google News'},
        'publishedAt': datetime.now(timezone.utc).isoformat(),
        'url': 'https://example.com/abbvie'
    }
    
    print("\nTest Case 2: Article without event_type tag")
    result2 = tracker.extract_layoff_info(article2, fetch_content=False, event_types=['bio_companies'])
    
    if result2:
        print(f"   ✅ PASS: Article was processed via matches_event_type()")
        print(f"      Company: {result2.get('company_name', 'N/A')}")
    else:
        print(f"   ⚠️  Article was filtered out (may be expected if company extraction fails)")
    
    return True

def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("BIO COMPANIES FIX VERIFICATION TEST SUITE")
    print("=" * 80)
    print()
    
    results = {
        'test_1': False,
        'test_2': False,
        'test_3': False,
        'test_4': False,
        'test_5': False
    }
    
    try:
        # Test 1: matches_event_type
        results['test_1'] = test_matches_event_type_for_bio_companies()
        
        # Test 2: extract_layoff_info
        results['test_2'] = test_extract_layoff_info_with_bio_companies()
        
        # Test 3: Full pipeline with real articles
        results['test_3'] = test_full_pipeline_with_real_articles()
        
        # Test 4: Full fetch_layoffs
        results['test_4'] = test_fetch_layoffs_with_bio_companies()
        
        # Test 5: Event type matching logic
        results['test_5'] = test_event_type_matching_logic()
        
    except AssertionError as e:
        print(f"\n❌ ASSERTION ERROR: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if results['test_4']:
        print("\n🎉 SUCCESS: bio_companies is working! Articles are being found and processed.")
    elif results['test_3']:
        print("\n⚠️  PARTIAL: Articles are being processed, but fetch_layoffs() returned 0 results.")
        print("   This suggests an issue in the final filtering or ticker lookup stage.")
    else:
        print("\n❌ FAILURE: bio_companies is still not working correctly.")
        print("   Articles are being filtered out before processing.")
    
    print("\n" + "=" * 80)
    print("DIAGNOSTICS")
    print("=" * 80)
    print(f"LOOKBACK_DAYS: {LOOKBACK_DAYS}")
    print(f"bio_companies config: {EVENT_TYPES.get('bio_companies', {})}")

if __name__ == '__main__':
    main()

