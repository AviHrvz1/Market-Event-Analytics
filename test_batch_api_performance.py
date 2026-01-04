#!/usr/bin/env python3
"""
Unit test to diagnose batch API max_tokens issue and slow extraction
"""

import sys
import time
from main import LayoffTracker
from config import EVENT_TYPES

def test_max_tokens_calculation():
    """Test 1: Verify max_tokens calculation doesn't exceed Claude's limit"""
    print("=" * 80)
    print("TEST 1: Max Tokens Calculation")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Test with different batch sizes
    test_sizes = [10, 20, 30, 40, 50, 60]
    claude_haiku_limit = 4096
    
    print(f"Claude Haiku max_tokens limit: {claude_haiku_limit}")
    print()
    
    for batch_size in test_sizes:
        # Simulate the calculation from get_ai_prediction_score_batch
        max_tokens = batch_size * 100
        exceeds_limit = max_tokens > claude_haiku_limit
        
        status = "❌ EXCEEDS" if exceeds_limit else "✅ OK"
        print(f"Batch size {batch_size:2d}: max_tokens = {max_tokens:4d} {status}")
        
        if exceeds_limit:
            max_allowed_batch = claude_haiku_limit // 100
            print(f"   → Max safe batch size: {max_allowed_batch} articles")
    
    print()
    return True

def test_actual_batch_api_call():
    """Test 2: Test actual batch API call with different batch sizes"""
    print("=" * 80)
    print("TEST 2: Actual Batch API Call")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Create test articles
    test_articles = []
    for i in range(50):
        test_articles.append({
            'index': i,
            'title': f'Test Article {i+1}: Biotech Company Announces New Drug',
            'description': f'Description for article {i+1} about biotech company news',
            'url': f'https://example.com/article{i+1}'
        })
    
    print(f"Testing with {len(test_articles)} articles")
    print()
    
    # Test with full batch (50 articles)
    print("Test A: Full batch (50 articles)...")
    start_time = time.time()
    results_50 = tracker.get_ai_prediction_score_batch(test_articles[:50])
    time_50 = time.time() - start_time
    
    success_count_50 = sum(1 for r in results_50.values() if r and r.get('company_name'))
    print(f"   Time: {time_50:.2f}s")
    print(f"   Results: {len(results_50)} returned")
    print(f"   Success: {success_count_50}/{50} articles extracted")
    print()
    
    # Test with smaller batch (40 articles)
    print("Test B: Smaller batch (40 articles)...")
    start_time = time.time()
    results_40 = tracker.get_ai_prediction_score_batch(test_articles[:40])
    time_40 = time.time() - start_time
    
    success_count_40 = sum(1 for r in results_40.values() if r and r.get('company_name'))
    print(f"   Time: {time_40:.2f}s")
    print(f"   Results: {len(results_40)} returned")
    print(f"   Success: {success_count_40}/{40} articles extracted")
    print()
    
    # Test with safe batch (30 articles)
    print("Test C: Safe batch (30 articles)...")
    start_time = time.time()
    results_30 = tracker.get_ai_prediction_score_batch(test_articles[:30])
    time_30 = time.time() - start_time
    
    success_count_30 = sum(1 for r in results_30.values() if r and r.get('company_name'))
    print(f"   Time: {time_30:.2f}s")
    print(f"   Results: {len(results_30)} returned")
    print(f"   Success: {success_count_30}/{30} articles extracted")
    print()
    
    return {
        'batch_50': {'time': time_50, 'success': success_count_50, 'total': 50},
        'batch_40': {'time': time_40, 'success': success_count_40, 'total': 40},
        'batch_30': {'time': time_30, 'success': success_count_30, 'total': 30}
    }

def test_extraction_loop_performance():
    """Test 3: Measure extraction loop performance"""
    print("=" * 80)
    print("TEST 3: Extraction Loop Performance")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Simulate articles (like what would come from Google News)
    test_articles = []
    for i in range(50):
        test_articles.append({
            'title': f'Century Therapeutics Announces New Clinical Trial Results',
            'description': f'Century Therapeutics Inc has announced positive results from its Phase 2 trial',
            'publishedAt': '2025-01-15',
            'url': f'https://example.com/article{i}',
            'source': {'name': 'Google News'},
            'event_type': 'bio_companies_small_cap'
        })
    
    print(f"Testing extraction loop with {len(test_articles)} articles")
    print()
    
    # Simulate batch API results (some succeed, some fail)
    batch_results = {}
    for i in range(len(test_articles)):
        # Simulate 30% success rate (like what happens when max_tokens fails)
        if i % 3 == 0:
            batch_results[i] = {
                'company_name': 'Century Therapeutics',
                'ticker': 'IPSC',
                'score': 7,
                'direction': 'bullish'
            }
        else:
            batch_results[i] = None  # Failed
    
    success_count = sum(1 for r in batch_results.values() if r)
    print(f"Simulated batch results: {success_count}/{len(test_articles)} succeeded")
    print()
    
    # Measure extraction loop
    print("Running extraction loop...")
    start_time = time.time()
    
    extracted_count = 0
    extraction_times = []
    
    for i, article in enumerate(test_articles):
        article_start = time.time()
        
        ai_result = batch_results.get(i)
        
        result = tracker.extract_layoff_info(
            article,
            fetch_content=False,
            event_types=['bio_companies_small_cap'],
            pre_fetched_ai_result=ai_result
        )
        
        article_time = time.time() - article_start
        extraction_times.append(article_time)
        
        if result:
            extracted_count += 1
        
        if (i + 1) % 10 == 0:
            elapsed = time.time() - start_time
            avg_time = elapsed / (i + 1)
            print(f"   Progress: {i + 1}/{len(test_articles)} - Elapsed: {elapsed:.1f}s, Avg: {avg_time:.3f}s/article")
    
    total_time = time.time() - start_time
    avg_time = sum(extraction_times) / len(extraction_times) if extraction_times else 0
    max_time = max(extraction_times) if extraction_times else 0
    min_time = min(extraction_times) if extraction_times else 0
    
    print()
    print(f"✅ Extraction complete")
    print(f"   Total time: {total_time:.2f}s")
    print(f"   Average per article: {avg_time:.3f}s")
    print(f"   Min: {min_time:.3f}s, Max: {max_time:.3f}s")
    print(f"   Extracted: {extracted_count}/{len(test_articles)}")
    print()
    
    # Identify slow articles
    slow_articles = [(i, t) for i, t in enumerate(extraction_times) if t > 0.5]
    if slow_articles:
        print(f"⚠️  Slow articles (>0.5s): {len(slow_articles)}")
        for idx, t in sorted(slow_articles, key=lambda x: x[1], reverse=True)[:5]:
            print(f"   Article {idx + 1}: {t:.2f}s")
    print()
    
    return {
        'total_time': total_time,
        'avg_time': avg_time,
        'extracted': extracted_count,
        'total': len(test_articles)
    }

def test_batch_size_optimization():
    """Test 4: Find optimal batch size"""
    print("=" * 80)
    print("TEST 4: Optimal Batch Size")
    print("=" * 80)
    print()
    
    claude_haiku_limit = 4096
    tokens_per_article = 100
    
    max_safe_batch = claude_haiku_limit // tokens_per_article
    print(f"Claude Haiku limit: {claude_haiku_limit} tokens")
    print(f"Tokens per article: {tokens_per_article}")
    print(f"Max safe batch size: {max_safe_batch} articles")
    print()
    
    # Test different batch sizes
    test_sizes = [30, 35, 40, 45, 50]
    
    print("Calculated max_tokens for different batch sizes:")
    for size in test_sizes:
        max_tokens = size * tokens_per_article
        status = "❌ EXCEEDS" if max_tokens > claude_haiku_limit else "✅ OK"
        print(f"   Batch size {size:2d}: max_tokens = {max_tokens:4d} {status}")
    print()
    
    print(f"✅ Recommended batch size: {max_safe_batch} articles")
    print(f"   This ensures max_tokens = {max_safe_batch * tokens_per_article} < {claude_haiku_limit}")
    print()
    
    return max_safe_batch

def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("BATCH API PERFORMANCE DIAGNOSIS")
    print("=" * 80)
    print()
    
    try:
        test_1_result = test_max_tokens_calculation()
        test_2_result = test_actual_batch_api_call()
        test_3_result = test_extraction_loop_performance()
        test_4_result = test_batch_size_optimization()
        
        print("=" * 80)
        print("SUMMARY & RECOMMENDATIONS")
        print("=" * 80)
        print()
        
        print("Issue 1: Max Tokens")
        print(f"   Problem: Batch size 50 → max_tokens = 5000 > 4096 (Claude Haiku limit)")
        print(f"   Solution: Reduce batch size to {test_4_result} or cap max_tokens at 4096")
        print()
        
        print("Issue 2: Extraction Performance")
        if test_3_result['avg_time'] > 0.5:
            print(f"   Problem: Average extraction time is {test_3_result['avg_time']:.3f}s/article")
            print(f"   Impact: For 186 articles, this would take ~{test_3_result['avg_time'] * 186:.0f}s ({test_3_result['avg_time'] * 186 / 60:.1f} minutes)")
            print(f"   Solution: Add progress logging and optimize fallback extraction")
        else:
            print(f"   ✅ Extraction performance is acceptable: {test_3_result['avg_time']:.3f}s/article")
        print()
        
        print("Recommended fixes:")
        print("1. Cap max_tokens at 4096 in get_ai_prediction_score_batch()")
        print(f"2. Reduce BATCH_SIZE from 50 to {test_4_result}")
        print("3. Add progress logging to extraction loop")
        print()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())

