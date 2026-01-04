#!/usr/bin/env python3
"""
Simple test to count real estate search results
Tests search only (not full extraction) for faster results
"""

import sys
from main import LayoffTracker

print("=" * 80)
print("REAL ESTATE SEARCH RESULTS COUNT")
print("=" * 80)
print()
print("This test counts articles found by search (before extraction)")
print("Full extraction may filter some articles, so final count may be lower")
print()

tracker = LayoffTracker()

results = {}

for event_type in ['real_estate_good_news', 'real_estate_bad_news']:
    print(f"{'='*80}")
    print(f"Testing: {event_type}")
    print(f"{'='*80}")
    print()
    
    try:
        # Test search_all_realtime_sources (what fetch_layoffs uses)
        articles, source_stats = tracker.search_all_realtime_sources(
            event_types=[event_type],
            selected_sources=['google_news']
        )
        
        total_articles = len(articles)
        articles_with_matched_company = sum(1 for a in articles if a.get('matched_company'))
        
        print(f"✓ Search completed")
        print(f"  Total articles found: {total_articles}")
        print(f"  Articles with pre-matched company: {articles_with_matched_company}")
        print(f"  Source stats: {source_stats.get('google_news', {})}")
        print()
        
        if articles:
            print(f"  Sample articles (first 5):")
            for i, article in enumerate(articles[:5], 1):
                title = article.get('title', 'N/A')[:65]
                matched = article.get('matched_company', 'None')
                event_tag = article.get('event_type', 'None')
                print(f"    {i}. {title}...")
                print(f"       Event Type: {event_tag}, Matched Company: {matched}")
        
        results[event_type] = {
            'total_articles': total_articles,
            'with_matched_company': articles_with_matched_company,
            'source_stats': source_stats.get('google_news', {})
        }
        
    except Exception as e:
        print(f"✗ Error: {str(e)[:200]}")
        import traceback
        traceback.print_exc()
        results[event_type] = {'error': str(e)[:200]}
    
    print()
    print()

# Summary
print("=" * 80)
print("SUMMARY - EXPECTED RESULTS")
print("=" * 80)
print()

for event_type, data in results.items():
    event_name = event_type.replace('_', ' ').title()
    print(f"{event_name}:")
    
    if 'error' in data:
        print(f"  ✗ Error: {data['error']}")
    else:
        total = data['total_articles']
        matched = data['with_matched_company']
        stats = data.get('source_stats', {})
        
        print(f"  ✓ Articles found by search: {total}")
        print(f"  ✓ Articles with pre-matched company: {matched}")
        if stats:
            print(f"  ✓ Google News stats: {stats.get('total', 0)} total, {stats.get('matched', 0)} matched")
        
        print()
        print(f"  ESTIMATED FINAL RESULTS (after extraction):")
        print(f"    - Expected final count: {total} articles (all articles are kept)")
        print(f"    - Articles with company name: ~{matched}-{total} (pre-matched + extracted)")
        print(f"    - Articles without company name: ~{total - matched} (will show 'Didn't find')")
        print(f"    - Articles with ticker: ~{matched}-{total} (depends on ticker lookup success)")
        print(f"    - Articles without ticker: ~{total - matched} (will show 'Didn't find')")
        print()
        print(f"  NOTE: Final count may be slightly lower due to:")
        print(f"    - Extraction failures (rare)")
        print(f"    - Duplicate filtering")
        print(f"    - Date range filtering (if any)")
    
    print()

print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)


