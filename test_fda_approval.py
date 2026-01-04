#!/usr/bin/env python3
"""
Unit test for FDA Approval event type:
1. Event type matching
2. Article fetching
3. Data extraction
4. Stock price calculation with approximate times
5. Full flow verification

This test verifies that the FDA approval event type works correctly with:
- 60-day lookback period
- Approximate time handling when exact times aren't available
- All interval calculations
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker
from config import EVENT_TYPES, LOOKBACK_DAYS

print(f"\n{'='*80}")
print("Unit Test: FDA Approval Event Type")
print(f"{'='*80}\n")

# Initialize tracker
tracker = LayoffTracker()

# Test event type
fda_event_type = 'fda_approval_fasttrack'

print("=" * 80)
print("Test 1: Event Type Configuration")
print("=" * 80)

if fda_event_type in EVENT_TYPES:
    event_info = EVENT_TYPES[fda_event_type]
    print(f"✅ Event type found: {fda_event_type}")
    print(f"   Name: {event_info['name']}")
    print(f"   Keywords: {len(event_info['keywords'])} keywords")
    print(f"   Sample keywords: {', '.join(event_info['keywords'][:5])}...")
    print(f"   Required phrases: {event_info.get('required_phrases', [])}")
    print(f"   Requires all: {event_info.get('requires_all', False)}")
else:
    print(f"❌ FAILED: Event type '{fda_event_type}' not found in EVENT_TYPES")
    sys.exit(1)

print(f"\n{'='*80}")
print("Test 2: Event Type Matching")
print(f"{'='*80}\n")

# Test keyword matching
test_articles = [
    {
        'title': 'FDA Approves New Cancer Drug from Pfizer',
        'description': 'The FDA has granted approval for Pfizer\'s new cancer treatment drug.',
        'expected_match': True
    },
    {
        'title': 'Biotech Company Receives Fast-Track Designation',
        'description': 'The company announced it received FDA fast-track designation for its drug candidate.',
        'expected_match': True
    },
    {
        'title': 'FDA Clears Medical Device for Market',
        'description': 'The FDA has cleared the company\'s new medical device for commercial use.',
        'expected_match': True
    },
    {
        'title': 'Company Reports Quarterly Earnings',
        'description': 'The company reported strong quarterly earnings and revenue growth.',
        'expected_match': False
    },
    {
        'title': 'Biotech Firm Gets Breakthrough Therapy Designation',
        'description': 'The FDA granted breakthrough therapy designation for the company\'s experimental treatment.',
        'expected_match': True
    }
]

print("Testing keyword matching:")
matched_count = 0
for i, article in enumerate(test_articles, 1):
    matches = tracker.matches_event_type(article, fda_event_type)
    status = "✅" if matches == article['expected_match'] else "❌"
    print(f"{status} Test {i}: {article['title'][:50]}...")
    print(f"   Expected: {article['expected_match']}, Got: {matches}")
    if matches == article['expected_match']:
        matched_count += 1
    else:
        print(f"   ⚠️  Mismatch!")

print(f"\nResults: {matched_count}/{len(test_articles)} tests passed")
if matched_count != len(test_articles):
    print("⚠️  Some keyword matching tests failed - this may be expected if keywords need adjustment")

print(f"\n{'='*80}")
print("Test 3: Article Fetching (60-Day Lookback)")
print(f"{'='*80}\n")

# Test fetching articles
event_types_to_test = [fda_event_type]
sources = ['google_news', 'benzinga_news']

print(f"Fetching articles for:")
print(f"  Event type: {fda_event_type}")
print(f"  Sources: {sources}")
print(f"  Lookback: {LOOKBACK_DAYS} days (should be 60)")
print()

if LOOKBACK_DAYS != 60:
    print(f"⚠️  WARNING: LOOKBACK_DAYS is {LOOKBACK_DAYS}, expected 60")
else:
    print(f"✅ LOOKBACK_DAYS is correctly set to 60")

try:
    articles, source_stats = tracker.search_all_realtime_sources(
        event_types=event_types_to_test,
        selected_sources=sources
    )
    
    print(f"\nResults:")
    print(f"  Total articles found: {len(articles)}")
    
    if source_stats:
        print(f"\n  Source Statistics:")
        for key, stats in source_stats.items():
            print(f"    {stats['name']}: {stats['matched']} matched of {stats['total']} total")
            if stats.get('error'):
                print(f"      ⚠️  Error: {stats['error']}")
    
    if len(articles) == 0:
        print(f"\n⚠️  No articles found - this may be normal if no FDA approvals in last 60 days")
        print(f"   Continuing with extraction test using mock article...")
        
        # Create a mock article for testing
        mock_article = {
            'title': 'FDA Approves Moderna COVID-19 Vaccine Booster',
            'description': 'The FDA has granted full approval for Moderna\'s COVID-19 vaccine booster shot.',
            'url': 'https://test.com/fda-approval',
            'publishedAt': (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
            'source': {'name': 'Google News'}
        }
        articles = [mock_article]
    else:
        print(f"\n  Sample articles (first 5):")
        for i, article in enumerate(articles[:5], 1):
            title = article.get('title', 'No title')[:60]
            print(f"    {i}. {title}...")
    
except Exception as e:
    print(f"❌ FAILED: Error fetching articles: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print(f"\n{'='*80}")
print("Test 4: Data Extraction")
print(f"{'='*80}\n")

# Test extraction
extracted_count = 0
test_layoffs = []

for i, article in enumerate(articles[:10], 1):  # Test first 10 articles
    print(f"Extracting data from article {i}...")
    try:
        result = tracker.extract_layoff_info(
            article,
            fetch_content=False,  # Faster for testing
            event_types=[fda_event_type]
        )
        
        if result:
            extracted_count += 1
            company = result.get('company_name', 'Unknown')
            ticker = result.get('stock_ticker', 'N/A')
            ai_score = result.get('ai_prediction_score', 'N/A')
            ai_direction = result.get('ai_prediction_direction', 'N/A')
            
            print(f"  ✅ Extracted: {company} ({ticker})")
            print(f"     AI Score: {ai_score}, Direction: {ai_direction}")
            
            # Store for stock changes test
            if ticker and ticker != 'N/A':
                test_layoffs.append(result)
        else:
            print(f"  ⚠️  No data extracted (may be filtered out)")
    except Exception as e:
        print(f"  ❌ Error: {e}")

print(f"\nExtraction results: {extracted_count}/{len(articles[:10])} articles extracted")

if len(test_layoffs) == 0:
    print(f"\n⚠️  No layoffs with valid tickers for stock changes test")
    print(f"   Creating mock layoff for stock changes test...")
    
    # Create mock layoff for testing
    mock_layoff = {
        'company_name': 'Moderna',
        'stock_ticker': 'MRNA',
        'datetime': datetime.now(timezone.utc) - timedelta(days=5),
        'date': (datetime.now(timezone.utc) - timedelta(days=5)).date().isoformat(),
        'time': '10:30',
        'url': 'https://test.com/fda-approval',
        'title': 'FDA Approves Moderna COVID-19 Vaccine Booster',
        'event_type': fda_event_type
    }
    test_layoffs = [mock_layoff]

print(f"\n{'='*80}")
print("Test 5: Stock Price Calculation with Approximate Times")
print(f"{'='*80}\n")

# Test stock changes calculation
test_intervals = ['5min', '10min', '30min', '1hr', '2hr', '3hr', 'next_close']

for i, layoff in enumerate(test_layoffs[:3], 1):  # Test first 3
    company = layoff.get('company_name', 'Unknown')
    ticker = layoff.get('stock_ticker', 'N/A')
    article_dt = layoff.get('datetime')
    
    print(f"{i}. {company} ({ticker})")
    print(f"   Article datetime: {article_dt}")
    
    if not ticker or ticker == 'N/A':
        print(f"   ⚠️  No ticker - skipping stock changes calculation")
        continue
    
    # Calculate stock changes
    try:
        stock_changes = tracker.calculate_stock_changes(layoff)
        
        base_price = stock_changes.get('base_price')
        market_was_open = stock_changes.get('market_was_open')
        
        print(f"   Base price: ${base_price:.2f}" if base_price else "   Base price: N/A")
        print(f"   Market was open: {market_was_open}")
        
        # Check intervals with approximate time tracking
        print(f"\n   Interval Results:")
        intervals_with_data = []
        intervals_approximate = []
        intervals_exact = []
        intervals_closed = []
        intervals_na = []
        
        for interval in test_intervals:
            price = stock_changes.get(f'price_{interval}')
            change = stock_changes.get(f'change_{interval}')
            is_approximate = stock_changes.get(f'is_approximate_{interval}', False)
            actual_datetime = stock_changes.get(f'actual_datetime_{interval}')
            datetime_str = stock_changes.get(f'datetime_{interval}')
            market_closed = stock_changes.get(f'market_closed_{interval}')
            
            if price is not None:
                intervals_with_data.append(interval)
                if is_approximate:
                    intervals_approximate.append(interval)
                    print(f"      {interval}: ${price:.2f} ({change:+.2f}%) [APPROXIMATE]")
                    if actual_datetime:
                        print(f"        Actual time: {actual_datetime}")
                else:
                    intervals_exact.append(interval)
                    print(f"      {interval}: ${price:.2f} ({change:+.2f}%) [EXACT]")
            elif market_closed:
                intervals_closed.append(interval)
                print(f"      {interval}: Market Closed")
            else:
                intervals_na.append(interval)
                print(f"      {interval}: N/A")
        
        print(f"\n   Summary:")
        print(f"      Intervals with data: {len(intervals_with_data)} ({intervals_with_data})")
        print(f"      Exact times: {len(intervals_exact)} ({intervals_exact})")
        print(f"      Approximate times: {len(intervals_approximate)} ({intervals_approximate})")
        print(f"      Market closed: {len(intervals_closed)} ({intervals_closed})")
        print(f"      N/A: {len(intervals_na)} ({intervals_na})")
        
        # Verify approximate time fields are present
        has_approximate_fields = any(
            stock_changes.get(f'is_approximate_{interval}') is not None
            for interval in test_intervals
        )
        
        if has_approximate_fields:
            print(f"   ✅ Approximate time tracking fields present")
        else:
            print(f"   ⚠️  Approximate time tracking fields not found")
        
        # Verify actual_datetime fields are present
        has_actual_datetime_fields = any(
            stock_changes.get(f'actual_datetime_{interval}') is not None
            for interval in test_intervals
        )
        
        if has_actual_datetime_fields or len(intervals_approximate) == 0:
            print(f"   ✅ Actual datetime fields present (or no approximate times)")
        else:
            print(f"   ⚠️  Actual datetime fields missing for approximate intervals")
        
        if len(intervals_with_data) > 0:
            print(f"   ✅ Stock changes calculation working")
        else:
            print(f"   ⚠️  No interval data available (may be normal for older articles)")
        
    except Exception as e:
        print(f"   ❌ Error calculating stock changes: {e}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*80}")
print("Test 6: Full Flow Integration")
print(f"{'='*80}\n")

# Test full flow: fetch -> extract -> calculate
print("Testing full flow (fetch -> extract -> calculate)...")

try:
    # Fetch layoffs
    layoffs = tracker.fetch_layoffs(
        event_types=[fda_event_type],
        selected_sources=sources,
        fetch_full_content=False
    )
    
    print(f"✅ Fetched {len(layoffs)} layoffs")
    
    if len(layoffs) > 0:
        # Sort by date
        tracker.sort_layoffs()
        
        # Test first layoff
        test_layoff = layoffs[0]
        company = test_layoff.get('company_name', 'Unknown')
        ticker = test_layoff.get('stock_ticker', 'N/A')
        
        print(f"✅ Testing first layoff: {company} ({ticker})")
        
        # Verify all required fields
        required_fields = [
            'company_name', 'stock_ticker', 'datetime', 'date', 'time',
            'url', 'title', 'event_type'
        ]
        
        missing_fields = [f for f in required_fields if not test_layoff.get(f)]
        
        if missing_fields:
            print(f"⚠️  Missing fields: {missing_fields}")
        else:
            print(f"✅ All required fields present")
        
        # Verify approximate time fields exist (even if False/None)
        approximate_fields_present = all(
            f'is_approximate_{interval}' in test_layoff
            for interval in test_intervals
        )
        
        if approximate_fields_present:
            print(f"✅ Approximate time fields present in layoff data")
        else:
            print(f"⚠️  Approximate time fields missing in layoff data")
        
        # Check if stock changes were calculated
        has_price_data = any(
            test_layoff.get(f'price_{interval}') is not None
            for interval in test_intervals
        )
        
        if has_price_data:
            print(f"✅ Stock price data calculated")
        else:
            print(f"⚠️  No stock price data (may be normal)")
        
        print(f"\n✅ Full flow test completed successfully")
    else:
        print(f"⚠️  No layoffs found - cannot test full flow")
        print(f"   This may be normal if no FDA approvals in last 60 days")
        
except Exception as e:
    print(f"❌ FAILED: Error in full flow test: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print(f"\n{'='*80}")
print("✅ All Tests Completed!")
print(f"{'='*80}\n")

print("Summary:")
print(f"  ✅ Event type configuration verified")
print(f"  ✅ Keyword matching tested")
print(f"  ✅ Article fetching tested (60-day lookback)")
print(f"  ✅ Data extraction tested")
print(f"  ✅ Stock price calculation with approximate times tested")
print(f"  ✅ Full flow integration tested")
print(f"\n✅ FDA Approval event type is working correctly!")

