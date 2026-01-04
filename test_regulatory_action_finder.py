#!/usr/bin/env python3
"""Unit test to check if we can find regulatory action/investigation announcements 
from official sources: SEC, DOJ, OFAC, FINRA, FCA, ESMA, ISA

This test checks if these sources can help find regulatory action articles that
the current system might be missing.
"""

import requests
from datetime import datetime, timedelta
from config import EVENT_TYPES, SEC_USER_AGENT
import time
import re

print("=" * 80)
print("Regulatory Action/Investigation Finder Test")
print("=" * 80)
print()
print("Testing if official sources (SEC, DOJ, OFAC, FINRA, FCA, ESMA, ISA)")
print("can help find regulatory action/investigation announcements")
print()

# Official data sources with RSS feeds
OFFICIAL_SOURCES = {
    'SEC': {
        'name': 'SEC EDGAR',
        'rss_url': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=&company=&dateb=&owner=include&start=0&count=100&output=atom',
        'keywords': ['sec investigation', 'sec enforcement', 'regulatory action', '8-k', '10-k'],
        'description': 'SEC EDGAR filings for regulatory disclosures'
    },
    'DOJ': {
        'name': 'Department of Justice',
        'rss_url': 'https://www.justice.gov/opa/rss/press-releases.xml',
        'keywords': ['doj lawsuit', 'doj settlement', 'justice department', 'antitrust', 'enforcement action'],
        'description': 'DOJ press releases on enforcement actions'
    },
    'OFAC': {
        'name': 'Office of Foreign Assets Control',
        'rss_url': 'https://ofac.treasury.gov/recent-actions/rss',
        'keywords': ['ofac sanctions', 'ofac designation', 'sanctions', 'blocked assets'],
        'description': 'OFAC sanctions and designations'
    },
    'FINRA': {
        'name': 'Financial Industry Regulatory Authority',
        'rss_url': 'https://www.finra.org/rules-guidance/oversight-enforcement/finra-disciplinary-actions/rss',
        'keywords': ['finra fine', 'finra disciplinary', 'finra enforcement', 'finra settlement'],
        'description': 'FINRA disciplinary actions and fines'
    },
    'FCA': {
        'name': 'Financial Conduct Authority (UK)',
        'rss_url': 'https://www.fca.org.uk/news/rss',
        'keywords': ['fca fine', 'fca enforcement', 'fca investigation', 'fca penalty'],
        'description': 'FCA enforcement actions and investigations'
    },
    'ESMA': {
        'name': 'European Securities and Markets Authority',
        'rss_url': 'https://www.esma.europa.eu/press-news/esma-news/rss',
        'keywords': ['esma fine', 'esma enforcement', 'esma investigation', 'esma penalty'],
        'description': 'ESMA enforcement actions and investigations'
    },
    'ISA': {
        'name': 'Israel Securities Authority',
        'rss_url': None,  # May not have RSS
        'keywords': ['isa enforcement', 'isa investigation', 'isa fine', 'isa penalty'],
        'description': 'ISA enforcement actions and investigations'
    }
}

# Get regulatory action event type keywords
REGULATORY_EVENT_TYPES = ['regulatory_action', 'regulatory_investigation', 'penalty', 'fine', 'settlement', 'litigation']
REGULATORY_KEYWORDS = set()
for event_type in REGULATORY_EVENT_TYPES:
    if event_type in EVENT_TYPES:
        REGULATORY_KEYWORDS.update([kw.lower() for kw in EVENT_TYPES[event_type]['keywords']])

print(f"Testing with {len(REGULATORY_KEYWORDS)} regulatory keywords from event types:")
print(f"  {', '.join(REGULATORY_EVENT_TYPES)}")
print()

def test_rss_feed_for_regulatory_articles(source_key, source_info):
    """Test if RSS feed contains articles matching regulatory action keywords"""
    if not source_info['rss_url']:
        return {
            'source': source_key,
            'accessible': False,
            'reason': 'No RSS URL provided',
            'articles_found': 0,
            'regulatory_matches': 0,
            'sample_articles': []
        }
    
    headers = {
        'User-Agent': SEC_USER_AGENT,
        'Accept': 'application/rss+xml, application/xml, text/xml, */*'
    }
    
    try:
        response = requests.get(source_info['rss_url'], headers=headers, timeout=15, allow_redirects=True)
        
        if response.status_code != 200:
            return {
                'source': source_key,
                'accessible': False,
                'reason': f'HTTP {response.status_code}',
                'articles_found': 0,
                'regulatory_matches': 0,
                'sample_articles': []
            }
        
        # Parse RSS feed
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return {
                'source': source_key,
                'accessible': False,
                'reason': 'BeautifulSoup not available',
                'articles_found': 0,
                'regulatory_matches': 0,
                'sample_articles': []
            }
        
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')
        
        if not items:
            return {
                'source': source_key,
                'accessible': True,
                'reason': 'No items in RSS feed',
                'articles_found': 0,
                'regulatory_matches': 0,
                'sample_articles': []
            }
        
        # Check each item for regulatory keywords
        regulatory_matches = []
        for item in items:
            title_elem = item.find('title')
            desc_elem = item.find('description')
            link_elem = item.find('link')
            pubdate_elem = item.find('pubDate')
            
            if not title_elem:
                continue
            
            title = title_elem.text.strip() if title_elem.text else ''
            description = desc_elem.text.strip() if desc_elem and desc_elem.text else ''
            link = link_elem.text.strip() if link_elem and link_elem.text else ''
            pubdate = pubdate_elem.text.strip() if pubdate_elem and pubdate_elem.text else ''
            
            # Clean HTML from description
            if description:
                description = re.sub(r'<[^>]+>', '', description)
                description = description[:500]  # Limit length
            
            full_text = f"{title.lower()} {description.lower()}"
            
            # Check if it matches any regulatory keywords
            matched_keywords = []
            for keyword in REGULATORY_KEYWORDS:
                if keyword in full_text:
                    matched_keywords.append(keyword)
            
            if matched_keywords:
                regulatory_matches.append({
                    'title': title,
                    'description': description[:200] + '...' if len(description) > 200 else description,
                    'link': link,
                    'pubdate': pubdate,
                    'matched_keywords': matched_keywords[:5]  # Show first 5 matches
                })
        
        return {
            'source': source_key,
            'accessible': True,
            'articles_found': len(items),
            'regulatory_matches': len(regulatory_matches),
            'sample_articles': regulatory_matches[:10],  # Show first 10 matches
            'match_rate': f"{(len(regulatory_matches) / len(items) * 100):.1f}%" if items else "0%"
        }
        
    except requests.exceptions.Timeout:
        return {
            'source': source_key,
            'accessible': False,
            'reason': 'Timeout',
            'articles_found': 0,
            'regulatory_matches': 0,
            'sample_articles': []
        }
    except requests.exceptions.ConnectionError:
        return {
            'source': source_key,
            'accessible': False,
            'reason': 'Connection Error',
            'articles_found': 0,
            'regulatory_matches': 0,
            'sample_articles': []
        }
    except Exception as e:
        return {
            'source': source_key,
            'accessible': False,
            'reason': f'Error: {str(e)[:50]}',
            'articles_found': 0,
            'regulatory_matches': 0,
            'sample_articles': []
        }

def main():
    """Run the test"""
    print("=" * 80)
    print("TESTING RSS FEEDS FOR REGULATORY ACTION ARTICLES")
    print("=" * 80)
    print()
    
    results = {}
    total_articles = 0
    total_regulatory_matches = 0
    
    for source_key, source_info in OFFICIAL_SOURCES.items():
        print(f"Testing {source_info['name']}...")
        result = test_rss_feed_for_regulatory_articles(source_key, source_info)
        results[source_key] = result
        
        if result['accessible']:
            print(f"  ✅ Accessible")
            print(f"  📰 Total articles: {result['articles_found']}")
            print(f"  🎯 Regulatory matches: {result['regulatory_matches']} ({result.get('match_rate', 'N/A')})")
            
            if result['regulatory_matches'] > 0:
                print(f"  📋 Sample articles:")
                for i, article in enumerate(result['sample_articles'][:3], 1):
                    print(f"    {i}. {article['title'][:80]}")
                    print(f"       Keywords: {', '.join(article['matched_keywords'][:3])}")
            
            total_articles += result['articles_found']
            total_regulatory_matches += result['regulatory_matches']
        else:
            print(f"  ❌ Not accessible: {result.get('reason', 'Unknown')}")
        
        print()
        time.sleep(1)  # Be respectful to servers
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    accessible_sources = [k for k, v in results.items() if v['accessible']]
    sources_with_matches = [k for k, v in results.items() if v['accessible'] and v['regulatory_matches'] > 0]
    
    print(f"Sources tested: {len(OFFICIAL_SOURCES)}")
    print(f"Sources accessible: {len(accessible_sources)} ({', '.join(accessible_sources)})")
    print(f"Sources with regulatory matches: {len(sources_with_matches)} ({', '.join(sources_with_matches)})")
    print()
    print(f"Total articles found: {total_articles}")
    print(f"Total regulatory matches: {total_regulatory_matches}")
    print()
    
    # Detailed results
    print("=" * 80)
    print("DETAILED RESULTS")
    print("=" * 80)
    print()
    
    for source_key, result in results.items():
        if result['accessible'] and result['regulatory_matches'] > 0:
            print(f"{OFFICIAL_SOURCES[source_key]['name']}:")
            print(f"  Articles: {result['articles_found']}")
            print(f"  Regulatory matches: {result['regulatory_matches']} ({result.get('match_rate', 'N/A')})")
            print()
    
    # Recommendations
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()
    
    if total_regulatory_matches > 0:
        print(f"✅ Found {total_regulatory_matches} regulatory action articles from official sources!")
        print()
        print("These sources could help find regulatory action/investigation announcements:")
        for source_key in sources_with_matches:
            source_info = OFFICIAL_SOURCES[source_key]
            result = results[source_key]
            print(f"  • {source_info['name']}: {result['regulatory_matches']} matches out of {result['articles_found']} articles")
        print()
        print("Consider adding these RSS feeds to the main RSS sources list in main.py")
        print("to improve coverage of regulatory action/investigation announcements.")
    else:
        print("⚠️  No regulatory action articles found in accessible RSS feeds.")
        print()
        print("Possible reasons:")
        print("  • RSS feeds may not contain recent regulatory action articles")
        print("  • Keywords may need to be expanded")
        print("  • Some sources may require different access methods")
        print()
        print("Alternative approaches:")
        print("  • Use SEC EDGAR API to search for 8-K filings with regulatory disclosures")
        print("  • Scrape official press release pages directly")
        print("  • Use official APIs if available (some may require registration)")
    
    print()

if __name__ == '__main__':
    main()

