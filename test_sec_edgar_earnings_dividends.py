#!/usr/bin/env python3
"""
Unit test to verify if SEC EDGAR can provide earnings and dividend data
"""

import sys
import requests
from datetime import datetime, timedelta
from main import LayoffTracker
from config import SEC_EDGAR_COMPANY_API, SEC_EDGAR_BASE_URL, SEC_USER_AGENT

def test_sec_edgar_earnings_dividends(ticker: str, start_date: datetime, end_date: datetime):
    """Test if we can get earnings and dividend data from SEC EDGAR for a ticker in a date range"""
    print(f"\n{'='*80}")
    print(f"Testing SEC EDGAR: {ticker}")
    print(f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"{'='*80}\n")
    
    result = {
        'ticker': ticker,
        'earnings': [],
        'dividends': [],
        'has_earnings': False,
        'has_dividends': False,
        'earnings_details': [],
        'dividend_details': [],
        'methods_tested': []
    }
    
    tracker = LayoffTracker()
    
    # Step 1: Get CIK from ticker (with fallback to known CIKs)
    print("📋 Step 1: Getting CIK from ticker...")
    cik = tracker.get_cik_from_ticker(ticker)
    
    # Fallback: Use known CIKs for common tickers if lookup fails
    known_ciks = {
        'AAPL': '0000320193',
        'MSFT': '0000789019',
        'JNJ': '0000200406',
        'KO': '0000021344',
        'GOOGL': '0001652044',
        'AMZN': '0001018724',
        'TSLA': '0001318605',
        'META': '0001326801',
        'NVDA': '0001045810',
        'WMT': '0000104169'
    }
    
    if not cik and ticker.upper() in known_ciks:
        cik = known_ciks[ticker.upper()]
        print(f"   ⚠️  Using fallback CIK for {ticker}")
    
    if not cik:
        print(f"   ❌ Could not find CIK for ticker {ticker}")
        return result
    
    print(f"   ✅ Found CIK: {cik}")
    result['methods_tested'].append('get_cik')
    
    # Step 2: Fetch company filings
    print(f"\n📄 Step 2: Fetching company filings from SEC EDGAR...")
    try:
        # SEC API requires CIK to be zero-padded to 10 digits in the URL
        url = f"{SEC_EDGAR_COMPANY_API}/CIK{cik}.json"
        headers = {
            'User-Agent': SEC_USER_AGENT,
            'Accept': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        result['methods_tested'].append('fetch_filings')
        
        if response.status_code != 200:
            print(f"   ❌ HTTP {response.status_code}: {response.text[:200]}")
            return result
        
        data = response.json()
        filings = data.get('filings', {}).get('recent', {})
        
        if not filings:
            print(f"   ⚠️  No filings found")
            return result
        
        print(f"   ✅ Retrieved filings data")
        
        # Extract filing information
        form_types = filings.get('form', [])
        filing_dates = filings.get('filingDate', [])
        accession_numbers = filings.get('accessionNumber', [])
        descriptions = filings.get('description', [])
        
        print(f"   Found {len(form_types)} total filings")
        
        # Step 3: Look for earnings-related filings
        print(f"\n💰 Step 3: Looking for earnings-related filings...")
        print(f"   Searching for: 8-K (Item 2.02), 10-Q, 10-K")
        
        earnings_keywords = ['earnings', 'results of operations', 'financial results', 'quarterly results']
        earnings_forms = ['10-Q', '10-K', '8-K']
        
        earnings_found = []
        for i, form_type in enumerate(form_types):
            if i >= len(filing_dates) or i >= len(accession_numbers):
                continue
            
            try:
                filing_date_str = filing_dates[i]
                filing_date = datetime.strptime(filing_date_str, '%Y-%m-%d').date()
                
                # Check if filing is in date range
                if not (start_date.date() <= filing_date <= end_date.date()):
                    continue
                
                # Check for earnings-related forms
                if form_type in earnings_forms:
                    accession = accession_numbers[i]
                    desc = descriptions[i] if i < len(descriptions) else ''
                    
                    # For 8-K, check if it's Item 2.02 (Results of Operations)
                    is_earnings = False
                    if form_type == '8-K':
                        # Item 2.02 is "Results of Operations and Financial Condition"
                        if '2.02' in desc or 'Results of Operations' in desc:
                            is_earnings = True
                    elif form_type in ['10-Q', '10-K']:
                        # 10-Q and 10-K are quarterly/annual reports (always contain earnings)
                        is_earnings = True
                    
                    if is_earnings:
                        earnings_found.append({
                            'date': filing_date,
                            'form': form_type,
                            'accession': accession,
                            'description': desc
                        })
                        print(f"   ✅ Found {form_type} on {filing_date}: {desc[:60]}")
            except (ValueError, IndexError) as e:
                continue
        
        if earnings_found:
            result['has_earnings'] = True
            result['earnings'] = [e['date'] for e in earnings_found]
            result['earnings_details'] = earnings_found
            print(f"   ✅ Found {len(earnings_found)} earnings-related filing(s)")
        else:
            print(f"   ⚠️  No earnings filings found in date range")
        
        # Step 4: Look for dividend-related filings
        print(f"\n💵 Step 4: Looking for dividend-related filings...")
        print(f"   Searching for: 8-K (Item 8.01 with dividend keywords), DEFA14A (proxy statements)")
        
        dividend_keywords = ['dividend', 'dividend declaration', 'cash dividend', 'quarterly dividend']
        dividend_forms = ['8-K', 'DEFA14A', 'DEF 14A']
        
        dividends_found = []
        for i, form_type in enumerate(form_types):
            if i >= len(filing_dates) or i >= len(accession_numbers):
                continue
            
            try:
                filing_date_str = filing_dates[i]
                filing_date = datetime.strptime(filing_date_str, '%Y-%m-%d').date()
                
                # Check if filing is in date range
                if not (start_date.date() <= filing_date <= end_date.date()):
                    continue
                
                # Check for dividend-related forms
                if form_type in dividend_forms:
                    accession = accession_numbers[i]
                    desc = descriptions[i] if i < len(descriptions) else ''
                    
                    # For 8-K, check if it mentions dividends
                    is_dividend = False
                    if form_type == '8-K':
                        # Check description for dividend keywords
                        desc_lower = desc.lower()
                        if any(keyword in desc_lower for keyword in dividend_keywords):
                            is_dividend = True
                        # Item 8.01 is "Other Events" - often used for dividend declarations
                        if '8.01' in desc and 'dividend' in desc_lower:
                            is_dividend = True
                    elif form_type in ['DEFA14A', 'DEF 14A']:
                        # Proxy statements often contain dividend information
                        desc_lower = desc.lower()
                        if any(keyword in desc_lower for keyword in dividend_keywords):
                            is_dividend = True
                    
                    if is_dividend:
                        dividends_found.append({
                            'date': filing_date,
                            'form': form_type,
                            'accession': accession,
                            'description': desc
                        })
                        print(f"   ✅ Found {form_type} on {filing_date}: {desc[:60]}")
            except (ValueError, IndexError) as e:
                continue
        
        if dividends_found:
            result['has_dividends'] = True
            result['dividends'] = [d['date'] for d in dividends_found]
            result['dividend_details'] = dividends_found
            print(f"   ✅ Found {len(dividends_found)} dividend-related filing(s)")
        else:
            print(f"   ⚠️  No dividend filings found in date range")
        
        # Step 5: Try to get more details from filing documents (optional, slower)
        print(f"\n📑 Step 5: Checking if we can access filing content...")
        print(f"   (This would require fetching and parsing the actual filing documents)")
        print(f"   Note: This is slower and may hit rate limits")
        
        # For now, just note that we could fetch the documents
        if earnings_found or dividends_found:
            print(f"   ℹ️  To get full details, would need to:")
            print(f"      1. Fetch filing document from SEC EDGAR")
            print(f"      2. Parse HTML/XBRL content")
            print(f"      3. Extract specific information (earnings per share, dividend amount, etc.)")
        
        result['methods_tested'].append('parse_filings')
        
    except requests.exceptions.Timeout:
        print(f"   ❌ Request timed out")
        return result
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return result
    
    return result

def main():
    """Run tests on multiple tickers with different date ranges"""
    print("=" * 80)
    print("SEC EDGAR EARNINGS & DIVIDENDS DETECTION TEST")
    print("=" * 80)
    print()
    print("Testing if SEC EDGAR can provide earnings and dividend data")
    print()
    
    # Test with companies that regularly file earnings and pay dividends
    # Use a date range that includes recent quarters
    test_cases = [
        {
            'ticker': 'AAPL',
            'name': 'Apple Inc.',
            'start_date': datetime(2024, 1, 1),
            'end_date': datetime(2024, 12, 31)
        },
        {
            'ticker': 'MSFT',
            'name': 'Microsoft Corporation',
            'start_date': datetime(2024, 1, 1),
            'end_date': datetime(2024, 12, 31)
        },
        {
            'ticker': 'JNJ',
            'name': 'Johnson & Johnson',
            'start_date': datetime(2024, 1, 1),
            'end_date': datetime(2024, 12, 31)
        },
        {
            'ticker': 'KO',
            'name': 'Coca-Cola Company',
            'start_date': datetime(2024, 1, 1),
            'end_date': datetime(2024, 12, 31)
        }
    ]
    
    results = []
    for test_case in test_cases:
        result = test_sec_edgar_earnings_dividends(
            test_case['ticker'],
            test_case['start_date'],
            test_case['end_date']
        )
        result['name'] = test_case['name']
        results.append(result)
    
    # Final summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print()
    
    successful_tickers = []
    for r in results:
        if r['has_earnings'] or r['has_dividends']:
            successful_tickers.append(r['ticker'])
            print(f"✅ {r['ticker']} ({r['name']}):")
            if r['has_earnings']:
                print(f"   Earnings: {len(r['earnings'])} filing(s) found")
                for e in r['earnings_details'][:3]:  # Show first 3
                    print(f"     - {e['date']}: {e['form']} - {e['description'][:50]}")
            if r['has_dividends']:
                print(f"   Dividends: {len(r['dividends'])} filing(s) found")
                for d in r['dividend_details'][:3]:  # Show first 3
                    print(f"     - {d['date']}: {d['form']} - {d['description'][:50]}")
        else:
            print(f"⚠️  {r['ticker']} ({r['name']}): No earnings/dividend filings found in date range")
        print()
    
    print()
    if successful_tickers:
        print(f"✅ SUCCESS: SEC EDGAR can provide earnings/dividend data")
        print(f"   Working tickers: {', '.join(successful_tickers)}")
        print()
        print("📝 Notes:")
        print("   - SEC EDGAR provides filing dates and form types")
        print("   - Earnings: Found via 8-K (Item 2.02), 10-Q, 10-K forms")
        print("   - Dividends: Found via 8-K (Item 8.01) with dividend keywords")
        print("   - To get detailed info (EPS, dividend amount), need to parse filing documents")
        print()
        print("✅ Ready to implement earnings/dividend detection using SEC EDGAR")
    else:
        print("❌ WARNING: No earnings/dividend filings found in test cases")
        print("   This might be due to:")
        print("   - Date range doesn't include earnings/dividend filing dates")
        print("   - Companies haven't filed yet in the date range")
        print("   - Need to adjust search criteria")
        print()
        print("⚠️  Recommend testing with more tickers or different date ranges")
    
    return len(successful_tickers) > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

