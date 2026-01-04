#!/usr/bin/env python3
"""Unit test to understand what happens with Airbus articles"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

print("=" * 80)
print("Airbus Unit Test - Understanding the Flow")
print("=" * 80)

tracker = LayoffTracker()

# Test 1: Check if Claude can extract Airbus
print("\n[Test 1] Testing Claude extraction for Airbus...")
airbus_article = {
    'title': 'Airbus announces recall of A320 aircraft due to safety concerns',
    'description': 'Airbus SE has issued a recall for certain A320 aircraft models due to potential safety issues affecting flight control systems.',
    'url': 'https://example.com/airbus-recall-test',
    'publishedAt': datetime.now(timezone.utc).isoformat()
}

print(f"Title: {airbus_article['title']}")
print(f"Description: {airbus_article['description']}")

claude_result = tracker.get_ai_prediction_score(
    title=airbus_article['title'],
    description=airbus_article['description'],
    url=airbus_article['url']
)

if claude_result:
    print(f"\n✅ Claude Response:")
    print(f"  Company Name: {claude_result.get('company_name')}")
    print(f"  Ticker: {claude_result.get('ticker')}")
    print(f"  Score: {claude_result.get('score')}")
    print(f"  Direction: {claude_result.get('direction')}")
else:
    print("\n❌ Claude returned None")

# Test 2: Check ticker lookup
print("\n[Test 2] Testing ticker lookup for 'Airbus'...")
ticker = tracker.get_stock_ticker('Airbus')
print(f"Ticker from get_stock_ticker('Airbus'): {ticker}")

# Test 3: Check if ticker is available
if ticker:
    print(f"\n[Test 3] Testing if ticker '{ticker}' is available...")
    is_available = tracker._is_ticker_available(ticker)
    print(f"_is_ticker_available('{ticker}'): {is_available}")
    
    # Check why it might not be available
    ticker_upper = ticker.upper()
    print(f"\n  Checking reasons:")
    print(f"  - In invalid_tickers: {ticker_upper in tracker.invalid_tickers}")
    print(f"  - In failed_tickers: {ticker_upper in tracker.failed_tickers}")
    print(f"  - In SEC EDGAR (ticker_to_cik_cache): {ticker_upper in tracker.ticker_to_cik_cache}")
    print(f"  - _is_valid_ticker result: {tracker._is_valid_ticker(ticker)}")
    
    if ticker_upper in tracker.ticker_to_cik_cache:
        print(f"  ✅ Ticker found in SEC EDGAR")
    else:
        print(f"  ❌ Ticker NOT found in SEC EDGAR")
        print(f"  This is why it's being filtered out!")

# Test 4: Full extraction flow
print("\n[Test 4] Testing full extract_layoff_info() flow...")
full_article = {
    'title': 'Airbus recalls A320 aircraft models due to safety issues',
    'description': 'Airbus SE has announced a recall of certain A320 aircraft models manufactured between 2020 and 2023 due to potential flight control system malfunctions.',
    'url': 'https://example.com/airbus-full-test',
    'publishedAt': datetime.now(timezone.utc).isoformat(),
    'source': {'name': 'Google News'}
}

print(f"Article: {full_article['title']}")
result = tracker.extract_layoff_info(full_article, fetch_content=False, event_types=['recall'])

if result:
    print(f"\n✅ Article was NOT filtered out:")
    print(f"  Company: {result.get('company_name')}")
    print(f"  Ticker: {result.get('stock_ticker')}")
    print(f"  Event Type: {result.get('event_type')}")
    print(f"  AI Score: {result.get('ai_prediction_score')}")
else:
    print(f"\n❌ Article was FILTERED OUT (returned None)")
    print(f"  This means it won't appear in the UI!")

# Test 5: Check fallback mapping
print("\n[Test 5] Checking fallback ticker mapping...")
# Check if Airbus is in the fallback map by trying get_stock_ticker
ticker_from_fallback = tracker.get_stock_ticker('Airbus')
print(f"Ticker from get_stock_ticker('Airbus'): {ticker_from_fallback}")

# Test 6: Check Prixe.io availability (if we can)
if ticker:
    print(f"\n[Test 6] Checking Prixe.io data availability for {ticker}...")
    # Try a simple Prixe.io request to see if ticker exists there
    try:
        # Just check if we can make a request (don't actually fetch data)
        print(f"  Note: Prixe.io check would require actual API call")
        print(f"  If ticker is not in SEC but exists in Prixe.io, it should still work")
    except Exception as e:
        print(f"  Error: {e}")

print("\n" + "=" * 80)
print("Summary:")
print("=" * 80)
if ticker:
    if tracker._is_ticker_available(ticker):
        print(f"✅ Airbus ticker '{ticker}' is AVAILABLE - articles should appear in UI")
    else:
        print(f"❌ Airbus ticker '{ticker}' is NOT AVAILABLE - articles are being filtered out")
        print(f"   Reason: Ticker not found in SEC EDGAR database")
        print(f"   Solution: Add '{ticker}' to foreign ADR whitelist or skip SEC validation")
else:
    print(f"❌ No ticker found for Airbus - Claude or fallback mapping failed")

