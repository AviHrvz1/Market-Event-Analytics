#!/usr/bin/env python3
"""
Comprehensive unit test to analyze why only 11 articles show when 51 are retrieved
Tracks each article through the entire pipeline and identifies filtering reasons
"""

import sys
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from main import LayoffTracker
from config import EVENT_TYPES, LOOKBACK_DAYS

def test_bio_positive_filtering_analysis():
    """Analyze filtering at each stage of the pipeline"""
    
    print("=" * 80)
    print("BIO POSITIVE NEWS FILTERING ANALYSIS")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Track articles at each stage
    stage_counts = {
        'initial_fetch': 0,
        'after_event_matching': 0,
        'after_date_filtering': 0,
        'after_company_extraction': 0,
        'after_ticker_lookup': 0,
        'after_ticker_validation': 0,
        'after_stock_calculation': 0,
        'after_deduplication': 0,
        'final': 0
    }
    
    filtered_articles = {
        'no_event_match': [],
        'date_too_old': [],
        'no_company_name': [],
        'no_ticker': [],
        'ticker_invalid': [],
        'stock_calc_failed': [],
        'duplicate': []
    }
    
    print("Step 1: Fetching articles...")
    print("-" * 80)
    
    event_types = ['bio_positive_news']
    selected_sources = ['google_news']
    
    # Fetch articles
    tracker.fetch_layoffs(
        fetch_full_content=False,
        event_types=event_types,
        selected_sources=selected_sources
    )
    
    # Get the actual count from the internal articles list (before filtering)
    # We need to check what was actually retrieved
    stage_counts['initial_fetch'] = len(tracker.layoffs)
    print(f"✅ Articles after fetch_layoffs: {stage_counts['initial_fetch']} articles")
    print()
    
    # Analyze what happened during fetch_layoffs
    print("Step 1.5: Analyzing fetch_layoffs process...")
    print("-" * 80)
    
    # Check articles by ticker status
    articles_with_ticker = [l for l in tracker.layoffs if l.get('stock_ticker') and l.get('stock_ticker') != 'N/A']
    articles_without_ticker = [l for l in tracker.layoffs if not l.get('stock_ticker') or l.get('stock_ticker') == 'N/A']
    articles_unknown_company = [l for l in tracker.layoffs if l.get('company_name') == 'Unknown Company']
    articles_known_company = [l for l in tracker.layoffs if l.get('company_name') and l.get('company_name') != 'Unknown Company']
    
    print(f"Articles with tickers: {len(articles_with_ticker)}")
    print(f"Articles without tickers: {len(articles_without_ticker)}")
    print(f"Articles with 'Unknown Company': {len(articles_unknown_company)}")
    print(f"Articles with known companies: {len(articles_known_company)}")
    print()
    
    # Now analyze each article individually
    print("Step 2: Analyzing each article through pipeline...")
    print("-" * 80)
    print()
    
    articles_by_stage = defaultdict(list)
    
    for i, layoff in enumerate(tracker.layoffs, 1):
        article_info = {
            'index': i,
            'title': layoff.get('title', 'No title')[:60],
            'url': layoff.get('url', ''),
            'company_name': layoff.get('company_name'),
            'stock_ticker': layoff.get('stock_ticker'),
            'datetime': layoff.get('datetime'),
            'event_type': layoff.get('event_type'),
        }
        
        # Stage 1: Event matching (should already be matched)
        if layoff.get('event_type') in event_types:
            stage_counts['after_event_matching'] += 1
            articles_by_stage['event_matched'].append(article_info)
        else:
            filtered_articles['no_event_match'].append(article_info)
            continue
        
        # Stage 2: Date filtering
        article_dt = layoff.get('datetime')
        if article_dt:
            now = datetime.now(timezone.utc)
            days_ago = (now - article_dt).days if article_dt.tzinfo else (now - article_dt.replace(tzinfo=timezone.utc)).days
            if days_ago <= (LOOKBACK_DAYS + 5):
                stage_counts['after_date_filtering'] += 1
                articles_by_stage['date_ok'].append(article_info)
            else:
                filtered_articles['date_too_old'].append({
                    **article_info,
                    'days_ago': days_ago
                })
                continue
        else:
            # No date - allow through
            stage_counts['after_date_filtering'] += 1
            articles_by_stage['date_ok'].append(article_info)
        
        # Stage 3: Company name
        company_name = layoff.get('company_name')
        if company_name and company_name != "Unknown Company":
            stage_counts['after_company_extraction'] += 1
            articles_by_stage['has_company'].append(article_info)
        else:
            filtered_articles['no_company_name'].append(article_info)
            # Still count it (we allow Unknown Company now)
            stage_counts['after_company_extraction'] += 1
            articles_by_stage['has_company'].append(article_info)
        
        # Stage 4: Ticker lookup
        ticker = layoff.get('stock_ticker')
        if ticker and ticker != 'N/A':
            stage_counts['after_ticker_lookup'] += 1
            articles_by_stage['has_ticker'].append(article_info)
        else:
            filtered_articles['no_ticker'].append(article_info)
            # Still count it (we allow N/A now)
            stage_counts['after_ticker_lookup'] += 1
            articles_by_stage['has_ticker'].append(article_info)
        
        # Stage 5: Ticker validation (Prixe.io availability)
        if ticker and ticker != 'N/A':
            # Check if ticker is available (this would normally filter, but we allow it now)
            stage_counts['after_ticker_validation'] += 1
            articles_by_stage['ticker_valid'].append(article_info)
        else:
            # No ticker - still allow through
            stage_counts['after_ticker_validation'] += 1
            articles_by_stage['ticker_valid'].append(article_info)
        
        # Stage 6: Stock calculation (should always succeed now, even with None ticker)
        stage_counts['after_stock_calculation'] += 1
        articles_by_stage['stock_calc'].append(article_info)
    
    # Stage 7: Deduplication (check if there's a 3-per-ticker limit)
    print("Step 3: Checking deduplication/limiting...")
    print("-" * 80)
    
    # Group by ticker
    articles_by_ticker = defaultdict(list)
    for layoff in tracker.layoffs:
        ticker = layoff.get('stock_ticker') or 'N/A'
        articles_by_ticker[ticker].append(layoff)
    
    print(f"Unique tickers: {len(articles_by_ticker)}")
    print()
    
    # Check for 3-per-ticker limit
    tickers_with_many = {t: len(arts) for t, arts in articles_by_ticker.items() if len(arts) > 3}
    if tickers_with_many:
        print("Tickers with more than 3 articles:")
        for ticker, count in sorted(tickers_with_many.items(), key=lambda x: x[1], reverse=True):
            print(f"  {ticker}: {count} articles")
            # Show which articles would be kept (most recent 3)
            articles = articles_by_ticker[ticker]
            sorted_articles = sorted(articles, key=lambda x: x.get('datetime') or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
            kept = sorted_articles[:3]
            filtered = sorted_articles[3:]
            print(f"    → Would keep: {len(kept)} (most recent)")
            print(f"    → Would filter: {len(filtered)} (older)")
            for art in filtered[:3]:
                print(f"      - {art.get('title', 'No title')[:50]}...")
        print()
    
    # Check final count
    stage_counts['final'] = len(tracker.layoffs)
    
    # Print summary
    print("=" * 80)
    print("FILTERING SUMMARY")
    print("=" * 80)
    print()
    
    print("Pipeline Stages:")
    print(f"  1. Initial fetch: {stage_counts['initial_fetch']} articles")
    print(f"  2. After event matching: {stage_counts['after_event_matching']} articles")
    print(f"  3. After date filtering: {stage_counts['after_date_filtering']} articles")
    print(f"  4. After company extraction: {stage_counts['after_company_extraction']} articles")
    print(f"  5. After ticker lookup: {stage_counts['after_ticker_lookup']} articles")
    print(f"  6. After ticker validation: {stage_counts['after_ticker_validation']} articles")
    print(f"  7. After stock calculation: {stage_counts['after_stock_calculation']} articles")
    print(f"  8. Final count: {stage_counts['final']} articles")
    print()
    
    # Show filtered articles
    print("Filtered Articles by Reason:")
    print("-" * 80)
    
    total_filtered = 0
    for reason, articles in filtered_articles.items():
        if articles:
            total_filtered += len(articles)
            print(f"\n{reason.upper()}: {len(articles)} articles")
            for art in articles[:5]:  # Show first 5
                print(f"  - {art.get('title', 'No title')[:60]}...")
                if art.get('company_name'):
                    print(f"    Company: {art.get('company_name')}")
                if art.get('stock_ticker'):
                    print(f"    Ticker: {art.get('stock_ticker')}")
            if len(articles) > 5:
                print(f"  ... and {len(articles) - 5} more")
    
    if total_filtered == 0:
        print("  ✅ No articles filtered at these stages (allowing Unknown Company/N/A)")
    
    print()
    
    # Check for 3-per-ticker limiting
    print("=" * 80)
    print("3-PER-TICKER LIMITING ANALYSIS")
    print("=" * 80)
    print()
    
    if tickers_with_many:
        total_lost_to_limit = sum(max(0, count - 3) for count in tickers_with_many.values())
        print(f"⚠️  Articles lost to 3-per-ticker limit: {total_lost_to_limit}")
        print()
        print("This is likely the main reason for the discrepancy!")
        print(f"Expected: {stage_counts['initial_fetch']} articles")
        print(f"After 3-per-ticker limit: ~{stage_counts['initial_fetch'] - total_lost_to_limit} articles")
        print(f"Actual showing: {stage_counts['final']} articles")
    else:
        print("✅ No 3-per-ticker limiting applied (all tickers have ≤3 articles)")
    
    print()
    
    # Check company extraction success rate
    print("=" * 80)
    print("COMPANY EXTRACTION ANALYSIS")
    print("=" * 80)
    print()
    
    unknown_companies = [l for l in tracker.layoffs if l.get('company_name') == 'Unknown Company']
    known_companies = [l for l in tracker.layoffs if l.get('company_name') and l.get('company_name') != 'Unknown Company']
    
    print(f"Articles with company names: {len(known_companies)}")
    print(f"Articles with 'Unknown Company': {len(unknown_companies)}")
    print()
    
    if unknown_companies:
        print("Sample articles with 'Unknown Company':")
        for art in unknown_companies[:5]:
            print(f"  - {art.get('title', 'No title')[:60]}...")
            print(f"    URL: {art.get('url', '')[:60]}...")
    
    print()
    
    # Check ticker extraction success rate
    print("=" * 80)
    print("TICKER EXTRACTION ANALYSIS")
    print("=" * 80)
    print()
    
    no_ticker = [l for l in tracker.layoffs if not l.get('stock_ticker') or l.get('stock_ticker') == 'N/A']
    has_ticker = [l for l in tracker.layoffs if l.get('stock_ticker') and l.get('stock_ticker') != 'N/A']
    
    print(f"Articles with tickers: {len(has_ticker)}")
    print(f"Articles without tickers (N/A): {len(no_ticker)}")
    print()
    
    if no_ticker:
        print("Sample articles without tickers:")
        for art in no_ticker[:5]:
            print(f"  - {art.get('company_name', 'Unknown')} - {art.get('title', 'No title')[:50]}...")
    
    print()
    
    # Final analysis
    print("=" * 80)
    print("FINAL ANALYSIS")
    print("=" * 80)
    print()
    
    expected = 51
    actual = stage_counts['final']
    lost = expected - actual
    
    print(f"Expected articles: {expected}")
    print(f"Actual articles showing: {actual}")
    print(f"Lost: {lost} articles ({lost/expected*100:.1f}% loss)")
    print()
    
    if lost > 0:
        print("Main reasons for loss:")
        if tickers_with_many:
            total_lost_to_limit = sum(max(0, count - 3) for count in tickers_with_many.values())
            print(f"  1. 3-per-ticker limit: ~{total_lost_to_limit} articles")
        
        if len(unknown_companies) > 0:
            print(f"  2. Company extraction failed: {len(unknown_companies)} articles (but now showing as 'Unknown Company')")
        
        if len(no_ticker) > 0:
            print(f"  3. Ticker lookup failed: {len(no_ticker)} articles (but now showing as 'N/A')")
        
        remaining_loss = lost - (total_lost_to_limit if tickers_with_many else 0)
        if remaining_loss > 0:
            print(f"  4. Other reasons: ~{remaining_loss} articles")
    else:
        print("✅ All articles are showing!")

if __name__ == '__main__':
    test_bio_positive_filtering_analysis()

