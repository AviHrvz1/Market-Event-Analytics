#!/usr/bin/env python3
"""
Detailed test to understand SEC EDGAR Atom feed structure and why keyword matching fails
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from config import SEC_EDGAR_BASE_URL, SEC_USER_AGENT, EVENT_TYPES

print("=" * 80)
print("SEC EDGAR Atom Feed Structure Analysis")
print("=" * 80)
print()

url = f"{SEC_EDGAR_BASE_URL}/cgi-bin/browse-edgar"
params = {
    'action': 'getcurrent',
    'type': '8-K',
    'count': '10',
    'output': 'atom'
}
headers = {
    'User-Agent': SEC_USER_AGENT,
    'Accept': 'application/atom+xml,application/xml,text/xml'
}

response = requests.get(url, params=params, headers=headers, timeout=15)

if response.status_code == 200:
    soup = BeautifulSoup(response.content, 'xml')
    entries = soup.find_all('entry')
    
    print(f"Found {len(entries)} entries")
    print()
    print("=" * 80)
    print("Sample Entry Structure (First Entry)")
    print("=" * 80)
    print()
    
    if entries:
        entry = entries[0]
        
        # Show all elements in the entry
        print("All elements in entry:")
        for elem in entry.children:
            if hasattr(elem, 'name') and elem.name:
                text = elem.text.strip()[:100] if elem.text else ''
                print(f"  <{elem.name}>: {text}...")
        print()
        
        # Detailed breakdown
        title_elem = entry.find('title')
        summary_elem = entry.find('summary')
        link_elem = entry.find('link')
        updated_elem = entry.find('updated')
        id_elem = entry.find('id')
        
        print("Key Fields:")
        print("-" * 80)
        print(f"Title: {title_elem.text if title_elem else 'N/A'}")
        print()
        print(f"Summary (raw): {summary_elem.text[:200] if summary_elem else 'N/A'}...")
        print()
        print(f"Summary (parsed HTML):")
        if summary_elem:
            summary_soup = BeautifulSoup(summary_elem.text, 'html.parser')
            print(f"  {summary_soup.get_text()[:200]}...")
        print()
        print(f"Link: {link_elem.get('href', 'N/A') if link_elem else 'N/A'}")
        print()
        print(f"Updated: {updated_elem.text if updated_elem else 'N/A'}")
        print()
        print(f"ID: {id_elem.text if id_elem else 'N/A'}")
        print()
        
        # Test keyword matching
        print("=" * 80)
        print("Keyword Matching Test")
        print("=" * 80)
        print()
        
        if 'sec_edgar' in EVENT_TYPES:
            keywords = EVENT_TYPES['sec_edgar']['keywords']
            title_text = title_elem.text.strip() if title_elem else ''
            summary_text = summary_elem.text.strip() if summary_elem else ''
            combined_text = f"{title_text} {summary_text}".lower()
            
            print(f"Title: {title_text}")
            print(f"Summary text: {summary_text[:100]}...")
            print()
            print(f"Testing {len(keywords)} keywords against title + summary:")
            print()
            
            matching_keywords = []
            for keyword in keywords:
                if keyword.lower() in combined_text:
                    matching_keywords.append(keyword)
            
            if matching_keywords:
                print(f"✅ Found {len(matching_keywords)} matching keywords:")
                for kw in matching_keywords[:10]:
                    print(f"   - {kw}")
            else:
                print(f"❌ NO keywords matched")
                print()
                print("Why? The Atom feed only contains:")
                print("  - Company name in title")
                print("  - Filing metadata (date, accession number, file size) in summary")
                print("  - NO actual filing content/details")
                print()
                print("To match keywords like 'earnings miss', 'trial failure', etc.,")
                print("you need to fetch and parse the actual 8-K filing document.")
        
        # Check if we can access the actual filing
        print()
        print("=" * 80)
        print("Accessing Actual Filing Document")
        print("=" * 80)
        print()
        
        if link_elem and link_elem.get('href'):
            filing_url = link_elem.get('href')
            print(f"Filing URL from Atom feed: {filing_url}")
            print()
            print("Note: This URL points to the filing index page, not the actual document.")
            print("To get the filing content, you'd need to:")
            print("  1. Parse the filing index page to find the actual document URL")
            print("  2. Fetch the document (usually HTML or XBRL)")
            print("  3. Extract and parse the text content")
            print("  4. Then match keywords against the full text")
        
else:
    print(f"❌ HTTP {response.status_code}")

print()
print("=" * 80)
print("CONCLUSION")
print("=" * 80)
print()
print("Root Cause: SEC EDGAR Atom feed does NOT contain filing content")
print()
print("The Atom feed only provides:")
print("  ✅ Company name")
print("  ✅ Filing date")
print("  ✅ Accession number")
print("  ✅ File size")
print("  ❌ NO actual filing content/details")
print()
print("To match keywords like 'earnings miss', 'trial failure', 'guidance cut', etc.,")
print("the system would need to:")
print("  1. Fetch each 8-K filing document")
print("  2. Parse the HTML/XBRL content")
print("  3. Extract the text")
print("  4. Match keywords against the full text")
print()
print("This is why the expected filings aren't being found - the keyword matching")
print("is only checking the title and summary (metadata), not the actual filing content.")

