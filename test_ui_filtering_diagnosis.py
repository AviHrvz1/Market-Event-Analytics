#!/usr/bin/env python3
"""
Diagnostic test to understand why UI shows only 21 articles
Traces the exact same path as the UI
"""

import sys
from datetime import datetime, timezone
from main import LayoffTracker
from config import MAX_ARTICLES_TO_PROCESS, MIN_LAYOFF_PERCENTAGE

def test_ui_filtering_diagnosis():
    """Diagnose filtering in the exact same way as UI"""
    
    print("=" * 80)
    print("UI FILTERING DIAGNOSIS - EXACT UI PATH")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    event_types = ['bio_companies']
    selected_sources = ['google_news', 'benzinga_news']
    
    print(f"📋 Configuration:")
    print(f"   MAX_ARTICLES_TO_PROCESS: {MAX_ARTICLES_TO_PROCESS}")
    print(f"   MIN_LAYOFF_PERCENTAGE: {MIN_LAYOFF_PERCENTAGE}%")
    print()
    
    # Step 1: Fetch articles (same as UI)
    print("🔍 Step 1: Fetching articles...")
    articles, source_stats = tracker.search_all_realtime_sources(
        event_types=event_types, 
        selected_sources=selected_sources
    )
    
    initial_count = len(articles)
    print(f"   ✅ Initial articles: {initial_count}")
    print()
    
    # Step 2: Sort and limit (same as UI)
    print("🔍 Step 2: Sorting and limiting...")
    def parse_date(date_str):
        if not date_str:
            return datetime.min.replace(tzinfo=timezone.utc)
        try:
            from dateutil import parser
            return parser.parse(date_str).replace(tzinfo=timezone.utc)
        except:
            return datetime.min.replace(tzinfo=timezone.utc)
    
    articles.sort(key=lambda x: parse_date(x.get('publishedAt', '')), reverse=True)
    
    if len(articles) > MAX_ARTICLES_TO_PROCESS:
        articles = articles[:MAX_ARTICLES_TO_PROCESS]
        print(f"   ⚠️  Limited to {MAX_ARTICLES_TO_PROCESS}")
    else:
        print(f"   ✅ No limit applied: {len(articles)} articles")
    print()
    
    # Step 3: Extract layoff info (same as UI - this is where _is_ticker_available is called)
    print("🔍 Step 3: Extracting company/ticker info (with Prixe.io availability check)...")
    print("   ⚠️  NOTE: extract_layoff_info() filters out articles if ticker not available")
    print()
    
    extracted_layoffs = []
    companies_found = {}
    filtered_no_extraction = 0
    filtered_ticker_unavailable = 0
    ticker_availability_stats = {}
    
    for i, article in enumerate(articles, 1):
        layoff_info = tracker.extract_layoff_info(article, fetch_content=False, event_types=event_types)
        
        if layoff_info:
            ticker = layoff_info.get('stock_ticker')
            company = layoff_info.get('company_name')
            
            if ticker:
                # Track ticker availability
                is_available = tracker._is_ticker_available(ticker)
                ticker_availability_stats[ticker] = ticker_availability_stats.get(ticker, {'available': 0, 'unavailable': 0})
                if is_available:
                    ticker_availability_stats[ticker]['available'] += 1
                else:
                    ticker_availability_stats[ticker]['unavailable'] += 1
                    filtered_ticker_unavailable += 1
                    if filtered_ticker_unavailable <= 5:
                        print(f"   ❌ Filtered: {company} ({ticker}) - ticker not available")
            
            if company and ticker:
                companies_found[company] = companies_found.get(company, 0) + 1
                # Only add if ticker is available (extract_layoff_info already filtered this)
                if tracker._is_ticker_available(ticker):
                    extracted_layoffs.append(layoff_info)
        else:
            filtered_no_extraction += 1
    
    print(f"   ✅ Articles with extraction: {len(extracted_layoffs)}")
    print(f"   ❌ Filtered (no extraction): {filtered_no_extraction}")
    print(f"   ❌ Filtered (ticker unavailable): {filtered_ticker_unavailable}")
    print(f"   ✅ Unique companies: {len(companies_found)}")
    print()
    
    # Step 4: 3-per-ticker limit (same as UI)
    print("🔍 Step 4: Applying 3-per-ticker limit...")
    before_ticker_limit = len(extracted_layoffs)
    
    if extracted_layoffs:
        ticker_to_layoffs = {}
        for layoff in extracted_layoffs:
            ticker = layoff.get('stock_ticker')
            if not ticker:
                continue
            if ticker not in ticker_to_layoffs:
                ticker_to_layoffs[ticker] = []
            ticker_to_layoffs[ticker].append(layoff)
        
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
        
        print(f"   ✅ Before limit: {before_ticker_limit}")
        print(f"   ✅ After limit: {len(extracted_layoffs)}")
        print(f"   ❌ Filtered: {total_filtered_by_ticker_limit}")
        print(f"   📊 Tickers with >3 articles: {len(tickers_affected)}")
        
        if tickers_affected:
            print(f"   📋 Top tickers affected:")
            for item in sorted(tickers_affected, key=lambda x: x['filtered'], reverse=True)[:10]:
                print(f"      {item['ticker']}: {item['original']} → {item['kept']} (lost {item['filtered']})")
    print()
    
    # Step 5: Final filtering (same as UI)
    print("🔍 Step 5: Final filtering...")
    before_final = len(extracted_layoffs)
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
    
    print(f"   ✅ Before final filter: {before_final}")
    print(f"   ✅ After final filter: {len(final_layoffs)}")
    if filtered_no_company > 0:
        print(f"   ❌ Filtered (no company): {filtered_no_company}")
    if filtered_no_ticker > 0:
        print(f"   ❌ Filtered (no ticker): {filtered_no_ticker}")
    if filtered_low_percentage > 0:
        print(f"   ❌ Filtered (low percentage): {filtered_low_percentage}")
    print()
    
    # Summary
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"Initial articles:                {initial_count:>4}")
    print(f"After MAX_ARTICLES limit:        {len(articles):>4}  (lost {initial_count - len(articles)})")
    print(f"After extraction:                {before_ticker_limit:>4}  (lost {len(articles) - before_ticker_limit})")
    print(f"   - No extraction:               {filtered_no_extraction:>4}")
    print(f"   - Ticker unavailable:         {filtered_ticker_unavailable:>4}")
    print(f"After 3-per-ticker limit:        {len(extracted_layoffs):>4}  (lost {total_filtered_by_ticker_limit if 'total_filtered_by_ticker_limit' in locals() else 0})")
    print(f"After final filtering:           {len(final_layoffs):>4}  (lost {before_final - len(final_layoffs)})")
    print()
    print(f"🎯 FINAL RESULT: {len(final_layoffs)} articles")
    print()
    
    # Check ticker availability issues
    unavailable_tickers = {t: s for t, s in ticker_availability_stats.items() if s['unavailable'] > 0}
    if unavailable_tickers:
        print("⚠️  TICKERS MARKED AS UNAVAILABLE:")
        for ticker, stats in sorted(unavailable_tickers.items(), key=lambda x: x[1]['unavailable'], reverse=True)[:10]:
            print(f"   {ticker}: {stats['unavailable']} articles filtered")
    print()
    
    # Check failed_tickers cache
    if tracker.failed_tickers:
        print(f"⚠️  FAILED TICKERS CACHE: {len(tracker.failed_tickers)} tickers")
        print(f"   {list(tracker.failed_tickers)[:10]}")
    print()
    
    return {
        'initial': initial_count,
        'after_limit': len(articles),
        'after_extraction': before_ticker_limit,
        'filtered_ticker_unavailable': filtered_ticker_unavailable,
        'after_ticker_limit': len(extracted_layoffs),
        'final': len(final_layoffs)
    }

if __name__ == '__main__':
    try:
        results = test_ui_filtering_diagnosis()
        print("\n✅ Diagnosis completed")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Diagnosis failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

