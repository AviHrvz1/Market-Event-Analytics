#!/usr/bin/env python3
"""
Unit Test: Analyze Top Losers and Gainers from Yesterday
- Fetches top movers from yesterday
- Searches for articles published during market hours
- Identifies articles that likely caused the movement
- Extracts keywords/terms to look for
"""

import sys
import requests
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from config import PRIXE_API_KEY, PRIXE_BASE_URL, EVENT_TYPES
from main import LayoffTracker

try:
    from dateutil import parser
except ImportError:
    print("Warning: python-dateutil not installed. Install with: pip install python-dateutil")
    sys.exit(1)

def get_yesterday_date() -> str:
    """Get yesterday's date in YYYY-MM-DD format"""
    # Use a date that's definitely in the past and has trading data
    # Based on UI data, we know Nov 20-21, 2025 has data
    # Use Nov 20, 2025 as a known working date
    # Or go back to find the most recent weekday
    now = datetime.now(timezone.utc)
    
    # Try to find a recent weekday (Mon-Fri) that has data
    # Start from 5 days ago and go back up to 30 days
    for days_back in range(5, 31):
        candidate = now - timedelta(days=days_back)
        # Monday = 0, Friday = 4
        if candidate.weekday() < 5:  # Monday through Friday
            # Test if this date has data by checking a known ticker
            test_date_str = candidate.strftime('%Y-%m-%d')
            # We'll use this date - if it doesn't work, the API will return empty
            return test_date_str
    
    # Fallback to Nov 20, 2025 (known to have data from UI)
    return '2025-11-20'

def fetch_top_movers(date_str: str, limit: int = 10) -> Dict[str, List[Dict]]:
    """
    Fetch top gainers and losers for a specific date using Prixe.io
    Note: Prixe.io doesn't have a direct "top movers" endpoint, so we'll need to:
    1. Get a list of popular tickers
    2. Fetch their daily data for the date
    3. Calculate percentage changes
    4. Sort by change
    """
    print(f"\n{'='*80}")
    print(f"Fetching Top Movers for {date_str}")
    print(f"{'='*80}\n")
    
    # List of popular/active tickers to check
    # In a real scenario, you might fetch this from an index or use a larger list
    popular_tickers = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'NFLX',
        'AMD', 'INTC', 'JPM', 'BAC', 'WMT', 'JNJ', 'V', 'MA', 'PG', 'DIS',
        'XOM', 'CVX', 'ABBV', 'AVGO', 'COST', 'PEP', 'TMO', 'ABT', 'CSCO',
        'ADBE', 'NKE', 'MRK', 'ACN', 'TXN', 'QCOM', 'CMCSA', 'DHR', 'VZ',
        'NEE', 'LIN', 'PM', 'UNH', 'HD', 'WFC', 'RTX', 'LOW', 'UPS', 'DE',
        'CAT', 'HON', 'GE', 'BA', 'MMM', 'IBM', 'GS', 'AXP', 'BK', 'C',
        'SPY', 'QQQ', 'IWM', 'DIA', 'GLD', 'SLV', 'USO', 'TLT', 'HYG'
    ]
    
    movers = {
        'gainers': [],
        'losers': []
    }
    
    print(f"Checking {len(popular_tickers)} tickers for {date_str}...")
    
    successful = 0
    failed = 0
    
    for idx, ticker in enumerate(popular_tickers, 1):
        try:
            # Fetch daily data for the date
            url = f"{PRIXE_BASE_URL}/api/price"
            headers = {
                "Authorization": f"Bearer {PRIXE_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # Get data for date range (target date and 5 days before to ensure we have comparison data)
            target_dt = datetime.strptime(date_str, '%Y-%m-%d')
            start_date = target_dt - timedelta(days=5)
            
            payload = {
                'ticker': ticker,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': date_str,
                'interval': '1d'
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'data' in data:
                    price_data = data['data']
                    timestamps = price_data.get('timestamp', [])
                    closes = price_data.get('close', [])
                    opens = price_data.get('open', [])
                    
                    if not timestamps or not closes:
                        failed += 1
                        continue
                    
                    # Find the target date in the results
                    target_date_obj = target_dt.date()
                    target_idx = None
                    prev_idx = None
                    
                    # First, try to find the exact target date
                    for i, ts in enumerate(timestamps):
                        ts_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                        if ts_dt.date() == target_date_obj:
                            target_idx = i
                            break
                    
                    # If target date not found, use the most recent date in the response
                    if target_idx is None and timestamps:
                        target_idx = len(timestamps) - 1
                        # Update target_date_obj to match what we actually found
                        actual_ts = timestamps[target_idx]
                        actual_dt = datetime.fromtimestamp(actual_ts, tz=timezone.utc)
                        target_date_obj = actual_dt.date()
                    
                    # Now find previous trading day
                    if target_idx is not None and target_idx > 0:
                        for j in range(target_idx-1, -1, -1):
                            prev_ts_dt = datetime.fromtimestamp(timestamps[j], tz=timezone.utc)
                            # Make sure it's a different day
                            if prev_ts_dt.date() < target_date_obj:
                                prev_idx = j
                                break
                    
                    # If we found both dates, calculate change
                    if target_idx is not None and prev_idx is not None:
                        target_close = closes[target_idx]
                        prev_close = closes[prev_idx]
                        
                        if prev_close and prev_close > 0 and target_close:
                            change_pct = ((target_close - prev_close) / prev_close) * 100
                            
                            mover_info = {
                                'ticker': ticker,
                                'date': date_str,
                                'open': opens[target_idx] if target_idx < len(opens) else None,
                                'close': target_close,
                                'prev_close': prev_close,
                                'change_pct': change_pct,
                                'change_dollar': target_close - prev_close
                            }
                            
                            if change_pct > 0:
                                movers['gainers'].append(mover_info)
                                successful += 1
                            elif change_pct < 0:
                                movers['losers'].append(mover_info)
                                successful += 1
                        else:
                            failed += 1
                    else:
                        failed += 1
                else:
                    failed += 1
            else:
                failed += 1
            
            # Progress indicator
            if idx % 10 == 0:
                print(f"  Processed {idx}/{len(popular_tickers)} tickers... (found {successful} movers, {failed} failed/no data)")
                
        except Exception as e:
            failed += 1
            # Skip errors and continue
            if idx <= 3:  # Show first few errors for debugging
                print(f"  Error for {ticker}: {e}")
            continue
    
    print(f"\n  Completed: {successful} movers found, {failed} failed/no data")
    
    # Sort by absolute change percentage
    movers['gainers'].sort(key=lambda x: x['change_pct'], reverse=True)
    movers['losers'].sort(key=lambda x: x['change_pct'])
    
    # Keep top N
    movers['gainers'] = movers['gainers'][:limit]
    movers['losers'] = movers['losers'][:limit]
    
    return movers

def search_articles_for_ticker(tracker: LayoffTracker, ticker: str, date_str: str) -> List[Dict]:
    """Search for articles about a ticker published on a specific date during market hours"""
    print(f"\n  Searching articles for {ticker} on {date_str}...")
    
    # Get company name from ticker (simplified - in real scenario use SEC EDGAR lookup)
    # For now, we'll search with ticker symbol
    
    # Search Google News for articles on that date
    articles = []
    
    try:
        # Use Google News RSS with ticker symbol
        # Note: Google News RSS doesn't support precise date filtering
        # It returns recent articles, so we'll filter by date after fetching
        search_query = ticker
        url = f"https://news.google.com/rss/search?q={search_query}&hl=en-US&gl=US&ceid=US:en&num=100"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item')
            
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            for item in items:
                title_elem = item.find('title')
                pub_date_elem = item.find('pubDate')
                link_elem = item.find('link')
                description_elem = item.find('description')
                
                if not title_elem or not pub_date_elem:
                    continue
                
                title = title_elem.text.strip()
                pub_date_str = pub_date_elem.text.strip()
                
                # Parse publication date
                try:
                    pub_date = parser.parse(pub_date_str)
                    if pub_date.tzinfo is None:
                        pub_date = pub_date.replace(tzinfo=timezone.utc)
                    else:
                        pub_date = pub_date.astimezone(timezone.utc)
                    
                    # Check if article is on target date
                    if pub_date.date() == target_date:
                        # Check if published during market hours (9:30 AM - 4:00 PM ET)
                        # Convert UTC to ET (EST is UTC-5, EDT is UTC-4)
                        # For December, it's EST (UTC-5)
                        month = pub_date.month
                        if month >= 3 and month <= 10:
                            et_offset = timedelta(hours=-4)  # EDT
                        else:
                            et_offset = timedelta(hours=-5)  # EST
                        
                        et_time = pub_date + et_offset
                        hour = et_time.hour
                        minute = et_time.minute
                        
                        # Market hours: 9:30 AM - 4:00 PM ET
                        is_market_hours = (
                            (hour == 9 and minute >= 30) or
                            (9 < hour < 16) or
                            (hour == 16 and minute == 0)
                        )
                        
                        if is_market_hours:
                            # Format ET time for display
                            et_time_str = et_time.strftime('%H:%M:%S ET')
                            
                            description = ''
                            if description_elem and description_elem.text:
                                description = description_elem.text.strip()
                                # Remove HTML tags
                                desc_soup = BeautifulSoup(description, 'html.parser')
                                description = desc_soup.get_text()
                            
                            link = link_elem.text.strip() if link_elem else ''
                            
                            articles.append({
                                'title': title,
                                'description': description,
                                'url': link,
                                'published_at': pub_date.isoformat(),
                                'published_time_et': et_time_str,
                                'ticker': ticker
                            })
                except Exception as e:
                    continue
                    
    except Exception as e:
        print(f"    Error searching articles: {e}")
    
    return articles

def analyze_article_keywords(article: Dict) -> Dict:
    """Extract keywords and terms from article that might indicate stock-moving news"""
    title = article.get('title', '').lower()
    description = article.get('description', '').lower()
    full_text = f"{title} {description}"
    
    # Common stock-moving keywords
    keywords_found = []
    terms_found = []
    
    # Event type keywords (from config)
    for event_type, config in EVENT_TYPES.items():
        event_keywords = config.get('keywords', [])
        for keyword in event_keywords:
            if keyword.lower() in full_text:
                keywords_found.append(keyword)
                if event_type not in terms_found:
                    terms_found.append(event_type)
    
    # Additional financial terms
    financial_terms = [
        'earnings', 'revenue', 'profit', 'loss', 'guidance', 'forecast',
        'beat', 'miss', 'surprise', 'upgrade', 'downgrade', 'rating',
        'deal', 'acquisition', 'merger', 'partnership', 'contract',
        'lawsuit', 'settlement', 'investigation', 'regulatory',
        'approval', 'fda', 'trial', 'results', 'launch', 'recall',
        'layoff', 'ceo', 'executive', 'departure', 'resignation',
        'fire', 'explosion', 'breach', 'hack', 'cyberattack'
    ]
    
    for term in financial_terms:
        if term in full_text:
            if term not in keywords_found:
                keywords_found.append(term)
    
    return {
        'keywords': keywords_found,
        'event_types': terms_found,
        'title': article.get('title', ''),
        'url': article.get('url', '')
    }

def main():
    print(f"\n{'='*80}")
    print("Unit Test: Top Movers Analysis")
    print("Analyzing yesterday's top gainers and losers")
    print(f"{'='*80}\n")
    
    # Get yesterday's date
    yesterday = get_yesterday_date()
    print(f"Target Date: {yesterday}")
    
    # Initialize tracker
    tracker = LayoffTracker()
    
    # Fetch top movers
    print(f"\nStep 1: Fetching Top Movers...")
    movers = fetch_top_movers(yesterday, limit=5)  # Top 5 gainers and losers
    
    print(f"\nResults:")
    print(f"  Top Gainers: {len(movers['gainers'])}")
    print(f"  Top Losers: {len(movers['losers'])}")
    
    # Display top movers
    print(f"\n{'='*80}")
    print("TOP GAINERS")
    print(f"{'='*80}")
    for i, mover in enumerate(movers['gainers'], 1):
        print(f"{i}. {mover['ticker']}: +{mover['change_pct']:.2f}% (${mover['prev_close']:.2f} → ${mover['close']:.2f})")
    
    print(f"\n{'='*80}")
    print("TOP LOSERS")
    print(f"{'='*80}")
    for i, mover in enumerate(movers['losers'], 1):
        print(f"{i}. {mover['ticker']}: {mover['change_pct']:.2f}% (${mover['prev_close']:.2f} → ${mover['close']:.2f})")
    
    # Analyze articles for each mover
    print(f"\n{'='*80}")
    print("ANALYZING ARTICLES PUBLISHED DURING MARKET HOURS")
    print(f"{'='*80}\n")
    
    all_results = []
    
    # Analyze gainers
    print(f"\n{'='*80}")
    print("TOP GAINERS - Article Analysis")
    print(f"{'='*80}\n")
    
    for mover in movers['gainers']:
        ticker = mover['ticker']
        change_pct = mover['change_pct']
        
        print(f"\n{ticker} (+{change_pct:.2f}%):")
        print("-" * 80)
        
        articles = search_articles_for_ticker(tracker, ticker, yesterday)
        
        if articles:
            print(f"  Found {len(articles)} articles published during market hours:")
            
            for article in articles:
                analysis = analyze_article_keywords(article)
                
                print(f"\n  📰 {article['title'][:70]}...")
                print(f"     Time: {article['published_time_et']}")
                print(f"     URL: {article['url'][:80]}...")
                
                if analysis['keywords']:
                    print(f"     Keywords found: {', '.join(analysis['keywords'][:10])}")
                if analysis['event_types']:
                    print(f"     Event types: {', '.join(analysis['event_types'])}")
                
                all_results.append({
                    'ticker': ticker,
                    'change_pct': change_pct,
                    'direction': 'gainer',
                    'article': article,
                    'analysis': analysis
                })
        else:
            print(f"  ⚠️  No articles found published during market hours")
    
    # Analyze losers
    print(f"\n\n{'='*80}")
    print("TOP LOSERS - Article Analysis")
    print(f"{'='*80}\n")
    
    for mover in movers['losers']:
        ticker = mover['ticker']
        change_pct = mover['change_pct']
        
        print(f"\n{ticker} ({change_pct:.2f}%):")
        print("-" * 80)
        
        articles = search_articles_for_ticker(tracker, ticker, yesterday)
        
        if articles:
            print(f"  Found {len(articles)} articles published during market hours:")
            
            for article in articles:
                analysis = analyze_article_keywords(article)
                
                print(f"\n  📰 {article['title'][:70]}...")
                print(f"     Time: {article['published_time_et']}")
                print(f"     URL: {article['url'][:80]}...")
                
                if analysis['keywords']:
                    print(f"     Keywords found: {', '.join(analysis['keywords'][:10])}")
                if analysis['event_types']:
                    print(f"     Event types: {', '.join(analysis['event_types'])}")
                
                all_results.append({
                    'ticker': ticker,
                    'change_pct': change_pct,
                    'direction': 'loser',
                    'article': article,
                    'analysis': analysis
                })
        else:
            print(f"  ⚠️  No articles found published during market hours")
    
    # Summary: Extract common keywords/terms
    print(f"\n\n{'='*80}")
    print("SUMMARY: KEYWORDS AND TERMS TO LOOK FOR")
    print(f"{'='*80}\n")
    
    all_keywords = {}
    all_event_types = {}
    
    for result in all_results:
        analysis = result['analysis']
        for keyword in analysis['keywords']:
            all_keywords[keyword] = all_keywords.get(keyword, 0) + 1
        for event_type in analysis['event_types']:
            all_event_types[event_type] = all_event_types.get(event_type, 0) + 1
    
    if all_keywords:
        print("Most Common Keywords:")
        sorted_keywords = sorted(all_keywords.items(), key=lambda x: x[1], reverse=True)
        for keyword, count in sorted_keywords[:20]:
            print(f"  - {keyword} (appeared {count} times)")
    
    if all_event_types:
        print(f"\nMost Common Event Types:")
        sorted_events = sorted(all_event_types.items(), key=lambda x: x[1], reverse=True)
        for event_type, count in sorted_events:
            event_name = EVENT_TYPES.get(event_type, {}).get('name', event_type)
            print(f"  - {event_name} ({event_type}): {count} articles")
    
    print(f"\n{'='*80}")
    print("RECOMMENDATIONS")
    print(f"{'='*80}\n")
    print("Based on the analysis, consider adding these terms to your event types:")
    print("(If not already present)")
    
    # Suggest new keywords based on findings
    suggested_keywords = set()
    for result in all_results:
        analysis = result['analysis']
        for keyword in analysis['keywords']:
            # Check if keyword is in any existing event type
            found = False
            for event_type, config in EVENT_TYPES.items():
                if keyword.lower() in [k.lower() for k in config.get('keywords', [])]:
                    found = True
                    break
            if not found and keyword not in ['the', 'a', 'an', 'and', 'or', 'is', 'are', 'was', 'were']:
                suggested_keywords.add(keyword)
    
    if suggested_keywords:
        print("\nSuggested keywords to add:")
        for keyword in sorted(suggested_keywords)[:15]:
            print(f"  - '{keyword}'")
    else:
        print("\nAll found keywords are already covered by existing event types.")
    
    print(f"\n{'='*80}")
    print("Test Complete")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    main()

