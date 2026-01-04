#!/usr/bin/env python3
"""
Unit test to diagnose why only 19 articles appear when 279 were matched.
Tracks articles at each filtering stage.
"""

import sys
from datetime import datetime, timedelta, timezone
from main import LayoffTracker
from config import MAX_ARTICLES_TO_PROCESS, MIN_LAYOFF_PERCENTAGE

def test_article_filtering_diagnosis():
    """Diagnose where articles are being filtered out"""
    
    print("=" * 80)
    print("ARTICLE FILTERING DIAGNOSIS TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Use same parameters as the UI
    event_types = ['bio_companies']
    selected_sources = ['google_news', 'benzinga_news']
    
    print(f"📋 Test Configuration:")
    print(f"   Event types: {event_types}")
    print(f"   Sources: {selected_sources}")
    print(f"   MAX_ARTICLES_TO_PROCESS: {MAX_ARTICLES_TO_PROCESS}")
    print(f"   MIN_LAYOFF_PERCENTAGE: {MIN_LAYOFF_PERCENTAGE}%")
    print()
    
    # Step 1: Fetch articles from sources
    print("🔍 Step 1: Fetching articles from sources...")
    articles, source_stats = tracker.search_all_realtime_sources(
        event_types=event_types, 
        selected_sources=selected_sources
    )
    
    initial_count = len(articles)
    print(f"   ✅ Initial articles fetched: {initial_count}")
    print(f"   Source breakdown:")
    for key, stats in source_stats.items():
        print(f"      {stats['name']}: {stats['total']} total, {stats['matched']} matched")
    print()
    
    # Step 2: Sort and apply MAX_ARTICLES_TO_PROCESS limit
    print("🔍 Step 2: Sorting and applying MAX_ARTICLES_TO_PROCESS limit...")
    def parse_date(date_str):
        if not date_str:
            return datetime.min.replace(tzinfo=timezone.utc)
        try:
            from dateutil import parser
            return parser.parse(date_str).replace(tzinfo=timezone.utc)
        except:
            return datetime.min.replace(tzinfo=timezone.utc)
    
    articles.sort(key=lambda x: parse_date(x.get('publishedAt', '')), reverse=True)
    
    before_limit = len(articles)
    if len(articles) > MAX_ARTICLES_TO_PROCESS:
        articles = articles[:MAX_ARTICLES_TO_PROCESS]
        print(f"   ⚠️  Limited from {before_limit} to {len(articles)} articles (MAX_ARTICLES_TO_PROCESS={MAX_ARTICLES_TO_PROCESS})")
        print(f"   ❌ Lost: {before_limit - len(articles)} articles")
    else:
        print(f"   ✅ No limit applied: {len(articles)} articles (below {MAX_ARTICLES_TO_PROCESS} limit)")
    print()
    
    # Step 3: Extract company/ticker info
    print("🔍 Step 3: Extracting company/ticker information...")
    articles_processed = 0
    articles_with_companies = 0
    articles_without_companies = []
    companies_found = {}
    extracted_layoffs = []
    
    for article in articles:
        articles_processed += 1
        layoff_info = tracker.extract_layoff_info(article, fetch_content=False, event_types=event_types)
        
        if layoff_info:
            articles_with_companies += 1
            company = layoff_info.get('company_name')
            ticker = layoff_info.get('stock_ticker')
            
            if company:
                companies_found[company] = companies_found.get(company, 0) + 1
                extracted_layoffs.append(layoff_info)
            else:
                articles_without_companies.append({
                    'title': article.get('title', '')[:60],
                    'ticker': ticker
                })
        else:
            articles_without_companies.append({
                'title': article.get('title', '')[:60],
                'ticker': None
            })
    
    print(f"   ✅ Articles processed: {articles_processed}")
    print(f"   ✅ Articles with company/ticker extracted: {articles_with_companies}")
    print(f"   ❌ Articles without company/ticker: {len(articles_without_companies)}")
    print(f"   ✅ Unique companies found: {len(companies_found)}")
    print(f"   ✅ Total extracted layoffs: {len(extracted_layoffs)}")
    
    if articles_without_companies:
        print(f"   📋 Sample articles without company/ticker (first 5):")
        for i, item in enumerate(articles_without_companies[:5], 1):
            print(f"      {i}. {item['title']} (ticker: {item['ticker']})")
    print()
    
    # Step 4: Apply 3-per-ticker limit
    print("🔍 Step 4: Applying 3-per-ticker limit...")
    before_ticker_limit = len(extracted_layoffs)
    
    if extracted_layoffs:
        ticker_to_layoffs = {}
        ticker_counts = {}
        
        for layoff in extracted_layoffs:
            ticker = layoff.get('stock_ticker')
            if not ticker:
                continue
            
            if ticker not in ticker_to_layoffs:
                ticker_to_layoffs[ticker] = []
            
            ticker_to_layoffs[ticker].append(layoff)
            ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
        
        # Apply 3-per-ticker limit
        limited_layoffs = []
        tickers_affected = []
        total_filtered_by_ticker_limit = 0
        
        for ticker, layoffs_list in ticker_to_layoffs.items():
            layoffs_list.sort(
                key=lambda x: x.get('datetime') or datetime.min.replace(tzinfo=timezone.utc), 
                reverse=True
            )
            
            original_count = len(layoffs_list)
            kept = layoffs_list[:3]
            filtered = len(layoffs_list) - len(kept)
            
            if filtered > 0:
                tickers_affected.append({
                    'ticker': ticker,
                    'original': original_count,
                    'kept': len(kept),
                    'filtered': filtered
                })
                total_filtered_by_ticker_limit += filtered
            
            limited_layoffs.extend(kept)
        
        extracted_layoffs = limited_layoffs
        
        print(f"   ✅ Before ticker limit: {before_ticker_limit} articles")
        print(f"   ✅ After ticker limit: {len(extracted_layoffs)} articles")
        print(f"   ❌ Filtered by ticker limit: {total_filtered_by_ticker_limit} articles")
        print(f"   📊 Tickers with >3 articles: {len(tickers_affected)}")
        
        if tickers_affected:
            print(f"   📋 Tickers affected by 3-per-ticker limit:")
            for item in sorted(tickers_affected, key=lambda x: x['filtered'], reverse=True)[:10]:
                print(f"      {item['ticker']}: {item['original']} → {item['kept']} (filtered {item['filtered']})")
    else:
        print(f"   ⚠️  No layoffs to limit")
    print()
    
    # Step 5: Final filtering (company_name + ticker requirement)
    print("🔍 Step 5: Final filtering (company_name + ticker requirement)...")
    before_final_filter = len(extracted_layoffs)
    final_layoffs = []
    filtered_no_company = 0
    filtered_no_ticker = 0
    filtered_low_percentage = 0
    
    for layoff_info in extracted_layoffs:
        has_company = layoff_info.get('company_name')
        has_ticker = layoff_info.get('stock_ticker')
        percentage = layoff_info.get('layoff_percentage')
        
        if percentage:
            if percentage >= MIN_LAYOFF_PERCENTAGE:
                final_layoffs.append(layoff_info)
            else:
                filtered_low_percentage += 1
        elif has_company and has_ticker:
            layoff_info['layoff_percentage'] = 0
            final_layoffs.append(layoff_info)
        else:
            if not has_company:
                filtered_no_company += 1
            if not has_ticker:
                filtered_no_ticker += 1
    
    print(f"   ✅ Before final filter: {before_final_filter} articles")
    print(f"   ✅ After final filter: {len(final_layoffs)} articles")
    if filtered_no_company > 0:
        print(f"   ❌ Filtered (no company_name): {filtered_no_company}")
    if filtered_no_ticker > 0:
        print(f"   ❌ Filtered (no stock_ticker): {filtered_no_ticker}")
    if filtered_low_percentage > 0:
        print(f"   ❌ Filtered (low percentage < {MIN_LAYOFF_PERCENTAGE}%): {filtered_low_percentage}")
    print()
    
    # Summary
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"Initial articles fetched:     {initial_count:>4}")
    print(f"After MAX_ARTICLES limit:     {len(articles):>4}  (lost {initial_count - len(articles)})")
    print(f"After company extraction:     {len(extracted_layoffs):>4}  (lost {len(articles) - before_ticker_limit})")
    print(f"After 3-per-ticker limit:    {len(extracted_layoffs):>4}  (lost {total_filtered_by_ticker_limit if 'total_filtered_by_ticker_limit' in locals() else 0})")
    print(f"After final filtering:        {len(final_layoffs):>4}  (lost {before_final_filter - len(final_layoffs)})")
    print()
    print(f"🎯 FINAL RESULT: {len(final_layoffs)} articles")
    print()
    
    # Breakdown by ticker
    if final_layoffs:
        print("📋 Final articles by ticker:")
        ticker_final_counts = {}
        for layoff in final_layoffs:
            ticker = layoff.get('stock_ticker', 'N/A')
            ticker_final_counts[ticker] = ticker_final_counts.get(ticker, 0) + 1
        
        for ticker, count in sorted(ticker_final_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   {ticker}: {count} article(s)")
    
    print()
    print("=" * 80)
    
    return {
        'initial_count': initial_count,
        'after_max_limit': len(articles),
        'after_extraction': before_ticker_limit,
        'after_ticker_limit': len(extracted_layoffs),
        'final_count': len(final_layoffs),
        'companies_found': len(companies_found),
        'tickers_affected': len(tickers_affected) if 'tickers_affected' in locals() else 0
    }

if __name__ == '__main__':
    try:
        results = test_article_filtering_diagnosis()
        print("\n✅ Test completed successfully")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

