#!/usr/bin/env python3
"""
Test to verify date filtering is working (120 days limit)
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker
from config import LOOKBACK_DAYS

print("=" * 80)
print("DATE FILTERING VERIFICATION TEST")
print("=" * 80)
print()

print(f"LOOKBACK_DAYS setting: {LOOKBACK_DAYS} days")
print()

tracker = LayoffTracker()

# Test: Check if Google News queries include date filter
print("Testing Google News query construction...")
print("-" * 80)

articles, stats = tracker.search_all_realtime_sources(
    event_types=['real_estate_good_news'],
    selected_sources=['google_news']
)

print(f"✓ Search completed")
print(f"  Articles found: {len(articles)}")
print()

# Check article dates
if articles:
    print("Checking article dates...")
    print("-" * 80)
    
    now = datetime.now(timezone.utc)
    articles_within_range = 0
    articles_outside_range = 0
    oldest_article = None
    newest_article = None
    
    for article in articles:
        published_at = article.get('publishedAt', '')
        if published_at:
            try:
                from dateutil import parser
                article_date = parser.parse(published_at)
                if article_date.tzinfo is None:
                    article_date = article_date.replace(tzinfo=timezone.utc)
                else:
                    article_date = article_date.astimezone(timezone.utc)
                
                days_ago = (now - article_date).days
                
                if days_ago <= LOOKBACK_DAYS:
                    articles_within_range += 1
                else:
                    articles_outside_range += 1
                    if oldest_article is None or days_ago > oldest_article['days_ago']:
                        oldest_article = {
                            'title': article.get('title', '')[:60],
                            'days_ago': days_ago,
                            'date': article_date.strftime('%Y-%m-%d')
                        }
                
                if newest_article is None or days_ago < newest_article['days_ago']:
                    newest_article = {
                        'title': article.get('title', '')[:60],
                        'days_ago': days_ago,
                        'date': article_date.strftime('%Y-%m-%d')
                    }
            except:
                pass
    
    print(f"  Articles within {LOOKBACK_DAYS} days: {articles_within_range}")
    print(f"  Articles outside {LOOKBACK_DAYS} days: {articles_outside_range}")
    print()
    
    if newest_article:
        print(f"  Newest article: {newest_article['days_ago']} days ago ({newest_article['date']})")
        print(f"    {newest_article['title']}...")
    print()
    
    if oldest_article:
        print(f"  Oldest article: {oldest_article['days_ago']} days ago ({oldest_article['date']})")
        print(f"    {oldest_article['title']}...")
        if oldest_article['days_ago'] > LOOKBACK_DAYS:
            print(f"    ⚠️  WARNING: This article is older than {LOOKBACK_DAYS} days!")
        else:
            print(f"    ✓ This article is within the {LOOKBACK_DAYS} day limit")
    print()
    
    print("=" * 80)
    print("VERIFICATION RESULT")
    print("=" * 80)
    print()
    
    if articles_outside_range == 0:
        print(f"✅ SUCCESS: All articles are within {LOOKBACK_DAYS} days")
        print(f"   Date filtering is working correctly")
    else:
        print(f"⚠️  WARNING: {articles_outside_range} articles are older than {LOOKBACK_DAYS} days")
        print(f"   Google News RSS may not be filtering by date correctly")
        print(f"   Consider adding additional date filtering in extract_layoff_info")
    print()
else:
    print("✗ No articles found to check dates")

print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)


