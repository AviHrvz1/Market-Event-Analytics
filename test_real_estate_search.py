#!/usr/bin/env python3
"""
Test real estate search functionality
"""

import sys
from main import LayoffTracker
from config import EVENT_TYPES, LOOKBACK_DAYS

print("=" * 80)
print("REAL ESTATE SEARCH TEST")
print("=" * 80)
print()

# Initialize tracker
tracker = LayoffTracker()

# Test 1: Check real estate companies function
print("Test 1: Real Estate Companies Function")
print("-" * 80)
companies = tracker._get_real_estate_companies()
print(f"✓ Found {len(companies)} real estate companies")
print(f"First 10: {companies[:10]}")
print()

# Test 2: Check config
print("Test 2: Event Type Configuration")
print("-" * 80)
for event_type in ['real_estate_good_news', 'real_estate_bad_news']:
    if event_type in EVENT_TYPES:
        config = EVENT_TYPES[event_type]
        print(f"{event_type}:")
        print(f"  query_by_company_names: {config.get('query_by_company_names')}")
        print(f"  keywords: {len(config.get('keywords', []))} keywords")
        print(f"  sic_codes: {config.get('sic_codes')}")
    else:
        print(f"✗ {event_type} NOT FOUND in EVENT_TYPES")
print()

# Test 3: Test search query construction
print("Test 3: Search Query Construction")
print("-" * 80)
event_types = ['real_estate_good_news']
articles, stats = tracker.search_google_news_rss(event_types=event_types)
print(f"✓ Search completed")
print(f"  Articles found: {len(articles)}")
print(f"  Stats: {stats}")
print()

# Test 4: Check if articles have matched_company
print("Test 4: Article Pre-tagging")
print("-" * 80)
if articles:
    print(f"First 5 articles:")
    for i, article in enumerate(articles[:5], 1):
        title = article.get('title', '')[:60]
        matched = article.get('matched_company', 'None')
        event_type = article.get('event_type', 'None')
        print(f"  {i}. {title}...")
        print(f"     Matched Company: {matched}")
        print(f"     Event Type: {event_type}")
else:
    print("✗ No articles found")
    print()
    print("Debugging: Checking search query construction...")
    # Manually test query construction
    from main import EVENT_TYPES as MAIN_EVENT_TYPES
    event_type = 'real_estate_good_news'
    if event_type in MAIN_EVENT_TYPES:
        event_config = MAIN_EVENT_TYPES[event_type]
        if event_config.get('query_by_company_names', False):
            companies = tracker._get_real_estate_companies()
            print(f"  Companies available: {len(companies)}")
            if companies:
                # Test first batch
                company_queries = []
                for company in companies[:5]:
                    company_clean = company.replace('"', '').replace("'", '').strip()
                    if company_clean and len(company_clean) > 2:
                        company_queries.append(f'"{company_clean}"')
                if company_queries:
                    search_query = ' OR '.join(company_queries)
                    print(f"  Sample query (first 5 companies): {search_query}")
                    print(f"  Query length: {len(search_query)} characters")
print()

# Test 5: Try fetching articles directly
print("Test 5: Direct Article Fetch")
print("-" * 80)
try:
    layoffs = tracker.fetch_layoffs(
        event_types=['real_estate_good_news'],
        selected_sources=['google_news'],
        fetch_full_content=False
    )
    print(f"✓ fetch_layoffs completed")
    print(f"  Articles processed: {len(layoffs)}")
    if layoffs:
        print(f"  First article:")
        first = layoffs[0]
        print(f"    Title: {first.get('title', 'N/A')[:60]}...")
        print(f"    Company: {first.get('company_name', 'N/A')}")
        print(f"    Ticker: {first.get('stock_ticker', 'N/A')}")
    else:
        print("  ✗ No articles returned from fetch_layoffs")
except Exception as e:
    print(f"  ✗ Error: {str(e)[:200]}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)

