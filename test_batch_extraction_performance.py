#!/usr/bin/env python3
"""
Diagnostic test to identify why extraction is slow after batch API calls
"""

import sys
import time
from datetime import datetime, timezone
from main import LayoffTracker
from config import MAX_ARTICLES_TO_PROCESS

def test_batch_extraction_performance():
    """Test batch extraction performance and identify bottlenecks"""
    
    print("=" * 80)
    print("BATCH EXTRACTION PERFORMANCE DIAGNOSIS")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    event_types = ['bio_companies']
    selected_sources = ['google_news', 'benzinga_news']
    
    # Step 1: Fetch articles
    print("🔍 Step 1: Fetching articles...")
    start_time = time.time()
    articles, source_stats = tracker.search_all_realtime_sources(
        event_types=event_types, 
        selected_sources=selected_sources
    )
    fetch_time = time.time() - start_time
    print(f"   ✅ Fetched {len(articles)} articles in {fetch_time:.2f}s")
    print()
    
    # Sort and limit
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
    
    total_articles = len(articles)
    print(f"📊 Processing {total_articles} articles")
    print()
    
    # Step 2: Test batch API calls
    print("🔍 Step 2: Testing batch Claude API calls...")
    BATCH_SIZE = 50
    
    batch_results = {}
    batch_times = []
    
    for batch_start in range(0, total_articles, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_articles)
        batch_articles = articles[batch_start:batch_end]
        
        print(f"   Processing batch {batch_start//BATCH_SIZE + 1}/{(total_articles + BATCH_SIZE - 1)//BATCH_SIZE} "
              f"(articles {batch_start + 1}-{batch_end}/{total_articles})...")
        
        # Prepare articles for batch API call
        batch_input = []
        for i, article in enumerate(batch_articles):
            batch_input.append({
                'index': batch_start + i,
                'title': article.get('title', ''),
                'description': article.get('description', ''),
                'url': article.get('url', '')
            })
        
        # Get batch results from Claude
        batch_start_time = time.time()
        batch_ai_results = tracker.get_ai_prediction_score_batch(batch_input)
        batch_time = time.time() - batch_start_time
        batch_times.append(batch_time)
        
        batch_results.update(batch_ai_results)
        print(f"      ✅ Batch completed in {batch_time:.2f}s")
    
    total_batch_time = sum(batch_times)
    print(f"   ✅ All batch API calls complete in {total_batch_time:.2f}s")
    print()
    
    # Analyze batch results
    claude_success_count = sum(1 for r in batch_results.values() if r and r.get('company_name'))
    claude_failed_count = sum(1 for r in batch_results.values() if not r or not r.get('company_name'))
    print(f"📊 Batch API Results:")
    print(f"   ✅ Claude returned company names: {claude_success_count}/{total_articles} ({claude_success_count/total_articles*100:.1f}%)")
    print(f"   ❌ Claude failed/returned None: {claude_failed_count}/{total_articles} ({claude_failed_count/total_articles*100:.1f}%)")
    print()
    
    # Step 3: Test extraction loop performance
    print("🔍 Step 3: Testing extraction loop performance...")
    print(f"   This simulates what happens after 'Batch API calls complete' message")
    print()
    
    extraction_times = []
    fallback_count = 0
    claude_used_count = 0
    
    start_time = time.time()
    for i, article in enumerate(articles):
        article_start = time.time()
        
        # Get pre-fetched AI result from batch
        ai_result = batch_results.get(i)
        
        # Track if we'll use Claude result or fallback
        if ai_result and ai_result.get('company_name'):
            claude_used_count += 1
        else:
            fallback_count += 1
        
        # Simulate extract_layoff_info call (but measure time)
        # We'll call it but track timing
        layoff_info = tracker.extract_layoff_info(
            article, 
            fetch_content=False, 
            event_types=event_types, 
            pre_fetched_ai_result=ai_result
        )
        
        article_time = time.time() - article_start
        extraction_times.append(article_time)
        
        # Show progress every 25 articles
        if (i + 1) % 25 == 0 or (i + 1) == total_articles:
            elapsed = time.time() - start_time
            avg_time = elapsed / (i + 1)
            remaining = avg_time * (total_articles - (i + 1))
            print(f"   [PROGRESS] {i + 1}/{total_articles} ({((i + 1)/total_articles*100):.1f}%) - "
                  f"Elapsed: {elapsed:.1f}s, Avg: {avg_time:.3f}s/article, "
                  f"Est. remaining: {remaining:.1f}s")
    
    total_extraction_time = time.time() - start_time
    print()
    print(f"   ✅ Extraction loop complete in {total_extraction_time:.2f}s")
    print()
    
    # Analyze extraction performance
    if extraction_times:
        avg_extraction = sum(extraction_times) / len(extraction_times)
        max_extraction = max(extraction_times)
        min_extraction = min(extraction_times)
        
        # Find slow articles
        slow_articles = []
        for i, ext_time in enumerate(extraction_times):
            if ext_time > 1.0:  # Articles taking more than 1 second
                slow_articles.append({
                    'index': i + 1,
                    'time': ext_time,
                    'title': articles[i].get('title', '')[:60] if i < len(articles) else 'N/A',
                    'claude_result': 'Yes' if (batch_results.get(i) and batch_results.get(i).get('company_name')) else 'No'
                })
        
        print("=" * 80)
        print("⏱️  PERFORMANCE ANALYSIS")
        print("=" * 80)
        print()
        print(f"Batch API calls:")
        print(f"  Total time:        {total_batch_time:>8.2f}s")
        print(f"  Average per batch: {sum(batch_times)/len(batch_times):>8.2f}s")
        print(f"  Batches:           {len(batch_times)}")
        print()
        print(f"Extraction loop:")
        print(f"  Total time:        {total_extraction_time:>8.2f}s ({total_extraction_time/60:.1f} minutes)")
        print(f"  Average per article: {avg_extraction:>8.3f}s")
        print(f"  Min:               {min_extraction:>8.3f}s")
        print(f"  Max:               {max_extraction:>8.3f}s")
        print()
        print(f"Claude vs Fallback:")
        print(f"  Used Claude result: {claude_used_count} ({claude_used_count/total_articles*100:.1f}%)")
        print(f"  Used fallback:      {fallback_count} ({fallback_count/total_articles*100:.1f}%)")
        print()
        
        if slow_articles:
            print(f"⚠️  SLOW ARTICLES (>1s): {len(slow_articles)} articles")
            print()
            for item in sorted(slow_articles, key=lambda x: x['time'], reverse=True)[:10]:
                print(f"  Article {item['index']}: {item['time']:.2f}s "
                      f"(Claude: {item['claude_result']}) - {item['title']}")
            print()
        
        # Identify bottleneck
        print("=" * 80)
        print("🎯 BOTTLENECK IDENTIFICATION")
        print("=" * 80)
        print()
        
        if total_extraction_time > total_batch_time * 2:
            print("⚠️  EXTRACTION LOOP IS THE BOTTLENECK")
            print(f"   Extraction takes {total_extraction_time/total_batch_time:.1f}x longer than batch API calls")
            print()
            
            if fallback_count > total_articles * 0.5:
                print("⚠️  PRIMARY ISSUE: Too many fallback extractions")
                print(f"   {fallback_count} articles ({fallback_count/total_articles*100:.1f}%) need fallback")
                print("   Fallback searches through 10,499 SEC EDGAR companies - very slow!")
                print()
                print("   Solutions:")
                print("   1. Fix batch API call to return more results")
                print("   2. Optimize extract_company_name() to be faster")
                print("   3. Skip fallback for articles where Claude clearly failed")
                print()
            else:
                print("⚠️  ISSUE: Even with Claude results, extraction is slow")
                print("   Possible causes:")
                print("   1. extract_layoff_info() doing other slow operations")
                print("   2. Prixe.io availability checks")
                print("   3. Other processing in extract_layoff_info()")
                print()
        
        if avg_extraction > 0.5:
            print(f"⚠️  AVERAGE EXTRACTION TIME IS HIGH: {avg_extraction:.3f}s/article")
            print(f"   For {total_articles} articles, this means {total_extraction_time:.1f}s total")
            print("   This is likely the cause of the 4-minute delay")
            print()
    
    return {
        'total_articles': total_articles,
        'batch_time': total_batch_time,
        'extraction_time': total_extraction_time,
        'claude_success': claude_success_count,
        'fallback_count': fallback_count,
        'avg_extraction_time': avg_extraction if extraction_times else 0
    }

if __name__ == '__main__':
    try:
        results = test_batch_extraction_performance()
        print("\n✅ Diagnosis completed")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Diagnosis failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

