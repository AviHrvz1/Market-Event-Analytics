#!/usr/bin/env python3
"""
Unit test to compare yfinance vs NASDAQ for finding events (earnings + dividends)
This test helps determine if yfinance is good enough to replace NASDAQ
"""

import sys
import os
from datetime import datetime, timezone, timedelta

# Fix certificate path for yfinance
try:
    import ssl
    import certifi
    system_cert = '/private/etc/ssl/cert.pem'
    certifi_cert = certifi.where()
    if os.path.exists(system_cert) and os.access(system_cert, os.R_OK):
        cert_path = system_cert
    else:
        cert_path = certifi_cert
    os.environ['SSL_CERT_FILE'] = cert_path
    os.environ['REQUESTS_CA_BUNDLE'] = cert_path
    os.environ['CURL_CA_BUNDLE'] = cert_path
except:
    pass

from main import LayoffTracker

def fetch_events_yfinance(ticker: str, start_date: datetime, end_date: datetime):
    """Fetch events from yfinance for a given date range"""
    try:
        import yfinance as yf
        ticker_obj = yf.Ticker(ticker)
        
        events = {
            'earnings': [],
            'dividends': [],
            'total': 0
        }
        
        # Fetch earnings dates
        try:
            earnings_dates = ticker_obj.get_earnings_dates(limit=100)
            if earnings_dates is not None and len(earnings_dates) > 0:
                # Filter by date range
                if earnings_dates.index.tz is not None:
                    start_dt = start_date.astimezone(earnings_dates.index.tz)
                    end_dt = end_date.astimezone(earnings_dates.index.tz)
                else:
                    start_dt = start_date
                    end_dt = end_date
                
                earnings_during = earnings_dates[
                    (earnings_dates.index >= start_dt) & 
                    (earnings_dates.index <= end_dt)
                ]
                
                for date_idx, row in earnings_during.iterrows():
                    event_date = date_idx
                    if event_date.tz is not None:
                        event_date_utc = event_date.astimezone(timezone.utc)
                    else:
                        event_date_utc = event_date.replace(tzinfo=timezone.utc)
                    
                    events['earnings'].append({
                        'date': event_date_utc.strftime('%Y-%m-%d'),
                        'type': 'earnings',
                        'name': 'Earnings',
                        'form': 'yfinance',
                        'description': f"Earnings - {row.get('EPS Estimate', 'N/A')} estimate" if 'EPS Estimate' in row else 'Earnings'
                    })
        except Exception as e:
            print(f"  ⚠️  yfinance earnings error for {ticker}: {e}")
        
        # Fetch dividends
        try:
            dividends = ticker_obj.dividends
            if dividends is not None and len(dividends) > 0:
                # Filter by date range
                if dividends.index.tz is not None:
                    start_dt = start_date.astimezone(dividends.index.tz)
                    end_dt = end_date.astimezone(dividends.index.tz)
                else:
                    start_dt = start_date
                    end_dt = end_date
                
                dividends_during = dividends[
                    (dividends.index >= start_dt) & 
                    (dividends.index <= end_dt)
                ]
                
                for date_idx, dividend_amount in dividends_during.items():
                    event_date = date_idx
                    if event_date.tz is not None:
                        event_date_utc = event_date.astimezone(timezone.utc)
                    else:
                        event_date_utc = event_date.replace(tzinfo=timezone.utc)
                    
                    events['dividends'].append({
                        'date': event_date_utc.strftime('%Y-%m-%d'),
                        'type': 'dividend',
                        'name': f"Dividend ${dividend_amount:.4f}",
                        'form': 'yfinance',
                        'description': f"Dividend payment: ${dividend_amount:.4f} per share",
                        'dividend_rate': float(dividend_amount)
                    })
        except Exception as e:
            print(f"  ⚠️  yfinance dividends error for {ticker}: {e}")
        
        events['total'] = len(events['earnings']) + len(events['dividends'])
        return events
        
    except ImportError:
        return {'earnings': [], 'dividends': [], 'total': 0, 'error': 'yfinance not available'}
    except Exception as e:
        return {'earnings': [], 'dividends': [], 'total': 0, 'error': str(e)}

def fetch_events_nasdaq(ticker: str, start_date: datetime, end_date: datetime):
    """Fetch events from NASDAQ for a given date range"""
    tracker = LayoffTracker()
    try:
        result = tracker._check_earnings_dividends_nasdaq(ticker, start_date, end_date, future_days=0)
        events = {
            'earnings': [],
            'dividends': [],
            'total': 0
        }
        
        for event in result.get('events_during', []):
            event_type = event.get('type', '')
            if event_type == 'earnings':
                events['earnings'].append(event)
            elif event_type == 'dividend':
                events['dividends'].append(event)
        
        events['total'] = len(events['earnings']) + len(events['dividends'])
        return events
    except Exception as e:
        return {'earnings': [], 'dividends': [], 'total': 0, 'error': str(e)}

def compare_events(yfinance_events, nasdaq_events, ticker):
    """Compare events from both sources"""
    comparison = {
        'ticker': ticker,
        'yfinance_total': yfinance_events['total'],
        'nasdaq_total': nasdaq_events['total'],
        'yfinance_earnings': len(yfinance_events['earnings']),
        'nasdaq_earnings': len(nasdaq_events['earnings']),
        'yfinance_dividends': len(yfinance_events['dividends']),
        'nasdaq_dividends': len(nasdaq_events['dividends']),
        'yfinance_only': [],
        'nasdaq_only': [],
        'common': [],
        'verdict': ''
    }
    
    # Create sets for comparison (using date + type as key)
    yf_set = set()
    for event in yfinance_events['earnings'] + yfinance_events['dividends']:
        key = (event['date'], event['type'])
        yf_set.add(key)
    
    nasdaq_set = set()
    for event in nasdaq_events['earnings'] + nasdaq_events['dividends']:
        key = (event['date'], event['type'])
        nasdaq_set.add(key)
    
    # Find common events
    common_keys = yf_set & nasdaq_set
    comparison['common'] = list(common_keys)
    
    # Find yfinance-only events
    yf_only_keys = yf_set - nasdaq_set
    for key in yf_only_keys:
        date, event_type = key
        # Find the event details
        all_yf_events = yfinance_events['earnings'] + yfinance_events['dividends']
        for event in all_yf_events:
            if event['date'] == date and event['type'] == event_type:
                comparison['yfinance_only'].append(event)
                break
    
    # Find NASDAQ-only events
    nasdaq_only_keys = nasdaq_set - yf_set
    for key in nasdaq_only_keys:
        date, event_type = key
        # Find the event details
        all_nasdaq_events = nasdaq_events['earnings'] + nasdaq_events['dividends']
        for event in all_nasdaq_events:
            if event['date'] == date and event['type'] == event_type:
                comparison['nasdaq_only'].append(event)
                break
    
    # Determine verdict
    if comparison['yfinance_total'] > comparison['nasdaq_total']:
        comparison['verdict'] = 'yfinance_better'
    elif comparison['yfinance_total'] == comparison['nasdaq_total']:
        if len(comparison['nasdaq_only']) == 0:
            comparison['verdict'] = 'yfinance_same'
        else:
            comparison['verdict'] = 'yfinance_good_enough'  # Same total but NASDAQ has some extras
    else:
        if len(comparison['nasdaq_only']) > comparison['yfinance_total']:
            comparison['verdict'] = 'yfinance_worse'
        else:
            comparison['verdict'] = 'yfinance_good_enough'  # NASDAQ finds more but not significantly
    
    return comparison

def test_comparison():
    """Test comparison between yfinance and NASDAQ"""
    print("=" * 80)
    print("YFINANCE vs NASDAQ EVENT DETECTION COMPARISON")
    print("=" * 80)
    print()
    
    # Test with multiple tickers and date ranges
    # Including tickers from the user's stock list and known problematic cases
    test_cases = [
        {
            'ticker': 'AAPL',
            'start_date': datetime(2024, 12, 1, tzinfo=timezone.utc),
            'end_date': datetime(2024, 12, 31, tzinfo=timezone.utc),
            'description': 'AAPL - Dec 2024 (recent past, tech stock)'
        },
        {
            'ticker': 'MSFT',
            'start_date': datetime(2024, 10, 1, tzinfo=timezone.utc),
            'end_date': datetime(2024, 12, 31, tzinfo=timezone.utc),
            'description': 'MSFT - Q4 2024 (3 months, tech stock)'
        },
        {
            'ticker': 'JPM',
            'start_date': datetime(2024, 9, 1, tzinfo=timezone.utc),
            'end_date': datetime(2024, 12, 31, tzinfo=timezone.utc),
            'description': 'JPM - Q4 2024 (bank with regular dividends)'
        },
        {
            'ticker': 'SRE',
            'start_date': datetime(2024, 12, 1, tzinfo=timezone.utc),
            'end_date': datetime(2024, 12, 31, tzinfo=timezone.utc),
            'description': 'SRE - Dec 2024 (known dividend issue - Dec 11, 2024)'
        },
        {
            'ticker': 'KO',
            'start_date': datetime(2024, 9, 1, tzinfo=timezone.utc),
            'end_date': datetime(2024, 12, 31, tzinfo=timezone.utc),
            'description': 'KO - Q4 2024 (regular dividend payer)'
        },
        {
            'ticker': 'APD',
            'start_date': datetime(2024, 9, 23, tzinfo=timezone.utc),
            'end_date': datetime(2024, 10, 30, tzinfo=timezone.utc),
            'description': 'APD - Sep-Oct 2024 (previously tested, no events found)'
        },
        {
            'ticker': 'RIVN',
            'start_date': datetime(2024, 12, 1, tzinfo=timezone.utc),
            'end_date': datetime(2024, 12, 31, tzinfo=timezone.utc),
            'description': 'RIVN - Dec 2024 (from user stock list)'
        },
        {
            'ticker': 'LVS',
            'start_date': datetime(2024, 12, 1, tzinfo=timezone.utc),
            'end_date': datetime(2024, 12, 31, tzinfo=timezone.utc),
            'description': 'LVS - Dec 2024 (casino/resort from user list)'
        },
        {
            'ticker': 'MGM',
            'start_date': datetime(2024, 12, 1, tzinfo=timezone.utc),
            'end_date': datetime(2024, 12, 31, tzinfo=timezone.utc),
            'description': 'MGM - Dec 2024 (casino/resort from user list)'
        },
        {
            'ticker': 'WMT',
            'start_date': datetime(2024, 10, 1, tzinfo=timezone.utc),
            'end_date': datetime(2024, 12, 31, tzinfo=timezone.utc),
            'description': 'WMT - Q4 2024 (retail, regular dividends)'
        }
    ]
    
    all_comparisons = []
    
    for i, test_case in enumerate(test_cases, 1):
        ticker = test_case['ticker']
        start_date = test_case['start_date']
        end_date = test_case['end_date']
        description = test_case['description']
        
        print(f"Test Case {i}: {description}")
        print("-" * 80)
        print(f"Ticker: {ticker}")
        print(f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print()
        
        # Fetch from yfinance
        print(f"Fetching events from yfinance...")
        yfinance_events = fetch_events_yfinance(ticker, start_date, end_date)
        if 'error' in yfinance_events:
            print(f"  ❌ Error: {yfinance_events['error']}")
        else:
            print(f"  ✅ Found {yfinance_events['total']} events ({len(yfinance_events['earnings'])} earnings, {len(yfinance_events['dividends'])} dividends)")
        
        # Fetch from NASDAQ
        print(f"Fetching events from NASDAQ...")
        nasdaq_events = fetch_events_nasdaq(ticker, start_date, end_date)
        if 'error' in nasdaq_events:
            print(f"  ❌ Error: {nasdaq_events['error']}")
        else:
            print(f"  ✅ Found {nasdaq_events['total']} events ({len(nasdaq_events['earnings'])} earnings, {len(nasdaq_events['dividends'])} dividends)")
        
        print()
        
        # Compare
        comparison = compare_events(yfinance_events, nasdaq_events, ticker)
        all_comparisons.append(comparison)
        
        # Display comparison
        print("Comparison Results:")
        print(f"  yfinance: {comparison['yfinance_total']} events ({comparison['yfinance_earnings']} earnings, {comparison['yfinance_dividends']} dividends)")
        print(f"  NASDAQ:   {comparison['nasdaq_total']} events ({comparison['nasdaq_earnings']} earnings, {comparison['nasdaq_dividends']} dividends)")
        print(f"  Common:   {len(comparison['common'])} events")
        print(f"  yfinance only: {len(comparison['yfinance_only'])} events")
        print(f"  NASDAQ only:   {len(comparison['nasdaq_only'])} events")
        
        if comparison['yfinance_only']:
            print()
            print("  Events found by yfinance but NOT by NASDAQ:")
            for event in comparison['yfinance_only']:
                print(f"    - {event['date']}: {event['name']} ({event['type']})")
        
        if comparison['nasdaq_only']:
            print()
            print("  ⚠️  CRITICAL: Events found by NASDAQ but NOT by yfinance:")
            for event in comparison['nasdaq_only']:
                print(f"    - {event['date']}: {event['name']} ({event['type']})")
                if 'description' in event:
                    print(f"      Description: {event['description']}")
        
        # Verdict
        verdict_map = {
            'yfinance_better': '✅ yfinance finds MORE events',
            'yfinance_same': '✅ yfinance finds SAME events',
            'yfinance_good_enough': '⚠️  yfinance finds most events (good enough)',
            'yfinance_worse': '❌ yfinance finds FEWER events (may miss important events)'
        }
        print()
        print(f"  Verdict: {verdict_map.get(comparison['verdict'], comparison['verdict'])}")
        print()
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    total_yfinance = sum(c['yfinance_total'] for c in all_comparisons)
    total_nasdaq = sum(c['nasdaq_total'] for c in all_comparisons)
    total_common = sum(len(c['common']) for c in all_comparisons)
    total_yf_only = sum(len(c['yfinance_only']) for c in all_comparisons)
    total_nasdaq_only = sum(len(c['nasdaq_only']) for c in all_comparisons)
    
    print(f"Total Events Found:")
    print(f"  yfinance: {total_yfinance} events")
    print(f"  NASDAQ:   {total_nasdaq} events")
    print(f"  Common:   {total_common} events")
    print(f"  yfinance only: {total_yf_only} events")
    print(f"  NASDAQ only:   {total_nasdaq_only} events")
    print()
    
    # Overall verdict
    print("=" * 80)
    print("OVERALL VERDICT")
    print("=" * 80)
    print()
    
    if total_yfinance > total_nasdaq:
        print("✅ OVERALL: yfinance finds MORE events overall")
        print(f"   yfinance: {total_yfinance} events, NASDAQ: {total_nasdaq} events")
        print("   Recommendation: yfinance is BETTER - can replace NASDAQ")
    elif total_yfinance == total_nasdaq and total_nasdaq_only == 0:
        print("✅ OVERALL: yfinance finds SAME events as NASDAQ")
        print(f"   Both found: {total_yfinance} events")
        print("   Recommendation: yfinance is EQUIVALENT - can replace NASDAQ")
    elif total_nasdaq_only <= total_yfinance * 0.1:  # NASDAQ finds <10% more
        print("⚠️  OVERALL: yfinance finds most events (misses <10% compared to NASDAQ)")
        print(f"   yfinance: {total_yfinance} events, NASDAQ: {total_nasdaq} events")
        print(f"   Missed: {total_nasdaq_only} events ({total_nasdaq_only/total_nasdaq*100:.1f}%)")
        print("   Recommendation: yfinance is GOOD ENOUGH - can replace NASDAQ")
    else:
        print("❌ OVERALL: yfinance finds FEWER events (misses >10% compared to NASDAQ)")
        print(f"   yfinance: {total_yfinance} events, NASDAQ: {total_nasdaq} events")
        print(f"   Missed: {total_nasdaq_only} events ({total_nasdaq_only/total_nasdaq*100:.1f}%)")
        print("   Recommendation: yfinance may MISS important events - consider keeping NASDAQ")
        print()
        print("   ⚠️  CRITICAL: Review the 'NASDAQ only' events above to determine")
        print("      if they are important enough to keep NASDAQ as a fallback")
    
    print()
    
    # Breakdown by type
    total_yf_earnings = sum(c['yfinance_earnings'] for c in all_comparisons)
    total_nasdaq_earnings = sum(c['nasdaq_earnings'] for c in all_comparisons)
    total_yf_dividends = sum(c['yfinance_dividends'] for c in all_comparisons)
    total_nasdaq_dividends = sum(c['nasdaq_dividends'] for c in all_comparisons)
    
    print("Breakdown by Event Type:")
    print(f"  Earnings:")
    print(f"    yfinance: {total_yf_earnings}")
    print(f"    NASDAQ:   {total_nasdaq_earnings}")
    print(f"  Dividends:")
    print(f"    yfinance: {total_yf_dividends}")
    print(f"    NASDAQ:   {total_nasdaq_dividends}")
    print()
    
    # Detailed analysis of missed events
    if total_nasdaq_only > 0:
        print("=" * 80)
        print("DETAILED ANALYSIS: Events Missed by yfinance")
        print("=" * 80)
        print()
        
        missed_by_ticker = {}
        for comp in all_comparisons:
            if comp['nasdaq_only']:
                missed_by_ticker[comp['ticker']] = comp['nasdaq_only']
        
        if missed_by_ticker:
            print(f"Total tickers with missed events: {len(missed_by_ticker)}")
            print()
            for ticker, events in missed_by_ticker.items():
                print(f"{ticker}: {len(events)} missed event(s)")
                for event in events:
                    print(f"  - {event['date']}: {event.get('name', 'N/A')} ({event.get('type', 'N/A')})")
                    if 'description' in event:
                        print(f"    {event['description']}")
                print()
            
            # Check for SRE specific issue
            if 'SRE' in missed_by_ticker:
                sre_events = missed_by_ticker['SRE']
                dec_11_events = [e for e in sre_events if '2024-12-11' in e.get('date', '')]
                if dec_11_events:
                    print("⚠️  CRITICAL: SRE dividend on Dec 11, 2024 was MISSED by yfinance!")
                    print("   This is the known issue that was previously identified.")
                    print()
        print()
    
    return all_comparisons

if __name__ == "__main__":
    print()
    comparisons = test_comparison()
    print()
    
    # Exit code based on overall verdict
    total_yfinance = sum(c['yfinance_total'] for c in comparisons)
    total_nasdaq = sum(c['nasdaq_total'] for c in comparisons)
    total_nasdaq_only = sum(len(c['nasdaq_only']) for c in comparisons)
    
    if total_yfinance >= total_nasdaq or total_nasdaq_only <= total_yfinance * 0.1:
        print("=" * 80)
        print("✅ TEST PASSED: yfinance is good enough to replace NASDAQ")
        print("=" * 80)
        sys.exit(0)
    else:
        print("=" * 80)
        print("❌ TEST FAILED: yfinance may miss important events")
        print("=" * 80)
        sys.exit(1)

