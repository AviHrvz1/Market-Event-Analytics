#!/usr/bin/env python3
"""
Verification script to check which small-cap biotech companies have options trading
Checks options availability and volume for each company in the list
"""

import sys
from datetime import datetime, timedelta
from main import LayoffTracker

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("❌ yfinance not installed. Install with: pip install yfinance")
    sys.exit(1)

def get_ticker_for_company(company_name: str, tracker: LayoffTracker) -> str:
    """Get ticker symbol for a company name"""
    # Check cache first
    company_upper = company_name.upper()
    if company_upper in tracker.company_ticker_cache:
        return tracker.company_ticker_cache[company_upper]
    
    # Try to find ticker using the public method
    ticker = tracker.get_stock_ticker(company_name)
    if ticker:
        tracker.company_ticker_cache[company_upper] = ticker
    return ticker

def check_options_availability(ticker: str) -> dict:
    """Check if a ticker has options available
    
    Returns:
        dict with:
            - has_options: bool
            - options_count: int (number of expiration dates)
            - sample_volume: int (total volume for nearest expiration, if available)
            - error: str (if any error occurred)
    """
    result = {
        'has_options': False,
        'options_count': 0,
        'sample_volume': 0,
        'error': None
    }
    
    try:
        stock = yf.Ticker(ticker)
        
        # Get options expiration dates
        try:
            expirations = stock.options
            if expirations and len(expirations) > 0:
                result['has_options'] = True
                result['options_count'] = len(expirations)
                
                # Try to get volume for nearest expiration
                try:
                    nearest_exp = expirations[0]
                    opt_chain = stock.option_chain(nearest_exp)
                    
                    # Get total volume from calls and puts
                    calls_volume = opt_chain.calls['volume'].sum() if not opt_chain.calls.empty else 0
                    puts_volume = opt_chain.puts['volume'].sum() if not opt_chain.puts.empty else 0
                    result['sample_volume'] = int(calls_volume + puts_volume)
                except Exception as e:
                    # Options exist but couldn't get volume
                    result['sample_volume'] = -1  # -1 means "exists but volume unknown"
                    pass
        except Exception as e:
            # No options available
            result['error'] = str(e)
            pass
            
    except Exception as e:
        result['error'] = str(e)
    
    return result

def verify_small_cap_options():
    """Verify options availability for all small-cap biotech companies"""
    print("=" * 80)
    print("SMALL-CAP BIOTECH OPTIONS VERIFICATION")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Get small-cap companies list
    small_cap_companies = tracker._get_bio_pharma_companies(category='small_cap')
    
    # For testing, you can limit to first N companies
    # Remove this line to check all companies
    # small_cap_companies = small_cap_companies[:10]  # Uncomment to test with first 10
    
    print(f"Total companies to check: {len(small_cap_companies)}")
    print()
    
    results = []
    companies_with_tickers = 0
    companies_with_options = 0
    companies_with_volume = 0
    
    for i, company in enumerate(small_cap_companies, 1):
        print(f"[{i}/{len(small_cap_companies)}] Checking: {company}")
        
        # Get ticker
        ticker = get_ticker_for_company(company, tracker)
        
        if not ticker:
            print(f"  ❌ No ticker found")
            results.append({
                'company': company,
                'ticker': None,
                'has_options': False,
                'options_count': 0,
                'sample_volume': 0,
                'error': 'No ticker found'
            })
            continue
        
        companies_with_tickers += 1
        print(f"  Ticker: {ticker}")
        
        # Check options
        options_info = check_options_availability(ticker)
        
        if options_info['has_options']:
            companies_with_options += 1
            if options_info['sample_volume'] > 0:
                companies_with_volume += 1
                print(f"  ✅ Has options: {options_info['options_count']} expirations, Volume: {options_info['sample_volume']:,}")
            elif options_info['sample_volume'] == -1:
                print(f"  ✅ Has options: {options_info['options_count']} expirations, Volume: Unknown")
            else:
                print(f"  ⚠️  Has options: {options_info['options_count']} expirations, Volume: 0")
        else:
            print(f"  ❌ No options available")
            if options_info['error']:
                print(f"     Error: {options_info['error']}")
        
        results.append({
            'company': company,
            'ticker': ticker,
            'has_options': options_info['has_options'],
            'options_count': options_info['options_count'],
            'sample_volume': options_info['sample_volume'],
            'error': options_info['error']
        })
        
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"Total companies checked: {len(small_cap_companies)}")
    print(f"Companies with tickers: {companies_with_tickers}")
    print(f"Companies with options: {companies_with_options}")
    print(f"Companies with options volume > 0: {companies_with_volume}")
    print()
    
    # Breakdown by options status
    print("Breakdown:")
    print(f"  ✅ Has options with volume: {companies_with_volume}")
    print(f"  ⚠️  Has options but no volume: {companies_with_options - companies_with_volume}")
    print(f"  ❌ No options: {companies_with_tickers - companies_with_options}")
    print(f"  ❌ No ticker: {len(small_cap_companies) - companies_with_tickers}")
    print()
    
    # List companies with options
    print("=" * 80)
    print("COMPANIES WITH OPTIONS (Volume > 0)")
    print("=" * 80)
    print()
    
    companies_with_volume_list = [r for r in results if r['has_options'] and r['sample_volume'] > 0]
    companies_with_volume_list.sort(key=lambda x: x['sample_volume'], reverse=True)
    
    if companies_with_volume_list:
        for result in companies_with_volume_list:
            print(f"  ✅ {result['company']} ({result['ticker']}) - {result['sample_volume']:,} volume, {result['options_count']} expirations")
    else:
        print("  None found")
    print()
    
    # List companies with options but no volume
    print("=" * 80)
    print("COMPANIES WITH OPTIONS BUT NO VOLUME")
    print("=" * 80)
    print()
    
    companies_no_volume = [r for r in results if r['has_options'] and r['sample_volume'] == 0]
    if companies_no_volume:
        for result in companies_no_volume:
            print(f"  ⚠️  {result['company']} ({result['ticker']}) - {result['options_count']} expirations")
    else:
        print("  None found")
    print()
    
    # List companies without options
    print("=" * 80)
    print("COMPANIES WITHOUT OPTIONS")
    print("=" * 80)
    print()
    
    companies_no_options = [r for r in results if not r['has_options'] and r['ticker']]
    if companies_no_options:
        for result in companies_no_options[:20]:  # Show first 20
            print(f"  ❌ {result['company']} ({result['ticker']})")
        if len(companies_no_options) > 20:
            print(f"  ... and {len(companies_no_options) - 20} more")
    else:
        print("  None found")
    print()
    
    # Save results to file
    import json
    output_file = 'options_verification_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"✅ Results saved to: {output_file}")
    print()
    
    # Recommendations
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()
    print(f"1. Companies with options and volume: {companies_with_volume}")
    print(f"   → These are the most liquid and suitable for options trading")
    print()
    print(f"2. Companies with options but no volume: {companies_with_options - companies_with_volume}")
    print(f"   → Options exist but may be illiquid")
    print()
    print(f"3. Companies without options: {companies_with_tickers - companies_with_options}")
    print(f"   → Consider removing from list or marking as 'no options'")
    print()
    
    if companies_with_volume < len(small_cap_companies) * 0.5:
        print("⚠️  WARNING: Less than 50% of companies have options with volume")
        print("   Consider filtering the list to only include companies with options")
    print()

if __name__ == '__main__':
    try:
        verify_small_cap_options()
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n⚠️  Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

