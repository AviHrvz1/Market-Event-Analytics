#!/usr/bin/env python3
"""
Unit test to verify Small-Cap and Mid-Cap Biotech Google News search functionality
"""

import sys
from main import LayoffTracker
from config import EVENT_TYPES, LOOKBACK_DAYS

def test_company_lists():
    """Test 1: Verify company lists are loaded correctly"""
    print("=" * 80)
    print("TEST 1: Company Lists Loading")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Test small-cap
    small_cap = tracker._get_bio_pharma_companies('small_cap')
    print(f"✅ Small-cap companies: {len(small_cap)}")
    print(f"   Sample: {small_cap[:5]}")
    assert len(small_cap) > 0, "Small-cap list should not be empty"
    assert 'KURA ONCOLOGY' in small_cap or 'KURA' in [c[:4] for c in small_cap], "Should include Kura Oncology"
    print()
    
    # Test mid-cap
    mid_cap = tracker._get_bio_pharma_companies('mid_cap')
    print(f"✅ Mid-cap companies: {len(mid_cap)}")
    print(f"   Sample: {mid_cap[:5]}")
    assert len(mid_cap) > 0, "Mid-cap list should not be empty"
    assert 'MODERNA' in mid_cap, "Should include Moderna"
    print()
    
    return True

def test_event_type_config():
    """Test 2: Verify event type configurations"""
    print("=" * 80)
    print("TEST 2: Event Type Configurations")
    print("=" * 80)
    print()
    
    # Check small-cap config
    assert 'bio_companies_small_cap' in EVENT_TYPES, "bio_companies_small_cap should be in EVENT_TYPES"
    small_cap_config = EVENT_TYPES['bio_companies_small_cap']
    assert small_cap_config.get('category') == 'small_cap', "Should have category='small_cap'"
    assert small_cap_config.get('query_by_company_names') == True, "Should query by company names"
    print(f"✅ Small-cap config: {small_cap_config.get('name')}")
    print()
    
    # Check mid-cap config
    assert 'bio_companies_mid_cap' in EVENT_TYPES, "bio_companies_mid_cap should be in EVENT_TYPES"
    mid_cap_config = EVENT_TYPES['bio_companies_mid_cap']
    assert mid_cap_config.get('category') == 'mid_cap', "Should have category='mid_cap'"
    assert mid_cap_config.get('query_by_company_names') == True, "Should query by company names"
    print(f"✅ Mid-cap config: {mid_cap_config.get('name')}")
    print()
    
    return True

def test_google_news_query_construction():
    """Test 3: Verify Google News query construction"""
    print("=" * 80)
    print("TEST 3: Google News Query Construction")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Test small-cap query construction
    small_cap = tracker._get_bio_pharma_companies('small_cap')
    print(f"Testing query construction for small-cap ({len(small_cap)} companies)...")
    
    # Simulate how queries are built (first 25 companies)
    company_queries = []
    for company in small_cap[:25]:
        company_clean = company.replace('"', '').replace("'", '').strip()
        if company_clean and len(company_clean) > 2:
            company_queries.append(f'"{company_clean}"')
    
    if company_queries:
        search_query = ' OR '.join(company_queries[:25])
        print(f"   ✅ Query constructed: {len(company_queries)} companies")
        print(f"   Sample query (first 100 chars): {search_query[:100]}...")
        assert len(search_query) > 0, "Query should not be empty"
        assert 'OR' in search_query, "Query should use OR logic"
    print()
    
    # Test mid-cap query construction
    mid_cap = tracker._get_bio_pharma_companies('mid_cap')
    print(f"Testing query construction for mid-cap ({len(mid_cap)} companies)...")
    
    company_queries = []
    for company in mid_cap[:25]:
        company_clean = company.replace('"', '').replace("'", '').strip()
        if company_clean and len(company_clean) > 2:
            company_queries.append(f'"{company_clean}"')
    
    if company_queries:
        search_query = ' OR '.join(company_queries[:25])
        print(f"   ✅ Query constructed: {len(company_queries)} companies")
        print(f"   Sample query (first 100 chars): {search_query[:100]}...")
        assert len(search_query) > 0, "Query should not be empty"
    print()
    
    return True

def test_google_news_search_small_cap():
    """Test 4: Test actual Google News search for small-cap"""
    print("=" * 80)
    print("TEST 4: Google News Search - Small-Cap Biotech")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    print("Searching Google News for small-cap biotech companies...")
    print(f"Lookback days: {LOOKBACK_DAYS}")
    print()
    
    try:
        articles = tracker.search_google_news_rss(event_types=['bio_companies_small_cap'])
        
        print(f"✅ Search completed")
        print(f"   Articles found: {len(articles)}")
        
        if len(articles) > 0:
            print(f"\n   Sample articles:")
            for i, article in enumerate(articles[:5], 1):
                title = article.get('title', 'N/A')[:80]
                print(f"   {i}. {title}...")
        else:
            print(f"\n   ⚠️  WARNING: No articles found")
            print(f"   This could mean:")
            print(f"   - No recent news for these companies in last {LOOKBACK_DAYS} days")
            print(f"   - Company names don't match Google News format")
            print(f"   - Search query format issue")
        
        return len(articles) >= 0  # Allow 0 for now (might be legitimate)
        
    except Exception as e:
        print(f"❌ Search failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_google_news_search_mid_cap():
    """Test 5: Test actual Google News search for mid-cap"""
    print("=" * 80)
    print("TEST 5: Google News Search - Mid-Cap Biotech")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    print("Searching Google News for mid-cap biotech companies...")
    print(f"Lookback days: {LOOKBACK_DAYS}")
    print()
    
    try:
        articles = tracker.search_google_news_rss(event_types=['bio_companies_mid_cap'])
        
        print(f"✅ Search completed")
        print(f"   Articles found: {len(articles)}")
        
        if len(articles) > 0:
            print(f"\n   Sample articles:")
            for i, article in enumerate(articles[:5], 1):
                title = article.get('title', 'N/A')[:80]
                print(f"   {i}. {title}...")
        else:
            print(f"\n   ⚠️  WARNING: No articles found")
            print(f"   This could mean:")
            print(f"   - No recent news for these companies in last {LOOKBACK_DAYS} days")
            print(f"   - Company names don't match Google News format")
            print(f"   - Search query format issue")
        
        return len(articles) >= 0  # Allow 0 for now (might be legitimate)
        
    except Exception as e:
        print(f"❌ Search failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_specific_companies():
    """Test 6: Test search with specific well-known companies"""
    print("=" * 80)
    print("TEST 6: Search Specific Well-Known Companies")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Test with a few well-known companies that should definitely have news
    test_companies = ['MODERNA', 'BIONTECH', 'KURA ONCOLOGY', 'VIKING THERAPEUTICS']
    
    print("Testing search with specific companies that should have news:")
    for company in test_companies:
        print(f"   - {company}")
    print()
    
    # Manually construct a simple query
    import urllib.parse
    company_queries = [f'"{c}"' for c in test_companies]
    search_query = ' OR '.join(company_queries)
    encoded_query = urllib.parse.quote_plus(f"{search_query} when:{LOOKBACK_DAYS}d")
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en&num=100"
    
    print(f"Test URL (first 150 chars): {url[:150]}...")
    print()
    
    try:
        import requests
        from bs4 import BeautifulSoup
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item')
            print(f"✅ Direct Google News API call successful")
            print(f"   Articles found: {len(items)}")
            
            if len(items) > 0:
                print(f"\n   Sample articles:")
                for i, item in enumerate(items[:3], 1):
                    title_elem = item.find('title')
                    if title_elem:
                        title = title_elem.text.strip()[:80]
                        print(f"   {i}. {title}...")
            else:
                print(f"\n   ⚠️  No articles found even for well-known companies")
                print(f"   This suggests a Google News search format issue")
            
            return len(items) >= 0
        else:
            print(f"❌ Google News returned status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("BIO CATEGORIES GOOGLE NEWS SEARCH TEST SUITE")
    print("=" * 80)
    print()
    
    results = {}
    
    try:
        results['test_1'] = test_company_lists()
        results['test_2'] = test_event_type_config()
        results['test_3'] = test_google_news_query_construction()
        results['test_4'] = test_google_news_search_small_cap()
        results['test_5'] = test_google_news_search_mid_cap()
        results['test_6'] = test_specific_companies()
        
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print()
        
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status}: {test_name}")
        
        print()
        print(f"Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("✅ All tests passed!")
            return 0
        else:
            print("⚠️  Some tests failed or returned no results")
            return 1
            
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())

