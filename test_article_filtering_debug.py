#!/usr/bin/env python3
"""
Debug test to see where articles are being filtered out in the actual app flow
"""

import sys
from main import LayoffTracker
from config import EVENT_TYPES

def test_full_flow_small_cap():
    """Test the full flow that the app uses"""
    print("=" * 80)
    print("DEBUG: Full Flow Test - Small-Cap Biotech")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    event_types = ['bio_companies_small_cap']
    selected_sources = ['google_news', 'benzinga_news']
    
    # Step 1: Search for articles
    print("Step 1: Searching for articles...")
    articles, source_stats = tracker.search_all_realtime_sources(
        event_types=event_types,
        selected_sources=selected_sources
    )
    print(f"   ✅ Found {len(articles)} articles from search")
    print()
    
    if len(articles) == 0:
        print("   ❌ PROBLEM: No articles found in search!")
        print("   This means the search itself is failing, not the filtering")
        return
    
    # Step 2: Check event type matching
    print("Step 2: Checking event type matching...")
    matched_articles = []
    for article in articles[:10]:  # Check first 10
        matches = tracker.matches_event_type(article, 'bio_companies_small_cap')
        if matches:
            matched_articles.append(article)
            print(f"   ✅ Matches: {article.get('title', 'N/A')[:60]}...")
        else:
            print(f"   ❌ Doesn't match: {article.get('title', 'N/A')[:60]}...")
    print(f"   Matched: {len(matched_articles)}/{min(10, len(articles))}")
    print()
    
    # Step 3: Check extract_layoff_info
    print("Step 3: Testing extract_layoff_info...")
    extracted_count = 0
    for article in articles[:10]:
        try:
            result = tracker.extract_layoff_info(
                article,
                fetch_content=False,
                event_types=event_types
            )
            if result:
                extracted_count += 1
                print(f"   ✅ Extracted: {result.get('company_name', 'N/A')} ({result.get('ticker', 'N/A')})")
            else:
                print(f"   ❌ Failed extraction: {article.get('title', 'N/A')[:60]}...")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    print(f"   Extracted: {extracted_count}/{min(10, len(articles))}")
    print()
    
    # Step 4: Check what extract_layoff_info filters out
    print("Step 4: Analyzing why articles are filtered...")
    for article in articles[:5]:
        title = article.get('title', '')
        description = article.get('description', '')
        event_type_tag = article.get('event_type', 'N/A')
        source_name = article.get('source', {}).get('name', 'N/A')
        
        print(f"\n   Article: {title[:60]}...")
        print(f"   Event type tag: {event_type_tag}")
        print(f"   Source: {source_name}")
        
        # Check if it matches
        matches = tracker.matches_event_type(article, 'bio_companies_small_cap')
        print(f"   matches_event_type: {matches}")
        
        if matches:
            # Try extraction
            result = tracker.extract_layoff_info(
                article,
                fetch_content=False,
                event_types=event_types
            )
            if result:
                print(f"   ✅ Extraction successful")
            else:
                print(f"   ❌ Extraction failed (likely company/ticker extraction)")

if __name__ == '__main__':
    try:
        test_full_flow_small_cap()
        print("\n✅ Debug test completed")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

