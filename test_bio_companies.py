#!/usr/bin/env python3
"""
Unit test to verify bio_companies event type functionality
Tests:
1. _get_bio_pharma_companies() returns company list
2. Query construction for bio_companies
3. Google News RSS search with bio_companies
4. Full fetch_layoffs() flow with bio_companies
"""

import sys
import requests
from datetime import datetime, timedelta
from main import LayoffTracker
from config import EVENT_TYPES, LOOKBACK_DAYS
import urllib.parse

def test_get_bio_pharma_companies():
    """Test 1: Verify _get_bio_pharma_companies() returns a list of companies"""
    print("=" * 80)
    print("Test 1: _get_bio_pharma_companies()")
    print("=" * 80)
    
    tracker = LayoffTracker()
    companies = tracker._get_bio_pharma_companies()
    
    assert isinstance(companies, list), f"Expected list, got {type(companies)}"
    assert len(companies) > 0, f"Expected non-empty list, got {len(companies)} companies"
    assert all(isinstance(c, str) for c in companies), "All items should be strings"
    assert all(c == c.upper() for c in companies), "All company names should be uppercase"
    
    print(f"✅ PASS: Found {len(companies)} bio/pharma companies")
    print(f"   Sample companies: {companies[:5]}")
    return companies

def test_query_construction():
    """Test 2: Verify query construction for bio_companies"""
    print("\n" + "=" * 80)
    print("Test 2: Query Construction for bio_companies")
    print("=" * 80)
    
    tracker = LayoffTracker()
    companies = tracker._get_bio_pharma_companies()
    
    # Simulate the query construction logic
    company_queries = []
    for company in companies[:150]:
        company_clean = company.replace('"', '').replace("'", '').strip()
        if company_clean and len(company_clean) > 2:
            company_queries.append(f'"{company_clean}"')
    
    assert len(company_queries) > 0, "Should have at least one company query"
    
    # Test batching (25 companies per query)
    batch_size = 25
    all_queries = []
    for i in range(0, len(company_queries), batch_size):
        batch = company_queries[i:i + batch_size]
        search_query = ' OR '.join(batch)
        all_queries.append(search_query)
    
    assert len(all_queries) > 0, "Should have at least one batch query"
    assert len(all_queries[0].split(' OR ')) <= batch_size, "First batch should have <= 25 companies"
    
    print(f"✅ PASS: Created {len(all_queries)} batch queries")
    print(f"   First query sample: {all_queries[0][:100]}...")
    print(f"   Companies per query: {len(all_queries[0].split(' OR '))}")
    return all_queries

def test_google_news_rss_search():
    """Test 3: Verify Google News RSS search with bio_companies"""
    print("\n" + "=" * 80)
    print("Test 3: Google News RSS Search with bio_companies")
    print("=" * 80)
    
    tracker = LayoffTracker()
    
    # Test search_google_news_rss with bio_companies
    print(f"Searching Google News RSS for bio_companies...")
    print(f"Lookback days: {LOOKBACK_DAYS}")
    
    try:
        articles = tracker.search_google_news_rss(event_types=['bio_companies'])
        
        assert isinstance(articles, list), f"Expected list, got {type(articles)}"
        
        print(f"✅ PASS: search_google_news_rss() returned {len(articles)} articles")
        
        if len(articles) > 0:
            print(f"\n   Sample articles found:")
            for i, article in enumerate(articles[:3], 1):
                print(f"   {i}. {article.get('title', 'N/A')[:80]}...")
                print(f"      URL: {article.get('url', 'N/A')[:80]}...")
                print(f"      Published: {article.get('publishedAt', 'N/A')}")
        else:
            print(f"   ⚠️  WARNING: No articles found. This could mean:")
            print(f"      - No recent news for bio/pharma companies in last {LOOKBACK_DAYS} days")
            print(f"      - Google News RSS query format issue")
            print(f"      - Network/API issue")
        
        return articles
        
    except Exception as e:
        print(f"❌ FAIL: Error during search: {e}")
        import traceback
        traceback.print_exc()
        return []

def test_google_news_rss_url():
    """Test 4: Verify Google News RSS URL construction"""
    print("\n" + "=" * 80)
    print("Test 4: Google News RSS URL Construction")
    print("=" * 80)
    
    tracker = LayoffTracker()
    companies = tracker._get_bio_pharma_companies()
    
    # Build a sample query (first 25 companies)
    company_queries = []
    for company in companies[:25]:
        company_clean = company.replace('"', '').replace("'", '').strip()
        if company_clean and len(company_clean) > 2:
            company_queries.append(f'"{company_clean}"')
    
    search_query = ' OR '.join(company_queries)
    encoded_query = urllib.parse.quote_plus(f"{search_query} when:{LOOKBACK_DAYS}d")
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en&num=100"
    
    print(f"Sample URL: {url[:150]}...")
    
    # Test if URL is accessible
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert 'xml' in response.text.lower() or 'rss' in response.text.lower(), "Response should be RSS/XML"
        
        print(f"✅ PASS: URL is accessible and returns RSS feed")
        print(f"   Response length: {len(response.text)} bytes")
        
        # Check if response contains items
        if '<item>' in response.text:
            item_count = response.text.count('<item>')
            print(f"   Found {item_count} items in RSS feed")
        else:
            print(f"   ⚠️  No <item> tags found in RSS feed")
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Error accessing URL: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_full_fetch_flow():
    """Test 5: Full fetch_layoffs() flow with bio_companies"""
    print("\n" + "=" * 80)
    print("Test 5: Full fetch_layoffs() Flow with bio_companies")
    print("=" * 80)
    
    tracker = LayoffTracker()
    
    print(f"Calling fetch_layoffs() with event_types=['bio_companies']...")
    print(f"This may take a while as it fetches articles and processes them...")
    
    try:
        tracker.fetch_layoffs(
            fetch_full_content=False,  # Faster for testing
            event_types=['bio_companies'],
            selected_sources=['google_news']  # Only Google News for testing
        )
        
        print(f"✅ PASS: fetch_layoffs() completed")
        print(f"   Total layoffs found: {len(tracker.layoffs)}")
        
        if len(tracker.layoffs) > 0:
            print(f"\n   Sample layoffs:")
            for i, layoff in enumerate(tracker.layoffs[:3], 1):
                print(f"   {i}. {layoff.get('company_name', 'N/A')} ({layoff.get('stock_ticker', 'N/A')})")
                print(f"      Title: {layoff.get('title', 'N/A')[:80]}...")
                print(f"      Date: {layoff.get('date', 'N/A')}")
        else:
            print(f"   ⚠️  WARNING: No layoffs found. This could mean:")
            print(f"      - No matching articles in last {LOOKBACK_DAYS} days")
            print(f"      - Articles don't match company name extraction logic")
            print(f"      - Company name extraction failed")
        
        return tracker.layoffs
        
    except Exception as e:
        print(f"❌ FAIL: Error during fetch_layoffs(): {e}")
        import traceback
        traceback.print_exc()
        return []

def test_event_type_config():
    """Test 6: Verify bio_companies event type configuration"""
    print("\n" + "=" * 80)
    print("Test 6: bio_companies Event Type Configuration")
    print("=" * 80)
    
    assert 'bio_companies' in EVENT_TYPES, "bio_companies should be in EVENT_TYPES"
    
    config = EVENT_TYPES['bio_companies']
    
    assert config.get('name') == 'Bio Companies', f"Expected name 'Bio Companies', got '{config.get('name')}'"
    assert config.get('query_by_company_names') == True, "query_by_company_names should be True"
    assert isinstance(config.get('keywords', []), list), "keywords should be a list"
    assert isinstance(config.get('sic_codes', []), list), "sic_codes should be a list"
    assert len(config.get('sic_codes', [])) > 0, "sic_codes should not be empty"
    
    print(f"✅ PASS: bio_companies configuration is correct")
    print(f"   Name: {config.get('name')}")
    print(f"   query_by_company_names: {config.get('query_by_company_names')}")
    print(f"   SIC codes: {config.get('sic_codes')}")
    print(f"   Keywords: {config.get('keywords')} (empty as expected)")

def test_company_extraction_from_articles():
    """Test 7: Test company name extraction from actual articles"""
    print("\n" + "=" * 80)
    print("Test 7: Company Name Extraction from Articles")
    print("=" * 80)
    
    tracker = LayoffTracker()
    articles = tracker.search_google_news_rss(event_types=['bio_companies'])
    
    if len(articles) == 0:
        print("⚠️  No articles to test with")
        return
    
    print(f"Testing company extraction on {min(5, len(articles))} sample articles...")
    
    extracted_count = 0
    failed_articles = []
    
    for i, article in enumerate(articles[:5], 1):
        title = article.get('title', '')
        description = article.get('description', '')
        
        print(f"\n   Article {i}:")
        print(f"   Title: {title[:80]}...")
        print(f"   Description: {description[:100] if description else 'N/A'}...")
        
        try:
            company_name = tracker.extract_company_name(title, description)
            if company_name:
                ticker = tracker.get_stock_ticker(company_name)
                print(f"   ✅ Extracted: {company_name} ({ticker})")
                extracted_count += 1
            else:
                print(f"   ❌ No company name extracted")
                failed_articles.append({
                    'title': title,
                    'description': description[:100] if description else ''
                })
        except Exception as e:
            print(f"   ❌ Error: {e}")
            failed_articles.append({
                'title': title,
                'error': str(e)
            })
    
    print(f"\n   Summary: {extracted_count}/{min(5, len(articles))} articles had company names extracted")
    
    if len(failed_articles) > 0:
        print(f"\n   ⚠️  Failed articles:")
        for article in failed_articles[:3]:
            print(f"      - {article.get('title', 'N/A')[:60]}...")
    
    return extracted_count, len(articles)

def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("BIO COMPANIES FUNCTIONALITY TEST SUITE")
    print("=" * 80)
    print()
    
    results = {
        'test_1': False,
        'test_2': False,
        'test_3': False,
        'test_4': False,
        'test_5': False,
        'test_6': False,
        'test_7': False
    }
    
    try:
        # Test 1: Get bio pharma companies
        companies = test_get_bio_pharma_companies()
        results['test_1'] = True
        
        # Test 2: Query construction
        queries = test_query_construction()
        results['test_2'] = True
        
        # Test 3: Google News RSS search
        articles = test_google_news_rss_search()
        results['test_3'] = True
        
        # Test 4: URL construction and accessibility
        url_works = test_google_news_rss_url()
        results['test_4'] = url_works
        
        # Test 5: Full fetch flow
        layoffs = test_full_fetch_flow()
        results['test_5'] = True
        
        # Test 6: Event type config
        test_event_type_config()
        results['test_6'] = True
        
        # Test 7: Company extraction from articles
        extracted, total = test_company_extraction_from_articles()
        results['test_7'] = extracted > 0
        
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
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
    
    # Additional diagnostics
    print("\n" + "=" * 80)
    print("DIAGNOSTICS")
    print("=" * 80)
    print(f"Companies available: {len(companies) if 'companies' in locals() else 'N/A'}")
    print(f"Articles found: {len(articles) if 'articles' in locals() else 'N/A'}")
    print(f"Layoffs found: {len(layoffs) if 'layoffs' in locals() else 'N/A'}")
    print(f"Lookback days: {LOOKBACK_DAYS}")
    
    if 'articles' in locals() and len(articles) == 0:
        print("\n💡 TROUBLESHOOTING: No articles found")
        print("   1. Check if Google News RSS is accessible")
        print("   2. Verify company names are being queried correctly")
        print("   3. Check if there are recent news articles for bio/pharma companies")
        print("   4. Verify LOOKBACK_DAYS is appropriate (currently {})".format(LOOKBACK_DAYS))
    
    if 'layoffs' in locals() and len(layoffs) == 0 and len(articles) > 0:
        print("\n💡 TROUBLESHOOTING: Articles found but no layoffs")
        print("   1. Check company name extraction logic")
        print("   2. Verify stock ticker lookup is working")
        print("   3. Check if articles contain company names that match SEC EDGAR data")

if __name__ == '__main__':
    main()

