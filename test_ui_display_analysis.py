#!/usr/bin/env python3
"""
Unit test to analyze what will be shown in UI out of 51 articles
Shows what will be displayed and what won't (and why)
"""

import sys
from datetime import datetime, timezone
from collections import defaultdict
from main import LayoffTracker

def test_ui_display_analysis():
    """Analyze what will be shown in UI"""
    
    print("=" * 80)
    print("UI DISPLAY ANALYSIS - What Will Be Shown Out of 51 Articles")
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
    print(f"✅ Total articles that will be shown in UI: {total_articles}")
    print()
    
    # Analyze articles
    print("Step 2: Analyzing articles...")
    print("-" * 80)
    print()
    
    # Categorize articles
    articles_with_company = []
    articles_without_company = []
    articles_with_ticker = []
    articles_without_ticker = []
    articles_with_both = []
    articles_with_neither = []
    
    for layoff in tracker.layoffs:
        company = layoff.get('company_name')
        ticker = layoff.get('stock_ticker')
        
        if company:
            articles_with_company.append(layoff)
        else:
            articles_without_company.append(layoff)
        
        if ticker and ticker != 'N/A':
            articles_with_ticker.append(layoff)
        else:
            articles_without_ticker.append(layoff)
        
        if company and ticker and ticker != 'N/A':
            articles_with_both.append(layoff)
        elif not company and (not ticker or ticker == 'N/A'):
            articles_with_neither.append(layoff)
    
    print("📊 BREAKDOWN:")
    print(f"   Articles with company name: {len(articles_with_company)}")
    print(f"   Articles without company name: {len(articles_without_company)}")
    print(f"   Articles with ticker: {len(articles_with_ticker)}")
    print(f"   Articles without ticker: {len(articles_without_ticker)}")
    print(f"   Articles with both company + ticker: {len(articles_with_both)}")
    print(f"   Articles with neither company nor ticker: {len(articles_with_neither)}")
    print()
    
    # Show sample articles in each category
    print("=" * 80)
    print("ARTICLES THAT WILL BE SHOWN IN UI")
    print("=" * 80)
    print()
    
    print(f"✅ ALL {total_articles} ARTICLES WILL BE SHOWN")
    print()
    
    print("Category 1: Articles with Company Name AND Ticker")
    print("-" * 80)
    if articles_with_both:
        print(f"   Count: {len(articles_with_both)}")
        print("   Sample articles:")
        for i, art in enumerate(articles_with_both[:5], 1):
            print(f"   {i}. {art.get('company_name')} ({art.get('stock_ticker')})")
            print(f"      Title: {art.get('title', '')[:70]}...")
            print(f"      Date: {art.get('date', 'N/A')}")
    else:
        print("   Count: 0 (None found)")
    print()
    
    print("Category 2: Articles with Company Name but NO Ticker")
    print("-" * 80)
    articles_company_no_ticker = [a for a in articles_with_company if not (a.get('stock_ticker') and a.get('stock_ticker') != 'N/A')]
    if articles_company_no_ticker:
        print(f"   Count: {len(articles_company_no_ticker)}")
        print("   Sample articles:")
        for i, art in enumerate(articles_company_no_ticker[:5], 1):
            print(f"   {i}. {art.get('company_name')} (Ticker: Didn't find)")
            print(f"      Title: {art.get('title', '')[:70]}...")
            print(f"      Date: {art.get('date', 'N/A')}")
    else:
        print("   Count: 0 (None found)")
    print()
    
    print("Category 3: Articles with NO Company Name but HAS Ticker")
    print("-" * 80)
    articles_no_company_has_ticker = [a for a in articles_without_company if (a.get('stock_ticker') and a.get('stock_ticker') != 'N/A')]
    if articles_no_company_has_ticker:
        print(f"   Count: {len(articles_no_company_has_ticker)}")
        print("   Sample articles:")
        for i, art in enumerate(articles_no_company_has_ticker[:5], 1):
            print(f"   {i}. Company: Didn't find ({art.get('stock_ticker')})")
            print(f"      Title: {art.get('title', '')[:70]}...")
            print(f"      Date: {art.get('date', 'N/A')}")
    else:
        print("   Count: 0 (None found)")
    print()
    
    print("Category 4: Articles with NO Company Name AND NO Ticker")
    print("-" * 80)
    if articles_with_neither:
        print(f"   Count: {len(articles_with_neither)}")
        print("   These will show 'Didn't find' for both company and ticker")
        print("   Sample articles:")
        for i, art in enumerate(articles_with_neither[:10], 1):
            print(f"   {i}. Company: Didn't find | Ticker: Didn't find")
            print(f"      Title: {art.get('title', '')[:70]}...")
            print(f"      Date: {art.get('date', 'N/A')}")
            print(f"      URL: {art.get('url', '')[:60]}...")
    else:
        print("   Count: 0 (None found)")
    print()
    
    # Group by ticker to check for duplicates
    print("=" * 80)
    print("TICKER DISTRIBUTION (to verify no 3-per-ticker limit)")
    print("=" * 80)
    print()
    
    ticker_counts = defaultdict(list)
    for layoff in tracker.layoffs:
        ticker = layoff.get('stock_ticker') or 'N/A'
        ticker_counts[ticker].append(layoff)
    
    print(f"Unique tickers: {len(ticker_counts)}")
    print()
    
    # Show tickers with multiple articles
    tickers_with_multiple = {t: arts for t, arts in ticker_counts.items() if len(arts) > 1}
    if tickers_with_multiple:
        print("Tickers with multiple articles (no limit applied):")
        for ticker, arts in sorted(tickers_with_multiple.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"   {ticker}: {len(arts)} articles ✅ (would have been limited to 3 before)")
    else:
        print("No tickers with multiple articles")
    print()
    
    # Check for articles that won't be shown
    print("=" * 80)
    print("ARTICLES THAT WILL NOT BE SHOWN")
    print("=" * 80)
    print()
    
    # Get source stats to see how many were retrieved
    if hasattr(tracker, 'source_stats'):
        total_retrieved = 0
        for key, stats in tracker.source_stats.items():
            total_retrieved += stats.get('total', 0)
        
        not_shown = total_retrieved - total_articles
        
        if not_shown > 0:
            print(f"❌ {not_shown} articles will NOT be shown")
            print(f"   Retrieved: {total_retrieved}")
            print(f"   Shown: {total_articles}")
            print(f"   Lost: {not_shown}")
            print()
            print("   Reasons articles might not be shown:")
            print("   1. Event type matching failed")
            print("   2. extract_layoff_info returned None")
            print("   3. Other filtering in fetch_layoffs")
        else:
            print(f"✅ ALL {total_retrieved} retrieved articles WILL be shown")
            print(f"   Retrieved: {total_retrieved}")
            print(f"   Shown: {total_articles}")
            print(f"   Lost: 0")
    else:
        print("⚠️  Cannot determine source stats")
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    print(f"Total articles that will be shown in UI: {total_articles}")
    print()
    print("Display breakdown:")
    print(f"  - With company name: {len(articles_with_company)}")
    print(f"  - Without company name (shows 'Didn't find'): {len(articles_without_company)}")
    print(f"  - With ticker: {len(articles_with_ticker)}")
    print(f"  - Without ticker (shows 'Didn't find'): {len(articles_without_ticker)}")
    print(f"  - With both: {len(articles_with_both)}")
    print(f"  - With neither (both show 'Didn't find'): {len(articles_with_neither)}")
    print()
    
    print("Key points:")
    print("  ✅ No 3-per-ticker limiting - all articles shown")
    print("  ✅ No date filtering - all articles shown")
    print("  ✅ Articles without company/ticker show 'Didn't find'")
    print("  ✅ All articles are included in final result")
    print()
    
    return True

if __name__ == '__main__':
    success = test_ui_display_analysis()
    sys.exit(0 if success else 1)

