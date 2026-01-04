#!/usr/bin/env python3
"""
Test to capture actual errors from batch API calls
"""

import sys
import requests
import json
from main import LayoffTracker
from config import MAX_ARTICLES_TO_PROCESS
from datetime import datetime, timezone

def test_batch_api_with_logging():
    """Test batch API with detailed error logging"""
    
    print("=" * 80)
    print("BATCH API ERROR LOGGING TEST")
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
    test_articles = articles[:10]  # Just 10 for testing
    
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
    
    # Build prompt
    articles_text = ""
    for i, article in enumerate(batch_input, 1):
        title = article.get('title', '')
        description = article.get('description', '')
        articles_text += f"\n\nArticle {i}:\nTitle: {title}\nDescription: {description}\n"
    
    prompt = f"""Analyze the following {len(batch_input)} news articles and extract company information and predict stock impact for each.

{articles_text}

For EACH article, provide:
1. Company Name: The full official name of the company mentioned (e.g., "Tesla Inc", "Microsoft Corporation")
2. Stock Ticker: The stock ticker symbol if publicly traded (e.g., "TSLA", "MSFT"), or "N/A" if private
3. Stock price impact score (1-10): 1-3=Low, 4-6=Moderate, 7-10=High
4. Direction: "bullish" or "bearish"

IMPORTANT: Respond with ONE LINE PER ARTICLE in this exact format:
Article 1: [company name], [ticker or N/A], [score 1-10], [bullish or bearish]
Article 2: [company name], [ticker or N/A], [score 1-10], [bullish or bearish]
...

Examples:
Article 1: Tesla Inc, TSLA, 7, bearish
Article 2: Rad Power Bikes, N/A, 5, bearish
Article 3: Microsoft Corporation, MSFT, 3, bullish

Do not include any explanation. Just the numbered lines with the four values separated by commas."""

    headers = {
        'x-api-key': tracker.claude_api_key,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json'
    }
    
    payload = {
        'model': 'claude-3-haiku-20240307',
        'max_tokens': len(batch_input) * 100,
        'messages': [
            {
                'role': 'user',
                'content': prompt
            }
        ]
    }
    
    print("🔍 Making API call with detailed logging...")
    print()
    
    try:
        print(f"   API URL: {tracker.claude_api_url}")
        print(f"   Model: {payload['model']}")
        print(f"   Max tokens: {payload['max_tokens']}")
        print(f"   Articles: {len(batch_input)}")
        print()
        
        response = requests.post(tracker.claude_api_url, headers=headers, json=payload, timeout=60)
        
        print(f"   Status code: {response.status_code}")
        print()
        
        if response.status_code == 200:
            try:
                data = response.json()
                print("   ✅ Response is valid JSON")
                print()
                
                content = data.get('content', [])
                print(f"   Content array length: {len(content)}")
                
                if content and len(content) > 0:
                    text = content[0].get('text', '').strip()
                    print(f"   Response text length: {len(text)} characters")
                    print()
                    print("   First 500 chars of response:")
                    print("   " + "-" * 76)
                    print("   " + text[:500].replace('\n', '\n   '))
                    print("   " + "-" * 76)
                    print()
                    
                    # Check for parsing issues
                    lines = text.split('\n')
                    article_lines = [l for l in lines if l.strip().startswith('Article ')]
                    print(f"   Lines starting with 'Article ': {len(article_lines)}")
                    
                    if len(article_lines) != len(batch_input):
                        print(f"   ⚠️  WARNING: Expected {len(batch_input)} article lines, got {len(article_lines)}")
                else:
                    print("   ❌ No content in response")
                    print(f"   Full response: {json.dumps(data, indent=2)}")
            except json.JSONDecodeError as e:
                print(f"   ❌ Response is not valid JSON: {e}")
                print(f"   Response text: {response.text[:500]}")
        else:
            print(f"   ❌ API returned error status: {response.status_code}")
            print(f"   Response text: {response.text[:1000]}")
            
    except requests.exceptions.Timeout:
        print("   ❌ Request timed out after 60 seconds")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request exception: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    try:
        test_batch_api_with_logging()
        print("\n✅ Test completed")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

