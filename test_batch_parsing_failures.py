#!/usr/bin/env python3
"""
Test to identify why batch parsing fails for 95% of articles
"""

import sys
import re
from main import LayoffTracker
from config import MAX_ARTICLES_TO_PROCESS
from datetime import datetime, timezone

def test_parsing_failures():
    """Test what causes parsing failures"""
    
    print("=" * 80)
    print("BATCH PARSING FAILURE DIAGNOSIS")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    event_types = ['bio_companies']
    selected_sources = ['google_news']
    
    # Fetch articles
    print("🔍 Fetching articles...")
    articles, source_stats = tracker.search_all_realtime_sources(
        event_types=event_types, 
        selected_sources=selected_sources
    )
    
    def parse_date(date_str):
        if not date_str:
            return datetime.min.replace(tzinfo=timezone.utc)
        try:
            from dateutil import parser
            return parser.parse(date_str).replace(tzinfo=timezone.utc)
        except:
            return datetime.min.replace(tzinfo=timezone.utc)
    
    articles.sort(key=lambda x: parse_date(x.get('publishedAt', '')), reverse=True)
    test_articles = articles[:50]  # First 50 for testing
    
    print(f"   ✅ Testing with {len(test_articles)} articles")
    print()
    
    # Prepare batch input
    batch_input = []
    for i, article in enumerate(test_articles):
        batch_input.append({
            'index': i,
            'title': article.get('title', ''),
            'description': article.get('description', ''),
            'url': article.get('url', '')
        })
    
    # Call batch API
    print("🔍 Calling batch API...")
    batch_results = tracker.get_ai_prediction_score_batch(batch_input)
    print()
    
    # Analyze results
    success_count = 0
    failure_count = 0
    failure_reasons = {
        'no_result': 0,
        'no_company_name': 0,
        'no_ticker': 0,
        'invalid_direction': 0,
        'invalid_score': 0
    }
    
    failed_articles = []
    
    for i, article in enumerate(batch_input):
        result = batch_results.get(i)
        
        if result and result.get('company_name'):
            success_count += 1
        else:
            failure_count += 1
            
            if not result:
                failure_reasons['no_result'] += 1
                failed_articles.append({
                    'index': i + 1,
                    'title': article['title'][:60],
                    'reason': 'No result from Claude'
                })
            elif not result.get('company_name'):
                failure_reasons['no_company_name'] += 1
                failed_articles.append({
                    'index': i + 1,
                    'title': article['title'][:60],
                    'reason': 'No company name in result',
                    'result': result
                })
            elif not result.get('ticker'):
                failure_reasons['no_ticker'] += 1
            elif result.get('direction') not in ['bullish', 'bearish']:
                failure_reasons['invalid_direction'] += 1
                failed_articles.append({
                    'index': i + 1,
                    'title': article['title'][:60],
                    'reason': f"Invalid direction: {result.get('direction')}",
                    'result': result
                })
            elif not (1 <= result.get('score', 0) <= 10):
                failure_reasons['invalid_score'] += 1
    
    print("=" * 80)
    print("RESULTS ANALYSIS")
    print("=" * 80)
    print()
    print(f"Total articles: {len(batch_input)}")
    print(f"✅ Success: {success_count} ({success_count/len(batch_input)*100:.1f}%)")
    print(f"❌ Failed: {failure_count} ({failure_count/len(batch_input)*100:.1f}%)")
    print()
    print("Failure reasons:")
    for reason, count in failure_reasons.items():
        if count > 0:
            print(f"  {reason}: {count}")
    print()
    
    if failed_articles:
        print("Sample failed articles:")
        for item in failed_articles[:10]:
            print(f"  Article {item['index']}: {item['reason']}")
            print(f"    Title: {item['title']}")
            if 'result' in item:
                print(f"    Result: {item['result']}")
            print()
    
    # Now test the actual parsing logic with a mock response
    print("=" * 80)
    print("PARSING LOGIC TEST")
    print("=" * 80)
    print()
    
    # Test cases that might fail
    test_cases = [
        ('Article 1: Johnson & Johnson, Inc., JNJ, 7, bullish', 'Company with comma'),
        ('Article 2: Pfizer Inc, PFE, 8, neutral', 'Neutral direction'),
        ('Article 3: Moderna, MRNA, 9, bullish', 'Simple case'),
        ('Article 4: "Tesla, Inc.", TSLA, 6, bearish', 'Quoted company name'),
        ('Article 5: Company Name, Inc., TICKER, 5, bullish', 'Standard format'),
    ]
    
    print("Testing parsing logic with edge cases:")
    print()
    for test_line, description in test_cases:
        print(f"Test: {description}")
        print(f"  Input: {test_line}")
        
        # Simulate the parsing logic
        line = test_line.strip()
        if line.startswith('Article '):
            match = re.match(r'Article\s+(\d+):\s*(.+)', line, re.IGNORECASE)
            if match:
                article_num = int(match.group(1))
                data_str = match.group(2)
                parts = [p.strip() for p in data_str.split(',')]
                
                print(f"  Parsed parts: {len(parts)} - {parts}")
                
                if len(parts) >= 4:
                    company_name = parts[0].strip()
                    ticker_str = parts[1].strip().upper()
                    ticker = None if ticker_str == 'N/A' or ticker_str == '' else ticker_str
                    try:
                        score = int(parts[2].strip())
                        direction = parts[3].strip().lower()
                        
                        print(f"  Company: {company_name}")
                        print(f"  Ticker: {ticker}")
                        print(f"  Score: {score}")
                        print(f"  Direction: {direction}")
                        
                        if 1 <= score <= 10 and direction in ['bullish', 'bearish']:
                            print(f"  ✅ Would be accepted")
                        else:
                            print(f"  ❌ Would be rejected (score: {score}, direction: {direction})")
                    except (ValueError, IndexError) as e:
                        print(f"  ❌ Parse error: {e}")
                else:
                    print(f"  ❌ Not enough parts (need 4, got {len(parts)})")
            else:
                print(f"  ❌ Regex didn't match")
        print()

if __name__ == '__main__':
    try:
        test_parsing_failures()
        print("\n✅ Diagnosis completed")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Diagnosis failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

