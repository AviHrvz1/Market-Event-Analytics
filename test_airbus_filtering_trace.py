#!/usr/bin/env python3
"""Trace through the filtering process to see where the second Airbus article is removed"""

from main import LayoffTracker
import sys

# Add verbose logging
original_print = print
def verbose_print(*args, **kwargs):
    original_print(*args, **kwargs)

print = verbose_print

print("=" * 80)
print("Airbus Filtering Trace")
print("=" * 80)

tracker = LayoffTracker()

# Mock the extract_layoff_info to log what happens to each article
original_extract = tracker.extract_layoff_info

airbus_extractions = []

def logged_extract(article, fetch_content=False, event_types=None):
    title = article.get('title', '')
    if 'airbus' in title.lower() or 'airbus' in article.get('description', '').lower():
        print(f"\n🔍 Processing Airbus article: {title[:60]}...")
        result = original_extract(article, fetch_content, event_types)
        if result:
            print(f"   ✅ PASSED - Company: {result.get('company_name')}, Ticker: {result.get('stock_ticker')}")
            airbus_extractions.append({
                'title': title,
                'result': result
            })
        else:
            print(f"   ❌ FILTERED OUT - Returned None")
            airbus_extractions.append({
                'title': title,
                'result': None
            })
        return result
    else:
        return original_extract(article, fetch_content, event_types)

tracker.extract_layoff_info = logged_extract

# Fetch articles
print("\n📰 Fetching articles for 'recall' event type...")
tracker.fetch_layoffs(fetch_full_content=False, event_types=['recall'])

print(f"\n📊 Summary:")
print(f"   Airbus articles processed: {len(airbus_extractions)}")
print(f"   Airbus articles that passed: {sum(1 for a in airbus_extractions if a['result'])}")
print(f"   Airbus articles filtered out: {sum(1 for a in airbus_extractions if not a['result'])}")

if airbus_extractions:
    print(f"\n📋 Details:")
    for i, extraction in enumerate(airbus_extractions, 1):
        status = "✅ PASSED" if extraction['result'] else "❌ FILTERED"
        print(f"   {i}. {status}: {extraction['title'][:70]}...")
        if extraction['result']:
            print(f"      Company: {extraction['result'].get('company_name')}")
            print(f"      Ticker: {extraction['result'].get('stock_ticker')}")

# Check final layoffs
airbus_final = [l for l in tracker.layoffs if 'airbus' in l.get('company_name', '').lower() or 'air.pa' in l.get('stock_ticker', '').lower()]
print(f"\n📊 Final layoffs list:")
print(f"   Total layoffs: {len(tracker.layoffs)}")
print(f"   Airbus in final: {len(airbus_final)}")

print("\n" + "=" * 80)

