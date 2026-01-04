#!/usr/bin/env python3
"""Unit test to check how many Airbus articles are found with 100 article limit"""

import os
import sys
from main import LayoffTracker

# Temporarily override MAX_ARTICLES_TO_PROCESS to 100 for this test
original_max = os.environ.get('MAX_ARTICLES_TO_PROCESS', '50')
os.environ['MAX_ARTICLES_TO_PROCESS'] = '100'

# Reload config to pick up the new value
if 'config' in sys.modules:
    del sys.modules['config']
from config import MAX_ARTICLES_TO_PROCESS

print("=" * 80)
print("Airbus Articles Test with 100 Article Limit")
print("=" * 80)
print(f"\n📊 MAX_ARTICLES_TO_PROCESS set to: {MAX_ARTICLES_TO_PROCESS}")

tracker = LayoffTracker()

# Fetch articles for recall event type
print("\n📰 Fetching articles for 'recall' event type...")
tracker.fetch_layoffs(fetch_full_content=False, event_types=['recall'])

# Find all Airbus articles
airbus_articles = []
for layoff in tracker.layoffs:
    ticker = layoff.get('stock_ticker', '').upper()
    company = layoff.get('company_name', '').upper()
    title = layoff.get('title', '').upper()
    
    if 'AIR.PA' in ticker or 'AIRBUS' in company or 'EADSY' in ticker or 'AIRBUS' in title:
        airbus_articles.append(layoff)

print(f"\n✅ Found {len(airbus_articles)} Airbus article(s) with {MAX_ARTICLES_TO_PROCESS} article limit")

if airbus_articles:
    print(f"\n📋 Airbus Articles Details:")
    for i, article in enumerate(airbus_articles, 1):
        ticker = article.get('stock_ticker', 'N/A')
        company = article.get('company_name', 'N/A')
        date = article.get('date', 'N/A')
        time = article.get('time', 'N/A')
        title = article.get('title', 'N/A')
        url = article.get('url', 'N/A')
        
        print(f"\n  {i}. {company} ({ticker})")
        print(f"     Date: {date} {time}")
        print(f"     Title: {title[:100]}...")
        print(f"     URL: {url[:80]}...")
else:
    print("\n⚠️  No Airbus articles found")

# Also check total articles processed
print(f"\n📊 Summary:")
print(f"   Total articles processed: {len(tracker.layoffs)}")
print(f"   Airbus articles found: {len(airbus_articles)}")
print(f"   MAX_ARTICLES_TO_PROCESS: {MAX_ARTICLES_TO_PROCESS}")

# Check articles per ticker
print(f"\n📋 Articles per ticker:")
ticker_counts = {}
for layoff in tracker.layoffs:
    ticker = layoff.get('stock_ticker', 'N/A')
    if ticker not in ticker_counts:
        ticker_counts[ticker] = []
    ticker_counts[ticker].append(layoff)

for ticker in sorted(ticker_counts.keys()):
    count = len(ticker_counts[ticker])
    print(f"   {ticker}: {count} article(s)")

print("\n" + "=" * 80)

# Restore original value
os.environ['MAX_ARTICLES_TO_PROCESS'] = original_max

