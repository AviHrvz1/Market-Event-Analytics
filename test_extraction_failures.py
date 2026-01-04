#!/usr/bin/env python3
"""
Diagnostic test to investigate why extraction fails for 48% of articles
Analyzes each step of the extraction process
"""

import sys
from datetime import datetime, timezone
from main import LayoffTracker
from config import MAX_ARTICLES_TO_PROCESS, LOOKBACK_DAYS

def test_extraction_failures():
    """Investigate why extraction is failing"""
    
    print("=" * 80)
    print("EXTRACTION FAILURE INVESTIGATION")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    event_types = ['bio_companies']
    selected_sources = ['google_news', 'benzinga_news']
    
    # Fetch articles
    print("🔍 Fetching articles...")
    articles, source_stats = tracker.search_all_realtime_sources(
        event_types=event_types, 
        selected_sources=selected_sources
    )
    
    # Sort and limit
    def parse_date(date_str):
        if not date_str:
            return datetime.min.replace(tzinfo=timezone.utc)
        try:
            from dateutil import parser
            return parser.parse(date_str).replace(tzinfo=timezone.utc)
        except:
            return datetime.min.replace(tzinfo=timezone.utc)
    
    articles.sort(key=lambda x: parse_date(x.get('publishedAt', '')), reverse=True)
    if len(articles) > MAX_ARTICLES_TO_PROCESS:
        articles = articles[:MAX_ARTICLES_TO_PROCESS]
    
    print(f"   ✅ Processing {len(articles)} articles")
    print()
    
    # Track failures at each step
    failures = {
        'event_type_mismatch': [],
        'date_out_of_range': [],
        'claude_failed_no_company': [],
        'extract_company_name_failed': [],
        'ticker_lookup_failed': [],
        'no_ticker_private_company': [],
        'ticker_unavailable': [],
        'success': []
    }
    
    print("🔍 Analyzing extraction failures...")
    print()
    
    for i, article in enumerate(articles, 1):
        title = article.get('title', '')
        description = article.get('description', '')
        published_at = article.get('publishedAt', '')
        url = article.get('url', '')
        
        failure_reason = None
        
        # Step 1: Event type matching
        matches_any = False
        if article.get('event_type') in event_types and article.get('source', {}).get('name') == 'Google News':
            matches_any = True
        else:
            for event_type in event_types:
                if tracker.matches_event_type(article, event_type):
                    matches_any = True
                    break
        
        if not matches_any:
            failures['event_type_mismatch'].append({
                'title': title[:80],
                'url': url
            })
            continue
        
        # Step 2: Date filtering
        try:
            article_date = None
            if published_at:
                try:
                    article_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                except:
                    try:
                        from dateutil import parser
                        article_date = parser.parse(published_at)
                    except:
                        pass
            
            if article_date:
                if article_date.tzinfo is None:
                    article_date = article_date.replace(tzinfo=timezone.utc)
                else:
                    article_date = article_date.astimezone(timezone.utc)
                
                now = datetime.now(timezone.utc)
                days_ago = (now - article_date).days
                if days_ago > LOOKBACK_DAYS:
                    failures['date_out_of_range'].append({
                        'title': title[:80],
                        'days_ago': days_ago
                    })
                    continue
        except Exception:
            failures['date_out_of_range'].append({
                'title': title[:80],
                'days_ago': 'parse_error'
            })
            continue
        
        # Step 3: Try Claude extraction
        ai_result = tracker.get_ai_prediction_score(
            title=title,
            description=description,
            url=url
        )
        
        company_name = None
        ticker = None
        
        if ai_result and ai_result.get('company_name'):
            company_name = ai_result.get('company_name')
            ticker = ai_result.get('ticker')
        else:
            # Step 4: Fallback to extract_company_name
            company_name = tracker.extract_company_name(title, description)
            if not company_name:
                failures['extract_company_name_failed'].append({
                    'title': title[:80],
                    'description': description[:100] if description else ''
                })
                continue
            
            # Step 5: Get ticker
            ticker = tracker.get_stock_ticker(company_name)
            if not ticker or ticker == 'N/A':
                failures['ticker_lookup_failed'].append({
                    'title': title[:80],
                    'company_name': company_name
                })
                continue
        
        # Step 6: Check if ticker exists (private company check)
        if not ticker or ticker == 'N/A':
            failures['no_ticker_private_company'].append({
                'title': title[:80],
                'company_name': company_name
            })
            continue
        
        # Step 7: Check ticker availability
        if not tracker._is_ticker_available(ticker):
            failures['ticker_unavailable'].append({
                'title': title[:80],
                'company_name': company_name,
                'ticker': ticker
            })
            continue
        
        # Success!
        failures['success'].append({
            'title': title[:80],
            'company_name': company_name,
            'ticker': ticker
        })
    
    # Print results
    print("=" * 80)
    print("📊 EXTRACTION FAILURE BREAKDOWN")
    print("=" * 80)
    print()
    
    total = len(articles)
    success = len(failures['success'])
    total_failures = total - success
    
    print(f"Total articles processed:     {total:>4}")
    print(f"Successful extractions:       {success:>4} ({success/total*100:.1f}%)")
    print(f"Failed extractions:           {total_failures:>4} ({total_failures/total*100:.1f}%)")
    print()
    
    print("Failure reasons:")
    print()
    
    for reason, items in failures.items():
        if reason == 'success':
            continue
        count = len(items)
        if count > 0:
            pct = count / total * 100
            print(f"  {reason:30} {count:>4} ({pct:>5.1f}%)")
    
    print()
    print("=" * 80)
    print("📋 SAMPLE FAILURES BY REASON")
    print("=" * 80)
    print()
    
    # Show samples of each failure type
    for reason, items in failures.items():
        if reason == 'success' or len(items) == 0:
            continue
        
        print(f"❌ {reason.upper().replace('_', ' ')} ({len(items)} articles):")
        for i, item in enumerate(items[:5], 1):
            if 'title' in item:
                print(f"   {i}. {item['title']}")
                if 'company_name' in item:
                    print(f"      Company: {item['company_name']}")
                if 'ticker' in item:
                    print(f"      Ticker: {item['ticker']}")
                if 'days_ago' in item:
                    print(f"      Days ago: {item['days_ago']}")
        if len(items) > 5:
            print(f"   ... and {len(items) - 5} more")
        print()
    
    # Analyze patterns
    print("=" * 80)
    print("🔍 PATTERN ANALYSIS")
    print("=" * 80)
    print()
    
    # Check extract_company_name failures
    if failures['extract_company_name_failed']:
        print("Articles where extract_company_name() failed:")
        print("  Common patterns:")
        sample_titles = [item['title'] for item in failures['extract_company_name_failed'][:10]]
        
        # Check for common words
        common_words = {}
        for title in sample_titles:
            words = title.upper().split()
            for word in words:
                if len(word) > 3:
                    common_words[word] = common_words.get(word, 0) + 1
        
        print("  Top words in failed titles:")
        for word, count in sorted(common_words.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"    {word}: {count}")
        print()
    
    # Check ticker lookup failures
    if failures['ticker_lookup_failed']:
        print("Articles where ticker lookup failed (company found but no ticker):")
        companies_no_ticker = {}
        for item in failures['ticker_lookup_failed']:
            company = item.get('company_name', 'Unknown')
            companies_no_ticker[company] = companies_no_ticker.get(company, 0) + 1
        
        print("  Companies without tickers:")
        for company, count in sorted(companies_no_ticker.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"    {company}: {count} articles")
        print()
    
    # Summary recommendations
    print("=" * 80)
    print("💡 RECOMMENDATIONS")
    print("=" * 80)
    print()
    
    if failures['extract_company_name_failed']:
        print("1. Improve extract_company_name() method:")
        print("   - Add more pattern matching for bio/pharma companies")
        print("   - Handle company name variations (e.g., 'Incyte' vs 'Incyte Diagnostics')")
        print("   - Improve fuzzy matching for company names")
        print()
    
    if failures['ticker_lookup_failed']:
        print("2. Improve ticker lookup:")
        print("   - Add missing companies to hardcoded list")
        print("   - Improve SEC EDGAR matching")
        print("   - Handle subsidiary companies")
        print()
    
    if failures['ticker_unavailable']:
        print("3. Ticker availability issues:")
        print("   - Check why tickers are marked as unavailable")
        print("   - Review failed_tickers cache")
        print()
    
    return failures

if __name__ == '__main__':
    try:
        failures = test_extraction_failures()
        print("\n✅ Investigation completed")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Investigation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

