#!/usr/bin/env python3
"""
Debug yfinance news to see what it actually returns
"""

import sys
from datetime import datetime, timezone, timedelta

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    print("❌ yfinance not available")
    sys.exit(1)

def debug_yfinance_news(ticker: str):
    """Debug what yfinance returns for news"""
    print(f"\n{'='*80}")
    print(f"Debugging yfinance news for: {ticker}")
    print(f"{'='*80}\n")
    
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        
        if not news:
            print(f"❌ No news found for {ticker}")
            return
        
        print(f"✅ Found {len(news)} total news articles\n")
        
        # Show all articles with dates
        now = datetime.now(timezone.utc)
        print("All articles (showing first 10):")
        print("-" * 80)
        
        # First, show the structure of the first article
        if news:
            print("First article structure:")
            print(f"Keys: {list(news[0].keys())}")
            print(f"Full first article: {news[0]}")
            print()
        
        for i, article in enumerate(news[:10], 1):
            # Try different possible keys
            title = article.get('title') or article.get('headline') or article.get('summary') or 'No title'
            pub_time = article.get('providerPublishTime') or article.get('pubDate') or article.get('publishedAt') or 0
            
            if pub_time:
                if isinstance(pub_time, (int, float)):
                    pub_date = datetime.fromtimestamp(pub_time, tz=timezone.utc)
                else:
                    # Try to parse string date
                    try:
                        pub_date = datetime.fromisoformat(str(pub_time).replace('Z', '+00:00'))
                    except:
                        pub_date = None
                
                if pub_date:
                    days_old = (now - pub_date).days
                    date_str = pub_date.strftime('%Y-%m-%d %H:%M:%S UTC')
                else:
                    date_str = f"Unknown format: {pub_time}"
                    days_old = None
            else:
                date_str = "No date"
                days_old = None
            
            print(f"{i}. {str(title)[:70]}...")
            print(f"   Date: {date_str}")
            if days_old is not None:
                print(f"   Age: {days_old} days ago")
            print(f"   All keys: {list(article.keys())}")
            print()
        
        # Analyze date range
        if news:
            dates = []
            for article in news:
                pub_time = article.get('providerPublishTime', 0)
                if pub_time:
                    pub_date = datetime.fromtimestamp(pub_time, tz=timezone.utc)
                    dates.append(pub_date)
            
            if dates:
                oldest = min(dates)
                newest = max(dates)
                date_range = (newest - oldest).days
                
                print(f"\nDate Range Analysis:")
                print(f"  Oldest article: {oldest.strftime('%Y-%m-%d')} ({(now - oldest).days} days ago)")
                print(f"  Newest article: {newest.strftime('%Y-%m-%d')} ({(now - newest).days} days ago)")
                print(f"  Date range span: {date_range} days")
                print(f"  Total articles: {len(news)}")
                
                # Check if we can get articles older than 30 days
                articles_older_than_30_days = sum(1 for d in dates if (now - d).days > 30)
                print(f"  Articles older than 30 days: {articles_older_than_30_days}/{len(dates)}")
        
        return news
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Test with popular stocks
    test_tickers = ['AAPL', 'MSFT', 'TSLA']
    
    print("=" * 80)
    print("YFINANCE NEWS DEBUG")
    print("=" * 80)
    
    for ticker in test_tickers:
        debug_yfinance_news(ticker)
        print()

