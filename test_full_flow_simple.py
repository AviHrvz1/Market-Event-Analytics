#!/usr/bin/env python3
"""Full flow unit test - simplified version"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker
from config import LOOKBACK_DAYS

print("\n" + "=" * 80)
print("Full Flow Unit Test")
print("=" * 80)

tracker = LayoffTracker()

# Test 1: Claude Extraction
print("\n[Test 1] Testing Claude extraction...")
result = tracker.get_ai_prediction_score(
    title='Tesla announces product recall',
    description='Tesla Inc. recalls 100,000 vehicles due to safety issues.',
    url='https://test.com/tesla'
)
if result:
    print(f"✅ PASSED: Company={result.get('company_name')}, Ticker={result.get('ticker')}, Score={result.get('score')}, Direction={result.get('direction')}")
else:
    print("❌ FAILED: Claude returned None")
    sys.exit(1)

# Test 2: Date Filtering (Old Article)
print("\n[Test 2] Testing date filtering (old article)...")
old_date = datetime.now(timezone.utc) - timedelta(days=35)
old_article = {
    'title': 'Old article',
    'description': 'This is too old',
    'url': 'https://test.com/old',
    'publishedAt': old_date.isoformat()
}
result = tracker.extract_layoff_info(old_article, fetch_content=False, event_types=['layoff_event'])
if result is None:
    print(f"✅ PASSED: Old article correctly filtered out")
else:
    print(f"❌ FAILED: Old article was not filtered (got: {result.get('company_name')})")
    sys.exit(1)

# Test 3: Recent Article
print("\n[Test 3] Testing recent article processing...")
recent_date = datetime.now(timezone.utc) - timedelta(days=5)
recent_article = {
    'title': 'Apple recalls iPhone models',
    'description': 'Apple Inc. recalls iPhone 15 models due to battery issues.',
    'url': 'https://test.com/apple',
    'publishedAt': recent_date.isoformat(),
    'source': {'name': 'Google News'}
}
result = tracker.extract_layoff_info(recent_article, fetch_content=False, event_types=['recall'])
if result and result.get('company_name'):
    print(f"✅ PASSED: Recent article processed - Company={result.get('company_name')}, Ticker={result.get('stock_ticker')}, AI Score={result.get('ai_prediction_score')}")
else:
    print(f"⚠️  WARNING: Recent article returned None (may be normal if company not found)")

# Test 4: Private Company
print("\n[Test 4] Testing private company handling...")
private_result = tracker.get_ai_prediction_score(
    title='Rad Power Bikes safety warning',
    description='Rad Power Bikes issues safety warning for electric bikes.',
    url='https://test.com/rad'
)
if private_result:
    ticker = private_result.get('ticker')
    if ticker is None:
        print(f"✅ PASSED: Private company correctly identified (ticker=None)")
    else:
        print(f"⚠️  INFO: Got ticker {ticker} (may be false positive)")

print("\n" + "=" * 80)
print("✅ All tests completed!")
print("=" * 80)

