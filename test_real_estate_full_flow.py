#!/usr/bin/env python3
"""
Test full flow for real estate - from search to extraction
"""

import sys
from main import LayoffTracker

print("=" * 80)
print("REAL ESTATE FULL FLOW TEST")
print("=" * 80)
print()

tracker = LayoffTracker()

# Test the full fetch_layoffs flow
print("Testing fetch_layoffs with real_estate_good_news...")
print("-" * 80)

try:
    layoffs = tracker.fetch_layoffs(
        event_types=['real_estate_good_news'],
        selected_sources=['google_news'],
        fetch_full_content=False  # Faster for testing
    )
    
    print(f"\n✓ fetch_layoffs completed")
    print(f"  Total layoffs returned: {len(layoffs)}")
    print()
    
    if layoffs:
        print("First 10 articles:")
        for i, layoff in enumerate(layoffs[:10], 1):
            title = layoff.get('title', 'N/A')[:60]
            company = layoff.get('company_name', 'N/A')
            ticker = layoff.get('stock_ticker', 'N/A')
            event_type = layoff.get('event_type', 'N/A')
            print(f"  {i}. {title}...")
            print(f"     Company: {company}, Ticker: {ticker}, Event: {event_type}")
    else:
        print("✗ No articles returned")
        print()
        print("Debugging: Checking search results...")
        
        # Check what search_google_news_rss returns
        articles, stats = tracker.search_google_news_rss(event_types=['real_estate_good_news'])
        print(f"  search_google_news_rss returned: {len(articles)} articles")
        print(f"  Stats: {stats}")
        
        if articles:
            print(f"\n  First 5 raw articles:")
            for i, article in enumerate(articles[:5], 1):
                title = article.get('title', 'N/A')[:60]
                event_type = article.get('event_type', 'N/A')
                matched = article.get('matched_company', 'None')
                print(f"    {i}. {title}...")
                print(f"       Event Type: {event_type}, Matched Company: {matched}")
            
            print(f"\n  Testing extract_layoff_info on first article...")
            first_article = articles[0]
            result = tracker.extract_layoff_info(
                first_article,
                fetch_content=False,
                event_types=['real_estate_good_news']
            )
            
            if result:
                print(f"    ✓ extract_layoff_info returned data")
                print(f"      Company: {result.get('company_name', 'N/A')}")
                print(f"      Ticker: {result.get('stock_ticker', 'N/A')}")
            else:
                print(f"    ✗ extract_layoff_info returned None")
                print(f"      This means the article was filtered out")
                
                # Check why it was filtered
                print(f"\n    Checking matches_event_type...")
                matches = tracker.matches_event_type(first_article, 'real_estate_good_news')
                print(f"      matches_event_type: {matches}")
                
except Exception as e:
    print(f"✗ Error: {str(e)[:200]}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)

