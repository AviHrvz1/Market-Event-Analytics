#!/usr/bin/env python3
"""
Performance test for bio pharma event type to identify bottlenecks
"""

import sys
import time
from datetime import datetime, timezone
from main import LayoffTracker
from config import MAX_ARTICLES_TO_PROCESS

def test_bio_pharma_performance():
    """Test performance of bio pharma event type processing"""
    
    print("=" * 80)
    print("BIO PHARMA EVENT TYPE PERFORMANCE TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    event_types = ['bio_companies']
    selected_sources = ['google_news', 'benzinga_news']
    
    timings = {}
    
    # Step 1: Fetch articles
    print("🔍 Step 1: Fetching articles from sources...")
    start_time = time.time()
    articles, source_stats = tracker.search_all_realtime_sources(
        event_types=event_types, 
        selected_sources=selected_sources
    )
    timings['fetch_articles'] = time.time() - start_time
    print(f"   ✅ Fetched {len(articles)} articles in {timings['fetch_articles']:.2f}s")
    print()
    
    # Step 2: Sort and limit
    print("🔍 Step 2: Sorting and limiting articles...")
    start_time = time.time()
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
    timings['sort_limit'] = time.time() - start_time
    print(f"   ✅ Sorted and limited in {timings['sort_limit']:.2f}s")
    print()
    
    # Step 3: Extract company/ticker info (THIS IS LIKELY THE BOTTLENECK)
    print("🔍 Step 3: Extracting company/ticker info...")
    print(f"   Processing {len(articles)} articles...")
    print()
    
    extracted_layoffs = []
    companies_found = {}
    extraction_times = []
    claude_call_times = []
    fallback_times = []
    
    start_time = time.time()
    for i, article in enumerate(articles, 1):
        article_start = time.time()
        
        # Track Claude API call time
        claude_start = time.time()
        layoff_info = tracker.extract_layoff_info(article, fetch_content=False, event_types=event_types)
        claude_end = time.time()
        claude_call_times.append(claude_end - claude_start)
        
        article_end = time.time()
        extraction_times.append(article_end - article_start)
        
        if layoff_info:
            company = layoff_info.get('company_name')
            if company:
                companies_found[company] = companies_found.get(company, 0) + 1
                extracted_layoffs.append(layoff_info)
        
        # Show progress every 25 articles
        if i % 25 == 0 or i == len(articles):
            elapsed = time.time() - start_time
            avg_time = elapsed / i
            remaining = avg_time * (len(articles) - i)
            print(f"   [PROGRESS] {i}/{len(articles)} ({i/len(articles)*100:.1f}%) - "
                  f"Elapsed: {elapsed:.1f}s, Avg: {avg_time:.2f}s/article, "
                  f"Est. remaining: {remaining:.1f}s")
    
    timings['extraction'] = time.time() - start_time
    print()
    print(f"   ✅ Extraction complete in {timings['extraction']:.2f}s")
    print(f"   ✅ Found {len(extracted_layoffs)} articles with companies")
    print()
    
    # Analyze timing breakdown
    if extraction_times:
        avg_extraction = sum(extraction_times) / len(extraction_times)
        max_extraction = max(extraction_times)
        min_extraction = min(extraction_times)
        
        if claude_call_times:
            avg_claude = sum(claude_call_times) / len(claude_call_times)
            max_claude = max(claude_call_times)
            min_claude = min(claude_call_times)
            total_claude = sum(claude_call_times)
        else:
            avg_claude = 0
            max_claude = 0
            min_claude = 0
            total_claude = 0
        
        print("=" * 80)
        print("⏱️  TIMING ANALYSIS")
        print("=" * 80)
        print()
        print(f"Total time breakdown:")
        print(f"  Fetch articles:        {timings['fetch_articles']:>8.2f}s ({timings['fetch_articles']/sum(timings.values())*100:.1f}%)")
        print(f"  Sort & limit:          {timings['sort_limit']:>8.2f}s ({timings['sort_limit']/sum(timings.values())*100:.1f}%)")
        print(f"  Extraction:            {timings['extraction']:>8.2f}s ({timings['extraction']/sum(timings.values())*100:.1f}%)")
        print(f"  └─ Total Claude calls: {total_claude:>8.2f}s ({total_claude/timings['extraction']*100:.1f}% of extraction)")
        print()
        print(f"Per-article extraction timing:")
        print(f"  Average:               {avg_extraction:>8.2f}s/article")
        print(f"  Min:                   {min_extraction:>8.2f}s/article")
        print(f"  Max:                   {max_extraction:>8.2f}s/article")
        print()
        print(f"Claude API call timing:")
        print(f"  Average:               {avg_claude:>8.2f}s/call")
        print(f"  Min:                   {min_claude:>8.2f}s/call")
        print(f"  Max:                   {max_claude:>8.2f}s/call")
        print(f"  Total:                 {total_claude:>8.2f}s ({len(claude_call_times)} calls)")
        print()
        
        # Identify slow articles
        slow_articles = []
        for i, (ext_time, claude_time) in enumerate(zip(extraction_times, claude_call_times)):
            if ext_time > 3.0:  # Articles taking more than 3 seconds
                slow_articles.append({
                    'index': i + 1,
                    'extraction_time': ext_time,
                    'claude_time': claude_time,
                    'title': articles[i].get('title', '')[:60] if i < len(articles) else 'N/A'
                })
        
        if slow_articles:
            print("⚠️  SLOW ARTICLES (>3s):")
            for item in sorted(slow_articles, key=lambda x: x['extraction_time'], reverse=True)[:10]:
                print(f"  Article {item['index']}: {item['extraction_time']:.2f}s "
                      f"(Claude: {item['claude_time']:.2f}s) - {item['title']}")
            print()
    
    # Step 4: 3-per-ticker limit
    print("🔍 Step 4: Applying 3-per-ticker limit...")
    start_time = time.time()
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
        for ticker, layoffs_list in ticker_to_layoffs.items():
            layoffs_list.sort(
                key=lambda x: x.get('datetime') or datetime.min.replace(tzinfo=timezone.utc), 
                reverse=True
            )
            limited_layoffs.extend(layoffs_list[:3])
        
        extracted_layoffs = limited_layoffs
    timings['ticker_limit'] = time.time() - start_time
    print(f"   ✅ Applied limit in {timings['ticker_limit']:.2f}s")
    print(f"   ✅ Final count: {len(extracted_layoffs)} articles")
    print()
    
    # Summary
    total_time = sum(timings.values())
    print("=" * 80)
    print("📊 PERFORMANCE SUMMARY")
    print("=" * 80)
    print()
    print(f"Total processing time:     {total_time:>8.2f}s ({total_time/60:.1f} minutes)")
    print()
    print(f"Time breakdown:")
    for step, duration in sorted(timings.items(), key=lambda x: x[1], reverse=True):
        pct = duration / total_time * 100
        print(f"  {step:20} {duration:>8.2f}s ({pct:>5.1f}%)")
    print()
    
    # Recommendations
    print("=" * 80)
    print("💡 RECOMMENDATIONS")
    print("=" * 80)
    print()
    
    if timings['extraction'] > total_time * 0.8:
        print("⚠️  Extraction is the main bottleneck (>80% of total time)")
        print("   Solutions:")
        print("   1. Reduce MAX_ARTICLES_TO_PROCESS (currently {})".format(MAX_ARTICLES_TO_PROCESS))
        print("   2. Skip Claude API for articles where fallback extraction works")
        print("   3. Batch Claude API calls or use caching")
        print("   4. Process articles in parallel (if API allows)")
        print()
    
    if avg_claude > 1.0:
        print(f"⚠️  Claude API calls are slow (avg {avg_claude:.2f}s/call)")
        print("   Solutions:")
        print("   1. Use Claude API only when fallback extraction fails")
        print("   2. Cache Claude API results by article URL")
        print("   3. Reduce Claude API timeout or retry logic")
        print()
    
    if len(articles) > 200:
        print(f"⚠️  Processing {len(articles)} articles is slow")
        print("   Solutions:")
        print(f"   1. Reduce MAX_ARTICLES_TO_PROCESS from {MAX_ARTICLES_TO_PROCESS} to 100-150")
        print("   2. Process only most recent articles first")
        print()
    
    return {
        'total_time': total_time,
        'timings': timings,
        'articles_processed': len(articles),
        'articles_extracted': len(extracted_layoffs),
        'avg_extraction_time': avg_extraction if extraction_times else 0,
        'avg_claude_time': avg_claude if claude_call_times else 0
    }

if __name__ == '__main__':
    try:
        results = test_bio_pharma_performance()
        print("\n✅ Performance test completed")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Performance test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

