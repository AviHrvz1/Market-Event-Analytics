#!/usr/bin/env python3
"""
Test to check why certain companies weren't found:
- EQ (Equillium Inc.) - +20% pre-market
- ABVX (Abivax SA) - +19.04%
- QNTM (Quantum Biopharma) - +18.45%
- AMLX (Amylyx Pharmaceuticals) - +12.31%
- THAR (Tharimmune) - +12%+
- GSIT (GSI Technology) - +26.24%
"""

import sys
from main import LayoffTracker

def test_missing_companies():
    """Check if these companies are in the bio/pharma lists"""
    print("=" * 80)
    print("MISSING COMPANIES ANALYSIS")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Companies to check
    companies_to_check = {
        'EQ': 'Equillium Inc.',
        'ABVX': 'Abivax SA',
        'QNTM': 'Quantum Biopharma',
        'AMLX': 'Amylyx Pharmaceuticals',
        'THAR': 'Tharimmune',
        'GSIT': 'GSI Technology'
    }
    
    # Check all categories
    categories = {
        'all': tracker._get_bio_pharma_companies('all'),
        'small_cap': tracker._get_bio_pharma_companies('small_cap'),
        'small_cap_with_options': tracker._get_bio_pharma_companies('small_cap_with_options'),
        'mid_cap': tracker._get_bio_pharma_companies('mid_cap')
    }
    
    print("Checking company names in bio/pharma lists...")
    print()
    
    for ticker, company_name in companies_to_check.items():
        print(f"🔍 {ticker} - {company_name}")
        print("-" * 80)
        
        found_in = []
        
        # Check each category
        for cat_name, company_list in categories.items():
            # Check exact match
            if company_name.upper() in company_list:
                found_in.append(f"{cat_name} (exact match)")
            # Check partial match
            elif any(company_name.upper() in c.upper() or c.upper() in company_name.upper() for c in company_list):
                matches = [c for c in company_list if company_name.upper() in c.upper() or c.upper() in company_name.upper()]
                found_in.append(f"{cat_name} (partial: {matches})")
        
        if found_in:
            print(f"  ✅ Found in: {', '.join(found_in)}")
        else:
            print(f"  ❌ NOT FOUND in any bio/pharma list")
            print(f"     Company name: '{company_name}'")
            print(f"     Ticker: {ticker}")
            print(f"     This company needs to be added to the bio/pharma lists")
        
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    missing = []
    for ticker, company_name in companies_to_check.items():
        found = False
        for cat_name, company_list in categories.items():
            if company_name.upper() in company_list or any(company_name.upper() in c.upper() or c.upper() in company_name.upper() for c in company_list):
                found = True
                break
        if not found:
            missing.append((ticker, company_name))
    
    if missing:
        print(f"❌ {len(missing)} companies are MISSING from bio/pharma lists:")
        for ticker, company_name in missing:
            print(f"   - {ticker} ({company_name})")
        print()
        print("These companies need to be added to the appropriate bio/pharma category.")
    else:
        print("✅ All companies are in the bio/pharma lists")
    
    # Also check ticker mapping (mapping is company name -> ticker, not ticker -> company)
    print()
    print("=" * 80)
    print("TICKER MAPPING CHECK")
    print("=" * 80)
    print()
    
    tickers = tracker._get_bio_pharma_tickers('all')
    for ticker, company_name in companies_to_check.items():
        company_upper = company_name.upper()
        # Check if company name maps to ticker
        if company_upper in tickers:
            if tickers[company_upper] == ticker:
                print(f"✅ {ticker} ({company_name}) is correctly mapped")
            else:
                print(f"⚠️  {company_name} maps to {tickers[company_upper]}, expected {ticker}")
        else:
            # Try partial match
            found = False
            for comp_name, comp_ticker in tickers.items():
                if company_upper in comp_name or comp_name in company_upper:
                    if comp_ticker == ticker:
                        print(f"✅ {ticker} ({company_name}) is mapped as '{comp_name}' -> {comp_ticker}")
                        found = True
                        break
            if not found:
                print(f"❌ {ticker} ({company_name}) is NOT in ticker mapping")
    
    return len(missing) == 0

if __name__ == "__main__":
    success = test_missing_companies()
    sys.exit(0 if success else 1)

