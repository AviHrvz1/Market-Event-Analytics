#!/usr/bin/env python3
"""
Detailed analysis of filtering during fetch_layoffs
Tracks articles at each stage to identify where they're being lost
"""

import sys
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from main import LayoffTracker
from config import EVENT_TYPES, LOOKBACK_DAYS, MAX_ARTICLES_TO_PROCESS

def test_detailed_filtering():
    """Track articles through fetch_layoffs to see where they're filtered"""
    
    print("=" * 80)
    print("DETAILED FILTERING ANALYSIS - BIO POSITIVE NEWS")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    event_types = ['bio_positive_news']
    selected_sources = ['google_news']
    
    # Step 1: Use fetch_layoffs but track intermediate steps
    # We'll modify the approach to track what happens
    print("Step 1: Running fetch_layoffs and analyzing result...")
    print("-" * 80)
    
    # Run fetch_layoffs
    tracker.fetch_layoffs(
        fetch_full_content=False,
        event_types=event_types,
        selected_sources=selected_sources
    )
    
    print(f"✅ fetch_layoffs completed: {len(tracker.layoffs)} articles in final result")
    print()
    
    # Since we can't easily intercept the internal steps, we'll analyze the final result
    # and compare with what we know should have been retrieved
    articles = []  # We'll work with tracker.layoffs instead
    
    # Analyze the final result
    print("Analyzing final articles...")
    print("-" * 80)
    
    # We know from logs that 51 articles were retrieved
    # Let's see what we have in the final result
    final_articles = tracker.layoffs
    
    print(f"Final articles: {len(final_articles)}")
    print()
    
    # Analyze by ticker status
    articles_with_ticker = [a for a in final_articles if a.get('stock_ticker') and a.get('stock_ticker') != 'N/A']
    articles_without_ticker = [a for a in final_articles if not a.get('stock_ticker') or a.get('stock_ticker') == 'N/A']
    articles_unknown_company = [a for a in final_articles if a.get('company_name') == 'Unknown Company']
    articles_known_company = [a for a in final_articles if a.get('company_name') and a.get('company_name') != 'Unknown Company']
    
    print(f"Articles with tickers: {len(articles_with_ticker)}")
    print(f"Articles without tickers: {len(articles_without_ticker)}")
    print(f"Articles with 'Unknown Company': {len(articles_unknown_company)}")
    print(f"Articles with known companies: {len(articles_known_company)}")
    print()
    
    # Group by ticker to see 3-per-ticker limiting
    ticker_counts = defaultdict(int)
    for article in final_articles:
        ticker = article.get('stock_ticker') or 'N/A'
        ticker_counts[ticker] += 1
    
    print("Ticker distribution:")
    for ticker, count in sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True):
        if count > 3:
            print(f"  {ticker}: {count} articles ⚠️ (should be max 3)")
        else:
            print(f"  {ticker}: {count} articles")
    print()
    
    # The issue: 51 articles retrieved, but only 11-12 showing
    # Expected loss: ~40 articles
    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print()
    print("From logs, we know:")
    print("  - 51 articles were retrieved from Google News")
    print(f"  - {len(final_articles)} articles are in final result")
    print(f"  - Lost: {51 - len(final_articles)} articles")
    print()
    print("Likely causes:")
    print("  1. 3-per-ticker limiting (if many articles have same ticker)")
    print("  2. Company extraction failures (but now showing as 'Unknown Company')")
    print("  3. Ticker lookup failures (but now showing as 'N/A')")
    print("  4. Additional filtering in fetch_layoffs that we haven't identified")
    print()
    
    # Step 2: Check event matching (skip - we can't easily test this)
    matched_articles = []
    unmatched_articles = []
    
    for article in articles:
        matches = False
        if article.get('event_type') in event_types and article.get('source', {}).get('name') == 'Google News':
            matches = True
        else:
            for event_type in event_types:
                if tracker.matches_event_type(article, event_type):
                    matches = True
                    break
        
        if matches:
            matched_articles.append(article)
        else:
            unmatched_articles.append(article)
    
    print(f"✅ Matched articles: {len(matched_articles)}")
    print(f"❌ Unmatched articles: {len(unmatched_articles)}")
    if unmatched_articles:
        print("\nSample unmatched articles:")
        for art in unmatched_articles[:3]:
            print(f"  - {art.get('title', '')[:60]}...")
    print()
    
    # Step 3: Date filtering
    print("Step 3: Date filtering...")
    print("-" * 80)
    
    now = datetime.now(timezone.utc)
    date_ok_articles = []
    date_filtered_articles = []
    
    for article in matched_articles:
        try:
            from dateutil import parser
            pub_date_str = article.get('publishedAt', '')
            if pub_date_str:
                pub_date = parser.parse(pub_date_str)
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
                else:
                    pub_date = pub_date.astimezone(timezone.utc)
                
                days_ago = (now - pub_date).days
                if days_ago <= (LOOKBACK_DAYS + 5):
                    date_ok_articles.append(article)
                else:
                    date_filtered_articles.append({
                        'article': article,
                        'days_ago': days_ago
                    })
            else:
                # No date - allow through
                date_ok_articles.append(article)
        except:
            # Parse error - allow through
            date_ok_articles.append(article)
    
    print(f"✅ Date OK articles: {len(date_ok_articles)}")
    print(f"❌ Date filtered articles: {len(date_filtered_articles)}")
    if date_filtered_articles:
        print("\nSample date-filtered articles:")
        for item in date_filtered_articles[:3]:
            print(f"  - {item['article'].get('title', '')[:60]}... ({item['days_ago']} days ago)")
    print()
    
    # Step 4: MAX_ARTICLES_TO_PROCESS limit
    print("Step 4: MAX_ARTICLES_TO_PROCESS limit...")
    print("-" * 80)
    
    before_limit = len(date_ok_articles)
    if len(date_ok_articles) > MAX_ARTICLES_TO_PROCESS:
        # Sort by date (most recent first)
        date_ok_articles.sort(key=lambda x: parser.parse(x.get('publishedAt', '2000-01-01')).replace(tzinfo=timezone.utc) if x.get('publishedAt') else datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        limited_articles = date_ok_articles[:MAX_ARTICLES_TO_PROCESS]
        print(f"⚠️  Limited from {before_limit} to {MAX_ARTICLES_TO_PROCESS} articles")
        print(f"❌ Lost: {before_limit - MAX_ARTICLES_TO_PROCESS} articles")
    else:
        limited_articles = date_ok_articles
        print(f"✅ No limit applied: {len(limited_articles)} articles (below {MAX_ARTICLES_TO_PROCESS} limit)")
    print()
    
    # Step 5: Company/ticker extraction
    print("Step 5: Company/ticker extraction...")
    print("-" * 80)
    
    extracted_articles = []
    no_extraction_articles = []
    extraction_stats = {
        'with_company': 0,
        'unknown_company': 0,
        'with_ticker': 0,
        'no_ticker': 0
    }
    
    for article in limited_articles:
        layoff_info = tracker.extract_layoff_info(article, fetch_content=False, event_types=event_types)
        
        if layoff_info:
            extracted_articles.append(layoff_info)
            company = layoff_info.get('company_name')
            ticker = layoff_info.get('stock_ticker')
            
            if company and company != 'Unknown Company':
                extraction_stats['with_company'] += 1
            elif company == 'Unknown Company':
                extraction_stats['unknown_company'] += 1
            
            if ticker and ticker != 'N/A':
                extraction_stats['with_ticker'] += 1
            else:
                extraction_stats['no_ticker'] += 1
        else:
            no_extraction_articles.append(article)
    
    print(f"✅ Extracted articles: {len(extracted_articles)}")
    print(f"❌ No extraction: {len(no_extraction_articles)}")
    print(f"   - With company names: {extraction_stats['with_company']}")
    print(f"   - Unknown Company: {extraction_stats['unknown_company']}")
    print(f"   - With tickers: {extraction_stats['with_ticker']}")
    print(f"   - No tickers: {extraction_stats['no_ticker']}")
    
    if no_extraction_articles:
        print("\nSample articles with no extraction:")
        for art in no_extraction_articles[:5]:
            print(f"  - {art.get('title', '')[:60]}...")
    print()
    
    # Step 6: 3-per-ticker limiting
    print("Step 6: 3-per-ticker limiting...")
    print("-" * 80)
    
    ticker_to_layoffs = defaultdict(list)
    no_ticker_layoffs = []
    
    for layoff in extracted_articles:
        ticker = layoff.get('stock_ticker')
        if not ticker or ticker == 'N/A':
            no_ticker_layoffs.append(layoff)
        else:
            ticker_to_layoffs[ticker].append(layoff)
    
    print(f"Unique tickers: {len(ticker_to_layoffs)}")
    print(f"Articles without tickers: {len(no_ticker_layoffs)}")
    
    # Apply 3-per-ticker limit
    limited_layoffs = []
    lost_to_limit = 0
    
    for ticker, layoffs_list in ticker_to_layoffs.items():
        # Sort by date (most recent first)
        layoffs_list.sort(key=lambda x: x.get('datetime') or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        limited_layoffs.extend(layoffs_list[:3])
        if len(layoffs_list) > 3:
            lost_to_limit += len(layoffs_list) - 3
            print(f"  {ticker}: {len(layoffs_list)} articles → keeping 3 (lost {len(layoffs_list) - 3})")
    
    # Add all articles without tickers (no limit)
    limited_layoffs.extend(no_ticker_layoffs)
    
    print(f"✅ After 3-per-ticker limit: {len(limited_layoffs)} articles")
    print(f"❌ Lost to limit: {lost_to_limit} articles")
    print()
    
    # Step 7: Final filtering (layoff_percentage check)
    print("Step 7: Final filtering (layoff_percentage check)...")
    print("-" * 80)
    
    from config import MIN_LAYOFF_PERCENTAGE
    final_layoffs = []
    filtered_by_percentage = []
    
    for layoff_info in limited_layoffs:
        layoff_pct = layoff_info.get('layoff_percentage')
        if layoff_pct:
            if layoff_pct >= MIN_LAYOFF_PERCENTAGE:
                final_layoffs.append(layoff_info)
            else:
                filtered_by_percentage.append(layoff_info)
        else:
            # No percentage - should be included now
            final_layoffs.append(layoff_info)
    
    print(f"✅ Final articles: {len(final_layoffs)}")
    print(f"❌ Filtered by percentage: {len(filtered_by_percentage)}")
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    print(f"1. Raw articles fetched: {len(articles)}")
    print(f"2. After event matching: {len(matched_articles)}")
    print(f"3. After date filtering: {len(date_ok_articles)}")
    print(f"4. After MAX_ARTICLES limit: {len(limited_articles)}")
    print(f"5. After extraction: {len(extracted_articles)}")
    print(f"6. After 3-per-ticker limit: {len(limited_layoffs)}")
    print(f"7. Final count: {len(final_layoffs)}")
    print()
    
    total_lost = len(articles) - len(final_layoffs)
    print(f"Total lost: {total_lost} articles ({total_lost/len(articles)*100:.1f}% loss)")
    print()
    
    print("Breakdown of losses:")
    print(f"  - Event matching: {len(unmatched_articles)}")
    print(f"  - Date filtering: {len(date_filtered_articles)}")
    if len(limited_articles) < len(date_ok_articles):
        print(f"  - MAX_ARTICLES limit: {len(date_ok_articles) - len(limited_articles)}")
    print(f"  - Extraction failed: {len(no_extraction_articles)}")
    print(f"  - 3-per-ticker limit: {lost_to_limit}")
    print(f"  - Percentage filtering: {len(filtered_by_percentage)}")
    
    # Compare with actual fetch_layoffs result
    print()
    print("=" * 80)
    print("COMPARISON WITH ACTUAL fetch_layoffs")
    print("=" * 80)
    print()
    
    tracker2 = LayoffTracker()
    tracker2.fetch_layoffs(
        fetch_full_content=False,
        event_types=event_types,
        selected_sources=selected_sources
    )
    
    actual_count = len(tracker2.layoffs)
    print(f"Actual fetch_layoffs result: {actual_count} articles")
    print(f"Expected from analysis: {len(final_layoffs)} articles")
    print(f"Difference: {abs(actual_count - len(final_layoffs))} articles")
    
    if actual_count != len(final_layoffs):
        print("\n⚠️  Mismatch detected! There may be additional filtering happening.")
        print("   Check for:")
        print("   - Additional filtering in fetch_layoffs")
        print("   - Batch processing differences")
        print("   - Deduplication logic")

if __name__ == '__main__':
    test_detailed_filtering()

