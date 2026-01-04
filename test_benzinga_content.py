#!/usr/bin/env python3
"""Quick test to see what content Benzinga RSS feed actually contains"""

import requests
from bs4 import BeautifulSoup
from config import SEC_USER_AGENT

headers = {
    'User-Agent': SEC_USER_AGENT,
    'Accept': 'application/rss+xml, application/xml, text/xml, */*'
}

url = 'https://www.benzinga.com/feed'

try:
    response = requests.get(url, headers=headers, timeout=15)
    print(f"Status: {response.status_code}")
    print()
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')
        
        print(f"Found {len(items)} items")
        print()
        print("Sample titles:")
        for i, item in enumerate(items[:10], 1):
            title_elem = item.find('title')
            desc_elem = item.find('description')
            if title_elem:
                title = title_elem.text.strip()
                desc = desc_elem.text.strip() if desc_elem and desc_elem.text else ''
                print(f"{i}. {title}")
                if desc:
                    print(f"   {desc[:100]}...")
                print()
except Exception as e:
    print(f"Error: {e}")

