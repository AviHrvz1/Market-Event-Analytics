#!/usr/bin/env python3
"""
Unit test to count results for real estate event types
Reports how many articles will be found for each event type
"""

import sys
from main import LayoffTracker
from config import EVENT_TYPES, LOOKBACK_DAYS

print("=" * 80)
print("REAL ESTATE RESULTS COUNT TEST")
print("=" * 80)
print()

# Initialize tracker
tracker = LayoffTracker()

# Test both event types
event_types_to_test = ['real_estate_good_news', 'real_estate_bad_news']

results_summary = {}

for event_type in event_types_to_test:
    print("=" * 80)
    print(f"Testing: {EVENT_TYPES[event_type]['name']}")
    print("=" * 80)
    print()
    
    # Test 1: Check search results
    print(f"Step 1: Testing search_google_news_rss for {event_type}...")
    print("-" * 80)
    articles, stats = tracker.search_google_news_rss(event_types=[event_type])
    print(f"✓ Search completed")
    print(f"  Articles found: {len(articles)}")
    print(f"  Stats: {stats}")
    
    if articles:
        print(f"\n  Sample articles (first 5):")
        for i, article in enumerate(articles[:5], 1):
            title = article.get('title', 'N/A')[:70]
            matched = article.get('matched_company', 'None')
            print(f"    {i}. {title}...")
            print(f"       Matched Company: {matched}")
    print()
    
    # Test 2: Check search_all_realtime_sources
    print(f"Step 2: Testing search_all_realtime_sources for {event_type}...")
    print("-" * 80)
    articles_all, source_stats = tracker.search_all_realtime_sources(
        event_types=[event_type],
        selected_sources=['google_news']
    )
    print(f"✓ search_all_realtime_sources completed")
    print(f"  Articles found: {len(articles_all)}")
    print(f"  Source stats: {source_stats}")
    print()
    
    # Test 3: Full fetch_layoffs flow (without full content for speed)
    print(f"Step 3: Testing full fetch_layoffs flow for {event_type}...")
    print("-" * 80)
    
    # Reset tracker
    tracker.layoffs = []
    
    try:
        layoffs = tracker.fetch_layoffs(
            event_types=[event_type],
            selected_sources=['google_news'],
            fetch_full_content=False  # Faster for testing
        )
        
        print(f"✓ fetch_layoffs completed")
        print(f"  Total layoffs returned: {len(layoffs)}")
        print()
        
        # Analyze results
        with_company = sum(1 for l in layoffs if l.get('company_name'))
        without_company = sum(1 for l in layoffs if not l.get('company_name'))
        with_ticker = sum(1 for l in layoffs if l.get('stock_ticker'))
        without_ticker = sum(1 for l in layoffs if not l.get('stock_ticker'))
        
        print(f"  Breakdown:")
        print(f"    Articles with company name: {with_company}")
        print(f"    Articles without company name: {without_company} (will show 'Didn't find')")
        print(f"    Articles with ticker: {with_ticker}")
        print(f"    Articles without ticker: {without_ticker} (will show 'Didn't find')")
        print()
        
        if layoffs:
            print(f"  Sample results (first 5):")
            for i, layoff in enumerate(layoffs[:5], 1):
                title = layoff.get('title', 'N/A')[:60]
                company = layoff.get('company_name', 'N/A') or "Didn't find"
                ticker = layoff.get('stock_ticker', 'N/A') or "Didn't find"
                print(f"    {i}. {title}...")
                print(f"       Company: {company}")
                print(f"       Ticker: {ticker}")
        
        # Store results
        results_summary[event_type] = {
            'name': EVENT_TYPES[event_type]['name'],
            'search_articles': len(articles),
            'all_sources_articles': len(articles_all),
            'final_layoffs': len(layoffs),
            'with_company': with_company,
            'without_company': without_company,
            'with_ticker': with_ticker,
            'without_ticker': without_ticker
        }
        
    except Exception as e:
        print(f"✗ Error in fetch_layoffs: {str(e)[:200]}")
        import traceback
        traceback.print_exc()
        results_summary[event_type] = {
            'name': EVENT_TYPES[event_type]['name'],
            'error': str(e)[:200]
        }
    
    print()
    print()

# Final Summary
print("=" * 80)
print("FINAL SUMMARY - EXPECTED RESULTS")
print("=" * 80)
print()

for event_type, summary in results_summary.items():
    print(f"{summary['name']}:")
    print(f"  Event Type Key: {event_type}")
    if 'error' in summary:
        print(f"  ✗ Error: {summary['error']}")
    else:
        print(f"  ✓ Search Articles Found: {summary['search_articles']}")
        print(f"  ✓ All Sources Articles: {summary['all_sources_articles']}")
        print(f"  ✓ Final Results (after extraction): {summary['final_layoffs']}")
        print(f"    - With company name: {summary['with_company']}")
        print(f"    - Without company name: {summary['without_company']} (shows 'Didn't find')")
        print(f"    - With ticker: {summary['with_ticker']}")
        print(f"    - Without ticker: {summary['without_ticker']} (shows 'Didn't find')")
    print()

print("=" * 80)
print("EXPECTED UI DISPLAY")
print("=" * 80)
print()

for event_type, summary in results_summary.items():
    if 'error' not in summary:
        print(f"{summary['name']}:")
        print(f"  You will see {summary['final_layoffs']} articles in the table")
        print(f"  - {summary['with_company']} articles will show company names and tickers")
        print(f"  - {summary['without_company']} articles will show 'Didn't find' for company/ticker")
        print(f"  - {summary['with_ticker']} articles will have stock price data")
        print(f"  - {summary['without_ticker']} articles will show 'Didn't find' for ticker and no price data")
        print()

print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)


