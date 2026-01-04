#!/usr/bin/env python3
"""
Quick diagnostic test - analyzes filtering without full API processing
"""

import sys
from datetime import datetime, timezone
from main import LayoffTracker
from config import MAX_ARTICLES_TO_PROCESS, MIN_LAYOFF_PERCENTAGE

def test_quick_filtering_analysis():
    """Quick analysis of filtering pipeline"""
    
    print("=" * 80)
    print("QUICK ARTICLE FILTERING ANALYSIS")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    event_types = ['bio_companies']
    selected_sources = ['google_news', 'benzinga_news']
    
    print(f"📋 Configuration:")
    print(f"   MAX_ARTICLES_TO_PROCESS: {MAX_ARTICLES_TO_PROCESS}")
    print(f"   MIN_LAYOFF_PERCENTAGE: {MIN_LAYOFF_PERCENTAGE}%")
    print()
    
    # Step 1: Fetch articles (this is fast)
    print("🔍 Step 1: Fetching articles from sources...")
    articles, source_stats = tracker.search_all_realtime_sources(
        event_types=event_types, 
        selected_sources=selected_sources
    )
    
    initial_count = len(articles)
    print(f"   ✅ Initial articles: {initial_count}")
    for key, stats in source_stats.items():
        print(f"      {stats['name']}: {stats['total']} total, {stats['matched']} matched")
    print()
    
    # Step 2: Apply MAX_ARTICLES limit
    print("🔍 Step 2: Applying MAX_ARTICLES_TO_PROCESS limit...")
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
        articles_after_limit = articles[:MAX_ARTICLES_TO_PROCESS]
        lost_at_limit = before_limit - len(articles_after_limit)
        print(f"   ⚠️  Limited: {before_limit} → {len(articles_after_limit)} (lost {lost_at_limit})")
    else:
        articles_after_limit = articles
        lost_at_limit = 0
        print(f"   ✅ No limit applied: {len(articles_after_limit)} articles")
    print()
    
    # Step 3: Quick sample extraction (process first 20 only for speed)
    print("🔍 Step 3: Sample company/ticker extraction (first 20 articles)...")
    sample_size = min(20, len(articles_after_limit))
    sample_articles = articles_after_limit[:sample_size]
    
    extracted_count = 0
    no_company_count = 0
    sample_titles_no_company = []
    
    for article in sample_articles:
        # Quick extraction without full API calls
        layoff_info = tracker.extract_layoff_info(article, fetch_content=False, event_types=event_types)
        if layoff_info and layoff_info.get('company_name') and layoff_info.get('stock_ticker'):
            extracted_count += 1
        else:
            no_company_count += 1
            if len(sample_titles_no_company) < 5:
                sample_titles_no_company.append(article.get('title', '')[:60])
    
    extraction_rate = (extracted_count / sample_size * 100) if sample_size > 0 else 0
    print(f"   📊 Sample results (first {sample_size} articles):")
    print(f"      ✅ With company/ticker: {extracted_count} ({extraction_rate:.1f}%)")
    print(f"      ❌ Without company/ticker: {no_company_count} ({100-extraction_rate:.1f}%)")
    
    if sample_titles_no_company:
        print(f"   📋 Sample articles without company/ticker:")
        for i, title in enumerate(sample_titles_no_company, 1):
            print(f"      {i}. {title}...")
    print()
    
    # Estimate full pipeline
    print("=" * 80)
    print("📊 ESTIMATED FULL PIPELINE RESULTS")
    print("=" * 80)
    print()
    
    estimated_after_extraction = int(len(articles_after_limit) * (extraction_rate / 100))
    estimated_after_ticker_limit = int(estimated_after_extraction * 0.6)  # Assume ~40% lost to 3-per-ticker
    estimated_final = int(estimated_after_ticker_limit * 0.95)  # Assume ~5% lost to final filter
    
    print(f"Initial articles fetched:        {initial_count:>4}")
    print(f"After MAX_ARTICLES limit:        {len(articles_after_limit):>4}  (lost {lost_at_limit})")
    print(f"After company extraction:        ~{estimated_after_extraction:>4}  (lost ~{len(articles_after_limit) - estimated_after_extraction}, ~{100-extraction_rate:.0f}% extraction failure)")
    print(f"After 3-per-ticker limit:        ~{estimated_after_ticker_limit:>4}  (lost ~{estimated_after_extraction - estimated_after_ticker_limit})")
    print(f"After final filtering:           ~{estimated_final:>4}  (lost ~{estimated_after_ticker_limit - estimated_final})")
    print()
    
    print("=" * 80)
    print("🎯 KEY FINDINGS")
    print("=" * 80)
    print()
    print(f"1. MAX_ARTICLES_TO_PROCESS = {MAX_ARTICLES_TO_PROCESS}")
    if lost_at_limit > 0:
        print(f"   → Loses {lost_at_limit} articles immediately ({lost_at_limit/initial_count*100:.1f}%)")
    else:
        print(f"   → No articles lost at this stage")
    print()
    print(f"2. Company/Ticker Extraction")
    print(f"   → Estimated success rate: {extraction_rate:.1f}%")
    print(f"   → Estimated failure rate: {100-extraction_rate:.1f}%")
    print(f"   → This is likely the biggest bottleneck")
    print()
    print("3. 3-Per-Ticker Limit")
    print("   → Keeps only 3 most recent articles per company")
    print("   → Estimated ~40% additional loss if many articles per company")
    print()
    print("4. Final Filtering")
    print("   → Requires company_name AND stock_ticker")
    print("   → Estimated ~5% additional loss")
    print()
    
    return {
        'initial': initial_count,
        'after_limit': len(articles_after_limit),
        'lost_at_limit': lost_at_limit,
        'extraction_rate': extraction_rate,
        'estimated_final': estimated_final
    }

if __name__ == '__main__':
    try:
        results = test_quick_filtering_analysis()
        print("\n✅ Quick analysis completed")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

