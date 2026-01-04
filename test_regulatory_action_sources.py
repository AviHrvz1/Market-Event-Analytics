#!/usr/bin/env python3
"""Unit test to check if we can find regulatory action/investigation announcements 
from official sources: SEC, DOJ, OFAC, FINRA, FCA, ESMA, ISA"""

import requests
from datetime import datetime, timedelta
from config import EVENT_TYPES, SEC_EDGAR_BASE_URL, SEC_USER_AGENT
import time

print("=" * 80)
print("Regulatory Action/Investigation Sources Test")
print("=" * 80)
print()

# Test event types related to regulatory actions
REGULATORY_EVENT_TYPES = [
    'regulatory_action',
    'regulatory_investigation',
    'penalty',
    'fine',
    'settlement',
    'litigation',
    'non_compliance'
]

# Official data sources to test
OFFICIAL_SOURCES = {
    'SEC': {
        'name': 'SEC EDGAR',
        'urls': {
            'base': 'https://www.sec.gov',
            'search': 'https://www.sec.gov/cgi-bin/browse-edgar',
            'company_api': 'https://data.sec.gov/submissions',
            'rss': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=&company=&dateb=&owner=include&start=0&count=100&output=atom'
        },
        'keywords': ['sec investigation', 'sec enforcement', 'sec filing', '8-k', '10-k', 'regulatory action'],
        'description': 'SEC EDGAR filings for regulatory disclosures'
    },
    'DOJ': {
        'name': 'Department of Justice',
        'urls': {
            'press_releases': 'https://www.justice.gov/opa/press-releases',
            'rss': 'https://www.justice.gov/opa/rss/press-releases.xml'
        },
        'keywords': ['doj lawsuit', 'doj settlement', 'justice department', 'antitrust', 'enforcement action'],
        'description': 'DOJ press releases on enforcement actions'
    },
    'OFAC': {
        'name': 'Office of Foreign Assets Control',
        'urls': {
            'sanctions': 'https://ofac.treasury.gov/recent-actions',
            'rss': 'https://ofac.treasury.gov/recent-actions/rss'
        },
        'keywords': ['ofac sanctions', 'ofac designation', 'sanctions', 'blocked assets'],
        'description': 'OFAC sanctions and designations'
    },
    'FINRA': {
        'name': 'Financial Industry Regulatory Authority',
        'urls': {
            'disciplinary': 'https://www.finra.org/rules-guidance/oversight-enforcement/finra-disciplinary-actions',
            'rss': 'https://www.finra.org/rules-guidance/oversight-enforcement/finra-disciplinary-actions/rss'
        },
        'keywords': ['finra fine', 'finra disciplinary', 'finra enforcement', 'finra settlement'],
        'description': 'FINRA disciplinary actions and fines'
    },
    'FCA': {
        'name': 'Financial Conduct Authority (UK)',
        'urls': {
            'enforcement': 'https://www.fca.org.uk/news/enforcement',
            'rss': 'https://www.fca.org.uk/news/rss'
        },
        'keywords': ['fca fine', 'fca enforcement', 'fca investigation', 'fca penalty'],
        'description': 'FCA enforcement actions and investigations'
    },
    'ESMA': {
        'name': 'European Securities and Markets Authority',
        'urls': {
            'enforcement': 'https://www.esma.europa.eu/press-news/esma-news',
            'rss': 'https://www.esma.europa.eu/press-news/esma-news/rss'
        },
        'keywords': ['esma fine', 'esma enforcement', 'esma investigation', 'esma penalty'],
        'description': 'ESMA enforcement actions and investigations'
    },
    'ISA': {
        'name': 'Israel Securities Authority',
        'urls': {
            'enforcement': 'https://www.isa.gov.il/en/Enforcement/Pages/default.aspx',
            'rss': None  # May not have RSS
        },
        'keywords': ['isa enforcement', 'isa investigation', 'isa fine', 'isa penalty'],
        'description': 'ISA enforcement actions and investigations'
    }
}

def test_keyword_matching():
    """Test if regulatory action keywords would match articles"""
    print("=" * 80)
    print("TEST 1: Keyword Matching for Regulatory Actions")
    print("=" * 80)
    print()
    
    # Sample article titles/descriptions that should match
    test_articles = [
        {
            'title': 'SEC Investigation into Company X',
            'description': 'The Securities and Exchange Commission has launched an investigation into Company X for potential securities violations.',
            'expected_types': ['regulatory_action', 'regulatory_investigation']
        },
        {
            'title': 'DOJ Files Antitrust Lawsuit Against Tech Giant',
            'description': 'The Department of Justice has filed a lawsuit against a major technology company for antitrust violations.',
            'expected_types': ['regulatory_action', 'litigation']
        },
        {
            'title': 'FINRA Fines Brokerage Firm $5 Million',
            'description': 'FINRA has imposed a $5 million fine on a brokerage firm for compliance violations.',
            'expected_types': ['regulatory_action', 'penalty', 'fine']
        },
        {
            'title': 'Company Settles with SEC for $10 Million',
            'description': 'A company has agreed to pay $10 million to settle SEC enforcement action.',
            'expected_types': ['regulatory_action', 'settlement', 'fine']
        },
        {
            'title': 'OFAC Designates New Sanctions Targets',
            'description': 'The Office of Foreign Assets Control has designated several entities for sanctions.',
            'expected_types': ['regulatory_action']
        },
        {
            'title': 'FCA Investigates Financial Firm',
            'description': 'The Financial Conduct Authority has launched an investigation into a UK financial firm.',
            'expected_types': ['regulatory_action', 'regulatory_investigation']
        },
    ]
    
    results = []
    for article in test_articles:
        title_lower = article['title'].lower()
        desc_lower = article['description'].lower()
        full_text = f"{title_lower} {desc_lower}"
        
        matched_types = []
        for event_type in REGULATORY_EVENT_TYPES:
            if event_type in EVENT_TYPES:
                keywords = EVENT_TYPES[event_type]['keywords']
                if any(keyword.lower() in full_text for keyword in keywords):
                    matched_types.append(event_type)
        
        expected = set(article['expected_types'])
        matched = set(matched_types)
        
        success = len(expected.intersection(matched)) > 0
        results.append({
            'title': article['title'],
            'expected': expected,
            'matched': matched,
            'success': success
        })
        
        status = "✅" if success else "❌"
        print(f"{status} {article['title']}")
        print(f"   Expected: {expected}")
        print(f"   Matched: {matched}")
        if not success:
            print(f"   ⚠️  No matching event types found!")
        print()
    
    passed = sum(1 for r in results if r['success'])
    print(f"Results: {passed}/{len(results)} articles would be matched by current keywords")
    print()
    return passed == len(results)

def test_source_accessibility():
    """Test if we can access official regulatory sources"""
    print("=" * 80)
    print("TEST 2: Source Accessibility Test")
    print("=" * 80)
    print()
    
    headers = {
        'User-Agent': SEC_USER_AGENT,
        'Accept': 'application/rss+xml, application/xml, text/xml, */*',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    
    results = {}
    
    for source_key, source_info in OFFICIAL_SOURCES.items():
        print(f"Testing {source_info['name']}...")
        source_results = {}
        
        for url_name, url in source_info['urls'].items():
            if url is None:
                source_results[url_name] = {'accessible': False, 'reason': 'No URL provided'}
                continue
            
            try:
                # Try to access the URL
                response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
                
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')
                    content_length = len(response.content)
                    
                    source_results[url_name] = {
                        'accessible': True,
                        'status_code': response.status_code,
                        'content_type': content_type,
                        'content_length': content_length,
                        'is_rss': 'rss' in content_type.lower() or 'xml' in content_type.lower() or url.endswith('.xml') or url.endswith('/rss')
                    }
                    print(f"  ✅ {url_name}: Accessible (Status: {response.status_code}, Size: {content_length} bytes)")
                elif response.status_code == 403:
                    source_results[url_name] = {
                        'accessible': False,
                        'reason': 'Forbidden (403) - May require authentication or have access restrictions'
                    }
                    print(f"  ⚠️  {url_name}: Forbidden (403)")
                elif response.status_code == 404:
                    source_results[url_name] = {
                        'accessible': False,
                        'reason': 'Not Found (404)'
                    }
                    print(f"  ❌ {url_name}: Not Found (404)")
                else:
                    source_results[url_name] = {
                        'accessible': False,
                        'reason': f'HTTP {response.status_code}'
                    }
                    print(f"  ⚠️  {url_name}: HTTP {response.status_code}")
                
                # Be respectful - don't hammer the servers
                time.sleep(1)
                
            except requests.exceptions.Timeout:
                source_results[url_name] = {
                    'accessible': False,
                    'reason': 'Timeout'
                }
                print(f"  ❌ {url_name}: Timeout")
            except requests.exceptions.ConnectionError:
                source_results[url_name] = {
                    'accessible': False,
                    'reason': 'Connection Error'
                }
                print(f"  ❌ {url_name}: Connection Error")
            except Exception as e:
                source_results[url_name] = {
                    'accessible': False,
                    'reason': f'Error: {str(e)[:50]}'
                }
                print(f"  ❌ {url_name}: {str(e)[:50]}")
        
        results[source_key] = source_results
        print()
    
    return results

def test_rss_feed_parsing():
    """Test if we can parse RSS feeds from regulatory sources"""
    print("=" * 80)
    print("TEST 3: RSS Feed Parsing Test")
    print("=" * 80)
    print()
    
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("❌ BeautifulSoup not available. Install with: pip install beautifulsoup4")
        return {}
    
    headers = {
        'User-Agent': SEC_USER_AGENT,
        'Accept': 'application/rss+xml, application/xml, text/xml, */*'
    }
    
    results = {}
    
    # Test RSS feeds that are likely to work
    rss_sources = [
        ('DOJ', OFFICIAL_SOURCES['DOJ']['urls'].get('rss')),
        ('FINRA', OFFICIAL_SOURCES['FINRA']['urls'].get('rss')),
        ('FCA', OFFICIAL_SOURCES['FCA']['urls'].get('rss')),
        ('ESMA', OFFICIAL_SOURCES['ESMA']['urls'].get('rss')),
        ('OFAC', OFFICIAL_SOURCES['OFAC']['urls'].get('rss')),
    ]
    
    for source_name, rss_url in rss_sources:
        if not rss_url:
            continue
        
        print(f"Testing {source_name} RSS feed...")
        try:
            response = requests.get(rss_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'xml')
                items = soup.find_all('item')
                
                if items:
                    # Check first few items for regulatory keywords
                    regulatory_matches = 0
                    sample_titles = []
                    
                    for item in items[:10]:  # Check first 10 items
                        title_elem = item.find('title')
                        desc_elem = item.find('description')
                        
                        if title_elem:
                            title = title_elem.text.strip() if title_elem.text else ''
                            description = desc_elem.text.strip() if desc_elem and desc_elem.text else ''
                            full_text = f"{title.lower()} {description.lower()}"
                            
                            # Check if it matches any regulatory keywords
                            for event_type in REGULATORY_EVENT_TYPES:
                                if event_type in EVENT_TYPES:
                                    keywords = EVENT_TYPES[event_type]['keywords']
                                    if any(keyword.lower() in full_text for keyword in keywords):
                                        regulatory_matches += 1
                                        if len(sample_titles) < 3:
                                            sample_titles.append(title[:80])
                                        break
                    
                    results[source_name] = {
                        'accessible': True,
                        'total_items': len(items),
                        'regulatory_matches': regulatory_matches,
                        'sample_titles': sample_titles
                    }
                    
                    print(f"  ✅ Found {len(items)} items, {regulatory_matches} match regulatory keywords")
                    if sample_titles:
                        print(f"  Sample titles:")
                        for title in sample_titles:
                            print(f"    - {title}")
                else:
                    results[source_name] = {
                        'accessible': True,
                        'total_items': 0,
                        'regulatory_matches': 0
                    }
                    print(f"  ⚠️  RSS feed accessible but no items found")
            else:
                results[source_name] = {
                    'accessible': False,
                    'reason': f'HTTP {response.status_code}'
                }
                print(f"  ❌ HTTP {response.status_code}")
            
            time.sleep(1)  # Be respectful
            
        except Exception as e:
            results[source_name] = {
                'accessible': False,
                'reason': str(e)[:50]
            }
            print(f"  ❌ Error: {str(e)[:50]}")
        
        print()
    
    return results

def test_sec_edgar_search():
    """Test SEC EDGAR search capabilities"""
    print("=" * 80)
    print("TEST 4: SEC EDGAR Search Test")
    print("=" * 80)
    print()
    
    headers = {
        'User-Agent': SEC_USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    
    # Test searching for recent 8-K filings (which often contain regulatory disclosures)
    search_url = 'https://www.sec.gov/cgi-bin/browse-edgar'
    params = {
        'action': 'getcurrent',
        'type': '8-K',  # Current reports (often contain regulatory actions)
        'count': '10'
    }
    
    try:
        response = requests.get(search_url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ SEC EDGAR search accessible")
            print(f"   URL: {response.url}")
            print(f"   Content length: {len(response.content)} bytes")
            
            # Check if response contains regulatory keywords
            content_lower = response.text.lower()
            regulatory_keywords_found = []
            
            for event_type in REGULATORY_EVENT_TYPES:
                if event_type in EVENT_TYPES:
                    keywords = EVENT_TYPES[event_type]['keywords']
                    for keyword in keywords:
                        if keyword.lower() in content_lower:
                            regulatory_keywords_found.append(keyword)
                            break
            
            if regulatory_keywords_found:
                print(f"   ✅ Found regulatory keywords: {', '.join(regulatory_keywords_found[:5])}")
            else:
                print(f"   ⚠️  No regulatory keywords found in response")
            
            return True
        else:
            print(f"❌ SEC EDGAR search returned HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error accessing SEC EDGAR: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("Testing regulatory action/investigation sources...")
    print("This test checks if we can find regulatory announcements from official sources.")
    print()
    
    # Test 1: Keyword matching
    keyword_test_passed = test_keyword_matching()
    print()
    
    # Test 2: Source accessibility
    accessibility_results = test_source_accessibility()
    print()
    
    # Test 3: RSS feed parsing
    rss_results = test_rss_feed_parsing()
    print()
    
    # Test 4: SEC EDGAR search
    sec_test_passed = test_sec_edgar_search()
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    print("1. Keyword Matching:")
    print(f"   {'✅ PASS' if keyword_test_passed else '❌ FAIL'} - Regulatory keywords would match articles")
    print()
    
    print("2. Source Accessibility:")
    accessible_count = 0
    for source_key, source_results in accessibility_results.items():
        accessible = any(r.get('accessible', False) for r in source_results.values())
        if accessible:
            accessible_count += 1
            print(f"   ✅ {source_key}: At least one endpoint accessible")
        else:
            print(f"   ❌ {source_key}: No accessible endpoints")
    print(f"   Total: {accessible_count}/{len(accessibility_results)} sources have accessible endpoints")
    print()
    
    print("3. RSS Feed Parsing:")
    if rss_results:
        rss_accessible = sum(1 for r in rss_results.values() if r.get('accessible', False))
        total_regulatory = sum(r.get('regulatory_matches', 0) for r in rss_results.values())
        print(f"   {rss_accessible}/{len(rss_results)} RSS feeds accessible")
        print(f"   {total_regulatory} articles found matching regulatory keywords")
    else:
        print("   ⚠️  No RSS feeds tested")
    print()
    
    print("4. SEC EDGAR Search:")
    print(f"   {'✅ PASS' if sec_test_passed else '❌ FAIL'} - SEC EDGAR search accessible")
    print()
    
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()
    print("Based on test results:")
    print("1. Consider adding RSS feeds from DOJ, FINRA, FCA, ESMA, OFAC to the main RSS sources list")
    print("2. SEC EDGAR can be searched for 8-K filings containing regulatory disclosures")
    print("3. Current keyword matching should work for regulatory action articles")
    print("4. Some sources may require specific API keys or have rate limits")
    print()

if __name__ == '__main__':
    main()

