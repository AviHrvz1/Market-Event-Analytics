#!/usr/bin/env python3
"""
Final count test for real estate event types
Shows expected number of results for each event type
"""

import sys
from main import LayoffTracker

print("\n" + "=" * 80)
print("REAL ESTATE RESULTS COUNT - FINAL SUMMARY")
print("=" * 80 + "\n")

tracker = LayoffTracker()

summary = {}

for event_type in ['real_estate_good_news', 'real_estate_bad_news']:
    event_name = event_type.replace('_', ' ').title()
    print(f"Testing: {event_name}")
    print("-" * 80)
    
    try:
        # Get articles from search
        articles, source_stats = tracker.search_all_realtime_sources(
            event_types=[event_type],
            selected_sources=['google_news']
        )
        
        total = len(articles)
        pre_matched = sum(1 for a in articles if a.get('matched_company'))
        google_stats = source_stats.get('google_news', {})
        
        summary[event_type] = {
            'name': event_name,
            'total_articles': total,
            'pre_matched': pre_matched,
            'google_total': google_stats.get('total', 0),
            'google_matched': google_stats.get('matched', 0)
        }
        
        print(f"✓ Search completed")
        print(f"  Total articles found: {total}")
        print(f"  Articles with pre-matched company: {pre_matched}")
        print(f"  Google News: {google_stats.get('total', 0)} total, {google_stats.get('matched', 0)} matched")
        
    except Exception as e:
        print(f"✗ Error: {str(e)[:100]}")
        summary[event_type] = {'name': event_name, 'error': str(e)[:100]}
    
    print()

# Final Summary
print("=" * 80)
print("EXPECTED RESULTS FOR UI")
print("=" * 80)
print()

for event_type, data in summary.items():
    if 'error' in data:
        print(f"{data['name']}:")
        print(f"  ✗ Error occurred: {data['error']}")
    else:
        total = data['total_articles']
        pre_matched = data['pre_matched']
        
        print(f"{data['name']}:")
        print(f"  📊 Total articles found: {total}")
        print(f"  🏢 Articles with pre-matched company: {pre_matched}")
        print(f"  ❓ Articles without pre-matched company: {total - pre_matched}")
        print()
        print(f"  📈 EXPECTED FINAL RESULTS:")
        print(f"     - You will see approximately {total} articles in the table")
        print(f"     - ~{pre_matched} articles will have company names (pre-matched)")
        print(f"     - ~{total - pre_matched} articles may need extraction (will show 'Didn't find' if extraction fails)")
        print(f"     - Most articles should have tickers (depends on ticker lookup success)")
        print()
    
    print()

print("=" * 80)
print("NOTE:")
print("=" * 80)
print("These are search results. Final count after extraction may be slightly")
print("different due to:")
print("  - Extraction success/failure")
print("  - Duplicate removal")
print("  - MAX_ARTICLES_TO_PROCESS limit (currently 300)")
print()
print("=" * 80)


