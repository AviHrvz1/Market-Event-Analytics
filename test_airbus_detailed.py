#!/usr/bin/env python3
"""Detailed test to find all Airbus articles before and after filtering"""

from main import LayoffTracker
import json

print("=" * 80)
print("Detailed Airbus Articles Test")
print("=" * 80)

tracker = LayoffTracker()

# Fetch articles
print("\n📰 Fetching articles for 'recall' event type...")
tracker.fetch_layoffs(fetch_full_content=False, event_types=['recall'])

# Check all layoffs for Airbus-related content
print(f"\n📊 Total layoffs found: {len(tracker.layoffs)}")

airbus_related = []
for i, layoff in enumerate(tracker.layoffs):
    ticker = layoff.get('stock_ticker', '').upper()
    company = layoff.get('company_name', '').upper()
    title = layoff.get('title', '')
    
    if 'AIR.PA' in ticker or 'AIRBUS' in company or 'EADSY' in ticker or 'AIRBUS' in title.upper():
        airbus_related.append({
            'index': i,
            'ticker': ticker,
            'company': company,
            'title': title,
            'date': layoff.get('date'),
            'url': layoff.get('url')
        })

print(f"\n✅ Found {len(airbus_related)} Airbus-related article(s)")

if airbus_related:
    for article in airbus_related:
        print(f"\n  {article['index']}. {article['company']} ({article['ticker']})")
        print(f"     Date: {article['date']}")
        print(f"     Title: {article['title'][:100]}...")
else:
    print("\n⚠️  No Airbus articles found in final layoffs list")

# Also check what tickers we have
print(f"\n📋 All unique tickers found:")
ticker_set = set()
for layoff in tracker.layoffs:
    ticker = layoff.get('stock_ticker')
    if ticker:
        ticker_set.add(ticker)

for ticker in sorted(ticker_set):
    count = sum(1 for l in tracker.layoffs if l.get('stock_ticker') == ticker)
    print(f"  {ticker}: {count} article(s)")

print("\n" + "=" * 80)

