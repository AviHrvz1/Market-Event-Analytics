#!/usr/bin/env python3
"""
Unit test to diagnose why specific bio/pharma companies with significant moves
weren't captured in the system.

Companies to check:
- AMC Robotics Corporation (AMCI) +256.46%
- NovaBay Pharmaceuticals (NBY) +89.29%
- Athira Pharma (ATHA) +80.10%
- Cumberland Pharmaceuticals (CPIX) +74.31%
- Century Therapeutics (IPSC) +61.38%
- Vistagen Therapeutics (VTGN) -81.70%
- Pyxis Oncology (PYXS) -70.35%
- GeoVax Labs (GOVX) -57.52%
"""

import sys
import requests
from bs4 import BeautifulSoup
import urllib.parse
from datetime import datetime, timedelta, timezone
from dateutil import parser
from main import LayoffTracker
from config import EVENT_TYPES, LOOKBACK_DAYS

# Companies to investigate
TEST_COMPANIES = [
    {'name': 'AMC Robotics Corporation', 'ticker': 'AMCI'},
    {'name': 'NovaBay Pharmaceuticals', 'ticker': 'NBY'},
    {'name': 'Athira Pharma', 'ticker': 'ATHA'},
    {'name': 'Cumberland Pharmaceuticals', 'ticker': 'CPIX'},
    {'name': 'Century Therapeutics', 'ticker': 'IPSC'},
    {'name': 'Vistagen Therapeutics', 'ticker': 'VTGN'},
    {'name': 'Pyxis Oncology', 'ticker': 'PYXS'},
    {'name': 'GeoVax Labs', 'ticker': 'GOVX'},
]

def test_1_check_company_in_bio_list():
    """Test 1: Check if companies are in the bio companies list"""
    print("\n" + "="*80)
    print("TEST 1: Checking if companies are in bio companies list")
    print("="*80)
    
    tracker = LayoffTracker()
    bio_companies = tracker._get_bio_pharma_companies()
    
    found = []
    missing = []
    
    for company in TEST_COMPANIES:
        company_upper = company['name'].upper().strip()
        # Check if company name appears in bio list (exact or partial match)
        is_in_list = any(
            company_upper in bio_name or bio_name in company_upper 
            for bio_name in bio_companies
        )
        
        if is_in_list:
            found.append(company)
            print(f"✅ {company['name']} ({company['ticker']}) - FOUND in bio list")
        else:
            missing.append(company)
            print(f"❌ {company['name']} ({company['ticker']}) - NOT in bio list")
    
    print(f"\n📊 Summary: {len(found)} found, {len(missing)} missing")
    return found, missing

def test_2_check_google_news_search():
    """Test 2: Check if Google News can find articles about these companies"""
    print("\n" + "="*80)
    print("TEST 2: Checking Google News search for these companies")
    print("="*80)
    print("Note: Testing by manually constructing Google News RSS queries")
    
    import requests
    from bs4 import BeautifulSoup
    import urllib.parse
    from datetime import datetime, timedelta, timezone
    from dateutil import parser
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    results = {}
    lookback_days = LOOKBACK_DAYS
    
    for company in TEST_COMPANIES:
        print(f"\n🔍 Searching for: {company['name']} ({company['ticker']})")
        
        try:
            # Manually construct Google News RSS query
            query = f'"{company["name"]}"'
            encoded_query = urllib.parse.quote_plus(f"{query} when:{lookback_days}d")
            url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en&num=100"
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'xml')
                items = soup.find_all('item')
                
                articles = []
                for item in items[:10]:
                    title_elem = item.find('title')
                    pub_date_elem = item.find('pubDate')
                    link_elem = item.find('link')
                    
                    if title_elem and title_elem.text:
                        title = title_elem.text.strip()
                        published_at = pub_date_elem.text.strip() if pub_date_elem else ''
                        url_link = link_elem.text.strip() if link_elem else ''
                        
                        articles.append({
                            'title': title,
                            'publishedAt': published_at,
                            'url': url_link
                        })
                
                results[company['ticker']] = {
                    'name': company['name'],
                    'articles_found': len(articles),
                    'articles': articles[:3]
                }
                print(f"   ✅ Found {len(articles)} articles")
                if articles:
                    for i, article in enumerate(articles[:3], 1):
                        print(f"   {i}. {article['title'][:80]}")
                        print(f"      Date: {article['publishedAt']}")
            else:
                results[company['ticker']] = {
                    'name': company['name'],
                    'articles_found': 0,
                    'error': f'HTTP {response.status_code}'
                }
                print(f"   ❌ HTTP Error: {response.status_code}")
        except Exception as e:
            results[company['ticker']] = {
                'name': company['name'],
                'articles_found': 0,
                'error': str(e)
            }
            print(f"   ❌ Error: {e}")
    
    return results

def test_3_check_date_range():
    """Test 3: Check if articles are within the allowed date range"""
    print("\n" + "="*80)
    print("TEST 3: Checking date range filtering")
    print("="*80)
    
    import requests
    from bs4 import BeautifulSoup
    import urllib.parse
    from dateutil import parser
    
    lookback_days = LOOKBACK_DAYS
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    
    print(f"📅 Lookback period: {lookback_days} days")
    print(f"📅 Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"📅 Current date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    results = {}
    
    for company in TEST_COMPANIES:
        print(f"\n🔍 Checking dates for: {company['name']} ({company['ticker']})")
        
        try:
            # Manually construct Google News RSS query
            query = f'"{company["name"]}"'
            encoded_query = urllib.parse.quote_plus(f"{query} when:{lookback_days}d")
            url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en&num=100"
            
            response = requests.get(url, headers=headers, timeout=15)
            
            articles = []
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'xml')
                items = soup.find_all('item')
                
                for item in items[:20]:
                    title_elem = item.find('title')
                    pub_date_elem = item.find('pubDate')
                    
                    if title_elem and title_elem.text:
                        title = title_elem.text.strip()
                        published_at = pub_date_elem.text.strip() if pub_date_elem else ''
                        articles.append({
                            'title': title,
                            'publishedAt': published_at
                        })
            
            if articles:
                # Parse dates and check if within range
                from dateutil import parser
                within_range = []
                outside_range = []
                
                for article in articles:
                    try:
                        pub_date_str = article.get('publishedAt', '')
                        if pub_date_str:
                            pub_date = parser.parse(pub_date_str)
                            if pub_date.tzinfo is None:
                                pub_date = pub_date.replace(tzinfo=timezone.utc)
                            
                            if pub_date >= cutoff_date:
                                within_range.append({
                                    'title': article.get('title', '')[:60],
                                    'date': pub_date.strftime('%Y-%m-%d'),
                                    'days_ago': (datetime.now(timezone.utc) - pub_date).days
                                })
                            else:
                                outside_range.append({
                                    'title': article.get('title', '')[:60],
                                    'date': pub_date.strftime('%Y-%m-%d'),
                                    'days_ago': (datetime.now(timezone.utc) - pub_date).days
                                })
                    except Exception as e:
                        print(f"   ⚠️ Error parsing date: {e}")
                
                results[company['ticker']] = {
                    'within_range': len(within_range),
                    'outside_range': len(outside_range),
                    'within_range_articles': within_range[:3],
                    'outside_range_articles': outside_range[:3]
                }
                
                print(f"   ✅ {len(within_range)} articles within {lookback_days} days")
                print(f"   ❌ {len(outside_range)} articles outside {lookback_days} days")
                
                if within_range:
                    print("   Recent articles:")
                    for art in within_range[:3]:
                        print(f"      - {art['date']} ({art['days_ago']} days ago): {art['title']}")
            else:
                results[company['ticker']] = {'within_range': 0, 'outside_range': 0}
                print(f"   ❌ No articles found")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results[company['ticker']] = {'error': str(e)}
    
    return results

def test_4_check_event_type_matching():
    """Test 4: Check if articles match the bio_companies event type"""
    print("\n" + "="*80)
    print("TEST 4: Checking event type matching")
    print("="*80)
    
    import requests
    from bs4 import BeautifulSoup
    import urllib.parse
    
    tracker = LayoffTracker()
    
    # Get bio_companies event config
    bio_config = EVENT_TYPES.get('bio_companies', {})
    print(f"📋 Bio companies config:")
    print(f"   - Keywords: {bio_config.get('keywords', [])}")
    print(f"   - Query by company names: {bio_config.get('query_by_company_names', False)}")
    print(f"   - SIC codes: {bio_config.get('sic_codes', [])}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    results = {}
    
    for company in TEST_COMPANIES:
        print(f"\n🔍 Testing event matching for: {company['name']} ({company['ticker']})")
        
        try:
            # Manually construct Google News RSS query
            query = f'"{company["name"]}"'
            encoded_query = urllib.parse.quote_plus(f"{query} when:{LOOKBACK_DAYS}d")
            url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en&num=100"
            
            response = requests.get(url, headers=headers, timeout=15)
            
            articles = []
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'xml')
                items = soup.find_all('item')
                
                for item in items[:10]:
                    title_elem = item.find('title')
                    pub_date_elem = item.find('pubDate')
                    link_elem = item.find('link')
                    description_elem = item.find('description')
                    
                    if title_elem and title_elem.text:
                        title = title_elem.text.strip()
                        published_at = pub_date_elem.text.strip() if pub_date_elem else ''
                        url_link = link_elem.text.strip() if link_elem else ''
                        description = description_elem.text.strip() if description_elem else ''
                        
                        articles.append({
                            'title': title,
                            'publishedAt': published_at,
                            'url': url_link,
                            'description': description
                        })
            
            if articles:
                matched = []
                not_matched = []
                
                for article in articles:
                    # Check if article would match bio_companies event type
                    matches = tracker.matches_event_type(article, 'bio_companies')
                    if matches:
                        matched.append({
                            'title': article.get('title', '')[:60],
                            'url': article.get('url', '')[:60]
                        })
                    else:
                        not_matched.append({
                            'title': article.get('title', '')[:60],
                            'url': article.get('url', '')[:60]
                        })
                
                results[company['ticker']] = {
                    'matched': len(matched),
                    'not_matched': len(not_matched),
                    'matched_articles': matched[:3],
                    'not_matched_articles': not_matched[:3]
                }
                
                print(f"   ✅ {len(matched)} articles match bio_companies event type")
                print(f"   ❌ {len(not_matched)} articles don't match")
                
                if matched:
                    print("   Matched articles:")
                    for art in matched[:3]:
                        print(f"      - {art['title']}")
            else:
                results[company['ticker']] = {'matched': 0, 'not_matched': 0}
                print(f"   ❌ No articles found to test")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            results[company['ticker']] = {'error': str(e)}
    
    return results

def test_5_full_fetch_simulation():
    """Test 5: Simulate full fetch_layoffs to see what gets captured"""
    print("\n" + "="*80)
    print("TEST 5: Full fetch simulation")
    print("="*80)
    
    tracker = LayoffTracker()
    
    print("🔄 Running fetch_layoffs with bio_companies event type...")
    print("   (This may take a minute)")
    
    try:
        tracker.fetch_layoffs(
            event_types=['bio_companies'],
            selected_sources=['google_news', 'benzinga_news']
        )
        
        print(f"\n📊 Total layoffs found: {len(tracker.layoffs)}")
        
        # Check if any of our test companies are in the results
        found_companies = []
        for layoff in tracker.layoffs:
            for test_company in TEST_COMPANIES:
                if (test_company['ticker'].upper() == layoff.get('stock_ticker', '').upper() or
                    test_company['name'].upper() in layoff.get('company_name', '').upper()):
                    found_companies.append({
                        'test_company': test_company,
                        'layoff': {
                            'company_name': layoff.get('company_name'),
                            'ticker': layoff.get('stock_ticker'),
                            'date': layoff.get('date'),
                            'title': layoff.get('title', '')[:60],
                            'url': layoff.get('url', '')[:60]
                        }
                    })
        
        print(f"\n✅ Found {len(found_companies)} test companies in results:")
        for item in found_companies:
            print(f"   - {item['test_company']['name']} ({item['test_company']['ticker']})")
            print(f"     Article: {item['layoff']['title']}")
            print(f"     Date: {item['layoff']['date']}")
        
        missing_companies = [
            tc for tc in TEST_COMPANIES 
            if not any(
                tc['ticker'].upper() == item['layoff']['ticker'].upper() or
                tc['name'].upper() in item['layoff']['company_name'].upper()
                for item in found_companies
            )
        ]
        
        print(f"\n❌ Missing {len(missing_companies)} test companies:")
        for company in missing_companies:
            print(f"   - {company['name']} ({company['ticker']})")
        
        return {
            'total_layoffs': len(tracker.layoffs),
            'found_companies': found_companies,
            'missing_companies': missing_companies,
            'source_stats': getattr(tracker, 'source_stats', {})
        }
    except Exception as e:
        print(f"❌ Error during fetch: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}

def main():
    """Run all diagnostic tests"""
    print("\n" + "="*80)
    print("BIO COMPANIES MISSING DIAGNOSIS TEST")
    print("="*80)
    print(f"Testing {len(TEST_COMPANIES)} companies that had significant moves")
    print(f"but weren't captured in the system")
    
    results = {}
    
    # Run all tests
    results['test1'] = test_1_check_company_in_bio_list()
    results['test2'] = test_2_check_google_news_search()
    results['test3'] = test_3_check_date_range()
    results['test4'] = test_4_check_event_type_matching()
    results['test5'] = test_5_full_fetch_simulation()
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY & DIAGNOSIS")
    print("="*80)
    
    found_in_list, missing_from_list = results['test1']
    print(f"\n1. Company List Check:")
    print(f"   - {len(found_in_list)} companies in bio list")
    print(f"   - {len(missing_from_list)} companies NOT in bio list")
    if missing_from_list:
        print(f"   ⚠️ ISSUE: Missing companies won't be searched!")
        for company in missing_from_list:
            print(f"      - {company['name']} ({company['ticker']})")
    
    print(f"\n2. Google News Search:")
    total_articles = sum(r.get('articles_found', 0) for r in results['test2'].values())
    print(f"   - Total articles found: {total_articles}")
    
    print(f"\n3. Date Range Filtering:")
    total_within = sum(r.get('within_range', 0) for r in results['test3'].values() if isinstance(r, dict))
    total_outside = sum(r.get('outside_range', 0) for r in results['test3'].values() if isinstance(r, dict))
    print(f"   - {total_within} articles within {LOOKBACK_DAYS} days")
    print(f"   - {total_outside} articles outside {LOOKBACK_DAYS} days")
    if total_outside > total_within:
        print(f"   ⚠️ ISSUE: Many articles are too old!")
    
    print(f"\n4. Event Type Matching:")
    total_matched = sum(r.get('matched', 0) for r in results['test4'].values() if isinstance(r, dict))
    total_not_matched = sum(r.get('not_matched', 0) for r in results['test4'].values() if isinstance(r, dict))
    print(f"   - {total_matched} articles matched bio_companies event type")
    print(f"   - {total_not_matched} articles didn't match")
    if total_not_matched > total_matched:
        print(f"   ⚠️ ISSUE: Event type matching may be too strict!")
    
    if 'test5' in results and 'total_layoffs' in results['test5']:
        print(f"\n5. Full Fetch Results:")
        print(f"   - Total layoffs captured: {results['test5']['total_layoffs']}")
        print(f"   - Test companies found: {len(results['test5'].get('found_companies', []))}")
        print(f"   - Test companies missing: {len(results['test5'].get('missing_companies', []))}")
    
    print("\n" + "="*80)
    print("RECOMMENDATIONS:")
    print("="*80)
    
    if missing_from_list:
        print("1. ⚠️ Add missing companies to _get_bio_pharma_companies() list")
    
    if total_articles == 0:
        print("2. ⚠️ Google News search may not be finding articles - check query format")
    
    if total_outside > total_within:
        print("3. ⚠️ Consider increasing LOOKBACK_DAYS or check if articles are too recent")
    
    if total_not_matched > total_matched:
        print("4. ⚠️ Review matches_event_type() logic for bio_companies")
    
    print("\n✅ Diagnosis complete!")

if __name__ == '__main__':
    main()

