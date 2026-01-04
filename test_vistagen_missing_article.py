#!/usr/bin/env python3
"""
Unit test to diagnose why Vistagen Phase 3 trial failure article wasn't found
Article: "Vistagen announced that its Phase 3 trial failed. This news was released on December 17"
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker
from config import EVENT_TYPES, MAX_ARTICLES_TO_PROCESS

def test_1_check_company_in_list():
    """Test 1: Check if Vistagen is in the bio companies list"""
    print("=" * 80)
    print("TEST 1: Check if Vistagen is in bio companies list")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Check all bio company categories
    for category in ['all', 'small_cap', 'mid_cap']:
        bio_companies = tracker._get_bio_pharma_companies(category=category)
        vistagen_variants = [
            'VISTAGEN',
            'VISTAGEN THERAPEUTICS',
            'Vistagen',
            'Vistagen Therapeutics',
            'VTGN'  # Ticker
        ]
        
        found = False
        for variant in vistagen_variants:
            if variant.upper() in [c.upper() for c in bio_companies]:
                found = True
                print(f"✅ Found '{variant}' in {category} bio companies list")
                break
        
        if not found:
            print(f"❌ Vistagen NOT found in {category} bio companies list")
            print(f"   List contains {len(bio_companies)} companies")
            # Show first 10 for reference
            print(f"   Sample companies: {bio_companies[:10]}")
        print()

def test_2_check_google_news_search():
    """Test 2: Check if Google News can find the article"""
    print("=" * 80)
    print("TEST 2: Check if Google News can find Vistagen Phase 3 article")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Test different search queries
    search_queries = [
        'Vistagen Phase 3 trial failed',
        'Vistagen Phase 3',
        'Vistagen trial failed December 17 2025',
        'VTGN Phase 3',
        'Vistagen Therapeutics Phase 3',
        'VistaGen Phase 3',  # Note: user wrote "VistaGen" (capital G)
    ]
    
    for query in search_queries:
        print(f"Searching: '{query}'")
        try:
            # Build Google News RSS URL
            import urllib.parse
            encoded_query = urllib.parse.quote(query)
            from config import LOOKBACK_DAYS
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&when={LOOKBACK_DAYS}d&hl=en-US&gl=US&ceid=US:en"
            
            # Make request
            import requests
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            response = requests.get(rss_url, headers=headers, timeout=10)
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'xml')
                items = soup.find_all('item')
                articles = []
                for item in items[:10]:  # Check first 10
                    title = item.find('title')
                    link = item.find('link')
                    pub_date = item.find('pubDate')
                    description = item.find('description')
                    articles.append({
                        'title': title.text if title else '',
                        'url': link.text if link else '',
                        'published_date': pub_date.text if pub_date else '',
                        'description': description.text if description else ''
                    })
            else:
                articles = []
            
            if articles:
                print(f"   ✅ Found {len(articles)} articles")
                # Check if any match the date (December 17, 2025)
                target_date = datetime(2025, 12, 17, tzinfo=timezone.utc)
                for article in articles[:5]:  # Check first 5
                    article_date = article.get('published_date')
                    if article_date:
                        # Check if date is close to Dec 17, 2024
                        if isinstance(article_date, str):
                            from dateutil import parser
                            try:
                                parsed_date = parser.parse(article_date)
                                days_diff = abs((parsed_date - target_date).days)
                                if days_diff <= 2:  # Within 2 days
                                    print(f"   ✅ Found article near target date: {article.get('title', 'No title')[:80]}")
                                    print(f"      Date: {article_date}")
                                    print(f"      URL: {article.get('url', 'No URL')[:100]}")
                            except:
                                pass
            else:
                print(f"   ❌ No articles found")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()

def test_3_check_date_range():
    """Test 3: Check if December 17, 2025 is within the allowed date range"""
    print("=" * 80)
    print("TEST 3: Check if December 17, 2025 is within allowed date range")
    print("=" * 80)
    print()
    
    from config import LOOKBACK_DAYS
    
    target_date = datetime(2025, 12, 17, tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    days_ago = (now - target_date).days
    
    print(f"Target date: {target_date.date()}")
    print(f"Today: {now.date()}")
    print(f"Days ago: {days_ago}")
    print(f"LOOKBACK_DAYS: {LOOKBACK_DAYS}")
    
    if days_ago <= LOOKBACK_DAYS:
        print(f"✅ Date is within {LOOKBACK_DAYS} day lookback period")
    else:
        print(f"❌ Date is OUTSIDE {LOOKBACK_DAYS} day lookback period")
        print(f"   Article is {days_ago} days old, but only {LOOKBACK_DAYS} days are allowed")
    print()

def test_4_check_event_type_matching():
    """Test 4: Check if the article would match bio_companies event type"""
    print("=" * 80)
    print("TEST 4: Check if article would match bio_companies event type")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Simulate article content
    test_article = {
        'title': 'Vistagen announced that its Phase 3 trial failed',
        'description': 'Vistagen Therapeutics announced that its Phase 3 trial failed. This news was released on December 17, and multiple outlets confirmed it.',
        'url': 'https://example.com/vistagen-phase3-failure'
    }
    
    # Test all bio event types
    bio_event_types = ['bio_companies', 'bio_companies_small_cap', 'bio_companies_mid_cap']
    
    for event_type in bio_event_types:
        if event_type in EVENT_TYPES:
            event_config = EVENT_TYPES[event_type]
            print(f"Testing event type: {event_type}")
            print(f"   Name: {event_config.get('name', 'N/A')}")
            print(f"   Keywords: {event_config.get('keywords', [])}")
            print(f"   Query by company names: {event_config.get('query_by_company_names', False)}")
            
            # Check if it matches
            matches = tracker.matches_event_type(test_article, event_type)
            if matches:
                print(f"   ✅ Article WOULD match this event type")
            else:
                print(f"   ❌ Article would NOT match this event type")
            print()

def test_5_full_search_simulation():
    """Test 5: Simulate full search to see what happens"""
    print("=" * 80)
    print("TEST 5: Simulate full search for bio_companies_small_cap")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Get bio companies list
    bio_companies = tracker._get_bio_pharma_companies(category='small_cap')
    vistagen_in_list = any('VISTAGEN' in c.upper() for c in bio_companies)
    
    print(f"Vistagen in small-cap list: {vistagen_in_list}")
    print(f"Total small-cap companies: {len(bio_companies)}")
    print()
    
    # Try searching with bio_companies_small_cap
    print("Searching Google News with bio_companies_small_cap event type...")
    try:
        # search_google_news_rss expects a list of event types
        articles = tracker.search_google_news_rss(['bio_companies_small_cap'])
        print(f"Found {len(articles)} total articles")
        
        # Check for Vistagen articles
        vistagen_articles = []
        for article in articles:
            title = article.get('title', '').upper()
            description = article.get('description', '').upper()
            if 'VISTAGEN' in title or 'VISTAGEN' in description or 'VTGN' in title or 'VTGN' in description:
                vistagen_articles.append(article)
        
        if vistagen_articles:
            print(f"✅ Found {len(vistagen_articles)} Vistagen articles:")
            for article in vistagen_articles[:5]:
                print(f"   - {article.get('title', 'No title')[:80]}")
                print(f"     Date: {article.get('published_date', 'No date')}")
                print(f"     URL: {article.get('url', 'No URL')[:100]}")
            
            # Check if any are from December 17, 2025
            target_date = datetime(2025, 12, 17, tzinfo=timezone.utc)
            dec17_articles = []
            for article in vistagen_articles:
                pub_date = article.get('published_date', '')
                if pub_date:
                    try:
                        from dateutil import parser
                        parsed_date = parser.parse(pub_date)
                        days_diff = abs((parsed_date - target_date).days)
                        if days_diff <= 1:  # Within 1 day
                            dec17_articles.append(article)
                    except:
                        pass
            
            if dec17_articles:
                print(f"\n   ✅ Found {len(dec17_articles)} articles from December 17, 2025:")
                for article in dec17_articles[:3]:
                    print(f"      - {article.get('title', 'No title')[:80]}")
        else:
            print(f"❌ No Vistagen articles found in {len(articles)} total articles")
            print(f"   Checking first 10 articles for reference:")
            for article in articles[:10]:
                title = article.get('title', 'No title')[:60]
                print(f"      - {title}")
            
    except Exception as e:
        print(f"❌ Error during search: {e}")
        import traceback
        traceback.print_exc()
    print()

def test_6_check_google_news_date_filtering():
    """Test 6: Check if Google News RSS date filtering is excluding the article"""
    print("=" * 80)
    print("TEST 6: Check Google News RSS date filtering")
    print("=" * 80)
    print()
    
    from config import LOOKBACK_DAYS
    
    target_date = datetime(2025, 12, 17, tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    days_ago = (now - target_date).days
    
    # Google News RSS uses "when:120d" parameter (120 days lookback)
    google_news_lookback = 120
    
    print(f"Target date: {target_date.date()}")
    print(f"Days ago: {days_ago}")
    print(f"Google News RSS lookback: {google_news_lookback} days")
    print(f"Config LOOKBACK_DAYS: {LOOKBACK_DAYS} days")
    
    if days_ago <= google_news_lookback:
        print(f"✅ Date is within Google News RSS {google_news_lookback} day limit")
    else:
        print(f"❌ Date is OUTSIDE Google News RSS {google_news_lookback} day limit")
        print(f"   This would cause the article to be filtered out by Google News RSS")
    
    if days_ago <= LOOKBACK_DAYS:
        print(f"✅ Date is within config LOOKBACK_DAYS ({LOOKBACK_DAYS})")
    else:
        print(f"❌ Date is OUTSIDE config LOOKBACK_DAYS ({LOOKBACK_DAYS})")
    print()

def main():
    """Run all tests"""
    print("=" * 80)
    print("VISTAGEN PHASE 3 TRIAL ARTICLE - DIAGNOSIS")
    print("=" * 80)
    print()
    print("Article: 'Vistagen announced that its Phase 3 trial failed.'")
    print("Source: MSN / VistaGen update")
    print("Date: December 17, 2025")
    print()
    
    test_1_check_company_in_list()
    test_2_check_google_news_search()
    test_3_check_date_range()
    test_4_check_event_type_matching()
    test_5_full_search_simulation()
    test_6_check_google_news_date_filtering()
    
    print("=" * 80)
    print("DIAGNOSIS COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    try:
        main()
        sys.exit(0)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

