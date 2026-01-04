#!/usr/bin/env python3
"""
Full pipeline test for Vistagen Phase 3 article - December 17, 2025
Tests the complete flow from search to final results
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker
from config import LOOKBACK_DAYS, EVENT_TYPES

def test_full_pipeline():
    """Test the complete pipeline for Vistagen article"""
    print("=" * 80)
    print("VISTAGEN FULL PIPELINE TEST")
    print("=" * 80)
    print()
    print("Article: 'Vistagen announced that its Phase 3 trial failed'")
    print("Date: December 17, 2025")
    print("Event Type: bio_companies_small_cap")
    print()
    
    tracker = LayoffTracker()
    
    # Step 1: Search for articles
    print("=" * 80)
    print("STEP 1: Search Google News RSS")
    print("=" * 80)
    print()
    
    event_types = ['bio_companies_small_cap']
    articles, source_stats = tracker.search_all_realtime_sources(
        event_types=event_types,
        selected_sources=['google_news']
    )
    
    print(f"Total articles found: {len(articles)}")
    print(f"Source stats: {source_stats}")
    print()
    
    # Step 2: Filter for Vistagen articles
    print("=" * 80)
    print("STEP 2: Filter for Vistagen articles")
    print("=" * 80)
    print()
    
    vistagen_articles = []
    for article in articles:
        title = article.get('title', '').upper()
        description = article.get('description', '').upper()
        if 'VISTAGEN' in title or 'VISTAGEN' in description or 'VTGN' in title:
            vistagen_articles.append(article)
    
    print(f"Found {len(vistagen_articles)} Vistagen articles")
    print()
    
    if not vistagen_articles:
        print("❌ No Vistagen articles found in search results")
        print("   Checking first 10 articles for reference:")
        for i, article in enumerate(articles[:10], 1):
            print(f"   {i}. {article.get('title', 'No title')[:80]}")
            print(f"      Date: {article.get('publishedAt', 'No date')[:50]}")
        return
    
    # Step 3: Check dates
    print("=" * 80)
    print("STEP 3: Check article dates")
    print("=" * 80)
    print()
    
    target_date = datetime(2025, 12, 17, tzinfo=timezone.utc)
    dec17_articles = []
    
    for article in vistagen_articles:
        pub_date_str = article.get('publishedAt', '')
        print(f"Article: {article.get('title', 'No title')[:60]}")
        print(f"  Published: {pub_date_str}")
        
        if pub_date_str:
            try:
                from dateutil import parser
                parsed_date = parser.parse(pub_date_str)
                if parsed_date.tzinfo is None:
                    parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                else:
                    parsed_date = parsed_date.astimezone(timezone.utc)
                
                days_diff = abs((parsed_date - target_date).days)
                print(f"  Parsed date: {parsed_date}")
                print(f"  Days from Dec 17: {days_diff}")
                
                if days_diff <= 1:
                    dec17_articles.append(article)
                    print(f"  ✅ Within 1 day of target date")
                else:
                    print(f"  ⚠️  More than 1 day from target date")
            except Exception as e:
                print(f"  ❌ Date parsing error: {e}")
        else:
            print(f"  ❌ No date found")
        print()
    
    print(f"Articles from December 17, 2025: {len(dec17_articles)}")
    print()
    
    if not dec17_articles:
        print("❌ No articles found from December 17, 2025")
        return
    
    # Step 4: Test event type matching
    print("=" * 80)
    print("STEP 4: Test event type matching")
    print("=" * 80)
    print()
    
    matching_articles = []
    for article in dec17_articles:
        matches = tracker.matches_event_type(article, 'bio_companies_small_cap')
        if matches:
            matching_articles.append(article)
            print(f"✅ Matches: {article.get('title', 'No title')[:60]}")
        else:
            print(f"❌ Doesn't match: {article.get('title', 'No title')[:60]}")
    
    print(f"\nArticles matching event type: {len(matching_articles)}")
    print()
    
    if not matching_articles:
        print("❌ No articles match event type")
        return
    
    # Step 5: Test company/ticker extraction
    print("=" * 80)
    print("STEP 5: Test company/ticker extraction")
    print("=" * 80)
    print()
    
    extracted_articles = []
    for article in matching_articles:
        print(f"Testing: {article.get('title', 'No title')[:60]}")
        
        # Get candidate companies for bio_companies_small_cap
        bio_companies = tracker._get_bio_pharma_companies(category='small_cap')
        
        # Try to extract company name
        title = article.get('title', '')
        description = article.get('description', '')
        company_name = tracker.extract_company_name(title, description, candidate_companies=bio_companies)
        
        if company_name:
            print(f"  ✅ Company: {company_name}")
            
            # Try to get ticker
            ticker = tracker.company_ticker_cache.get(company_name.upper())
            if not ticker:
                # Try to find ticker
                ticker = tracker._get_ticker_for_company(company_name)
            
            if ticker:
                print(f"  ✅ Ticker: {ticker}")
                article['_test_company'] = company_name
                article['_test_ticker'] = ticker
                extracted_articles.append(article)
            else:
                print(f"  ❌ No ticker found for {company_name}")
        else:
            print(f"  ❌ No company name extracted")
        print()
    
    print(f"Articles with company/ticker: {len(extracted_articles)}")
    print()
    
    if not extracted_articles:
        print("❌ No articles have company/ticker extracted")
        return
    
    # Step 6: Test full extraction
    print("=" * 80)
    print("STEP 6: Test full extraction (extract_layoff_info)")
    print("=" * 80)
    print()
    
    final_articles = []
    for article in extracted_articles:
        print(f"Extracting: {article.get('title', 'No title')[:60]}")
        
        try:
            result = tracker.extract_layoff_info(
                article,
                fetch_content=False,
                event_types=['bio_companies_small_cap']
            )
            
            if result:
                print(f"  ✅ Extraction successful")
                print(f"     Company: {result.get('company_name', 'N/A')}")
                print(f"     Ticker: {result.get('stock_ticker', 'N/A')}")
                print(f"     Date: {result.get('date', 'N/A')}")
                final_articles.append(result)
            else:
                print(f"  ❌ Extraction returned None")
        except Exception as e:
            print(f"  ❌ Extraction error: {e}")
            import traceback
            traceback.print_exc()
        print()
    
    print(f"Final extracted articles: {len(final_articles)}")
    print()
    
    # Step 7: Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"Total articles from search: {len(articles)}")
    print(f"Vistagen articles: {len(vistagen_articles)}")
    print(f"Articles from Dec 17, 2025: {len(dec17_articles)}")
    print(f"Articles matching event type: {len(matching_articles)}")
    print(f"Articles with company/ticker: {len(extracted_articles)}")
    print(f"Final extracted articles: {len(final_articles)}")
    print()
    
    if final_articles:
        print("✅ SUCCESS: Article would be found in the pipeline!")
        print()
        print("Final results:")
        for result in final_articles:
            print(f"  - {result.get('company_name', 'N/A')} ({result.get('stock_ticker', 'N/A')})")
            print(f"    Date: {result.get('date', 'N/A')}")
            print(f"    Title: {result.get('title', 'N/A')[:60]}")
    else:
        print("❌ FAILURE: Article would NOT be found in the pipeline")
        print()
        print("Bottleneck analysis:")
        if len(vistagen_articles) == 0:
            print("  ❌ Step 2: No Vistagen articles in search results")
        elif len(dec17_articles) == 0:
            print("  ❌ Step 3: No articles from December 17, 2025")
        elif len(matching_articles) == 0:
            print("  ❌ Step 4: Articles don't match event type")
        elif len(extracted_articles) == 0:
            print("  ❌ Step 5: Company/ticker extraction failed")
        else:
            print("  ❌ Step 6: Full extraction failed")

if __name__ == '__main__':
    try:
        test_full_pipeline()
        sys.exit(0)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

