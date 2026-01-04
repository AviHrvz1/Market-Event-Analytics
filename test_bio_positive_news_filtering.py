#!/usr/bin/env python3
"""
Unit test to check why bio_positive_news only returns 10 results
when Google News RSS returns 51 articles
"""

import sys
from datetime import datetime, timedelta, timezone
from main import LayoffTracker
from config import EVENT_TYPES, LOOKBACK_DAYS

def test_bio_positive_news_filtering():
    """Test bio_positive_news event type filtering"""
    
    print("=" * 80)
    print("BIO POSITIVE NEWS FILTERING ANALYSIS")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Get bio_positive_news keywords
    bio_positive_config = EVENT_TYPES.get('bio_positive_news', {})
    keywords = bio_positive_config.get('keywords', [])
    
    print(f"Bio Positive News Keywords: {len(keywords)} total")
    print(f"Sample keywords: {keywords[:10]}")
    print()
    
    # Test 1: Check Google News search
    print("=" * 80)
    print("TEST 1: Google News Search")
    print("=" * 80)
    print()
    
    # Search for bio positive news
    event_types = ['bio_positive_news']
    selected_sources = ['google_news']
    
    print("Fetching articles with bio_positive_news event type...")
    tracker.fetch_layoffs(
        fetch_full_content=False,
        event_types=event_types,
        selected_sources=selected_sources
    )
    
    print()
    print(f"Total articles fetched: {len(tracker.layoffs)}")
    print()
    
    # Analyze results
    if tracker.layoffs:
        print("Article Analysis:")
        print("-" * 80)
        
        # Check which keywords matched
        keyword_matches = {}
        for layoff in tracker.layoffs:
            title = layoff.get('title', '').lower()
            description = layoff.get('description', '').lower()
            content = f"{title} {description}"
            
            # Find which keywords matched
            matched_keywords = []
            for keyword in keywords:
                if keyword.lower() in content:
                    matched_keywords.append(keyword)
                    if keyword not in keyword_matches:
                        keyword_matches[keyword] = 0
                    keyword_matches[keyword] += 1
            
            if matched_keywords:
                print(f"  {layoff.get('company_name', 'Unknown')}: {len(matched_keywords)} keywords matched")
                print(f"    Matched: {matched_keywords[:3]}")
        
        print()
        print("Top Matched Keywords:")
        print("-" * 80)
        sorted_keywords = sorted(keyword_matches.items(), key=lambda x: x[1], reverse=True)
        for keyword, count in sorted_keywords[:20]:
            print(f"  '{keyword}': {count} articles")
    else:
        print("No articles found!")
    
    print()
    
    # Test 2: Check raw Google News RSS results
    print("=" * 80)
    print("TEST 2: Raw Google News RSS Results")
    print("=" * 80)
    print()
    
    # Manually search Google News RSS
    try:
        from main import search_google_news_rss
        
        # Search with bio positive keywords
        search_query = " OR ".join([f'"{kw}"' for kw in keywords[:20]])  # Use first 20 keywords
        print(f"Search query (first 20 keywords): {search_query[:200]}...")
        print()
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=LOOKBACK_DAYS)
        
        print(f"Date range: {start_date.date()} to {end_date.date()}")
        print()
        
        raw_articles = search_google_news_rss(
            query=search_query,
            start_date=start_date,
            end_date=end_date,
            max_results=100
        )
        
        print(f"Raw Google News RSS articles: {len(raw_articles)}")
        print()
        
        if raw_articles:
            print("Sample raw articles:")
            for i, article in enumerate(raw_articles[:10], 1):
                title = article.get('title', 'No title')
                print(f"  {i}. {title[:80]}...")
        
        print()
        
        # Check how many match bio_positive_news keywords
        print("Checking keyword matches in raw articles...")
        matched_articles = []
        unmatched_articles = []
        
        for article in raw_articles:
            title = article.get('title', '').lower()
            description = article.get('description', '').lower()
            content = f"{title} {description}"
            
            # Check if any keyword matches
            matched = False
            for keyword in keywords:
                if keyword.lower() in content:
                    matched = True
                    break
            
            if matched:
                matched_articles.append(article)
            else:
                unmatched_articles.append(article)
        
        print(f"Articles matching keywords: {len(matched_articles)}")
        print(f"Articles NOT matching keywords: {len(unmatched_articles)}")
        print()
        
        if unmatched_articles:
            print("Sample unmatched articles (why they didn't match):")
            for i, article in enumerate(unmatched_articles[:10], 1):
                title = article.get('title', 'No title')
                print(f"  {i}. {title[:80]}...")
        
    except Exception as e:
        print(f"Error in raw search: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # Test 3: Check filtering logic
    print("=" * 80)
    print("TEST 3: Filtering Logic Check")
    print("=" * 80)
    print()
    
    # Check if there's date filtering
    print("Checking date filtering...")
    if tracker.layoffs:
        dates = [layoff.get('datetime') for layoff in tracker.layoffs if layoff.get('datetime')]
        if dates:
            min_date = min(dates)
            max_date = max(dates)
            print(f"  Article date range: {min_date.date()} to {max_date.date()}")
            print(f"  Expected range: {start_date.date()} to {end_date.date()}")
            
            # Check for articles outside range
            outside_range = [d for d in dates if d < start_date or d > end_date]
            if outside_range:
                print(f"  ⚠️  {len(outside_range)} articles outside date range")
            else:
                print(f"  ✅ All articles within date range")
    
    # Check if there's deduplication
    print()
    print("Checking deduplication...")
    companies = [layoff.get('company_name') for layoff in tracker.layoffs]
    unique_companies = set(companies)
    print(f"  Total articles: {len(tracker.layoffs)}")
    print(f"  Unique companies: {len(unique_companies)}")
    
    if len(companies) > len(unique_companies):
        print(f"  ⚠️  {len(companies) - len(unique_companies)} duplicate companies found")
        # Show duplicates
        from collections import Counter
        company_counts = Counter(companies)
        duplicates = {k: v for k, v in company_counts.items() if v > 1}
        if duplicates:
            print(f"  Duplicate companies: {duplicates}")
    else:
        print(f"  ✅ No duplicates")
    
    print()
    
    # Test 4: Check keyword matching efficiency
    print("=" * 80)
    print("TEST 4: Keyword Matching Efficiency")
    print("=" * 80)
    print()
    
    # Test with sample articles
    test_articles = [
        "FDA approves new cancer drug after positive Phase 3 trial results",
        "Biotech company receives breakthrough therapy designation from FDA",
        "Phase 3 trial meets primary endpoint with statistically significant results",
        "Company announces positive topline results from clinical trial",
        "FDA grants fast track designation for new treatment",
        "Biotech stock surges on FDA approval news",
        "Company reports positive overall survival data",
        "Regulatory submission accepted for new drug application",
        "Partnership announced with major pharma company",
        "Acquisition offer received from larger biotech firm"
    ]
    
    print("Testing keyword matching on sample articles:")
    print()
    
    for article in test_articles:
        content_lower = article.lower()
        matched = [kw for kw in keywords if kw.lower() in content_lower]
        if matched:
            print(f"  ✅ '{article[:60]}...'")
            print(f"     Matched: {matched[:2]}")
        else:
            print(f"  ❌ '{article[:60]}...'")
            print(f"     No keywords matched!")
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"Total articles from fetch_layoffs: {len(tracker.layoffs)}")
    print(f"Expected from Google News RSS: 51")
    print()
    
    if len(tracker.layoffs) < 51:
        print("⚠️  ISSUE: Articles are being filtered out!")
        print()
        print(f"Lost: {51 - len(tracker.layoffs)} articles ({((51 - len(tracker.layoffs)) / 51 * 100):.1f}% loss)")
        print()
        print("Possible causes:")
        print("  1. Company name extraction failing (most likely)")
        print("  2. Ticker lookup failing")
        print("  3. Date filtering removing articles")
        print("  4. Deduplication removing articles")
        print()
        print("FIX APPLIED:")
        print("  - Added bio company candidates for bio_positive_news extraction")
        print("  - This should improve company name extraction from article titles/descriptions")
        print()
        print("If still seeing low results, check:")
        print("  - Are company names in the article titles/descriptions?")
        print("  - Are the company names matching our bio company list?")
        print("  - Is ticker lookup succeeding for extracted companies?")
    else:
        print("✅ Article count matches expected")

if __name__ == '__main__':
    test_bio_positive_news_filtering()

