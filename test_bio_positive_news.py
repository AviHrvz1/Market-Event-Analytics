#!/usr/bin/env python3
"""
Unit test to verify bio positive news event type is finding articles
Tests the updated keywords for bio_positive_news event type
"""

import sys
from datetime import datetime, timezone
from main import LayoffTracker
from config import EVENT_TYPES, LOOKBACK_DAYS

def test_bio_positive_news():
    """Test that bio_positive_news event type finds articles with updated keywords"""
    
    print("=" * 80)
    print("BIO POSITIVE NEWS EVENT TYPE TEST")
    print("=" * 80)
    print()
    
    # Check event type configuration
    print("📋 Event Type Configuration:")
    if 'bio_positive_news' in EVENT_TYPES:
        event_config = EVENT_TYPES['bio_positive_news']
        print(f"  ✅ Event type 'bio_positive_news' exists")
        print(f"  Name: {event_config.get('name', 'N/A')}")
        keywords = event_config.get('keywords', [])
        print(f"  Keywords count: {len(keywords)}")
        print(f"  Sample keywords (first 10):")
        for i, keyword in enumerate(keywords[:10], 1):
            print(f"    {i}. {keyword}")
        if len(keywords) > 10:
            print(f"    ... and {len(keywords) - 10} more")
    else:
        print(f"  ❌ Event type 'bio_positive_news' NOT FOUND")
        return
    print()
    
    # Test keyword matching
    print("🔍 Testing Keyword Matching:")
    tracker = LayoffTracker()
    
    # Sample articles that should match bio_positive_news
    test_articles = [
        {
            'title': 'FDA approves new cancer drug from Moderna',
            'description': 'The FDA has granted approval for Moderna\'s new treatment',
            'expected_match': True,
            'reason': 'Contains "FDA approval"'
        },
        {
            'title': 'Phase 3 trial meets primary endpoint for Vertex',
            'description': 'Vertex Pharmaceuticals announced positive Phase 3 results',
            'expected_match': True,
            'reason': 'Contains "Phase 3 meets primary endpoint"'
        },
        {
            'title': 'Breakthrough Therapy Designation granted to BioNTech',
            'description': 'FDA grants breakthrough therapy designation',
            'expected_match': True,
            'reason': 'Contains "Breakthrough Therapy Designation"'
        },
        {
            'title': 'Gilead receives Fast Track designation',
            'description': 'FDA Fast Track status for new drug',
            'expected_match': True,
            'reason': 'Contains "Fast Track designation"'
        },
        {
            'title': 'Positive topline results from Phase 2 trial',
            'description': 'Company announces positive Phase 2 topline data',
            'expected_match': True,
            'reason': 'Contains "positive topline results"'
        },
        {
            'title': 'Pfizer announces partnership with biotech company',
            'description': 'Major partnership deal announced',
            'expected_match': True,
            'reason': 'Contains "partnership"'
        },
        {
            'title': 'Johnson & Johnson reports earnings',
            'description': 'Company reports quarterly earnings',
            'expected_match': False,
            'reason': 'No bio positive keywords'
        },
        {
            'title': 'Biotech stock price increases',
            'description': 'Stock price goes up',
            'expected_match': False,
            'reason': 'No bio positive keywords'
        }
    ]
    
    matches = 0
    correct_matches = 0
    for article in test_articles:
        matches_event = tracker.matches_event_type(article, 'bio_positive_news')
        expected = article['expected_match']
        status = '✅' if matches_event == expected else '❌'
        if matches_event == expected:
            correct_matches += 1
        if matches_event:
            matches += 1
        
        print(f"  {status} Article: '{article['title'][:50]}...'")
        print(f"     Expected: {expected}, Got: {matches_event}, Reason: {article['reason']}")
    
    print()
    print(f"  Keyword Matching Results: {correct_matches}/{len(test_articles)} correct ({correct_matches*100/len(test_articles):.1f}%)")
    print()
    
    # Test actual Google News search
    print("🔍 Testing Google News Search:")
    print("  Searching for bio_positive_news articles...")
    print("  (This may take 30-60 seconds)")
    print()
    
    try:
        articles, source_stats = tracker.search_all_realtime_sources(
            event_types=['bio_positive_news'],
            selected_sources=['google_news']
        )
        
        print(f"  ✅ Search completed")
        print(f"  Total articles found: {len(articles)}")
        print()
        
        if source_stats.get('google_news'):
            stats = source_stats['google_news']
            print(f"  Google News Statistics:")
            print(f"    Total: {stats.get('total', 0)}")
            print(f"    Matched: {stats.get('matched', 0)}")
            if stats.get('error'):
                print(f"    Error: {stats.get('error')}")
        print()
        
        if articles:
            print(f"  Sample articles found (first 5):")
            for i, article in enumerate(articles[:5], 1):
                title = article.get('title', 'N/A')[:60]
                published = article.get('publishedAt', 'N/A')[:20]
                print(f"    {i}. {title}... ({published})")
            print()
            
            # Check if articles have dates within LOOKBACK_DAYS
            now = datetime.now(timezone.utc)
            articles_within_range = 0
            articles_out_of_range = 0
            
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
                        if days_ago <= (LOOKBACK_DAYS + 5):  # 5 day buffer
                            articles_within_range += 1
                        else:
                            articles_out_of_range += 1
                    except:
                        pass
            
            print(f"  Date Range Check:")
            print(f"    Articles within {LOOKBACK_DAYS} days: {articles_within_range}")
            print(f"    Articles out of range: {articles_out_of_range}")
            print()
        else:
            print(f"  ⚠️  No articles found")
            print(f"  This could mean:")
            print(f"    - No recent bio positive news matching keywords")
            print(f"    - Google News API issue")
            print(f"    - Keywords too restrictive")
            print()
        
    except Exception as e:
        print(f"  ❌ Error during search: {e}")
        import traceback
        traceback.print_exc()
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("Bio Positive News Event Type Test Results:")
    print(f"  ✅ Event type configured: {len(keywords)} keywords")
    print(f"  ✅ Keyword matching: {correct_matches}/{len(test_articles)} correct")
    if articles:
        print(f"  ✅ Google News search: {len(articles)} articles found")
        print(f"  ✅ Articles within date range: {articles_within_range}")
    else:
        print(f"  ⚠️  Google News search: No articles found")
    print()
    print("Expected keywords include:")
    print("  - Phase 3 trial success")
    print("  - FDA approval")
    print("  - Breakthrough Therapy Designation")
    print("  - Fast Track Designation")
    print("  - Priority Review")
    print("  - Positive topline results")
    print("  - Major partnerships/deals")
    print("  - Acquisition/buyout offers")
    print()

if __name__ == '__main__':
    test_bio_positive_news()

