#!/usr/bin/env python3
"""Test script to check which regulatory/investigation sources have accessible 
RSS feeds and return articles about regulatory actions and investigations."""

import requests
from datetime import datetime, timedelta
from config import EVENT_TYPES, SEC_USER_AGENT
import time
import re

print("=" * 80)
print("Regulatory/Investigation Sources Test")
print("=" * 80)
print()
print("Testing sources that report on regulatory actions, investigations,")
print("and other critical events that can affect stock prices")
print()

# Regulatory and investigation sources to test
REGULATORY_SOURCES = {
    # Official Regulatory Sources
    'sec_enforcement': {
        'name': 'SEC Enforcement Actions',
        'rss_url': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=&company=&dateb=&owner=include&start=0&count=100&output=atom',
        'description': 'SEC EDGAR filings (may include enforcement-related filings)',
        'category': 'Official'
    },
    'sec_8k': {
        'name': 'SEC 8-K Filings',
        'rss_url': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&output=atom',
        'description': 'Material events filings (often include regulatory disclosures)',
        'category': 'Official'
    },
    'doj_press': {
        'name': 'DOJ Press Releases',
        'rss_url': 'https://www.justice.gov/opa/rss/press-releases.xml',
        'description': 'DOJ enforcement actions and settlements',
        'category': 'Official'
    },
    'doj_antitrust': {
        'name': 'DOJ Antitrust Division',
        'rss_url': 'https://www.justice.gov/atr/rss/press-releases.xml',
        'description': 'Antitrust enforcement actions',
        'category': 'Official'
    },
    'finra_news': {
        'name': 'FINRA News Releases',
        'rss_url': 'https://www.finra.org/rules-guidance/oversight-enforcement/finra-disciplinary-actions/rss',
        'description': 'FINRA disciplinary actions and fines',
        'category': 'Official'
    },
    'cftc_enforcement': {
        'name': 'CFTC Enforcement',
        'rss_url': 'https://www.cftc.gov/PressRoom/PressReleases/rss',
        'description': 'CFTC enforcement actions',
        'category': 'Official'
    },
    'ofac_actions': {
        'name': 'OFAC Recent Actions',
        'rss_url': 'https://ofac.treasury.gov/recent-actions/rss',
        'description': 'OFAC sanctions and designations',
        'category': 'Official'
    },
    
    # Financial News Sites
    'reuters_business': {
        'name': 'Reuters Business',
        'rss_url': 'https://feeds.reuters.com/reuters/businessNews',
        'description': 'Reuters business news including regulatory actions',
        'category': 'News'
    },
    'reuters_markets': {
        'name': 'Reuters Markets',
        'rss_url': 'https://feeds.reuters.com/reuters/marketsNews',
        'description': 'Reuters markets news',
        'category': 'News'
    },
    'wsj_markets': {
        'name': 'WSJ Markets',
        'rss_url': 'https://feeds.a.dj.com/rss/RSSMarketsMain.xml',
        'description': 'Wall Street Journal markets news',
        'category': 'News'
    },
    'bloomberg_markets': {
        'name': 'Bloomberg Markets',
        'rss_url': 'https://feeds.bloomberg.com/markets/news.rss',
        'description': 'Bloomberg markets news',
        'category': 'News'
    },
    'financial_times': {
        'name': 'Financial Times',
        'rss_url': 'https://www.ft.com/?format=rss',
        'description': 'Financial Times news',
        'category': 'News'
    },
    'marketwatch': {
        'name': 'MarketWatch',
        'rss_url': 'https://feeds.marketwatch.com/marketwatch/topstories/',
        'description': 'MarketWatch top stories',
        'category': 'News'
    },
    'seeking_alpha': {
        'name': 'Seeking Alpha',
        'rss_url': 'https://seekingalpha.com/feed.xml',
        'description': 'Seeking Alpha news and analysis',
        'category': 'News'
    },
    'benzinga_news': {
        'name': 'Benzinga News',
        'rss_url': 'https://www.benzinga.com/news/feed',
        'description': 'Benzinga financial news',
        'category': 'News'
    },
    'investing_com': {
        'name': 'Investing.com',
        'rss_url': 'https://www.investing.com/rss/news.rss',
        'description': 'Investing.com news',
        'category': 'News'
    },
    'nasdaq_news': {
        'name': 'NASDAQ News',
        'rss_url': 'https://www.nasdaq.com/feed/rssoutbound?category=Stocks',
        'description': 'NASDAQ stock news',
        'category': 'News'
    },
}

# Keywords specifically for regulatory actions and investigations
REGULATORY_KEYWORDS = {
    'investigation': ['investigation', 'investigating', 'probe', 'probe launched', 'under investigation', 
                     'subject of investigation', 'facing investigation', 'investigation into'],
    'enforcement': ['enforcement action', 'enforcement', 'sec enforcement', 'doj enforcement', 
                   'regulatory enforcement', 'enforcement division'],
    'lawsuit': ['lawsuit', 'lawsuit filed', 'sued', 'facing lawsuit', 'class action lawsuit', 
                'lawsuit against', 'legal action', 'filed suit'],
    'settlement': ['settlement', 'agrees to settle', 'settlement reached', 'settlement agreement', 
                   'pays settlement', 'settles lawsuit'],
    'fine_penalty': ['fine', 'fined', 'penalty', 'penalty imposed', 'regulatory fine', 'civil penalty', 
                     'monetary penalty', 'ordered to pay'],
    'regulatory': ['regulatory action', 'regulatory investigation', 'regulatory probe', 
                  'regulatory violation', 'compliance issue', 'regulatory fine'],
    'sec_specific': ['sec investigation', 'sec enforcement', 'sec charges', 'sec filing', 
                     'securities and exchange commission'],
    'doj_specific': ['doj lawsuit', 'doj settlement', 'justice department', 'department of justice'],
    'antitrust': ['antitrust', 'antitrust lawsuit', 'antitrust investigation', 'monopoly', 
                  'anti-competitive'],
    'subpoena': ['subpoena', 'subpoenaed', 'received subpoena'],
}

# Combine all regulatory keywords
ALL_REGULATORY_KEYWORDS = set()
for keyword_list in REGULATORY_KEYWORDS.values():
    ALL_REGULATORY_KEYWORDS.update([kw.lower() for kw in keyword_list])

# Also get keywords from event types
for event_type in ['regulatory_action', 'regulatory_investigation', 'penalty', 'fine', 'settlement', 'litigation']:
    if event_type in EVENT_TYPES:
        keywords = EVENT_TYPES[event_type].get('keywords', [])
        ALL_REGULATORY_KEYWORDS.update([kw.lower() for kw in keywords])

print(f"Testing with {len(ALL_REGULATORY_KEYWORDS)} regulatory/investigation keywords")
print()

def test_rss_source(source_key, source_info):
    """Test if an RSS source is accessible and contains regulatory articles"""
    if not source_info.get('rss_url'):
        return {
            'source': source_key,
            'accessible': False,
            'reason': 'No RSS URL provided',
            'articles_found': 0,
            'regulatory_matches': 0,
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
                'regulatory_matches': 0,
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
                'regulatory_matches': 0,
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
                'regulatory_matches': 0,
                'match_rate': '0%',
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
                description = description[:300]
            
            full_text = f"{title.lower()} {description.lower()}"
            
            # Check if it matches any regulatory keywords
            matched_keywords = []
            matched_categories = set()
            
            for keyword in ALL_REGULATORY_KEYWORDS:
                if keyword in full_text:
                    matched_keywords.append(keyword)
                    # Find which category this keyword belongs to
                    for cat, kw_list in REGULATORY_KEYWORDS.items():
                        if keyword in [kw.lower() for kw in kw_list]:
                            matched_categories.add(cat)
                            break
            
            if matched_keywords:
                regulatory_matches.append({
                    'title': title,
                    'description': description[:150] + '...' if len(description) > 150 else description,
                    'link': link,
                    'pubdate': pubdate,
                    'matched_keywords': matched_keywords[:5],
                    'categories': sorted(matched_categories)
                })
        
        match_rate = (len(regulatory_matches) / len(items) * 100) if items else 0
        
        return {
            'source': source_key,
            'accessible': True,
            'articles_found': len(items),
            'regulatory_matches': len(regulatory_matches),
            'match_rate': f"{match_rate:.1f}%",
            'sample_articles': regulatory_matches[:5],
            'quality_score': calculate_quality_score(len(items), len(regulatory_matches), match_rate)
        }
        
    except requests.exceptions.Timeout:
        return {
            'source': source_key,
            'accessible': False,
            'reason': 'Timeout',
            'articles_found': 0,
            'regulatory_matches': 0,
            'match_rate': '0%',
            'sample_articles': []
        }
    except requests.exceptions.ConnectionError:
        return {
            'source': source_key,
            'accessible': False,
            'reason': 'Connection Error',
            'articles_found': 0,
            'regulatory_matches': 0,
            'match_rate': '0%',
            'sample_articles': []
        }
    except Exception as e:
        return {
            'source': source_key,
            'accessible': False,
            'reason': f'Error: {str(e)[:50]}',
            'articles_found': 0,
            'regulatory_matches': 0,
            'match_rate': '0%',
            'sample_articles': []
        }

def calculate_quality_score(total_articles, regulatory_matches, match_rate):
    """Calculate quality score (0-100) for regulatory sources"""
    if total_articles == 0:
        return 0
    
    # Higher weight on match rate for regulatory sources
    match_rate_score = min(match_rate, 60)  # Up to 60 points
    volume_score = min(total_articles / 5, 25)  # Up to 25 points
    matches_score = min(regulatory_matches * 3, 15)  # Up to 15 points
    
    return int(match_rate_score + volume_score + matches_score)

def main():
    """Run the test"""
    print("=" * 80)
    print("TESTING REGULATORY/INVESTIGATION SOURCES")
    print("=" * 80)
    print()
    
    results = {}
    total_articles = 0
    total_matches = 0
    
    # Test by category
    categories = {}
    for source_key, source_info in REGULATORY_SOURCES.items():
        category = source_info.get('category', 'Other')
        if category not in categories:
            categories[category] = []
        categories[category].append((source_key, source_info))
    
    for category, sources in categories.items():
        print(f"\n{'=' * 80}")
        print(f"CATEGORY: {category.upper()}")
        print(f"{'=' * 80}\n")
        
        for source_key, source_info in sources:
            print(f"Testing {source_info['name']}...")
            print(f"  Description: {source_info.get('description', 'N/A')}")
            
            result = test_rss_source(source_key, source_info)
            results[source_key] = result
            
            if result['accessible']:
                print(f"  ✅ Accessible")
                print(f"  📰 Total articles: {result['articles_found']}")
                print(f"  🎯 Regulatory matches: {result['regulatory_matches']} ({result['match_rate']})")
                print(f"  ⭐ Quality score: {result.get('quality_score', 0)}/100")
                
                if result['regulatory_matches'] > 0:
                    print(f"  📋 Sample articles:")
                    for i, article in enumerate(result['sample_articles'][:3], 1):
                        print(f"    {i}. {article['title'][:70]}")
                        if article['categories']:
                            print(f"       Categories: {', '.join(article['categories'])}")
                        if article['matched_keywords']:
                            print(f"       Keywords: {', '.join(article['matched_keywords'][:3])}")
                
                total_articles += result['articles_found']
                total_matches += result['regulatory_matches']
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
    useful_sources = [k for k, v in results.items() if v['accessible'] and v['regulatory_matches'] > 0]
    
    print(f"Sources tested: {len(REGULATORY_SOURCES)}")
    print(f"Sources accessible: {len(accessible_sources)}")
    print(f"Sources with regulatory matches: {len(useful_sources)}")
    print()
    print(f"Total articles found: {total_articles}")
    print(f"Total regulatory matches: {total_matches}")
    print()
    
    # Rank sources by quality
    print("=" * 80)
    print("RANKED BY QUALITY SCORE (Top 10)")
    print("=" * 80)
    print()
    
    ranked_sources = sorted(
        [(k, v) for k, v in results.items() if v['accessible']],
        key=lambda x: x[1].get('quality_score', 0),
        reverse=True
    )[:10]
    
    for i, (source_key, result) in enumerate(ranked_sources, 1):
        source_info = REGULATORY_SOURCES[source_key]
        print(f"{i}. {source_info['name']} (Score: {result.get('quality_score', 0)}/100)")
        print(f"   Category: {source_info.get('category', 'Unknown')}")
        print(f"   Articles: {result['articles_found']}, Matches: {result['regulatory_matches']} ({result['match_rate']})")
        print(f"   URL: {source_info['rss_url']}")
        print()
    
    # Top recommendations
    print("=" * 80)
    print("TOP RECOMMENDATIONS")
    print("=" * 80)
    print()
    
    if useful_sources:
        print("✅ Best sources for regulatory/investigation news:")
        print()
        
        # Top 5 by quality score
        top_sources = ranked_sources[:5]
        for source_key, result in top_sources:
            if result['regulatory_matches'] > 0:
                source_info = REGULATORY_SOURCES[source_key]
                print(f"  • {source_info['name']}")
                print(f"    Category: {source_info.get('category', 'Unknown')}")
                print(f"    Quality Score: {result.get('quality_score', 0)}/100")
                print(f"    Match Rate: {result['match_rate']}")
                print(f"    Articles: {result['articles_found']}, Matches: {result['regulatory_matches']}")
                print(f"    RSS URL: {source_info['rss_url']}")
                print()
        
        print("Consider adding these to your rss_sources list in main.py")
    else:
        print("⚠️  No sources found with regulatory matches.")
        print()
        print("Possible reasons:")
        print("  • Sources may not have recent regulatory articles")
        print("  • RSS feeds may be rate-limited or require authentication")
        print("  • Some official sources may not have RSS feeds")
        print()
        print("Alternative approaches:")
        print("  • Scrape official websites directly (SEC, DOJ, FINRA)")
        print("  • Use official APIs if available")
        print("  • Monitor specific company ticker pages")
    
    print()
    
    # Breakdown by category
    print("=" * 80)
    print("BREAKDOWN BY CATEGORY")
    print("=" * 80)
    print()
    
    for category in sorted(categories.keys()):
        category_sources = [k for k in categories[category] if results[k[0]]['accessible']]
        category_matches = [k for k in categories[category] if results[k[0]]['accessible'] and results[k[0]]['regulatory_matches'] > 0]
        
        print(f"{category.upper()}:")
        print(f"  Accessible: {len(category_sources)}/{len(categories[category])}")
        print(f"  With matches: {len(category_matches)}/{len(categories[category])}")
        if category_matches:
            total_cat_articles = sum(results[k[0]]['articles_found'] for k in category_matches)
            total_cat_matches = sum(results[k[0]]['regulatory_matches'] for k in category_matches)
            print(f"  Total articles: {total_cat_articles}, Total matches: {total_cat_matches}")
        print()

if __name__ == '__main__':
    main()

