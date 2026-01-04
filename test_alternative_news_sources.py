#!/usr/bin/env python3
"""Unit test to check if alternative free news sources are useful for finding 
stock-impacting news. Tests various RSS feeds and APIs to see which ones 
return the most relevant articles."""

import requests
from datetime import datetime, timedelta
from config import EVENT_TYPES, SEC_USER_AGENT
import time
import re

print("=" * 80)
print("Alternative News Sources Utility Test")
print("=" * 80)
print()
print("Testing free news sources to see which ones are most useful for")
print("finding stock-impacting news (layoffs, recalls, regulatory actions, etc.)")
print()

# Alternative news sources to test
ALTERNATIVE_SOURCES = {
    'benzinga_news': {
        'name': 'Benzinga News',
        'rss_url': 'https://www.benzinga.com/news/feed',
        'description': 'Benzinga news feed (not crypto predictions)',
        'expected_quality': 'High'
    },
    'benzinga_markets': {
        'name': 'Benzinga Markets',
        'rss_url': 'https://www.benzinga.com/markets/feed',
        'description': 'Benzinga markets news',
        'expected_quality': 'High'
    },
    'thestreet': {
        'name': 'TheStreet',
        'rss_url': 'https://www.thestreet.com/.rss',
        'description': 'Business and financial news',
        'expected_quality': 'High'
    },
    'zacks': {
        'name': 'Zacks Investment Research',
        'rss_url': 'https://www.zacks.com/rss/stock_news',
        'description': 'Stock-specific news and analysis',
        'expected_quality': 'High'
    },
    'sec_8k': {
        'name': 'SEC 8-K Filings',
        'rss_url': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&output=atom',
        'description': 'Direct company filings for material events',
        'expected_quality': 'Very High'
    },
    'sec_10k': {
        'name': 'SEC 10-K Filings',
        'rss_url': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=10-K&output=atom',
        'description': 'Annual reports with regulatory disclosures',
        'expected_quality': 'High'
    },
    'financial_times': {
        'name': 'Financial Times',
        'rss_url': 'https://www.ft.com/?format=rss',
        'description': 'High-quality financial journalism',
        'expected_quality': 'High'
    },
    'reuters_business': {
        'name': 'Reuters Business',
        'rss_url': 'https://feeds.reuters.com/reuters/businessNews',
        'description': 'Global business news',
        'expected_quality': 'High'
    },
    'reuters_markets': {
        'name': 'Reuters Markets',
        'rss_url': 'https://feeds.reuters.com/reuters/marketsNews',
        'description': 'Reuters markets news',
        'expected_quality': 'High'
    },
    'ap_business': {
        'name': 'AP Business News',
        'rss_url': 'https://feeds.apnews.com/rss/apf-topnews',
        'description': 'Associated Press business news',
        'expected_quality': 'Medium'
    },
    'business_insider': {
        'name': 'Business Insider',
        'rss_url': 'https://feeds.businessinsider.com/custom/all',
        'description': 'Business and tech news',
        'expected_quality': 'Medium'
    },
    'nasdaq_news': {
        'name': 'NASDAQ News',
        'rss_url': 'https://www.nasdaq.com/feed/rssoutbound?category=Stocks',
        'description': 'NASDAQ stock news',
        'expected_quality': 'High'
    },
    'fool_stocks': {
        'name': 'Motley Fool Stocks',
        'rss_url': 'https://www.fool.com/feeds/index.aspx?category=stocks',
        'description': 'Motley Fool stock news',
        'expected_quality': 'Medium'
    },
}

# Get all keywords from all event types
ALL_EVENT_KEYWORDS = set()
for event_type, event_config in EVENT_TYPES.items():
    keywords = event_config.get('keywords', [])
    ALL_EVENT_KEYWORDS.update([kw.lower() for kw in keywords])

print(f"Testing with {len(ALL_EVENT_KEYWORDS)} keywords from {len(EVENT_TYPES)} event types")
print()

def test_rss_source(source_key, source_info):
    """Test if an RSS source is useful for finding relevant articles"""
    if not source_info.get('rss_url'):
        return {
            'source': source_key,
            'accessible': False,
            'reason': 'No RSS URL provided',
            'articles_found': 0,
            'relevant_matches': 0,
            'match_rate': '0%',
            'sample_articles': []
        }
    
    headers = {
        'User-Agent': SEC_USER_AGENT,
        'Accept': 'application/rss+xml, application/xml, text/xml, */*'
    }
    
    try:
        response = requests.get(
            source_info['rss_url'], 
            headers=headers, 
            timeout=15, 
            allow_redirects=True
        )
        
        if response.status_code != 200:
            return {
                'source': source_key,
                'accessible': False,
                'reason': f'HTTP {response.status_code}',
                'articles_found': 0,
                'relevant_matches': 0,
                'match_rate': '0%',
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
                'relevant_matches': 0,
                'match_rate': '0%',
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
                'relevant_matches': 0,
                'match_rate': '0%',
                'sample_articles': []
            }
        
        # Check each item for relevant keywords
        relevant_matches = []
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
                description = description[:300]  # Limit length
            
            full_text = f"{title.lower()} {description.lower()}"
            
            # Check if it matches any event keywords
            matched_keywords = []
            for keyword in ALL_EVENT_KEYWORDS:
                if keyword in full_text:
                    matched_keywords.append(keyword)
            
            if matched_keywords:
                relevant_matches.append({
                    'title': title,
                    'description': description[:150] + '...' if len(description) > 150 else description,
                    'link': link,
                    'pubdate': pubdate,
                    'matched_keywords': matched_keywords[:5]  # Show first 5 matches
                })
        
        match_rate = (len(relevant_matches) / len(items) * 100) if items else 0
        
        return {
            'source': source_key,
            'accessible': True,
            'articles_found': len(items),
            'relevant_matches': len(relevant_matches),
            'match_rate': f"{match_rate:.1f}%",
            'sample_articles': relevant_matches[:5],  # Show first 5 matches
            'quality_score': calculate_quality_score(len(items), len(relevant_matches), match_rate)
        }
        
    except requests.exceptions.Timeout:
        return {
            'source': source_key,
            'accessible': False,
            'reason': 'Timeout',
            'articles_found': 0,
            'relevant_matches': 0,
            'match_rate': '0%',
            'sample_articles': []
        }
    except requests.exceptions.ConnectionError:
        return {
            'source': source_key,
            'accessible': False,
            'reason': 'Connection Error',
            'articles_found': 0,
            'relevant_matches': 0,
            'match_rate': '0%',
            'sample_articles': []
        }
    except Exception as e:
        return {
            'source': source_key,
            'accessible': False,
            'reason': f'Error: {str(e)[:50]}',
            'articles_found': 0,
            'relevant_matches': 0,
            'match_rate': '0%',
            'sample_articles': []
        }

def calculate_quality_score(total_articles, relevant_matches, match_rate):
    """Calculate a quality score (0-100) for the source"""
    if total_articles == 0:
        return 0
    
    # Factors:
    # - Match rate (higher is better)
    # - Total articles (more is better, but with diminishing returns)
    # - Absolute number of matches (more is better)
    
    match_rate_score = min(match_rate, 50)  # Cap at 50 points for match rate
    volume_score = min(total_articles / 10, 30)  # Up to 30 points for volume
    matches_score = min(relevant_matches * 2, 20)  # Up to 20 points for absolute matches
    
    return int(match_rate_score + volume_score + matches_score)

def main():
    """Run the test"""
    print("=" * 80)
    print("TESTING ALTERNATIVE NEWS SOURCES")
    print("=" * 80)
    print()
    
    results = {}
    total_articles = 0
    total_matches = 0
    
    for source_key, source_info in ALTERNATIVE_SOURCES.items():
        print(f"Testing {source_info['name']}...")
        print(f"  Expected quality: {source_info.get('expected_quality', 'Unknown')}")
        print(f"  Description: {source_info.get('description', 'N/A')}")
        
        result = test_rss_source(source_key, source_info)
        results[source_key] = result
        
        if result['accessible']:
            print(f"  ✅ Accessible")
            print(f"  📰 Total articles: {result['articles_found']}")
            print(f"  🎯 Relevant matches: {result['relevant_matches']} ({result['match_rate']})")
            print(f"  ⭐ Quality score: {result.get('quality_score', 0)}/100")
            
            if result['relevant_matches'] > 0:
                print(f"  📋 Sample articles:")
                for i, article in enumerate(result['sample_articles'][:3], 1):
                    print(f"    {i}. {article['title'][:70]}")
                    if article['matched_keywords']:
                        print(f"       Keywords: {', '.join(article['matched_keywords'][:3])}")
            
            total_articles += result['articles_found']
            total_matches += result['relevant_matches']
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
    useful_sources = [k for k, v in results.items() if v['accessible'] and v['relevant_matches'] > 0]
    
    print(f"Sources tested: {len(ALTERNATIVE_SOURCES)}")
    print(f"Sources accessible: {len(accessible_sources)}")
    print(f"Sources with relevant matches: {len(useful_sources)}")
    print()
    print(f"Total articles found: {total_articles}")
    print(f"Total relevant matches: {total_matches}")
    print()
    
    # Rank sources by quality
    print("=" * 80)
    print("RANKED BY QUALITY SCORE")
    print("=" * 80)
    print()
    
    ranked_sources = sorted(
        [(k, v) for k, v in results.items() if v['accessible']],
        key=lambda x: x[1].get('quality_score', 0),
        reverse=True
    )
    
    for i, (source_key, result) in enumerate(ranked_sources, 1):
        source_info = ALTERNATIVE_SOURCES[source_key]
        print(f"{i}. {source_info['name']} (Score: {result.get('quality_score', 0)}/100)")
        print(f"   Articles: {result['articles_found']}, Matches: {result['relevant_matches']} ({result['match_rate']})")
        print()
    
    # Top recommendations
    print("=" * 80)
    print("TOP RECOMMENDATIONS")
    print("=" * 80)
    print()
    
    if useful_sources:
        print("✅ Most useful sources to add:")
        print()
        
        # Top 5 by quality score
        top_sources = ranked_sources[:5]
        for source_key, result in top_sources:
            source_info = ALTERNATIVE_SOURCES[source_key]
            if result['relevant_matches'] > 0:
                print(f"  • {source_info['name']}")
                print(f"    URL: {source_info['rss_url']}")
                print(f"    Quality Score: {result.get('quality_score', 0)}/100")
                print(f"    Match Rate: {result['match_rate']}")
                print(f"    Articles: {result['articles_found']}, Matches: {result['relevant_matches']}")
                print()
        
        print("Consider adding these to your rss_sources list in main.py")
    else:
        print("⚠️  No sources found with relevant matches.")
        print()
        print("Possible reasons:")
        print("  • Sources may not have recent articles matching your keywords")
        print("  • RSS feeds may be rate-limited or require authentication")
        print("  • Keywords may need to be expanded")
        print()
        print("Try testing again later or consider:")
        print("  • Using API-based sources (Alpha Vantage, Finnhub)")
        print("  • Scraping news sites directly")
        print("  • Using company-specific RSS feeds")
    
    print()
    
    # Detailed breakdown by event type
    print("=" * 80)
    print("DETAILED BREAKDOWN")
    print("=" * 80)
    print()
    
    for source_key in useful_sources:
        result = results[source_key]
        source_info = ALTERNATIVE_SOURCES[source_key]
        
        if result['relevant_matches'] > 0:
            print(f"{source_info['name']}:")
            print(f"  Total articles: {result['articles_found']}")
            print(f"  Relevant matches: {result['relevant_matches']} ({result['match_rate']})")
            print(f"  Quality score: {result.get('quality_score', 0)}/100")
            print()
            
            # Show which event types are covered
            event_types_found = set()
            for article in result['sample_articles']:
                for keyword in article['matched_keywords']:
                    # Find which event type this keyword belongs to
                    for event_type, event_config in EVENT_TYPES.items():
                        if keyword in [kw.lower() for kw in event_config.get('keywords', [])]:
                            event_types_found.add(event_type)
                            break
            
            if event_types_found:
                print(f"  Event types found: {', '.join(sorted(event_types_found))}")
            print()

if __name__ == '__main__':
    main()

