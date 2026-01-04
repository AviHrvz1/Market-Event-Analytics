#!/usr/bin/env python3
"""
Unit test to check if yfinance can find tickers that Prixe.io cannot find
Compares Prixe.io API vs yfinance for tickers that return 404 from Prixe.io
"""

import sys
import requests
from datetime import datetime, timedelta, timezone
from main import LayoffTracker
from config import PRIXE_API_KEY, PRIXE_BASE_URL, PRIXE_PRICE_ENDPOINT

# Test tickers that are failing in Prixe.io
TEST_TICKERS = ['GILD', 'NCOX', 'PLTN', 'IMMU', 'NMTR']

def test_prixe_api(ticker):
    """Test if Prixe.io API can find the ticker"""
    try:
        url = f"{PRIXE_BASE_URL}{PRIXE_PRICE_ENDPOINT}"
        headers = {
            'X-API-Key': PRIXE_API_KEY,
            'Content-Type': 'application/json'
        }
        
        # Get data for today
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=5)
        
        params = {
            'ticker': ticker,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'interval': '1d'
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data and 'data' in data and len(data['data']) > 0:
                return True, "Success", data
            else:
                return False, "No data returned", None
        elif response.status_code == 404:
            return False, "404 - Endpoint not found", None
        else:
            return False, f"Status {response.status_code}: {response.text[:100]}", None
            
    except Exception as e:
        return False, f"Error: {str(e)[:100]}", None

def test_yfinance(ticker):
    """Test if yfinance can find the ticker"""
    try:
        import yfinance as yf
        
        # Try to get ticker info
        stock = yf.Ticker(ticker)
        
        # Get basic info
        info = stock.info
        
        if info and len(info) > 0:
            # Try to get historical data
            hist = stock.history(period="5d")
            
            if hist is not None and len(hist) > 0:
                return True, "Success", {
                    'info': info,
                    'history': hist.to_dict() if hasattr(hist, 'to_dict') else str(hist),
                    'last_price': hist['Close'].iloc[-1] if 'Close' in hist.columns else None
                }
            else:
                return False, "No historical data", {'info': info}
        else:
            return False, "No info available", None
            
    except ImportError:
        return False, "yfinance not installed", None
    except Exception as e:
        return False, f"Error: {str(e)[:100]}", None

def test_prixe_vs_yfinance():
    """Compare Prixe.io vs yfinance for failing tickers"""
    
    print("=" * 80)
    print("PRIXE.IO vs YFINANCE COMPARISON TEST")
    print("=" * 80)
    print()
    print(f"Testing tickers that are failing in Prixe.io: {', '.join(TEST_TICKERS)}")
    print()
    
    results = []
    
    for ticker in TEST_TICKERS:
        print(f"Testing ticker: {ticker}")
        print("-" * 80)
        
        # Test Prixe.io
        print("  Prixe.io API:")
        prixe_success, prixe_msg, prixe_data = test_prixe_api(ticker)
        if prixe_success:
            print(f"    ✅ SUCCESS: {prixe_msg}")
            if prixe_data:
                print(f"    Data points: {len(prixe_data.get('data', []))}")
        else:
            print(f"    ❌ FAILED: {prixe_msg}")
        
        # Test yfinance
        print("  yfinance:")
        yf_success, yf_msg, yf_data = test_yfinance(ticker)
        if yf_success:
            print(f"    ✅ SUCCESS: {yf_msg}")
            if yf_data:
                if 'last_price' in yf_data and yf_data['last_price']:
                    print(f"    Last price: ${yf_data['last_price']:.2f}")
                if 'info' in yf_data:
                    company_name = yf_data['info'].get('longName') or yf_data['info'].get('shortName', 'N/A')
                    print(f"    Company: {company_name}")
        else:
            print(f"    ❌ FAILED: {yf_msg}")
        
        results.append({
            'ticker': ticker,
            'prixe_success': prixe_success,
            'prixe_msg': prixe_msg,
            'yfinance_success': yf_success,
            'yfinance_msg': yf_msg,
            'yfinance_data': yf_data
        })
        
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    print("Comparison Results:")
    print()
    
    prixe_available = sum(1 for r in results if r['prixe_success'])
    yfinance_available = sum(1 for r in results if r['yfinance_success'])
    
    print(f"Prixe.io: {prixe_available}/{len(TEST_TICKERS)} tickers available")
    print(f"yfinance: {yfinance_available}/{len(TEST_TICKERS)} tickers available")
    print()
    
    print("Detailed Results:")
    print()
    
    for result in results:
        ticker = result['ticker']
        prixe_status = "✅" if result['prixe_success'] else "❌"
        yf_status = "✅" if result['yfinance_success'] else "❌"
        
        print(f"{ticker}:")
        print(f"  Prixe.io: {prixe_status} {result['prixe_msg']}")
        print(f"  yfinance: {yf_status} {result['yfinance_msg']}")
        
        if result['yfinance_success'] and result['yfinance_data']:
            if 'info' in result['yfinance_data']:
                info = result['yfinance_data']['info']
                company = info.get('longName') or info.get('shortName', 'N/A')
                market_cap = info.get('marketCap', 'N/A')
                print(f"    Company: {company}")
                if market_cap != 'N/A':
                    print(f"    Market Cap: ${market_cap:,.0f}")
        
        print()
    
    # Recommendations
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()
    
    yfinance_only = [r for r in results if not r['prixe_success'] and r['yfinance_success']]
    both_fail = [r for r in results if not r['prixe_success'] and not r['yfinance_success']]
    both_success = [r for r in results if r['prixe_success'] and r['yfinance_success']]
    
    if yfinance_only:
        print(f"✅ {len(yfinance_only)} tickers available in yfinance but NOT in Prixe.io:")
        for r in yfinance_only:
            print(f"   - {r['ticker']} (can use yfinance as fallback)")
        print()
    
    if both_fail:
        print(f"❌ {len(both_fail)} tickers NOT available in either service:")
        for r in both_fail:
            print(f"   - {r['ticker']}")
        print()
    
    if both_success:
        print(f"✅ {len(both_success)} tickers available in BOTH services:")
        for r in both_success:
            print(f"   - {r['ticker']}")
        print()
    
    print("Conclusion:")
    if yfinance_only:
        print(f"  ✅ yfinance can provide data for {len(yfinance_only)} tickers that Prixe.io cannot")
        print("  💡 Consider using yfinance as fallback for these tickers")
    else:
        print("  ⚠️  yfinance cannot provide data for tickers that Prixe.io cannot find")
    
    return True

if __name__ == '__main__':
    success = test_prixe_vs_yfinance()
    sys.exit(0 if success else 1)

