#!/usr/bin/env python3
"""
Unit test to verify news fetching functionality
Tests if we can find news articles for stocks using the current implementation
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_news_fetching():
    """Test news fetching for various stocks"""
    print("=" * 80)
    print("NEWS FETCHING TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # NewsAPI free tier only allows articles from the last ~1 month
    # Use recent dates (within last 30 days) to test
    now = datetime.now(timezone.utc)
    
    # Test cases: (ticker, company_name, bearish_date, expected_to_find_news)
    # Use dates from the last 2-3 weeks (within NewsAPI's free tier limit)
    test_cases = [
        ('AAPL', 'Apple Inc', now - timedelta(days=5), True),
        ('MSFT', 'Microsoft Corporation', now - timedelta(days=10), True),
        ('TSLA', 'Tesla Inc', now - timedelta(days=15), True),
        ('NVDA', 'NVIDIA Corporation', now - timedelta(days=20), True),
        ('GOOGL', 'Alphabet Inc', now - timedelta(days=25), True),
        # Test with a less popular stock
        ('CORT', 'Corcept Therapeutics', now - timedelta(days=5), False),  # Might not have news
    ]
    
    results = []
    
    for ticker, company_name, bearish_date, expected_has_news in test_cases:
        print(f"Testing: {ticker} ({company_name})")
        print(f"  Bearish Date: {bearish_date.strftime('%Y-%m-%d')}")
        print(f"  Search Window: {(bearish_date - timedelta(days=7)).strftime('%Y-%m-%d')} to {bearish_date.strftime('%Y-%m-%d')}")
        print()
        
        try:
            # First, let's test NewsAPI directly to see what's happening
            from config import NEWS_API_KEY, NEWS_API_EVERYTHING_URL
            import requests
            
            if NEWS_API_KEY:
                start_date = bearish_date - timedelta(days=7)
                query = f'"{company_name}" OR "{ticker}"'
                params = {
                    'q': query,
                    'from': start_date.strftime('%Y-%m-%d'),
                    'to': bearish_date.strftime('%Y-%m-%d'),
                    'sortBy': 'publishedAt',
                    'language': 'en',
                    'pageSize': 20,
                    'apiKey': NEWS_API_KEY
                }
                
                print(f"  🔍 Testing NewsAPI directly...")
                print(f"     Query: {query}")
                print(f"     Date range: {start_date.strftime('%Y-%m-%d')} to {bearish_date.strftime('%Y-%m-%d')}")
                
                try:
                    response = requests.get(NEWS_API_EVERYTHING_URL, params=params, timeout=10)
                    print(f"     Status code: {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        total_results = data.get('totalResults', 0)
                        articles_data = data.get('articles', [])
                        print(f"     Total results from NewsAPI: {total_results}")
                        print(f"     Articles returned: {len(articles_data)}")
                        
                        if total_results > 0 and len(articles_data) == 0:
                            print(f"     ⚠️  NewsAPI found {total_results} results but returned 0 articles")
                            print(f"     This might be a pagination issue or API limit")
                    elif response.status_code == 429:
                        print(f"     ❌ Rate limit exceeded")
                    elif response.status_code == 401:
                        print(f"     ❌ Invalid API key")
                    else:
                        print(f"     ❌ Error: {response.status_code}")
                        try:
                            error_data = response.json()
                            print(f"     Error message: {error_data}")
                        except:
                            print(f"     Response text: {response.text[:200]}")
                except Exception as api_error:
                    print(f"     ❌ Error calling NewsAPI: {api_error}")
            
            print()
            articles = tracker._fetch_stock_news(ticker, company_name, bearish_date, limit=20)
            
            print(f"  ✅ Successfully fetched news via method")
            print(f"  📰 Found {len(articles)} articles")
            
            if articles:
                print(f"\n  Sample articles (showing first 3):")
                for i, article in enumerate(articles[:3], 1):
                    print(f"    {i}. {article.get('title', 'No title')[:60]}...")
                    print(f"       Source: {article.get('source', 'Unknown')}")
                    print(f"       Date: {article.get('publishedAt', 'N/A')[:10]}")
                    print(f"       URL: {article.get('url', 'N/A')[:60]}...")
                    print()
                
                # Check if articles are in the right date range
                in_range_count = 0
                for article in articles:
                    pub_date_str = article.get('publishedAt', '')
                    if pub_date_str:
                        try:
                            # Parse ISO format date
                            if 'T' in pub_date_str:
                                pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                            else:
                                pub_date = datetime.strptime(pub_date_str[:10], '%Y-%m-%d').replace(tzinfo=timezone.utc)
                            
                            start_date = bearish_date - timedelta(days=7)
                            if start_date <= pub_date <= bearish_date:
                                in_range_count += 1
                        except Exception:
                            pass
                
                print(f"  📅 Articles in date range (7 days before to bearish_date): {in_range_count}/{len(articles)}")
                
                results.append({
                    'ticker': ticker,
                    'found_news': True,
                    'article_count': len(articles),
                    'in_range_count': in_range_count,
                    'expected': expected_has_news,
                    'match': True if (len(articles) > 0) == expected_has_news else False
                })
            else:
                print(f"  ⚠️  No articles found")
                print(f"  Possible reasons:")
                print(f"    - No news in the 7-day window before bearish_date")
                print(f"    - NewsAPI has no results for this stock")
                print(f"    - NewsAPI rate limit or API key issue")
                print(f"    - Stock is too small/unknown")
                print()
                
                results.append({
                    'ticker': ticker,
                    'found_news': False,
                    'article_count': 0,
                    'in_range_count': 0,
                    'expected': expected_has_news,
                    'match': True if (len(articles) == 0) == (not expected_has_news) else False
                })
            
        except Exception as e:
            print(f"  ❌ Error fetching news: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'ticker': ticker,
                'found_news': False,
                'article_count': 0,
                'error': str(e),
                'expected': expected_has_news,
                'match': False
            })
        
        print("-" * 80)
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    total_tests = len(results)
    successful_fetches = sum(1 for r in results if r.get('found_news', False))
    articles_found = sum(r.get('article_count', 0) for r in results)
    
    print(f"Total test cases: {total_tests}")
    print(f"Successful fetches: {successful_fetches}/{total_tests}")
    print(f"Total articles found: {articles_found}")
    print()
    
    print("Results by ticker:")
    for r in results:
        status = "✅" if r.get('found_news') else "❌"
        count = r.get('article_count', 0)
        print(f"  {status} {r['ticker']}: {count} articles")
        if r.get('in_range_count', 0) > 0:
            print(f"     ({r['in_range_count']} in date range)")
    
    print()
    
    # Check if NewsAPI is working
    if successful_fetches == 0:
        print("⚠️  WARNING: No news found for any stock!")
        print("   This could indicate:")
        print("   - NewsAPI key is invalid or expired")
        print("   - NewsAPI rate limit exceeded")
        print("   - Network connectivity issues")
        print("   - All test dates are too recent (no historical news)")
    elif successful_fetches < total_tests * 0.5:
        print("⚠️  WARNING: News fetching is partially working")
        print("   Some stocks found news, others didn't")
        print("   This is normal for less popular stocks")
    else:
        print("✅ News fetching is working well!")
        print("   Most stocks found news articles")
    
    return successful_fetches > 0

if __name__ == "__main__":
    success = test_news_fetching()
    sys.exit(0 if success else 1)

