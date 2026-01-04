#!/usr/bin/env python3
"""
Direct test of real estate search - check if Google News queries work
"""

import sys
import urllib.parse
import requests
from bs4 import BeautifulSoup
from main import LayoffTracker
from config import LOOKBACK_DAYS

print("=" * 80)
print("REAL ESTATE DIRECT SEARCH TEST")
print("=" * 80)
print()

tracker = LayoffTracker()

# Get real estate companies
companies = tracker._get_real_estate_companies()
print(f"✓ Found {len(companies)} real estate companies")
print()

# Test 1: Try a simple query with first 5 companies
print("Test 1: Simple Google News Query (First 5 Companies)")
print("-" * 80)
test_companies = companies[:5]
company_queries = [f'"{c}"' for c in test_companies]
search_query = ' OR '.join(company_queries)
print(f"Companies: {test_companies}")
print(f"Query: {search_query}")
print()

# Build URL
encoded_query = urllib.parse.quote_plus(f"{search_query} when:{LOOKBACK_DAYS}d")
url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en&num=100"
print(f"URL: {url[:100]}...")
print()

# Try to fetch
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

try:
    print("Fetching from Google News RSS...")
    response = requests.get(url, headers=headers, timeout=15, verify=False)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')
        print(f"✓ Found {len(items)} articles")
        
        if items:
            print("\nFirst 5 articles:")
            for i, item in enumerate(items[:5], 1):
                title = item.find('title')
                if title:
                    print(f"  {i}. {title.text.strip()[:80]}...")
        else:
            print("✗ No articles found in RSS feed")
            print("\nDebugging:")
            print(f"  Query length: {len(search_query)} characters")
            print(f"  Lookback days: {LOOKBACK_DAYS}")
            print(f"  Full URL: {url}")
    else:
        print(f"✗ HTTP Error: {response.status_code}")
        print(f"  Response: {response.text[:200]}")
        
except Exception as e:
    print(f"✗ Error: {str(e)[:200]}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("Test 2: Using _try_google_news_rss function")
print("=" * 80)
print()

try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    articles, stats = tracker._try_google_news_rss(['real_estate_good_news'], headers)
    print(f"✓ _try_google_news_rss completed")
    print(f"  Articles: {len(articles)}")
    print(f"  Stats: {stats}")
    
    if articles:
        print("\nFirst 5 articles:")
        for i, article in enumerate(articles[:5], 1):
            title = article.get('title', 'N/A')[:60]
            matched = article.get('matched_company', 'None')
            print(f"  {i}. {title}... (Company: {matched})")
    else:
        print("\n✗ No articles returned")
        print("  This suggests the search queries are not finding articles")
        
except Exception as e:
    print(f"✗ Error: {str(e)[:200]}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)

