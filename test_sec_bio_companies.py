#!/usr/bin/env python3
"""
Unit test to check if we can dynamically load bio/pharma companies from SEC SIC codes.
Tests loading companies with SIC codes 2834 (Pharmaceuticals) and 2836 (Biological Products).
"""

import sys
import requests
import json
import time
from typing import List, Dict, Set
from config import SEC_EDGAR_BASE_URL, SEC_EDGAR_COMPANY_API, SEC_USER_AGENT

# Bio/pharma SIC codes
BIO_SIC_CODES = [2834, 2836]  # Pharmaceuticals and Biological Products

def get_current_bio_companies() -> Set[str]:
    """Get the current hardcoded bio companies list"""
    # Current hardcoded list from main.py (as of latest update)
    current_list = [
        'PFIZER', 'MERCK', 'JOHNSON & JOHNSON', 'ABBVIE', 'BRISTOL-MYERS SQUIBB',
        'AMGEN', 'GILEAD SCIENCES', 'BIOGEN', 'REGENERON', 'MODERNA',
        'BIONTECH', 'NOVAVAX', 'ILLUMINA', 'VERTEX PHARMACEUTICALS', 'ALEXION',
        'CELGENE', 'ALNYLAM', 'IONIS PHARMACEUTICALS', 'SAGE THERAPEUTICS', 'BLUEBIRD BIO',
        'SPARK THERAPEUTICS', 'JUNO THERAPEUTICS', 'KITE PHARMA', 'NEUROCRINE BIOSCIENCES',
        'EXELIXIS', 'INCYTE', 'SEATTLE GENETICS', 'CLOVIS ONCOLOGY', 'TESARO',
        'ACADIA PHARMACEUTICALS', 'ARRAY BIOPHARMA', 'ARQULE', 'AVEO PHARMACEUTICALS',
        'CARA THERAPEUTICS', 'CRINETICS PHARMACEUTICALS', 'CURIS', 'CYTOMX THERAPEUTICS',
        'DICERNA PHARMACEUTICALS', 'EPIZYME', 'FATE THERAPEUTICS', 'FIBROGEN',
        'GOSSAMER BIO', 'HORIZON THERAPEUTICS', 'IMMUNOGEN', 'IMMUNOMEDICS',
        'INOVIO PHARMACEUTICALS', 'INTERCEPT PHARMACEUTICALS', 'KARYOPHARM THERAPEUTICS',
        'KURA ONCOLOGY', 'MIRATI THERAPEUTICS', 'NEUROCRINE', 'NOVOCURE',
        'ONCOMED PHARMACEUTICALS', 'PORTOLA PHARMACEUTICALS', 'PRECISION BIOSCIENCES',
        'RIGEL PHARMACEUTICALS', 'RUBIUS THERAPEUTICS', 'SANGAMO THERAPEUTICS',
        'SERES THERAPEUTICS', 'SYNAGEVA BIOPHARMA', 'SYNERGY PHARMACEUTICALS',
        'SYROS PHARMACEUTICS', 'THERAVANCE BIOPHARMA', 'TRACON PHARMACEUTICALS',
        'TREVENA', 'TRICIDA', 'ZOETIS', 'ZYMEWORKS',
        # Recently added
        'AMC ROBOTICS CORPORATION', 'NOVABAY PHARMACEUTICALS', 'ATHIRA PHARMA',
        'CUMBERLAND PHARMACEUTICALS', 'CENTURY THERAPEUTICS', 'VISTAGEN THERAPEUTICS',
        'PYXIS ONCOLOGY', 'GEOVAX LABS'
    ]
    return set(c.upper().strip() for c in current_list)

def load_sec_company_tickers() -> Dict:
    """Load SEC company tickers JSON file"""
    print("📥 Loading SEC company tickers...")
    url = f"{SEC_EDGAR_BASE_URL}/files/company_tickers.json"
    headers = {'User-Agent': SEC_USER_AGENT}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Loaded {len(data)} company entries from SEC")
            return data
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            return {}
    except Exception as e:
        print(f"❌ Error loading SEC tickers: {e}")
        return {}

def get_company_sic_code(cik: str) -> int:
    """Get SIC code for a company by CIK"""
    url = f"{SEC_EDGAR_COMPANY_API}/CIK{cik.zfill(10)}.json"
    headers = {'User-Agent': SEC_USER_AGENT}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # SIC code is in the company data
            sic = data.get('sic', '')
            if sic:
                try:
                    # SIC might be a string like "2834" or a number
                    return int(str(sic).split('-')[0])  # Handle "2834-2834" format
                except:
                    return None
        return None
    except Exception as e:
        # Rate limiting - be respectful
        time.sleep(0.1)  # Small delay between requests
        return None

def load_bio_companies_from_sec() -> List[Dict]:
    """Load all bio/pharma companies from SEC based on SIC codes"""
    print("\n" + "="*80)
    print("Loading Bio/Pharma Companies from SEC SIC Codes")
    print("="*80)
    
    # Load all company tickers
    tickers_data = load_sec_company_tickers()
    if not tickers_data:
        print("❌ Could not load SEC tickers")
        return []
    
    # Convert to list format (SEC JSON has numeric keys)
    companies = []
    if isinstance(tickers_data, dict):
        # Check if it's the format with numeric keys
        if '0' in tickers_data or 0 in tickers_data:
            # Format: {"0": {"cik_str": "0000320193", "ticker": "MSFT", "title": "MICROSOFT CORP"}, ...}
            for key, company in tickers_data.items():
                companies.append({
                    'cik': company.get('cik_str', '').zfill(10),
                    'ticker': company.get('ticker', ''),
                    'name': company.get('title', '')
                })
        else:
            # Might be different format
            print(f"⚠️ Unexpected SEC data format. Keys: {list(tickers_data.keys())[:5]}")
            return []
    
    print(f"📊 Processing {len(companies)} companies to find bio/pharma...")
    print("   (This may take a few minutes due to rate limiting)")
    
    bio_companies = []
    processed = 0
    errors = 0
    
    for company in companies:
        processed += 1
        if processed % 100 == 0:
            print(f"   Processed {processed}/{len(companies)} companies...")
        
        cik = company['cik']
        sic = get_company_sic_code(cik)
        
        if sic in BIO_SIC_CODES:
            bio_companies.append({
                'cik': cik,
                'ticker': company['ticker'],
                'name': company['name'],
                'sic': sic
            })
        
        # Rate limiting - SEC allows 10 requests per second
        time.sleep(0.11)  # Slightly more than 0.1 to be safe
    
    print(f"\n✅ Found {len(bio_companies)} bio/pharma companies from SEC")
    return bio_companies

def compare_lists(sec_companies: List[Dict], current_companies: Set[str]) -> Dict:
    """Compare SEC companies with current hardcoded list"""
    print("\n" + "="*80)
    print("Comparing SEC Companies with Current List")
    print("="*80)
    
    # Extract company names from SEC data
    sec_names = set()
    sec_by_ticker = {}
    
    for company in sec_companies:
        name_upper = company['name'].upper().strip()
        sec_names.add(name_upper)
        sec_by_ticker[company['ticker']] = {
            'name': name_upper,
            'cik': company['cik'],
            'sic': company['sic']
        }
    
    # Find matches and new companies
    matches = current_companies.intersection(sec_names)
    new_companies = sec_names - current_companies
    missing_from_sec = current_companies - sec_names
    
    return {
        'sec_total': len(sec_companies),
        'current_total': len(current_companies),
        'matches': len(matches),
        'new_companies': new_companies,
        'new_count': len(new_companies),
        'missing_from_sec': missing_from_sec,
        'missing_count': len(missing_from_sec),
        'sec_by_ticker': sec_by_ticker
    }

def main():
    """Run the test"""
    print("\n" + "="*80)
    print("SEC Bio/Pharma Companies Load Test")
    print("="*80)
    print(f"Target SIC codes: {BIO_SIC_CODES}")
    print("  - 2834: Pharmaceutical Preparations")
    print("  - 2836: Biological Products")
    
    # Get current hardcoded list
    print("\n📋 Step 1: Loading current hardcoded bio companies list...")
    current_companies = get_current_bio_companies()
    print(f"✅ Current list has {len(current_companies)} companies")
    
    # Load from SEC
    print("\n📋 Step 2: Loading bio/pharma companies from SEC...")
    sec_companies = load_bio_companies_from_sec()
    
    if not sec_companies:
        print("\n❌ Could not load companies from SEC")
        print("   This might be due to:")
        print("   - Network connectivity issues")
        print("   - SEC API rate limiting")
        print("   - API format changes")
        return
    
    # Compare
    print("\n📋 Step 3: Comparing lists...")
    comparison = compare_lists(sec_companies, current_companies)
    
    # Results
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    print(f"📊 SEC Bio/Pharma Companies Found: {comparison['sec_total']}")
    print(f"📊 Current Hardcoded List: {comparison['current_total']}")
    print(f"✅ Companies in Both Lists: {comparison['matches']}")
    print(f"🆕 New Companies from SEC (not in current list): {comparison['new_count']}")
    print(f"⚠️  Companies in Current List but NOT in SEC: {comparison['missing_count']}")
    
    if comparison['new_count'] > 0:
        print(f"\n🆕 NEW COMPANIES THAT WOULD BE ADDED ({comparison['new_count']}):")
        print("-" * 80)
        # Show first 50 new companies
        new_list = sorted(list(comparison['new_companies']))[:50]
        for i, name in enumerate(new_list, 1):
            # Try to find ticker
            ticker = None
            for tick, info in comparison['sec_by_ticker'].items():
                if info['name'] == name:
                    ticker = tick
                    break
            ticker_str = f" ({ticker})" if ticker else ""
            print(f"  {i:3d}. {name}{ticker_str}")
        
        if comparison['new_count'] > 50:
            print(f"  ... and {comparison['new_count'] - 50} more")
    
    if comparison['missing_count'] > 0:
        print(f"\n⚠️  COMPANIES IN CURRENT LIST BUT NOT IN SEC ({comparison['missing_count']}):")
        print("-" * 80)
        missing_list = sorted(list(comparison['missing_from_sec']))[:20]
        for i, name in enumerate(missing_list, 1):
            print(f"  {i:3d}. {name}")
        if comparison['missing_count'] > 20:
            print(f"  ... and {comparison['missing_count'] - 20} more")
        print("\n   Note: These might be:")
        print("   - Foreign companies not registered with SEC")
        print("   - Companies with different SIC codes")
        print("   - Companies that changed names")
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"✅ Successfully loaded {comparison['sec_total']} bio/pharma companies from SEC")
    print(f"🆕 Would add {comparison['new_count']} new companies to the list")
    print(f"📈 This would increase the list from {comparison['current_total']} to {comparison['current_total'] + comparison['new_count']} companies")
    
    if comparison['new_count'] > 0:
        print(f"\n💡 Recommendation: Consider adding these {comparison['new_count']} companies")
        print("   to improve coverage of bio/pharma news.")
    else:
        print("\n💡 Current list already covers all SEC-registered bio/pharma companies!")

if __name__ == '__main__':
    main()

