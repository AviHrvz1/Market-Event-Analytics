#!/usr/bin/env python3
"""
Unit test to analyze news from bio stocks with dramatic moves (last 30 days)
and extract useful terms for sentiment detection

REQUIRES NETWORK ACCESS:
- Needs Prixe.io API access for stock price data
- Needs NewsAPI access for fetching news articles
- Run with: python3 test_bio_news_term_extraction.py

This test will:
1. Find bio stocks with >30% moves (up or down) in last 30 days
2. Fetch news articles for those stocks
3. Extract common phrases from news
4. Filter out terms already in keyword lists
5. Rank terms by frequency and bio relevance
6. Suggest top terms to add to config.py

Output: bio_news_term_suggestions.json
"""

import sys
import re
import json
from datetime import datetime, timedelta, timezone
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Set
from main import LayoffTracker
from config import EVENT_TYPES, NEWS_API_KEY, NEWS_API_EVERYTHING_URL
import requests
import time

def get_stock_price_change(tracker: LayoffTracker, ticker: str, days: int = 30) -> Tuple[float, float]:
    """Get stock price change over last N days using Prixe.io API"""
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Get daily price data using get_stock_price_history
        price_history = tracker.get_stock_price_history(ticker, start_date, end_date)
        
        if not price_history or len(price_history) < 2:
            return None, None
        
        # Get first and last close prices
        first_price = price_history[0].get('close')
        last_price = price_history[-1].get('close')
        
        if first_price and last_price and first_price > 0:
            change_pct = ((last_price - first_price) / first_price) * 100
            return change_pct, last_price
        
        return None, None
    except Exception as e:
        # Handle case where price_history might not be assigned
        return None, None

def get_company_ticker(company_name: str, tracker: LayoffTracker) -> str:
    """Get ticker symbol for company name"""
    try:
        # Try hardcoded bio/pharma tickers first
        ticker_map = tracker._get_bio_pharma_tickers('small_cap_with_options')
        ticker = ticker_map.get(company_name.upper())
        if ticker:
            return ticker
        
        ticker_map = tracker._get_bio_pharma_tickers('mid_cap')
        ticker = ticker_map.get(company_name.upper())
        if ticker:
            return ticker
        
        # Fallback to general method
        return tracker.get_stock_ticker(company_name)
    except:
        return None

def fetch_news_for_ticker(ticker: str, company_name: str, days: int = 30) -> List[Dict]:
    """Fetch news articles for a ticker using Google News API"""
    articles = []
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Search by company name and ticker
        query = f'"{company_name}" OR "{ticker}"'
        
        params = {
            'q': query,
            'apiKey': NEWS_API_KEY,
            'language': 'en',
            'sortBy': 'publishedAt',
            'from': start_date.strftime('%Y-%m-%d'),
            'to': end_date.strftime('%Y-%m-%d'),
            'pageSize': 50
        }
        
        response = requests.get(NEWS_API_EVERYTHING_URL, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            articles = data.get('articles', [])
        
        time.sleep(0.5)  # Rate limiting
    except Exception as e:
        print(f"    Error fetching news for {ticker}: {e}")
    
    return articles

def extract_phrases_from_text(text: str, min_length: int = 3, max_length: int = 5) -> List[str]:
    """Extract meaningful phrases from text"""
    if not text:
        return []
    
    text_lower = text.lower()
    
    # Remove special characters but keep spaces
    text_clean = re.sub(r'[^\w\s]', ' ', text_lower)
    
    # Split into words
    words = text_clean.split()
    
    # Extract n-grams (phrases of 2-5 words)
    phrases = []
    for n in range(2, max_length + 1):
        for i in range(len(words) - n + 1):
            phrase = ' '.join(words[i:i+n])
            if len(phrase) >= min_length:
                phrases.append(phrase)
    
    return phrases

def analyze_news_terms(articles: List[Dict], existing_keywords: Set[str]) -> Dict[str, int]:
    """Analyze news articles to find common terms not in existing keywords"""
    all_phrases = []
    
    for article in articles:
        title = article.get('title', '')
        description = article.get('description', '')
        content = f"{title} {description}"
        
        # Extract phrases
        phrases = extract_phrases_from_text(content)
        all_phrases.extend(phrases)
    
    # Count phrase frequency
    phrase_counts = Counter(all_phrases)
    
    # Filter out phrases that are already in keywords (case-insensitive)
    existing_lower = {k.lower() for k in existing_keywords}
    new_phrases = {
        phrase: count 
        for phrase, count in phrase_counts.items() 
        if phrase.lower() not in existing_lower and count >= 2  # At least 2 occurrences
    }
    
    return new_phrases

def get_existing_keywords() -> Set[str]:
    """Get all existing keywords from bio_positive_news and bio_negative_news"""
    positive = set(EVENT_TYPES.get('bio_positive_news', {}).get('keywords', []))
    negative = set(EVENT_TYPES.get('bio_negative_news', {}).get('keywords', []))
    return positive.union(negative)

def find_dramatic_movers(tracker: LayoffTracker, min_change: float = 30.0) -> List[Tuple[str, str, float]]:
    """Find bio stocks with dramatic moves in last 30 days"""
    print("=" * 80)
    print("FINDING DRAMATIC MOVERS (Last 30 Days)")
    print("=" * 80)
    print()
    
    # Get bio companies
    companies = tracker._get_bio_pharma_companies('small_cap_with_options')
    companies.extend(tracker._get_bio_pharma_companies('mid_cap'))
    
    print(f"Checking {len(companies)} bio companies...")
    print()
    
    movers = []
    
    # Get ticker mappings
    small_cap_tickers = tracker._get_bio_pharma_tickers('small_cap_with_options')
    mid_cap_tickers = tracker._get_bio_pharma_tickers('mid_cap')
    all_ticker_map = {**small_cap_tickers, **mid_cap_tickers}
    
    for i, company in enumerate(companies[:50], 1):  # Limit to 50 for testing
        ticker = all_ticker_map.get(company.upper())
        if not ticker:
            # Try fallback
            ticker = tracker.get_stock_ticker(company)
        if not ticker:
            continue
        
        print(f"[{i}/{min(50, len(companies))}] {company} ({ticker})...", end=' ', flush=True)
        change_pct, price = get_stock_price_change(tracker, ticker, days=30)
        
        if change_pct is not None:
            if abs(change_pct) >= min_change:
                direction = "↑" if change_pct > 0 else "↓"
                print(f"{direction} {change_pct:.1f}%")
                movers.append((company, ticker, change_pct))
            else:
                print(f"{change_pct:.1f}%")
        else:
            print("N/A")
        
        time.sleep(0.2)  # Rate limiting
    
    print()
    print(f"Found {len(movers)} dramatic movers (>{min_change}% change)")
    print()
    
    return movers

def analyze_movers_news(movers: List[Tuple[str, str, float]]) -> Dict:
    """Analyze news for dramatic movers and extract useful terms"""
    print("=" * 80)
    print("ANALYZING NEWS FOR DRAMATIC MOVERS")
    print("=" * 80)
    print()
    
    existing_keywords = get_existing_keywords()
    print(f"Existing keywords count: {len(existing_keywords)}")
    print()
    
    positive_articles = []
    negative_articles = []
    
    for company, ticker, change_pct in movers:
        direction = "positive" if change_pct > 0 else "negative"
        print(f"Fetching news for {company} ({ticker}) - {direction} ({change_pct:.1f}%)...")
        
        articles = fetch_news_for_ticker(ticker, company, days=30)
        print(f"  Found {len(articles)} articles")
        
        if change_pct > 0:
            positive_articles.extend(articles)
        else:
            negative_articles.extend(articles)
        
        time.sleep(1)  # Rate limiting
    
    print()
    print(f"Total positive articles: {len(positive_articles)}")
    print(f"Total negative articles: {len(negative_articles)}")
    print()
    
    # Analyze terms
    print("Extracting terms from positive news...")
    positive_terms = analyze_news_terms(positive_articles, existing_keywords)
    
    print("Extracting terms from negative news...")
    negative_terms = analyze_news_terms(negative_articles, existing_keywords)
    
    return {
        'positive_terms': positive_terms,
        'negative_terms': negative_terms,
        'positive_articles_count': len(positive_articles),
        'negative_articles_count': len(negative_articles)
    }

def suggest_keyword_additions(analysis: Dict) -> Dict:
    """Suggest keyword additions based on analysis"""
    print("=" * 80)
    print("KEYWORD SUGGESTIONS")
    print("=" * 80)
    print()
    
    # Filter and rank terms
    positive_terms = analysis['positive_terms']
    negative_terms = analysis['negative_terms']
    
    # Get top terms (by frequency)
    top_positive = sorted(positive_terms.items(), key=lambda x: x[1], reverse=True)[:50]
    top_negative = sorted(negative_terms.items(), key=lambda x: x[1], reverse=True)[:50]
    
    # Filter for bio/pharma relevant terms
    bio_keywords = [
        'phase', 'trial', 'fda', 'clinical', 'drug', 'treatment', 'therapy',
        'approval', 'endpoint', 'data', 'results', 'safety', 'efficacy',
        'biotech', 'pharma', 'oncology', 'cancer', 'patient', 'dose',
        'regulatory', 'submission', 'nda', 'bla', 'ind', 'pipeline',
        'efficacy', 'response', 'survival', 'progression', 'disease',
        'indication', 'label', 'designation', 'review', 'advisory'
    ]
    
    def is_bio_relevant(phrase: str) -> bool:
        phrase_lower = phrase.lower()
        return any(keyword in phrase_lower for keyword in bio_keywords)
    
    filtered_positive = [(p, c) for p, c in top_positive if is_bio_relevant(p)]
    filtered_negative = [(p, c) for p, c in top_negative if is_bio_relevant(p)]
    
    print("TOP POSITIVE TERMS (Bio-relevant):")
    print("-" * 80)
    for phrase, count in filtered_positive[:30]:
        print(f"  '{phrase}' ({count} occurrences)")
    print()
    
    print("TOP NEGATIVE TERMS (Bio-relevant):")
    print("-" * 80)
    for phrase, count in filtered_negative[:30]:
        print(f"  '{phrase}' ({count} occurrences)")
    print()
    
    return {
        'suggested_positive': [p for p, c in filtered_positive[:20]],
        'suggested_negative': [p for p, c in filtered_negative[:20]]
    }

def main():
    """Main test function"""
    print("=" * 80)
    print("BIO STOCK NEWS TERM ANALYSIS")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Step 1: Find dramatic movers
    movers = find_dramatic_movers(tracker, min_change=30.0)
    
    if not movers:
        print("No dramatic movers found. Try lowering min_change threshold.")
        return
    
    # Step 2: Analyze news
    analysis = analyze_movers_news(movers)
    
    # Step 3: Suggest additions
    suggestions = suggest_keyword_additions(analysis)
    
    # Step 4: Output results
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"Dramatic movers analyzed: {len(movers)}")
    print(f"Positive articles: {analysis['positive_articles_count']}")
    print(f"Negative articles: {analysis['negative_articles_count']}")
    print(f"Suggested positive keywords: {len(suggestions['suggested_positive'])}")
    print(f"Suggested negative keywords: {len(suggestions['suggested_negative'])}")
    print()
    
    # Save suggestions to file
    output = {
        'date': datetime.now().isoformat(),
        'movers_analyzed': len(movers),
        'suggested_positive_keywords': suggestions['suggested_positive'],
        'suggested_negative_keywords': suggestions['suggested_negative'],
        'all_positive_terms': dict(analysis['positive_terms']),
        'all_negative_terms': dict(analysis['negative_terms'])
    }
    
    with open('bio_news_term_suggestions.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print("✅ Results saved to: bio_news_term_suggestions.json")
    print()
    print("Next steps:")
    print("1. Review suggested keywords")
    print("2. Add high-quality terms to config.py")
    print("3. Test with unit test to verify improvements")

if __name__ == '__main__':
    main()

