#!/usr/bin/env python3
"""
Unit test to verify article count in UI matches expected count
and identify any filtering that might be omitting articles
"""

import sys
from datetime import datetime, timezone
from main import LayoffTracker
from config import MAX_ARTICLES_TO_PROCESS, LOOKBACK_DAYS

def test_article_count_verification():
    """Verify article count at each stage of the pipeline"""
    print("=" * 80)
    print("ARTICLE COUNT VERIFICATION TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Reset state
    tracker.layoffs = []
    tracker.api_call_count = 0
    tracker.total_api_calls_estimated = 0
    
    # Use the default event type (small_cap_with_options)
    event_types = ['bio_companies_small_cap_options']
    selected_sources = ['google_news']
    
    print(f"[TEST] Event types: {event_types}")
    print(f"[TEST] Sources: {selected_sources}")
    print(f"[TEST] MAX_ARTICLES_TO_PROCESS: {MAX_ARTICLES_TO_PROCESS}")
    print(f"[TEST] LOOKBACK_DAYS: {LOOKBACK_DAYS}")
    print()
    
    # Stage 1: Fetch articles from sources
    print("[STAGE 1] Fetching articles from sources...")
    articles, stats = tracker.search_all_realtime_sources(event_types=event_types, selected_sources=selected_sources)
    print(f"   ✅ Fetched {len(articles)} articles from sources")
    print(f"   Source stats: {stats}")
    print()
    
    # Stage 2: Limit to MAX_ARTICLES_TO_PROCESS
    print(f"[STAGE 2] Applying MAX_ARTICLES_TO_PROCESS limit ({MAX_ARTICLES_TO_PROCESS})...")
    articles_after_limit = articles[:MAX_ARTICLES_TO_PROCESS] if len(articles) > MAX_ARTICLES_TO_PROCESS else articles
    print(f"   ✅ After limit: {len(articles_after_limit)} articles")
    if len(articles) > MAX_ARTICLES_TO_PROCESS:
        print(f"   ⚠️  {len(articles) - MAX_ARTICLES_TO_PROCESS} articles were truncated by MAX_ARTICLES_TO_PROCESS limit")
    print()
    
    # Stage 3: Extract company/ticker info
    print("[STAGE 3] Extracting company/ticker info...")
    # Simulate the extraction process
    extracted_count = 0
    companies_found = {}
    extracted_layoffs = []
    
    # Get batch results (simplified - just count)
    total_articles = len(articles_after_limit)
    print(f"   Processing {total_articles} articles for company/ticker extraction...")
    
    # Count articles that would pass extraction
    for i, article in enumerate(articles_after_limit):
        # Check if article has event_type tag (from Google News)
        if article.get('event_type') in event_types:
            # Check if pre-tagged with company
            if article.get('matched_company'):
                extracted_count += 1
                company = article.get('matched_company')
                companies_found[company] = companies_found.get(company, 0) + 1
            # For non-pre-tagged, we'd need Claude extraction (skip for now)
    
    print(f"   ✅ Pre-tagged articles: {extracted_count}")
    print(f"   Companies found: {len(companies_found)}")
    print()
    
    # Stage 4: Limit to 3 per ticker
    print("[STAGE 4] Applying 3-per-ticker limit...")
    # Simulate ticker grouping
    ticker_to_layoffs = {}
    for article in articles_after_limit:
        # This is simplified - in reality we'd need ticker extraction
        # For now, just count pre-tagged articles
        if article.get('matched_company'):
            company = article.get('matched_company')
            # Get ticker from hardcoded map
            ticker_map = tracker._get_bio_pharma_tickers('small_cap_with_options')
            ticker = ticker_map.get(company.upper().strip())
            if ticker:
                if ticker not in ticker_to_layoffs:
                    ticker_to_layoffs[ticker] = []
                ticker_to_layoffs[ticker].append(article)
    
    # Apply 3-per-ticker limit
    final_layoffs = []
    for ticker, layoff_list in ticker_to_layoffs.items():
        # Sort by date (most recent first) - simplified
        final_layoffs.extend(layoff_list[:3])
    
    print(f"   ✅ Unique tickers: {len(ticker_to_layoffs)}")
    print(f"   ✅ After 3-per-ticker limit: {len(final_layoffs)} articles")
    print()
    
    # Stage 5: Full pipeline test
    print("[STAGE 5] Running full fetch_layoffs pipeline...")
    try:
        tracker.layoffs = []
        tracker.api_call_count = 0
        tracker.total_api_calls_estimated = 0
        
        # Run full pipeline
        layoffs = tracker.fetch_layoffs(
            event_types=event_types,
            selected_sources=selected_sources,
            fetch_full_content=False
        )
        
        final_count = len(layoffs)
        print(f"   ✅ Final count from fetch_layoffs: {final_count} articles")
        print()
        
        # Analysis
        print("=" * 80)
        print("ANALYSIS")
        print("=" * 80)
        print()
        print(f"Initial articles fetched: {len(articles)}")
        print(f"After MAX_ARTICLES_TO_PROCESS limit: {len(articles_after_limit)}")
        print(f"Pre-tagged articles: {extracted_count}")
        print(f"Unique tickers: {len(ticker_to_layoffs)}")
        print(f"After 3-per-ticker limit (estimated): {len(final_layoffs)}")
        print(f"Final count (actual): {final_count}")
        print()
        
        if final_count == 114:
            print("✅ UI showing 114 articles matches the actual count!")
        else:
            print(f"⚠️  UI shows 114 but actual count is {final_count}")
            print(f"   Difference: {abs(114 - final_count)} articles")
        
        # Check for potential omissions
        print()
        print("POTENTIAL FILTERING POINTS:")
        print(f"1. MAX_ARTICLES_TO_PROCESS limit: {MAX_ARTICLES_TO_PROCESS}")
        if len(articles) > MAX_ARTICLES_TO_PROCESS:
            print(f"   ⚠️  {len(articles) - MAX_ARTICLES_TO_PROCESS} articles truncated")
        
        print(f"2. Company/ticker extraction: {extracted_count}/{len(articles_after_limit)} articles")
        if extracted_count < len(articles_after_limit):
            print(f"   ⚠️  {len(articles_after_limit) - extracted_count} articles may have failed extraction")
        
        print(f"3. 3-per-ticker limit: {len(ticker_to_layoffs)} unique tickers")
        print(f"   Estimated max articles: {len(ticker_to_layoffs) * 3}")
        if len(final_layoffs) < len(ticker_to_layoffs) * 3:
            print(f"   ⚠️  Some tickers may have fewer than 3 articles")
        
        print(f"4. Final filtering (date, ticker validation, etc.)")
        print(f"   Final count: {final_count}")
        
        return final_count
        
    except Exception as e:
        print(f"❌ Error during full pipeline test: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    count = test_article_count_verification()
    if count is not None:
        print()
        print("=" * 80)
        if count == 114:
            print("✅ VERIFICATION PASSED: UI count (114) matches actual count")
        else:
            print(f"⚠️  VERIFICATION FAILED: UI shows 114 but actual is {count}")
        print("=" * 80)

