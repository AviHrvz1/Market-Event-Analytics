#!/usr/bin/env python3
"""Unit test to investigate why only 1 Airbus article appears when logs show 2"""

from main import LayoffTracker

print("=" * 80)
print("Airbus Duplicate Article Investigation")
print("=" * 80)

tracker = LayoffTracker()

# Fetch articles for recall event type
print("\n📰 Fetching articles for 'recall' event type...")
tracker.fetch_layoffs(fetch_full_content=False, event_types=['recall'])

# Find all Airbus articles in final layoffs
airbus_in_layoffs = []
for i, layoff in enumerate(tracker.layoffs):
    ticker = layoff.get('stock_ticker', '').upper()
    company = layoff.get('company_name', '').upper()
    title = layoff.get('title', '').upper()
    
    if 'AIR.PA' in ticker or 'AIRBUS' in company or 'EADSY' in ticker or 'AIRBUS' in title:
        airbus_in_layoffs.append({
            'index': i,
            'ticker': ticker,
            'company': company,
            'title': title,
            'date': layoff.get('date'),
            'url': layoff.get('url')
        })

print(f"\n📊 Results:")
print(f"   Total layoffs in final list: {len(tracker.layoffs)}")
print(f"   Airbus articles in final list: {len(airbus_in_layoffs)}")

if airbus_in_layoffs:
    print(f"\n✅ Airbus Articles Found in Final List:")
    for article in airbus_in_layoffs:
        print(f"\n   {article['index']}. {article['company']} ({article['ticker']})")
        print(f"      Date: {article['date']}")
        print(f"      Title: {article['title'][:80]}...")
        print(f"      URL: {article['url'][:60]}...")
else:
    print(f"\n⚠️  No Airbus articles in final layoffs list")

# Check all tickers to see duplicates
print(f"\n📋 All Articles by Ticker:")
ticker_to_articles = {}
for layoff in tracker.layoffs:
    ticker = layoff.get('stock_ticker', 'N/A')
    if ticker not in ticker_to_articles:
        ticker_to_articles[ticker] = []
    ticker_to_articles[ticker].append(layoff)

for ticker in sorted(ticker_to_articles.keys()):
    articles = ticker_to_articles[ticker]
    print(f"   {ticker}: {len(articles)} article(s)")
    if len(articles) > 1:
        for i, article in enumerate(articles, 1):
            print(f"      {i}. {article.get('title', 'N/A')[:60]}...")

# Check if there's title deduplication happening
print(f"\n🔍 Checking for title deduplication...")
titles_seen = {}
for layoff in tracker.layoffs:
    title = layoff.get('title', '').lower()
    if title in titles_seen:
        print(f"   ⚠️  DUPLICATE TITLE FOUND: {title[:60]}...")
        print(f"      First: {titles_seen[title].get('company_name')} ({titles_seen[title].get('stock_ticker')})")
        print(f"      Second: {layoff.get('company_name')} ({layoff.get('stock_ticker')})")
    else:
        titles_seen[title] = layoff

print("\n" + "=" * 80)

