#!/usr/bin/env python3
"""
Unit test to verify if yfinance can retrieve earnings and dividend data
"""

import sys
import os
from datetime import datetime, timedelta

# Configure SSL certificate for curl_cffi (used by yfinance)
try:
    import certifi
    cert_path = certifi.where()
    # Set environment variables that curl_cffi might respect
    os.environ['SSL_CERT_FILE'] = cert_path
    os.environ['REQUESTS_CA_BUNDLE'] = cert_path
    os.environ['CURL_CA_BUNDLE'] = cert_path
    print(f"📜 Certificate configured: {cert_path}")
    print(f"   File exists: {os.path.exists(cert_path)}")
except Exception as e:
    print(f"⚠️  Warning: Could not configure certificate: {e}")

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("❌ yfinance not installed")
    sys.exit(1)

def test_earnings_and_dividends(ticker: str, start_date: datetime, end_date: datetime):
    """Test if we can get earnings and dividend data for a ticker in a date range"""
    print(f"\n{'='*80}")
    print(f"Testing: {ticker}")
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
    
    try:
        stock = yf.Ticker(ticker)
        
        # Test 1: Check calendar (earnings dates)
        print("📅 Test 1: Checking earnings calendar...")
        try:
            calendar = stock.calendar
            result['methods_tested'].append('calendar')
            if calendar is not None and not calendar.empty:
                print(f"   ✅ Calendar data available")
                print(f"   Calendar columns: {list(calendar.columns)}")
                print(f"   Calendar shape: {calendar.shape}")
                print(f"   Calendar data:\n{calendar}")
                
                # Check for earnings date column
                if 'Earnings Date' in calendar.columns:
                    earnings_dates = calendar['Earnings Date'].dropna()
                    print(f"   Found {len(earnings_dates)} earnings date(s)")
                    for idx, earnings_date in earnings_dates.items():
                        print(f"   - Earnings Date: {earnings_date}")
                        if isinstance(earnings_date, str):
                            try:
                                earnings_dt = datetime.strptime(earnings_date, '%Y-%m-%d')
                            except:
                                try:
                                    earnings_dt = datetime.strptime(earnings_date, '%Y-%m-%d %H:%M:%S')
                                    earnings_dt = earnings_dt.replace(hour=0, minute=0, second=0)
                                except:
                                    print(f"     ⚠️  Could not parse date: {earnings_date}")
                                    continue
                        elif hasattr(earnings_date, 'date'):
                            earnings_dt = earnings_date
                        else:
                            print(f"     ⚠️  Unknown date format: {type(earnings_date)}")
                            continue
                        
                        if start_date.date() <= earnings_dt.date() <= end_date.date():
                            result['earnings'].append(earnings_dt.date())
                            result['has_earnings'] = True
                            result['earnings_details'].append({
                                'date': earnings_dt.date(),
                                'type': 'Earnings Announcement'
                            })
                            print(f"     ✅ Earnings in date range: {earnings_dt.date()}")
                        else:
                            print(f"     ℹ️  Earnings outside range: {earnings_dt.date()}")
                else:
                    print(f"   ⚠️  No 'Earnings Date' column found")
            else:
                print(f"   ⚠️  Calendar is empty or None")
        except Exception as e:
            print(f"   ❌ Calendar error: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Test 2: Check dividend history
        print(f"\n💰 Test 2: Checking dividend history...")
        try:
            dividends = stock.dividends
            result['methods_tested'].append('dividends')
            if dividends is not None and len(dividends) > 0:
                print(f"   ✅ Dividend data available ({len(dividends)} entries)")
                
                # Filter dividends in date range
                in_range_count = 0
                for div_date, div_amount in dividends.items():
                    div_date_only = div_date.date() if hasattr(div_date, 'date') else div_date
                    
                    if start_date.date() <= div_date_only <= end_date.date():
                        in_range_count += 1
                        result['dividends'].append(div_date_only)
                        result['has_dividends'] = True
                        result['dividend_details'].append({
                            'date': div_date_only,
                            'amount': float(div_amount),
                            'type': 'Ex-Dividend Date'
                        })
                        print(f"   ✅ Dividend in range: {div_date_only} - ${div_amount:.4f}")
                
                if in_range_count == 0:
                    print(f"   ℹ️  No dividends in date range (checked {len(dividends)} total)")
            else:
                print(f"   ⚠️  No dividend data available")
        except Exception as e:
            print(f"   ❌ Dividend error: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Test 3: Check stock.info for earnings dates
        print(f"\n📊 Test 3: Checking stock.info for earnings dates...")
        try:
            info = stock.info
            result['methods_tested'].append('info')
            if info:
                print(f"   ✅ Info available ({len(info)} fields)")
                
                # Check for earnings-related fields
                earnings_fields = [k for k in info.keys() if 'earnings' in k.lower() or 'dividend' in k.lower()]
                if earnings_fields:
                    print(f"   Found earnings/dividend fields: {earnings_fields}")
                    for field in earnings_fields[:5]:  # Show first 5
                        print(f"     - {field}: {info[field]}")
                
                # Check specific fields
                if 'earningsDate' in info and info['earningsDate']:
                    earnings_date_raw = info['earningsDate']
                    print(f"   Found 'earningsDate': {earnings_date_raw} (type: {type(earnings_date_raw)})")
                    
                    try:
                        if isinstance(earnings_date_raw, list) and len(earnings_date_raw) > 0:
                            earnings_timestamp = earnings_date_raw[0]
                            earnings_dt = datetime.fromtimestamp(earnings_timestamp)
                        elif isinstance(earnings_date_raw, (int, float)):
                            earnings_dt = datetime.fromtimestamp(earnings_date_raw)
                        else:
                            earnings_dt = None
                        
                        if earnings_dt:
                            if start_date.date() <= earnings_dt.date() <= end_date.date():
                                if earnings_dt.date() not in result['earnings']:
                                    result['earnings'].append(earnings_dt.date())
                                    result['has_earnings'] = True
                                    result['earnings_details'].append({
                                        'date': earnings_dt.date(),
                                        'type': 'Earnings Announcement (from info)'
                                    })
                                    print(f"     ✅ Earnings in range: {earnings_dt.date()}")
                                else:
                                    print(f"     ℹ️  Earnings already found via calendar")
                            else:
                                print(f"     ℹ️  Earnings outside range: {earnings_dt.date()}")
                    except Exception as e:
                        print(f"     ⚠️  Could not parse earningsDate: {e}")
                
                if 'exDividendDate' in info and info['exDividendDate']:
                    ex_div_date_raw = info['exDividendDate']
                    print(f"   Found 'exDividendDate': {ex_div_date_raw}")
                    try:
                        if isinstance(ex_div_date_raw, (int, float)):
                            ex_div_dt = datetime.fromtimestamp(ex_div_date_raw)
                            if start_date.date() <= ex_div_dt.date() <= end_date.date():
                                if ex_div_dt.date() not in result['dividends']:
                                    result['dividends'].append(ex_div_dt.date())
                                    result['has_dividends'] = True
                                    result['dividend_details'].append({
                                        'date': ex_div_dt.date(),
                                        'amount': info.get('dividendRate', 0),
                                        'type': 'Ex-Dividend Date (from info)'
                                    })
                                    print(f"     ✅ Ex-dividend in range: {ex_div_dt.date()}")
                    except Exception as e:
                        print(f"     ⚠️  Could not parse exDividendDate: {e}")
            else:
                print(f"   ⚠️  No info available")
        except Exception as e:
            print(f"   ❌ Info error: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Summary
        print(f"\n{'='*80}")
        print(f"SUMMARY for {ticker}")
        print(f"{'='*80}")
        print(f"Methods tested: {', '.join(result['methods_tested'])}")
        print(f"Earnings found: {result['has_earnings']} ({len(result['earnings'])} dates)")
        if result['earnings']:
            for e in result['earnings_details']:
                print(f"  - {e['date']}: {e['type']}")
        print(f"Dividends found: {result['has_dividends']} ({len(result['dividends'])} dates)")
        if result['dividends']:
            for d in result['dividend_details']:
                print(f"  - {d['date']}: {d['type']} - ${d.get('amount', 0):.4f}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error testing {ticker}: {str(e)}")
        import traceback
        traceback.print_exc()
        return result

def main():
    """Run tests on multiple tickers with different date ranges"""
    print("=" * 80)
    print("YFINANCE EARNINGS & DIVIDENDS DETECTION TEST")
    print("=" * 80)
    print()
    print("Testing if yfinance can retrieve earnings and dividend data")
    print()
    
    # Test with various tickers that are likely to have earnings/dividends
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
        result = test_earnings_and_dividends(
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
            print(f"✅ {r['ticker']} ({r['name']}): Found data")
        else:
            print(f"⚠️  {r['ticker']} ({r['name']}): No data found in range")
    
    print()
    if successful_tickers:
        print(f"✅ SUCCESS: yfinance can retrieve earnings/dividend data")
        print(f"   Working tickers: {', '.join(successful_tickers)}")
        print()
        print("✅ Ready to implement earnings/dividend detection")
    else:
        print("❌ WARNING: No earnings/dividend data found in test cases")
        print("   This might be due to:")
        print("   - Date range doesn't include earnings/dividend dates")
        print("   - yfinance API limitations")
        print("   - Ticker-specific issues")
        print()
        print("⚠️  Recommend testing with more tickers or different date ranges")
    
    return len(successful_tickers) > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

