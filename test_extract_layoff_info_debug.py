#!/usr/bin/env python3
"""
Debug test to see why extract_layoff_info returns None for most articles
"""

import sys
from datetime import datetime, timezone
from main import LayoffTracker
from config import LOOKBACK_DAYS

def test_extract_debug():
    """Debug extract_layoff_info to see why it returns None"""
    
    print("=" * 80)
    print("DEBUG: extract_layoff_info")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    event_types = ['bio_positive_news']
    selected_sources = ['google_news']
    
    # Fetch articles using the same method as fetch_layoffs
    # We'll simulate by calling fetch_layoffs and then checking what happened
    tracker.fetch_layoffs(fetch_full_content=False, event_types=event_types, selected_sources=selected_sources)
    
    # Get the source stats to see how many were retrieved
    print(f"Articles in tracker.layoffs: {len(tracker.layoffs)}")
    if hasattr(tracker, 'source_stats'):
        for key, stats in tracker.source_stats.items():
            print(f"  {stats['name']}: {stats['total']} total, {stats['matched']} matched")
    print()
    
    # We can't easily get the raw articles, so let's just analyze what we have
    articles = []  # We'll work with what we have
    
    print(f"Total articles fetched: {len(articles)}")
    print(f"LOOKBACK_DAYS: {LOOKBACK_DAYS}")
    print()
    
    # Test extract_layoff_info on each article
    results = {
        'returned_info': 0,
        'returned_none': 0,
        'no_event_match': 0,
        'date_filtered': 0,
        'other_reason': 0
    }
    
    sample_filtered = []
    
    for i, article in enumerate(articles[:20]):  # Test first 20
        title = article.get('title', '')[:60]
        
        # Check event matching
        matches_any = False
        if article.get('event_type') in event_types and article.get('source', {}).get('name') == 'Google News':
            matches_any = True
        else:
            for event_type in event_types:
                if tracker.matches_event_type(article, event_type):
                    matches_any = True
                    break
        
        if not matches_any:
            results['no_event_match'] += 1
            if len(sample_filtered) < 3:
                sample_filtered.append({'title': title, 'reason': 'no_event_match'})
            continue
        
        # Check date filtering
        published_at = article.get('publishedAt', '')
        date_filtered = False
        if published_at:
            try:
                from dateutil import parser
                article_date = parser.parse(published_at)
                if article_date.tzinfo is None:
                    article_date = article_date.replace(tzinfo=timezone.utc)
                else:
                    article_date = article_date.astimezone(timezone.utc)
                
                now = datetime.now(timezone.utc)
                days_ago = (now - article_date).days
                
                if days_ago > (LOOKBACK_DAYS + 5):
                    date_filtered = True
                    results['date_filtered'] += 1
                    if len(sample_filtered) < 3:
                        sample_filtered.append({'title': title, 'reason': f'date_filtered ({days_ago} days ago)'})
            except Exception as e:
                pass
        
        # Try extract_layoff_info
        layoff_info = tracker.extract_layoff_info(article, fetch_content=False, event_types=event_types)
        
        if layoff_info:
            results['returned_info'] += 1
        else:
            results['returned_none'] += 1
            if not date_filtered and len(sample_filtered) < 3:
                sample_filtered.append({'title': title, 'reason': 'extract_layoff_info returned None'})
    
    print("Results (first 20 articles):")
    print(f"  Returned info: {results['returned_info']}")
    print(f"  Returned None: {results['returned_none']}")
    print(f"  No event match: {results['no_event_match']}")
    print(f"  Date filtered: {results['date_filtered']}")
    print()
    
    if sample_filtered:
        print("Sample filtered articles:")
        for item in sample_filtered:
            print(f"  - {item['title']}... ({item['reason']})")
    print()
    
    # Check date range of articles
    print("Date range of articles:")
    dates = []
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
                
                now = datetime.now(timezone.utc)
                days_ago = (now - article_date).days
                dates.append(days_ago)
            except:
                pass
    
    if dates:
        print(f"  Min days ago: {min(dates)}")
        print(f"  Max days ago: {max(dates)}")
        print(f"  Avg days ago: {sum(dates)/len(dates):.1f}")
        print(f"  Articles within {LOOKBACK_DAYS + 5} days: {sum(1 for d in dates if d <= LOOKBACK_DAYS + 5)}")
        print(f"  Articles outside {LOOKBACK_DAYS + 5} days: {sum(1 for d in dates if d > LOOKBACK_DAYS + 5)}")

if __name__ == '__main__':
    test_extract_debug()

