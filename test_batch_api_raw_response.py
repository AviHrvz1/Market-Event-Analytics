#!/usr/bin/env python3
"""
Test to capture Claude's raw response for real articles to see why parsing fails
"""

import sys
import requests
import json
from main import LayoffTracker
from config import MAX_ARTICLES_TO_PROCESS
from datetime import datetime, timezone

def test_batch_api_raw_response():
    """Capture Claude's raw response to see why parsing fails"""
    
    print("=" * 80)
    print("BATCH API RAW RESPONSE TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    event_types = ['bio_companies']
    selected_sources = ['google_news']
    
    # Fetch a small batch of real articles
    print("🔍 Fetching real articles...")
    articles, source_stats = tracker.search_all_realtime_sources(
        event_types=event_types, 
        selected_sources=selected_sources
    )
    
    # Sort and limit to first 10 for testing
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
    
    print(f"   ✅ Fetched {len(test_articles)} test articles")
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
    
    # Make the actual API call and capture raw response
    print("🔍 Making batch API call to Claude...")
    print()
    
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
    
    try:
        response = requests.post(tracker.claude_api_url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            content = data.get('content', [])
            if content and len(content) > 0:
                text = content[0].get('text', '').strip()
                
                print("=" * 80)
                print("RAW CLAUDE RESPONSE:")
                print("=" * 80)
                print()
                print(text)
                print()
                print("=" * 80)
                print("PARSING ANALYSIS:")
                print("=" * 80)
                print()
                
                # Try to parse
                lines = text.split('\n')
                parsed_count = 0
                failed_lines = []
                
                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    if line.startswith('Article '):
                        # Try to parse
                        import re
                        match = re.match(r'Article\s+(\d+):\s*(.+)', line, re.IGNORECASE)
                        if match:
                            article_num = int(match.group(1))
                            data_str = match.group(2)
                            parts = [p.strip() for p in data_str.split(',')]
                            
                            if len(parts) >= 4:
                                parsed_count += 1
                                print(f"✅ Line {line_num}: Successfully parsed")
                                print(f"   Article {article_num}: {parts[0]}, {parts[1]}, {parts[2]}, {parts[3]}")
                            else:
                                failed_lines.append((line_num, line, f"Only {len(parts)} parts (need 4)"))
                                print(f"❌ Line {line_num}: Failed - Only {len(parts)} comma-separated parts")
                                print(f"   Raw: {line}")
                        else:
                            failed_lines.append((line_num, line, "Regex match failed"))
                            print(f"❌ Line {line_num}: Failed - Regex didn't match")
                            print(f"   Raw: {line}")
                    else:
                        # Not an "Article X:" line - might be explanation or other text
                        if line and not line.startswith('Article '):
                            print(f"⚠️  Line {line_num}: Not an article line (might be explanation)")
                            print(f"   Raw: {line[:100]}...")
                
                print()
                print("=" * 80)
                print("SUMMARY:")
                print("=" * 80)
                print(f"Total lines: {len([l for l in lines if l.strip()])}")
                print(f"Successfully parsed: {parsed_count}/{len(batch_input)}")
                print(f"Failed: {len(failed_lines)}")
                print()
                
                if failed_lines:
                    print("Failed lines:")
                    for line_num, line, reason in failed_lines[:5]:
                        print(f"  Line {line_num}: {reason}")
                        print(f"    {line[:80]}...")
                
        else:
            print(f"❌ API Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    try:
        test_batch_api_raw_response()
        print("\n✅ Test completed")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

