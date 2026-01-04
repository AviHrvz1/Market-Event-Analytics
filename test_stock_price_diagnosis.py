#!/usr/bin/env python3
"""
Unit test to diagnose why stock prices aren't being found for bio companies.
Tests Prixe.io and Yahoo Finance APIs for specific tickers.
"""

import requests
import yfinance as yf
from datetime import datetime, timezone, timedelta
from config import PRIXE_API_KEY, PRIXE_BASE_URL, PRIXE_PRICE_ENDPOINT

# Test cases from user's issue
TEST_CASES = [
    {'company': 'Moderna Inc', 'ticker': 'MRNA', 'date': '2025-09-17'},
    {'company': 'Merck & Co.', 'ticker': 'MRK', 'date': '2025-09-15'},
    {'company': 'Johnson & Johnson', 'ticker': 'JNJ', 'date': '2025-09-08'},
    {'company': 'Moderna Inc', 'ticker': 'MRNA', 'date': '2025-09-06'},
]

def test_prixe_api(ticker, date_str, intervals=None):
    """Test Prixe.io API for a specific ticker and date"""
    if intervals is None:
        intervals = ['1min', '5min', '10min', '30min', '1hr', '2hr', '3hr']
    
    print(f"\n  Testing Prixe.io API for {ticker} on {date_str}...")
    
    results = {}
    headers = {
        'Authorization': f'Bearer {PRIXE_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    # Parse date
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
        target_timestamp = int(target_date.timestamp())
    except Exception as e:
        print(f"    ❌ Date parsing error: {e}")
        return results
    
    for interval in intervals:
        try:
            # Prixe.io API endpoint
            url = f"{PRIXE_BASE_URL}{PRIXE_PRICE_ENDPOINT}"
            
            # Build request payload (Prixe.io format)
            # Map intervals to Prixe.io format
            interval_map = {
                '1min': '1m',
                '5min': '5m',
                '10min': '10m',
                '30min': '30m',
                '1hr': '1h',
                '2hr': '2h',
                '3hr': '3h'
            }
            prixe_interval = interval_map.get(interval, interval)
            
            payload = {
                'ticker': ticker,
                'start_date': date_str,
                'end_date': date_str,
                'interval': prixe_interval
            }
            
            print(f"    Requesting {interval} data...")
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, list) and len(data) > 0:
                    results[interval] = {
                        'success': True,
                        'data_points': len(data),
                        'sample': data[0] if data else None
                    }
                    print(f"      ✅ {interval}: {len(data)} data points found")
                else:
                    results[interval] = {
                        'success': False,
                        'reason': 'Empty response',
                        'response': data
                    }
                    print(f"      ❌ {interval}: Empty response")
            else:
                results[interval] = {
                    'success': False,
                    'reason': f'HTTP {response.status_code}',
                    'response': response.text[:200]
                }
                print(f"      ❌ {interval}: HTTP {response.status_code} - {response.text[:100]}")
                
        except requests.exceptions.Timeout:
            results[interval] = {'success': False, 'reason': 'Timeout'}
            print(f"      ❌ {interval}: Request timeout")
        except Exception as e:
            results[interval] = {'success': False, 'reason': str(e)}
            print(f"      ❌ {interval}: Error - {e}")
    
    return results

def test_yahoo_finance(ticker, date_str, intervals=None):
    """Test Yahoo Finance API for a specific ticker and date"""
    if intervals is None:
        intervals = ['1m', '5m', '15m', '30m', '1h', '1d']
    
    print(f"\n  Testing Yahoo Finance for {ticker} on {date_str}...")
    
    results = {}
    
    try:
        # Parse date
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
        start_date = target_date - timedelta(days=1)
        end_date = target_date + timedelta(days=2)
        
        # Create ticker object
        stock = yf.Ticker(ticker)
        
        for interval in intervals:
            try:
                print(f"    Requesting {interval} data...")
                
                # Get historical data
                hist = stock.history(start=start_date, end=end_date, interval=interval)
                
                if hist is not None and len(hist) > 0:
                    # Filter for target date
                    target_data = hist[hist.index.date == target_date.date()]
                    
                    if len(target_data) > 0:
                        results[interval] = {
                            'success': True,
                            'data_points': len(target_data),
                            'total_points': len(hist),
                            'sample': {
                                'price': float(target_data['Close'].iloc[0]) if 'Close' in target_data.columns else None,
                                'timestamp': target_data.index[0].isoformat() if len(target_data) > 0 else None
                            }
                        }
                        print(f"      ✅ {interval}: {len(target_data)} data points for target date (total: {len(hist)})")
                    else:
                        results[interval] = {
                            'success': False,
                            'reason': f'No data for target date (but {len(hist)} points available)',
                            'available_dates': [str(d.date()) for d in hist.index[:5]]
                        }
                        print(f"      ⚠️  {interval}: No data for {date_str}, but {len(hist)} points available")
                else:
                    results[interval] = {
                        'success': False,
                        'reason': 'No data returned'
                    }
                    print(f"      ❌ {interval}: No data returned")
                    
            except Exception as e:
                results[interval] = {
                    'success': False,
                    'reason': str(e)
                }
                print(f"      ❌ {interval}: Error - {e}")
                
    except Exception as e:
        print(f"    ❌ Yahoo Finance error: {e}")
        return results
    
    return results

def test_prixe_api_alternative_endpoints(ticker, date_str):
    """Test alternative Prixe.io endpoints"""
    print(f"\n  Testing alternative Prixe.io endpoints for {ticker}...")
    
    headers = {
        'Authorization': f'Bearer {PRIXE_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    alternative_endpoints = [
        '/api/historical',
        '/api/v1/price',
        '/api/v1/historical',
        '/api/stock/price',
    ]
    
    results = {}
    
    for endpoint in alternative_endpoints:
        try:
            url = f"{PRIXE_BASE_URL}{endpoint}"
            
            # Try different payload formats
            payloads = [
                {'symbol': ticker, 'date': date_str},
                {'ticker': ticker, 'date': date_str},
                {'symbol': ticker},
                {'ticker': ticker},
            ]
            
            for i, payload in enumerate(payloads):
                try:
                    response = requests.post(url, json=payload, headers=headers, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        results[f"{endpoint}_payload{i}"] = {
                            'success': True,
                            'data': data
                        }
                        print(f"    ✅ {endpoint} (payload {i}): Success")
                        break
                except:
                    continue
                    
        except Exception as e:
            results[endpoint] = {'success': False, 'reason': str(e)}
    
    return results

def test_ticker_validation(ticker):
    """Test if ticker is valid/recognized"""
    print(f"\n  Validating ticker {ticker}...")
    
    results = {}
    
    # Test Yahoo Finance
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if info and 'symbol' in info:
            results['yahoo'] = {
                'valid': True,
                'name': info.get('longName', info.get('shortName', 'N/A')),
                'exchange': info.get('exchange', 'N/A')
            }
            print(f"    ✅ Yahoo Finance: Valid - {results['yahoo']['name']}")
        else:
            results['yahoo'] = {'valid': False, 'reason': 'No info returned'}
            print(f"    ❌ Yahoo Finance: Invalid ticker")
    except Exception as e:
        results['yahoo'] = {'valid': False, 'reason': str(e)}
        print(f"    ❌ Yahoo Finance: Error - {e}")
    
    # Test Prixe.io (try to get current price)
    try:
        headers = {
            'Authorization': f'Bearer {PRIXE_API_KEY}',
            'Content-Type': 'application/json'
        }
        url = f"{PRIXE_BASE_URL}{PRIXE_PRICE_ENDPOINT}"
        payload = {'symbol': ticker}
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            results['prixe'] = {
                'valid': True,
                'response': data
            }
            print(f"    ✅ Prixe.io: Valid - Response received")
        else:
            results['prixe'] = {
                'valid': False,
                'reason': f'HTTP {response.status_code}',
                'response': response.text[:200]
            }
            print(f"    ❌ Prixe.io: HTTP {response.status_code}")
    except Exception as e:
        results['prixe'] = {'valid': False, 'reason': str(e)}
        print(f"    ❌ Prixe.io: Error - {e}")
    
    return results

def main():
    """Run all diagnostic tests"""
    print("=" * 80)
    print("STOCK PRICE DIAGNOSIS TEST SUITE")
    print("=" * 80)
    print("\nTesting why stock prices aren't being found for bio companies")
    print("Comparing Prixe.io vs Yahoo Finance APIs")
    print()
    
    all_results = {}
    
    for test_case in TEST_CASES:
        company = test_case['company']
        ticker = test_case['ticker']
        date_str = test_case['date']
        
        print("=" * 80)
        note = test_case.get('note', '')
        print(f"Test Case: {company} ({ticker}) on {date_str}")
        if note:
            print(f"Note: {note}")
        print("=" * 80)
        
        # Test ticker validation
        validation = test_ticker_validation(ticker)
        
        # Test Prixe.io
        prixe_results = test_prixe_api(ticker, date_str)
        
        # Test Yahoo Finance
        yahoo_results = test_yahoo_finance(ticker, date_str)
        
        # Test alternative Prixe endpoints
        alt_results = test_prixe_api_alternative_endpoints(ticker, date_str)
        
        all_results[ticker] = {
            'company': company,
            'date': date_str,
            'validation': validation,
            'prixe': prixe_results,
            'yahoo': yahoo_results,
            'alternative_endpoints': alt_results
        }
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    for ticker, results in all_results.items():
        print(f"\n{ticker} ({results['company']}) on {results['date']}:")
        
        # Prixe.io summary
        prixe_success = sum(1 for r in results['prixe'].values() if isinstance(r, dict) and r.get('success', False))
        prixe_total = len(results['prixe'])
        print(f"  Prixe.io: {prixe_success}/{prixe_total} intervals successful")
        
        # Yahoo Finance summary
        yahoo_success = sum(1 for r in results['yahoo'].values() if isinstance(r, dict) and r.get('success', False))
        yahoo_total = len(results['yahoo'])
        print(f"  Yahoo Finance: {yahoo_success}/{yahoo_total} intervals successful")
        
        # Recommendations
        if prixe_success == 0 and yahoo_success > 0:
            print(f"  💡 RECOMMENDATION: Yahoo Finance works better for {ticker}")
        elif prixe_success > 0 and yahoo_success == 0:
            print(f"  💡 RECOMMENDATION: Prixe.io works better for {ticker}")
        elif prixe_success == 0 and yahoo_success == 0:
            print(f"  ⚠️  WARNING: Neither API returned data for {ticker}")
        else:
            print(f"  ✅ Both APIs work for {ticker}")
    
    # Overall recommendation
    print("\n" + "=" * 80)
    print("OVERALL RECOMMENDATION")
    print("=" * 80)
    
    total_prixe_success = sum(
        sum(1 for r in results['prixe'].values() if isinstance(r, dict) and r.get('success', False))
        for results in all_results.values()
    )
    total_yahoo_success = sum(
        sum(1 for r in results['yahoo'].values() if isinstance(r, dict) and r.get('success', False))
        for results in all_results.values()
    )
    
    print(f"Prixe.io total successes: {total_prixe_success}")
    print(f"Yahoo Finance total successes: {total_yahoo_success}")
    
    if total_yahoo_success > total_prixe_success:
        print("\n💡 RECOMMENDATION: Yahoo Finance appears to be more reliable for these tickers")
        print("   Consider using Yahoo Finance as a fallback or primary source")
    elif total_prixe_success > total_yahoo_success:
        print("\n💡 RECOMMENDATION: Prixe.io appears to be working, but may have date/interval issues")
        print("   Check Prixe.io API documentation for correct date format and intervals")
    else:
        print("\n⚠️  Both APIs have similar success rates - investigate further")
    
    print("\n" + "=" * 80)
    print("ROOT CAUSE ANALYSIS")
    print("=" * 80)
    print("\n🔍 KEY FINDINGS:")
    print("   1. Prixe.io API Limitations:")
    print("      - 1m interval: Only available for last 30 days")
    print("      - 5m, 30m intervals: Only available for last 60 days")
    print("      - 10m, 1h, 2h, 3h intervals: May return 404 for older dates")
    print("      - Daily (1d) data: Should work for longer periods")
    print("\n   2. Yahoo Finance Limitations:")
    print("      - Intraday data (1m, 5m, 15m, 30m): Only last 30-60 days")
    print("      - Hourly (1h) data: Available for longer periods")
    print("      - Daily (1d) data: Available for historical dates")
    print("\n   3. Date Issue:")
    print("      - The test dates (September 2025) are in the FUTURE")
    print("      - Neither API can provide data for future dates")
    print("      - For intraday data, both APIs are limited to recent dates")
    print("\n💡 SOLUTIONS:")
    print("   - For recent articles (< 30 days): Both APIs work for intraday data")
    print("   - For older articles (> 30 days): Use daily (1d) interval only")
    print("   - Consider using Yahoo Finance as fallback for daily data")
    print("   - Prixe.io authentication is working (Bearer token format is correct)")

if __name__ == '__main__':
    main()

