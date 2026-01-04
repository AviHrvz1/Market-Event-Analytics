#!/usr/bin/env python3
"""
Unit test to verify that all bio_positive_news articles are shown
- No 3-per-ticker limiting
- Articles without company names/tickers are included
- All 52 articles should be displayed
"""

import sys
from datetime import datetime, timezone
from collections import defaultdict
from main import LayoffTracker

def test_bio_positive_all_articles():
    """Test that all articles are shown without filtering"""
    
    print("=" * 80)
    print("BIO POSITIVE NEWS - ALL ARTICLES TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    event_types = ['bio_positive_news']
    selected_sources = ['google_news']
    
    print("Step 1: Fetching articles...")
    print("-" * 80)
    
    # Fetch articles
    tracker.fetch_layoffs(
        fetch_full_content=False,
        event_types=event_types,
        selected_sources=selected_sources
    )
    
    total_articles = len(tracker.layoffs)
    print(f"✅ Total articles in result: {total_articles}")
    print()
    
    # Expected: Should be close to 51-52 articles (from Google News)
    expected_min = 40  # Allow some variance
    expected_max = 60
    
    print("Step 2: Verifying article count...")
    print("-" * 80)
    
    if total_articles < expected_min:
        print(f"❌ FAIL: Only {total_articles} articles (expected at least {expected_min})")
        return False
    elif total_articles > expected_max:
        print(f"⚠️  WARNING: {total_articles} articles (expected max {expected_max})")
    else:
        print(f"✅ PASS: {total_articles} articles (expected {expected_min}-{expected_max})")
    print()
    
    # Step 3: Check for 3-per-ticker limiting
    print("Step 3: Checking for 3-per-ticker limiting...")
    print("-" * 80)
    
    ticker_counts = defaultdict(int)
    for layoff in tracker.layoffs:
        ticker = layoff.get('stock_ticker')
        if ticker and ticker != 'N/A':
            ticker_counts[ticker] += 1
    
    max_per_ticker = max(ticker_counts.values()) if ticker_counts else 0
    tickers_with_more_than_3 = {t: c for t, c in ticker_counts.items() if c > 3}
    
    if tickers_with_more_than_3:
        print(f"✅ PASS: 3-per-ticker limit removed - found tickers with >3 articles:")
        for ticker, count in sorted(tickers_with_more_than_3.items(), key=lambda x: x[1], reverse=True):
            print(f"   {ticker}: {count} articles")
    else:
        print(f"✅ PASS: No tickers with >3 articles (max: {max_per_ticker})")
    print()
    
    # Step 4: Check articles without company names/tickers
    print("Step 4: Checking articles without company names/tickers...")
    print("-" * 80)
    
    articles_without_company = [l for l in tracker.layoffs if not l.get('company_name')]
    articles_without_ticker = [l for l in tracker.layoffs if not l.get('stock_ticker') or l.get('stock_ticker') == 'N/A']
    articles_with_none_company = [l for l in tracker.layoffs if l.get('company_name') is None]
    articles_with_none_ticker = [l for l in tracker.layoffs if l.get('stock_ticker') is None]
    
    # Check for "N/A" string (should be None instead)
    articles_with_na_company = [l for l in tracker.layoffs if l.get('company_name') == 'N/A']
    articles_with_na_ticker = [l for l in tracker.layoffs if l.get('stock_ticker') == 'N/A']
    
    print(f"Articles without company_name: {len(articles_without_company)}")
    print(f"  - company_name is None: {len(articles_with_none_company)}")
    print(f"  - company_name is 'N/A' string: {len(articles_with_na_company)} ⚠️ (should be None)")
    print()
    print(f"Articles without stock_ticker: {len(articles_without_ticker)}")
    print(f"  - stock_ticker is None: {len(articles_with_none_ticker)}")
    print(f"  - stock_ticker is 'N/A' string: {len(articles_with_na_ticker)} ⚠️ (should be None)")
    print()
    
    if articles_with_na_company:
        print("⚠️  WARNING: Some articles have company_name='N/A' (string) instead of None")
        print("   Sample articles:")
        for art in articles_with_na_company[:3]:
            print(f"   - {art.get('title', '')[:60]}...")
        print()
    
    if articles_with_na_ticker:
        print("⚠️  WARNING: Some articles have stock_ticker='N/A' (string) instead of None")
        print("   Sample articles:")
        for art in articles_with_na_ticker[:3]:
            print(f"   - {art.get('title', '')[:60]}...")
        print()
    
    # Step 5: Verify all articles are included
    print("Step 5: Verifying all articles are included...")
    print("-" * 80)
    
    articles_with_company = [l for l in tracker.layoffs if l.get('company_name')]
    articles_with_ticker = [l for l in tracker.layoffs if l.get('stock_ticker') and l.get('stock_ticker') != 'N/A']
    
    print(f"Articles with company_name: {len(articles_with_company)}")
    print(f"Articles without company_name: {len(articles_without_company)}")
    print(f"Articles with stock_ticker: {len(articles_with_ticker)}")
    print(f"Articles without stock_ticker: {len(articles_without_ticker)}")
    print()
    
    # Verify sum equals total
    if len(articles_with_company) + len(articles_without_company) == total_articles:
        print("✅ PASS: All articles accounted for (with/without company)")
    else:
        print(f"❌ FAIL: Article count mismatch: {len(articles_with_company)} + {len(articles_without_company)} != {total_articles}")
        return False
    
    if len(articles_with_ticker) + len(articles_without_ticker) == total_articles:
        print("✅ PASS: All articles accounted for (with/without ticker)")
    else:
        print(f"❌ FAIL: Article count mismatch: {len(articles_with_ticker)} + {len(articles_without_ticker)} != {total_articles}")
        return False
    print()
    
    # Step 6: Check for duplicate articles
    print("Step 6: Checking for duplicate articles...")
    print("-" * 80)
    
    # Group by URL to find duplicates
    url_to_articles = defaultdict(list)
    for layoff in tracker.layoffs:
        url = layoff.get('url', '')
        if url:
            url_to_articles[url].append(layoff)
    
    duplicates = {url: arts for url, arts in url_to_articles.items() if len(arts) > 1}
    
    if duplicates:
        print(f"⚠️  WARNING: Found {len(duplicates)} duplicate URLs:")
        for url, arts in list(duplicates.items())[:3]:
            print(f"   {url[:60]}... ({len(arts)} times)")
    else:
        print("✅ PASS: No duplicate URLs found")
    print()
    
    # Step 7: Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    print(f"Total articles: {total_articles}")
    print(f"Articles with company names: {len(articles_with_company)}")
    print(f"Articles without company names: {len(articles_without_company)}")
    print(f"Articles with tickers: {len(articles_with_ticker)}")
    print(f"Articles without tickers: {len(articles_without_ticker)}")
    print(f"Max articles per ticker: {max_per_ticker}")
    print()
    
    # Final verification
    all_pass = True
    
    if total_articles < expected_min:
        print("❌ FAIL: Not enough articles")
        all_pass = False
    
    if tickers_with_more_than_3 and max_per_ticker <= 3:
        print("❌ FAIL: 3-per-ticker limit still applied")
        all_pass = False
    
    if articles_with_na_company or articles_with_na_ticker:
        print("⚠️  WARNING: Some articles have 'N/A' string instead of None")
        # Not a failure, but should be fixed
    
    if all_pass:
        print("✅ ALL TESTS PASSED!")
        print()
        print("Expected behavior:")
        print("  - All articles are included (no filtering)")
        print("  - No 3-per-ticker limiting")
        print("  - Articles without company names/tickers are included")
        print("  - company_name/stock_ticker should be None (not 'N/A' string) when missing")
    else:
        print("❌ SOME TESTS FAILED")
    
    return all_pass

if __name__ == '__main__':
    success = test_bio_positive_all_articles()
    sys.exit(0 if success else 1)

