#!/usr/bin/env python3
"""
Test to verify if Google News RSS actually supports 120-day lookback
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from dateutil import parser
import urllib.parse

print(f"\n{'='*80}")
print("Testing Google News RSS 120-Day Lookback")
print(f"{'='*80}\n")

# Test different when: parameters
test_periods = [30, 60, 90, 120, 365]

search_query = "recall OR product recall"
base_url = "https://news.google.com/rss/search"

for days in test_periods:
    print(f"\n{'='*80}")
    print(f"Testing when:{days}d")
    print(f"{'='*80}")
    
    encoded_query = urllib.parse.quote_plus(f"{search_query} when:{days}d")
    url = f"{base_url}?q={encoded_query}&hl=en-US&gl=US&ceid=US:en&num=100"
    
    print(f"URL: {url[:100]}...")
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item')
            
            print(f"✅ Status 200 - {len(items)} articles returned")
            
            if items:
                # Check date range of returned articles
                dates = []
                for item in items[:10]:  # Check first 10
                    pub_date_elem = item.find('pubDate')
                    if pub_date_elem:
                        try:
                            pub_date = parser.parse(pub_date_elem.text)
                            if pub_date.tzinfo is None:
                                pub_date = pub_date.replace(tzinfo=timezone.utc)
                            dates.append(pub_date)
                        except:
                            pass
                
                if dates:
                    now = datetime.now(timezone.utc)
                    oldest_date = min(dates)
                    newest_date = max(dates)
                    oldest_days_ago = (now - oldest_date).days
                    newest_days_ago = (now - newest_date).days
                    
                    print(f"   Date range of returned articles:")
                    print(f"   - Newest: {newest_days_ago} days ago ({newest_date.strftime('%Y-%m-%d')})")
                    print(f"   - Oldest: {oldest_days_ago} days ago ({oldest_date.strftime('%Y-%m-%d')})")
                    
                    if oldest_days_ago <= days:
                        print(f"   ✅ Oldest article is within {days}-day window")
                    else:
                        print(f"   ⚠️  Oldest article is {oldest_days_ago} days ago (beyond {days}-day window)")
                        print(f"   → Google News may be capping results")
            else:
                print(f"   ⚠️  No articles returned")
        else:
            print(f"❌ Status {response.status_code}")
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Error: {e}")

print(f"\n{'='*80}")
print("Conclusion")
print(f"{'='*80}\n")
print("If Google News only returns articles from the last 30 days regardless of when:120d,")
print("then Google News RSS has a maximum limit (likely 30 or 90 days).")
print("The 120-day setting will still work for:")
print("  1. Date filtering (filters articles to 120 days)")
print("  2. Other sources (Benzinga, etc.)")
print("  3. If Google News supports it in the future")

