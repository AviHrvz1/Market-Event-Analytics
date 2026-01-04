#!/usr/bin/env python3
"""
Test yfinance-only news fetching (no NewsAPI)
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_yfinance_news_only():
    """Test news fetching using only yfinance"""
    print("=" * 80)
    print("YFINANCE-ONLY NEWS FETCHING TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Test with recent dates (within last month) and older dates (beyond 30 days)
    now = datetime.now(timezone.utc)
    
    test_cases = [
        ('AAPL', 'Apple Inc', now - timedelta(days=5), 'Recent (5 days ago)'),
        ('MSFT', 'Microsoft Corporation', now - timedelta(days=15), 'Recent (15 days ago)'),
        ('TSLA', 'Tesla Inc', now - timedelta(days=45), 'Older (45 days ago - beyond NewsAPI limit)'),
        ('NVDA', 'NVIDIA Corporation', now - timedelta(days=60), 'Older (60 days ago - beyond NewsAPI limit)'),
        ('GOOGL', 'Alphabet Inc', datetime(2024, 11, 20, tzinfo=timezone.utc), 'Historical (Nov 2024)'),
    ]
    
    results = []
    
    for ticker, company_name, bearish_date, date_type in test_cases:
        print(f"Testing: {ticker} ({company_name})")
        print(f"  Bearish Date: {bearish_date.strftime('%Y-%m-%d')}")
        print(f"  Date Type: {date_type}")
        print(f"  Search Window: {(bearish_date - timedelta(days=7)).strftime('%Y-%m-%d')} to {bearish_date.strftime('%Y-%m-%d')}")
        print()
        
        try:
            articles = tracker._fetch_stock_news(ticker, company_name, bearish_date, limit=20)
            
            print(f"  ✅ Successfully fetched news")
            print(f"  📰 Found {len(articles)} articles")
            
            if articles:
                print(f"\n  Sample articles (showing first 3):")
                for i, article in enumerate(articles[:3], 1):
                    print(f"    {i}. {article.get('title', 'No title')[:60]}...")
                    print(f"       Source: {article.get('source', 'Unknown')}")
                    pub_date_str = article.get('publishedAt', '')
                    if pub_date_str:
                        try:
                            pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                            print(f"       Date: {pub_date.strftime('%Y-%m-%d')} ({(now - pub_date).days} days ago)")
                        except:
                            print(f"       Date: {pub_date_str[:10]}")
                    print(f"       URL: {article.get('url', 'N/A')[:60]}...")
                    print()
                
                # Check if articles are in the right date range
                in_range_count = 0
                for article in articles:
                    pub_date_str = article.get('publishedAt', '')
                    if pub_date_str:
                        try:
                            pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                            start_date = bearish_date - timedelta(days=7)
                            if start_date <= pub_date <= bearish_date:
                                in_range_count += 1
                        except:
                            pass
                
                print(f"  📅 Articles in date range (7 days before to bearish_date): {in_range_count}/{len(articles)}")
                
                results.append({
                    'ticker': ticker,
                    'date_type': date_type,
                    'found_news': True,
                    'article_count': len(articles),
                    'in_range_count': in_range_count
                })
            else:
                print(f"  ⚠️  No articles found")
                print(f"  Possible reasons:")
                print(f"    - No news in the 7-day window before bearish_date")
                print(f"    - yfinance has no news for this stock")
                print(f"    - Stock is too small/unknown")
                print()
                
                results.append({
                    'ticker': ticker,
                    'date_type': date_type,
                    'found_news': False,
                    'article_count': 0
                })
            
        except Exception as e:
            print(f"  ❌ Error fetching news: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'ticker': ticker,
                'date_type': date_type,
                'found_news': False,
                'article_count': 0,
                'error': str(e)
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
        date_type = r.get('date_type', 'Unknown')
        print(f"  {status} {r['ticker']} ({date_type}): {count} articles")
        if r.get('in_range_count', 0) > 0:
            print(f"     ({r['in_range_count']} in date range)")
    
    print()
    
    # Check if yfinance works for older dates
    older_date_results = [r for r in results if 'Older' in r.get('date_type', '') or 'Historical' in r.get('date_type', '')]
    if older_date_results:
        older_success = sum(1 for r in older_date_results if r.get('found_news', False))
        print(f"📊 Older dates (>30 days) test:")
        print(f"   Successfully fetched news for {older_success}/{len(older_date_results)} older date tests")
        if older_success > 0:
            print(f"   ✅ yfinance CAN fetch news for dates beyond 30 days!")
        else:
            print(f"   ⚠️  No news found for older dates (may be data availability issue)")
    
    if successful_fetches > 0:
        print("\n✅ yfinance news fetching is working!")
        if successful_fetches == total_tests:
            print("   All tests passed - yfinance is a good replacement for NewsAPI")
        else:
            print("   Some tests passed - yfinance works but may have coverage gaps")
    else:
        print("\n❌ yfinance news fetching failed for all tests")
    
    return successful_fetches > 0

if __name__ == "__main__":
    success = test_yfinance_news_only()
    sys.exit(0 if success else 1)

