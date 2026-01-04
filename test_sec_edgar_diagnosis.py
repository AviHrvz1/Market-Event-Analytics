#!/usr/bin/env python3
"""
Diagnostic test to understand why SEC EDGAR search isn't finding expected filings
"""

import sys
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from config import SEC_EDGAR_BASE_URL, SEC_USER_AGENT, LOOKBACK_DAYS, EVENT_TYPES

print("=" * 80)
print("SEC EDGAR Search Diagnosis")
print("=" * 80)
print()

# Expected filings that should be found
expected_filings = [
    {
        'date': '2025-12-11',
        'company': 'MAIA Biotechnology',
        'ticker': 'MAIA',
        'description': 'Insider buying disclosure + update on its telomere‑targeting cancer therapy (ateganosine) showing encouraging trial results',
        'keywords_to_match': ['trial results', 'phase 2', 'clinical trial', 'trial data']
    },
    {
        'date': '2025-12-10',
        'company': 'Immuron',
        'ticker': 'IMRN',
        'description': 'Reported failure in its ETEC vaccine trial',
        'keywords_to_match': ['trial failure', 'trial setback', 'trial failed']
    },
    {
        'date': '2025-12-09',
        'company': 'Applied Therapeutics',
        'ticker': 'APLT',
        'description': 'Disclosed Phase 2 trial results that missed endpoints',
        'keywords_to_match': ['phase 2 trial', 'missed endpoints', 'trial results', 'phase 2 failure']
    },
    {
        'date': '2025-12-05',
        'company': 'Merck',
        'ticker': 'MRK',
        'description': 'Quarterly earnings release + 2025 guidance',
        'keywords_to_match': ['earnings', 'guidance', 'earnings release']
    }
]

print("Test 1: Check SEC EDGAR API Response")
print("-" * 80)
print()

url = f"{SEC_EDGAR_BASE_URL}/cgi-bin/browse-edgar"
params = {
    'action': 'getcurrent',
    'type': '8-K',
    'count': '100',
    'output': 'atom'
}
headers = {
    'User-Agent': SEC_USER_AGENT,
    'Accept': 'application/atom+xml,application/xml,text/xml'
}

print(f"Requesting: {url}")
print(f"Params: {params}")
print()

try:
    response = requests.get(url, params=params, headers=headers, timeout=15)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'xml')
        entries = soup.find_all('entry')
        print(f"✅ Found {len(entries)} entries in Atom feed")
        print()
        
        # Check date range
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=LOOKBACK_DAYS)
        print(f"Date Range Check:")
        print(f"  Today: {now.strftime('%Y-%m-%d')}")
        print(f"  Start Date (LOOKBACK_DAYS={LOOKBACK_DAYS}): {start_date.strftime('%Y-%m-%d')}")
        print()
        
        # Analyze entries
        print("Test 2: Analyze Recent Entries")
        print("-" * 80)
        print()
        
        recent_entries = []
        for entry in entries[:20]:  # Check first 20
            title_elem = entry.find('title')
            summary_elem = entry.find('summary')
            link_elem = entry.find('link')
            updated_elem = entry.find('updated')
            
            if not title_elem:
                continue
            
            title_text = title_elem.text.strip() if title_elem.text else ''
            summary_text = summary_elem.text.strip() if summary_elem and summary_elem.text else ''
            
            # Parse date
            try:
                if updated_elem and updated_elem.text:
                    published_at = datetime.fromisoformat(updated_elem.text.replace('Z', '+00:00'))
                else:
                    continue
                
                # Check if within date range
                if published_at >= start_date:
                    recent_entries.append({
                        'title': title_text,
                        'summary': summary_text,
                        'date': published_at.strftime('%Y-%m-%d'),
                        'url': link_elem.get('href', '') if link_elem else ''
                    })
            except Exception as e:
                print(f"  ⚠️  Error parsing entry date: {e}")
                continue
        
        print(f"Found {len(recent_entries)} entries within {LOOKBACK_DAYS} days:")
        print()
        for i, entry in enumerate(recent_entries[:10], 1):
            print(f"{i}. Date: {entry['date']}")
            print(f"   Title: {entry['title'][:80]}...")
            print(f"   Summary: {entry['summary'][:80] if entry['summary'] else 'N/A'}...")
            print()
        
        # Check for expected companies
        print("Test 3: Check for Expected Companies")
        print("-" * 80)
        print()
        
        for expected in expected_filings:
            found = False
            matching_entries = []
            
            for entry in recent_entries:
                title_lower = entry['title'].lower()
                summary_lower = entry['summary'].lower()
                combined = f"{title_lower} {summary_lower}"
                
                # Check if company name or ticker appears
                if (expected['company'].lower() in combined or 
                    expected['ticker'].lower() in combined or
                    expected['ticker'].lower() in title_lower):
                    found = True
                    matching_entries.append(entry)
            
            if found:
                print(f"✅ Found {expected['company']} ({expected['ticker']}):")
                for entry in matching_entries:
                    print(f"   - {entry['date']}: {entry['title'][:60]}...")
            else:
                print(f"❌ NOT FOUND: {expected['company']} ({expected['ticker']})")
                print(f"   Expected date: {expected['date']}")
        
        print()
        print("Test 4: Check Keyword Matching")
        print("-" * 80)
        print()
        
        # Get SEC EDGAR event type keywords
        if 'sec_edgar' in EVENT_TYPES:
            sec_keywords = EVENT_TYPES['sec_edgar']['keywords']
            print(f"SEC EDGAR event type has {len(sec_keywords)} keywords")
            print()
            
            # Test if expected filing descriptions would match
            for expected in expected_filings:
                print(f"Testing: {expected['company']} - {expected['description']}")
                description_lower = expected['description'].lower()
                
                matching_keywords = []
                for keyword in sec_keywords:
                    if keyword.lower() in description_lower:
                        matching_keywords.append(keyword)
                
                if matching_keywords:
                    print(f"  ✅ Would match keywords: {', '.join(matching_keywords[:5])}")
                else:
                    print(f"  ❌ Would NOT match any keywords")
                    print(f"  Expected keywords: {', '.join(expected['keywords_to_match'])}")
                print()
        else:
            print("❌ 'sec_edgar' event type not found in EVENT_TYPES")
        
        print()
        print("Test 5: Check Event Type Matching Logic")
        print("-" * 80)
        print()
        
        # Simulate the matching logic from search_sec_edgar
        if 'sec_edgar' in EVENT_TYPES:
            event_types = ['sec_edgar']
            all_keywords = []
            for event_type in event_types:
                if event_type in EVENT_TYPES:
                    all_keywords.extend(EVENT_TYPES[event_type]['keywords'])
            
            print(f"Keywords for event type 'sec_edgar': {len(all_keywords)}")
            print(f"Sample keywords: {all_keywords[:10]}")
            print()
            
            # Test matching on sample entries
            print("Testing keyword matching on recent entries:")
            print()
            for entry in recent_entries[:5]:
                title_text = entry['title']
                summary_text = entry['summary']
                combined_text = f"{title_text} {summary_text}".lower()
                
                matches = any(keyword.lower() in combined_text for keyword in all_keywords)
                
                if matches:
                    matching_kw = [kw for kw in all_keywords if kw.lower() in combined_text][:3]
                    print(f"✅ {entry['date']}: {title_text[:50]}...")
                    print(f"   Matches: {', '.join(matching_kw)}")
                else:
                    print(f"❌ {entry['date']}: {title_text[:50]}...")
                    print(f"   No keyword matches")
                print()
        
    else:
        print(f"❌ HTTP {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("Diagnosis Complete")
print("=" * 80)

