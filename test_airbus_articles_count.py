#!/usr/bin/env python3
"""Unit test to count how many Airbus articles are found"""

from main import LayoffTracker
from datetime import datetime, timezone

print("=" * 80)
print("Airbus Articles Count Test")
print("=" * 80)

tracker = LayoffTracker()

# Fetch articles for recall event type (Airbus had recalls)
print("\n📰 Fetching articles for 'recall' event type...")
tracker.fetch_layoffs(fetch_full_content=False, event_types=['recall'])

# Find all Airbus articles
airbus_articles = []
for layoff in tracker.layoffs:
    ticker = layoff.get('stock_ticker', '').upper()
    company = layoff.get('company_name', '').upper()
    
    if 'AIR.PA' in ticker or 'AIRBUS' in company or 'EADSY' in ticker:
        airbus_articles.append(layoff)

print(f"\n✅ Found {len(airbus_articles)} Airbus article(s)")

if airbus_articles:
    print(f"\n📋 Airbus Articles Details:")
    for i, article in enumerate(airbus_articles, 1):
        ticker = article.get('stock_ticker', 'N/A')
        company = article.get('company_name', 'N/A')
        date = article.get('date', 'N/A')
        time = article.get('time', 'N/A')
        title = article.get('title', 'N/A')[:80]  # First 80 chars
        url = article.get('url', 'N/A')
        
        print(f"\n  {i}. {company} ({ticker})")
        print(f"     Date: {date} {time}")
        print(f"     Title: {title}...")
        print(f"     URL: {url}")
else:
    print("\n⚠️  No Airbus articles found")

# Also check all tickers to see how many per ticker
print(f"\n📊 Articles per ticker (all companies):")
ticker_counts = {}
for layoff in tracker.layoffs:
    ticker = layoff.get('stock_ticker', 'N/A')
    if ticker not in ticker_counts:
        ticker_counts[ticker] = []
    ticker_counts[ticker].append(layoff)

# Show tickers with multiple articles
multi_article_tickers = {t: articles for t, articles in ticker_counts.items() if len(articles) > 1}
if multi_article_tickers:
    print(f"\n  Tickers with multiple articles:")
    for ticker, articles in sorted(multi_article_tickers.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"    {ticker}: {len(articles)} article(s)")
        for article in articles[:3]:  # Show first 3
            date = article.get('date', 'N/A')
            title = article.get('title', 'N/A')[:60]
            print(f"      - {date}: {title}...")
else:
    print(f"\n  No tickers with multiple articles found")

print("\n" + "=" * 80)

